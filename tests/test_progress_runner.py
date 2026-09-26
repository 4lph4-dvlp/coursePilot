"""Integration and unit tests for progress pipeline runner, atomic cache, and course error isolation."""

from datetime import datetime, timedelta
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from kau_assistant.progress.calculator import SectionMeta
from kau_assistant.progress.models import (
    SCHEMA_VERSION,
    ActivityBreakdown,
    CourseProgress,
    DashboardSummary,
    ProgressReport,
)
from kau_assistant.progress.runner import (
    CACHE_TTL_SECONDS,
    extract_course_sections_meta,
    load_progress_cache,
    run_progress_pipeline,
    save_progress_cache,
)
from kau_assistant.scraper.date_parser import KST
from kau_assistant.scraper.models import CourseItem


def _sample_report(generated_at: datetime) -> ProgressReport:
    summary = DashboardSummary(
        total_courses=1,
        current_open_rate=100.0,
        current_open_completed=5,
        current_open_total=5,
        past_weeks_rate=100.0,
        past_weeks_completed=5,
        past_weeks_total=5,
        semester_overall_rate=50.0,
        semester_completed=5,
        semester_total=10,
        missed_past_count=0,
        current_week_todo_count=0,
        activity_totals=ActivityBreakdown(),
    )
    course = CourseProgress(
        course_id="101",
        course_name="자료구조",
        course_abbr="자구",
        current_week=2,
        current_open_rate=100.0,
        current_open_completed=5,
        current_open_total=5,
        past_weeks_rate=100.0,
        past_weeks_completed=5,
        past_weeks_total=5,
        semester_overall_rate=50.0,
        semester_completed=5,
        semester_total=10,
        activity_breakdown=ActivityBreakdown(),
        status="ok",
    )
    return ProgressReport(
        schema_version=SCHEMA_VERSION,
        command="progress",
        status="success",
        generated_at=generated_at,
        is_cached=False,
        summary=summary,
        courses=[course],
    )


def test_load_save_progress_cache(tmp_path: Path):
    cache_path = tmp_path / "progress_cache.json"
    now = datetime(2026, 9, 26, 12, 0, tzinfo=KST)
    report = _sample_report(now)

    save_progress_cache(cache_path, report)
    assert cache_path.exists()

    loaded = load_progress_cache(cache_path, max_age_seconds=600, now=now)
    assert loaded is not None
    assert loaded.is_cached is True
    assert loaded.summary.total_courses == 1
    assert loaded.courses[0].course_abbr == "자구"


def test_progress_cache_ttl_expiration(tmp_path: Path):
    cache_path = tmp_path / "progress_cache.json"
    old_time = datetime(2026, 9, 26, 12, 0, tzinfo=KST)
    report = _sample_report(old_time)

    save_progress_cache(cache_path, report)

    # 601 seconds later -> expired
    now_later = old_time + timedelta(seconds=601)
    loaded = load_progress_cache(cache_path, max_age_seconds=600, now=now_later)
    assert loaded is None


def test_progress_cache_corrupted_json(tmp_path: Path):
    cache_path = tmp_path / "corrupted_cache.json"
    cache_path.write_text("{invalid json", encoding="utf-8")

    loaded = load_progress_cache(cache_path, max_age_seconds=600)
    assert loaded is None


def test_extract_course_sections_meta():
    fixture_path = Path(__file__).parent / "fixtures" / "lxp_course_home.html"
    html_content = fixture_path.read_text(encoding="utf-8")

    sections = extract_course_sections_meta(html_content)
    assert len(sections) >= 4

    # Section 0: 강의 개요
    s0 = sections[0]
    assert s0.week_number == 0
    assert "강의 개요" in s0.title

    # Section 1: 1주차 with dates 2026-09-01 ~ 2026-09-07
    s1 = sections[1]
    assert s1.week_number == 1
    assert s1.start_date == datetime(2026, 9, 1, 0, 0, tzinfo=KST)
    assert s1.end_date == datetime(2026, 9, 7, 23, 59, 59, tzinfo=KST)


@patch("kau_assistant.progress.runner.SessionManager")
@patch("kau_assistant.progress.runner.get_authenticated_httpx_client")
def test_progress_runner_course_error_isolation(mock_get_client, mock_session_mgr_cls, tmp_path: Path):
    mock_settings = MagicMock()
    mock_settings.session_cache_path = tmp_path / "session.json"
    mock_settings.lms_url = "https://canvas.kau.ac.kr"

    mock_page = MagicMock()
    mock_sm = MagicMock()
    mock_sm.__enter__.return_value = mock_sm
    mock_sm.get_authenticated_page.return_value = mock_page
    mock_session_mgr_cls.return_value = mock_sm

    c1 = CourseItem(course_id="101", raw_name="알고리즘", clean_name="알고리즘", url="https://canvas.kau.ac.kr/c/101")
    c2 = CourseItem(course_id="102", raw_name="자료구조", clean_name="자료구조", url="https://canvas.kau.ac.kr/c/102")

    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    with patch("kau_assistant.progress.runner.extract_courses", return_value=[c1, c2]):
        with patch("kau_assistant.progress.runner._collect_single_course_progress") as mock_collect:
            # Course 1 raises exception (network failure)
            # Course 2 succeeds
            mock_collect.side_effect = [
                RuntimeError("Connection timeout 504"),
                CourseProgress(
                    course_id="102",
                    course_name="자료구조",
                    course_abbr="자구",
                    current_week=2,
                    current_open_rate=100.0,
                    current_open_completed=4,
                    current_open_total=4,
                    past_weeks_rate=100.0,
                    past_weeks_completed=4,
                    past_weeks_total=4,
                    semester_overall_rate=50.0,
                    semester_completed=4,
                    semester_total=8,
                    activity_breakdown=ActivityBreakdown(),
                    status="ok",
                ),
            ]

            report = run_progress_pipeline(settings=mock_settings)

            assert report.status == "partial_success"
            assert len(report.courses) == 2
            assert report.courses[0].status == "error"
            assert "Connection timeout 504" in (report.courses[0].error_message or "")
            assert report.courses[1].status == "ok"
            assert len(report.errors) == 1
            assert report.errors[0].course_id == "101"


@patch("kau_assistant.progress.runner.SessionManager")
@patch("kau_assistant.progress.runner.get_authenticated_httpx_client")
def test_progress_runner_cached_and_refresh_flags(mock_get_client, mock_session_mgr_cls, tmp_path: Path):
    mock_settings = MagicMock()
    cache_file = tmp_path / "progress_cache.json"
    mock_settings.session_cache_path = tmp_path / "session.json"
    mock_settings.lms_url = "https://canvas.kau.ac.kr"

    now = datetime(2026, 9, 26, 12, 0, tzinfo=KST)
    saved_report = _sample_report(now)
    save_progress_cache(cache_file, saved_report)

    # 1. cached=True -> Returns cached report immediately without opening SessionManager
    cached_res = run_progress_pipeline(cached=True, refresh=False, settings=mock_settings, now=now)
    assert cached_res.is_cached is True
    assert mock_session_mgr_cls.call_count == 0

    # 2. refresh=True -> Ignores cache and executes session collection
    mock_page = MagicMock()
    mock_sm = MagicMock()
    mock_sm.__enter__.return_value = mock_sm
    mock_sm.get_authenticated_page.return_value = mock_page
    mock_session_mgr_cls.return_value = mock_sm

    c1 = CourseItem(course_id="101", raw_name="알고리즘", clean_name="알고리즘", url="https://canvas.kau.ac.kr/c/101")
    with patch("kau_assistant.progress.runner.extract_courses", return_value=[c1]):
        with patch("kau_assistant.progress.runner._collect_single_course_progress") as mock_collect:
            mock_collect.return_value = CourseProgress(
                course_id="101",
                course_name="알고리즘",
                course_abbr="알고",
                current_week=1,
                current_open_rate=100.0,
                current_open_completed=2,
                current_open_total=2,
                past_weeks_rate=100.0,
                past_weeks_completed=0,
                past_weeks_total=0,
                semester_overall_rate=20.0,
                semester_completed=2,
                semester_total=10,
                activity_breakdown=ActivityBreakdown(),
                status="ok",
            )
            refresh_res = run_progress_pipeline(cached=True, refresh=True, settings=mock_settings, now=now)
            assert refresh_res.is_cached is False
            assert mock_session_mgr_cls.call_count == 1
