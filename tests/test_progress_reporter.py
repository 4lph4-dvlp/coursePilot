"""Unit tests for Rich terminal progress dashboard, styling, To-Do ordering, and alerts."""

from datetime import datetime
import io
from rich.console import Console
import pytest

from coursepilot.progress.models import (
    SCHEMA_VERSION,
    ActivityBreakdown,
    ActivityCount,
    ActivityItem,
    ActivityType,
    CourseProgress,
    DashboardSummary,
    ProgressReport,
)
from coursepilot.progress.reporter import (
    _get_rate_style,
    render_course_matrix,
    render_detailed_activities,
    render_progress_dashboard,
)
from coursepilot.scraper.date_parser import KST


def _create_test_report(missed_items_count: int = 0) -> ProgressReport:
    now = datetime(2026, 9, 26, 12, 0, tzinfo=KST)
    due_date = datetime(2026, 9, 26, 23, 59, tzinfo=KST)

    items = [
        ActivityItem(
            course_id="101",
            activity_type=ActivityType.ASSIGNMENT,
            week_number=3,
            title="3주차 실습 과제",
            is_completed=False,
            due_date=due_date,
            raw_due_date="2026-09-26 23:59",
            is_urgent=True,
        ),
        ActivityItem(
            course_id="101",
            activity_type=ActivityType.VOD,
            week_number=3,
            title="3주차 1차시 영상",
            is_completed=True,
            raw_due_date="2026-09-26 23:59",
        ),
    ]

    missed = []
    if missed_items_count > 0:
        missed.append(
            ActivityItem(
                course_id="101",
                activity_type=ActivityType.QUIZ,
                week_number=2,
                title="2주차 복습 퀴즈",
                is_completed=False,
                raw_due_date="2026-09-19 23:59",
                is_overdue=True,
            )
        )

    course = CourseProgress(
        course_id="101",
        course_name="자료구조(01분반)",
        course_abbr="자구",
        current_week=3,
        current_open_rate=80.0,
        current_open_completed=4,
        current_open_total=5,
        past_weeks_rate=75.0 if missed else 100.0,
        past_weeks_completed=3 if missed else 4,
        past_weeks_total=4,
        semester_overall_rate=40.0,
        semester_completed=4,
        semester_total=10,
        activity_breakdown=ActivityBreakdown(
            vod=ActivityCount(completed=2, total=2, rate=100.0),
            assignment=ActivityCount(completed=0, total=1, rate=0.0),
            quiz=ActivityCount(completed=1, total=1, rate=100.0),
            material=ActivityCount(completed=1, total=1, rate=100.0),
        ),
        current_week_items=items,
        missed_past_items=missed,
        all_items=items + missed,
        status="ok",
    )

    summary = DashboardSummary(
        total_courses=1,
        current_open_rate=course.current_open_rate,
        current_open_completed=course.current_open_completed,
        current_open_total=course.current_open_total,
        past_weeks_rate=course.past_weeks_rate,
        past_weeks_completed=course.past_weeks_completed,
        past_weeks_total=course.past_weeks_total,
        semester_overall_rate=course.semester_overall_rate,
        semester_completed=course.semester_completed,
        semester_total=course.semester_total,
        missed_past_count=len(missed),
        current_week_todo_count=1,
        activity_totals=course.activity_breakdown,
    )

    return ProgressReport(
        schema_version=SCHEMA_VERSION,
        command="progress",
        status="success",
        generated_at=now,
        is_cached=False,
        summary=summary,
        courses=[course],
    )


def test_rate_color_styles():
    assert _get_rate_style(100.0) == "bold green"
    assert _get_rate_style(85.5) == "bold blue"
    assert _get_rate_style(65.0) == "bold yellow"
    assert _get_rate_style(45.0) == "bold red"


def test_render_progress_dashboard_sections():
    report = _create_test_report(missed_items_count=0)
    buf = io.StringIO()
    console = Console(file=buf, width=120, force_terminal=True, color_system="standard")

    render_progress_dashboard(report, console)
    output = buf.getvalue()

    # Section 1 Header
    assert "학습활동 종합 진척도 현황" in output
    assert "자료구조" in output
    # Section 2 Header
    assert "이번 주차 주요 점검 항목" in output
    assert "To-Do 우선" in output
    # Section 3 Header (All Clear)
    assert "All Clear" in output


def test_render_todo_prioritization_and_tags():
    report = _create_test_report(missed_items_count=0)
    buf = io.StringIO()
    console = Console(file=buf, width=120, force_terminal=True, color_system="standard")

    render_progress_dashboard(report, console)
    output = buf.getvalue()

    # Incomplete assignment should appear before completed VOD
    todo_idx = output.find("3주차 실습 과제")
    done_idx = output.find("3주차 1차시 영상")
    assert todo_idx != -1
    assert done_idx != -1
    assert todo_idx < done_idx

    # Tags check
    assert "[과제]" in output
    assert "[VOD]" in output


def test_render_alert_panel_when_missed_items():
    report = _create_test_report(missed_items_count=1)
    buf = io.StringIO()
    console = Console(file=buf, width=120, force_terminal=True, color_system="standard")

    render_progress_dashboard(report, console)
    output = buf.getvalue()

    assert "과거 주차 누락/결석 경고 (1건)" in output
    assert "2주차 복습 퀴즈" in output


def test_render_all_clear_panel_when_zero_missed():
    report = _create_test_report(missed_items_count=0)
    buf = io.StringIO()
    console = Console(file=buf, width=120, force_terminal=True, color_system="standard")

    render_progress_dashboard(report, console)
    output = buf.getvalue()

    assert "All Clear - 과거 주차 누락 없음" in output
    assert "모든 필수 활동" in output


def test_render_course_matrix():
    report = _create_test_report(missed_items_count=0)
    course = report.courses[0]
    buf = io.StringIO()
    console = Console(file=buf, width=120, force_terminal=True, color_system="standard")

    render_course_matrix(course, console, week_filter=3)
    output = buf.getvalue()

    assert "학습활동 로드맵" in output
    assert "3주차" in output
    assert "VOD 현황" in output
    assert "과제 현황" in output


def test_render_detailed_activities():
    report = _create_test_report(missed_items_count=0)
    buf = io.StringIO()
    console = Console(file=buf, width=120, force_terminal=True, color_system="standard")

    render_detailed_activities(report, console)
    output = buf.getvalue()

    assert "전체 과목 세부 활동 내역" in output
    assert "3주차 실습 과제" in output
