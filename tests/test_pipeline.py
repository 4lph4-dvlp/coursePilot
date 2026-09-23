"""Pipeline resilience: per-course isolation, fatal-stage classification, progress,
relogin/headed forwarding, mappings, zero-course handling, and read-only scraping (05-02).
"""

import json
import logging
from datetime import datetime, timedelta

import pytest
from click.testing import CliRunner

import kau_assistant.pipeline as pipeline
from kau_assistant.cli import cli
from kau_assistant.exceptions import AuthenticationError, ConfigError, CourseAccessDeniedError
from kau_assistant.pipeline import collect_tasks
from kau_assistant.scraper.date_parser import KST
from kau_assistant.scraper.models import AttendanceStatus, CourseItem, LectureItem

NOW = datetime(2026, 9, 23, 12, 0, tzinfo=KST)


class FakePage:
    """Placeholder page object returned by FakeSession — real interactions are monkeypatched away."""


class FakeSession:
    """Fake SessionManager context manager standing in for the real Playwright-backed one."""

    def __init__(self, *, settings, headful=False):
        self.settings = settings
        self.headful = headful

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def get_authenticated_page(self):
        return FakePage()


def _course(course_id: str, name: str) -> CourseItem:
    return CourseItem(
        course_id=course_id,
        raw_name=name,
        clean_name=name,
        url=f"https://lms.kau.ac.kr/course/view.php?id={course_id}",
    )


def _lecture(course_id: str, days_from_now: int = 3) -> LectureItem:
    return LectureItem(
        course_id=course_id,
        week_number=1,
        clip_number=1,
        title="샘플 강의",
        full_title="[과목] 1주차 1차시: 샘플 강의",
        status=AttendanceStatus.INCOMPLETE,
        due_date=NOW + timedelta(days=days_from_now),
    )


def test_course_failure_is_isolated(monkeypatch, sample_settings):
    """One course raising CourseAccessDeniedError does not stop collection of the others (D-08)."""
    courses = [_course("c1", "과목1"), _course("c2", "과목2"), _course("c3", "과목3")]

    monkeypatch.setattr(pipeline, "SessionManager", FakeSession)
    monkeypatch.setattr(pipeline, "extract_courses", lambda page, lms_url: courses)

    def _fake_scrape_course(page, course, navigator):
        if course.course_id == "c2":
            raise CourseAccessDeniedError(
                f"course access denied for user {sample_settings.lms_username}"
            )
        return [_lecture(course.course_id)], []

    monkeypatch.setattr(pipeline, "scrape_course", _fake_scrape_course)

    result = collect_tasks(sample_settings, now=NOW)

    task_course_ids = {t.course_id for t in result.tasks}
    assert "c1" in task_course_ids
    assert "c3" in task_course_ids
    assert "c2" not in task_course_ids

    assert len(result.errors) == 1
    error = result.errors[0]
    assert error.scope == "course"
    assert error.course_id == "c2"
    assert error.course_name == "과목2"
    assert sample_settings.lms_username not in error.message


def test_exit_code_one_end_to_end_course_failure(monkeypatch, sample_settings):
    """The real CLI `check --json` exits 1 when the real pipeline reports one course error."""
    courses = [_course("c1", "과목1"), _course("c2", "과목2"), _course("c3", "과목3")]

    monkeypatch.setattr("kau_assistant.cli.get_settings", lambda: sample_settings)
    monkeypatch.setattr(pipeline, "SessionManager", FakeSession)
    monkeypatch.setattr(pipeline, "extract_courses", lambda page, lms_url: courses)

    def _fake_scrape_course(page, course, navigator):
        if course.course_id == "c2":
            raise CourseAccessDeniedError(f"denied for {sample_settings.lms_username}")
        return [_lecture(course.course_id)], []

    monkeypatch.setattr(pipeline, "scrape_course", _fake_scrape_course)

    runner = CliRunner()
    result = runner.invoke(cli, ["check", "--json"])

    assert result.exit_code == 1, result.output
    payload = json.loads(result.stdout)
    assert payload["summary"]["error_count"] == 1
    assert payload["errors"][0]["scope"] == "course"

    remaining_course_ids = {
        group["course_id"] for section in payload["items"].values() for group in section
    }
    assert "c1" in remaining_course_ids
    assert "c3" in remaining_course_ids
    assert "c2" not in remaining_course_ids

    assert sample_settings.lms_username not in result.stdout
    assert sample_settings.lms_password not in result.stdout
    assert sample_settings.lms_username not in result.stderr
    assert sample_settings.lms_password not in result.stderr


# --- Task 2: fatal-stage classification, LMS settings validation, progress order,
# relogin/headed forwarding, mappings, zero-course handling ---


def test_exit_code_config_error_before_browser(sample_settings):
    """Missing LMS_USERNAME/LMS_PASSWORD aborts before any session factory is constructed (D-18)."""
    settings = sample_settings.model_copy(update={"lms_username": "", "lms_password": ""})

    factory_calls: list[int] = []

    def _tracking_factory(*, settings, headful=False):
        factory_calls.append(1)
        raise AssertionError("session factory must never be constructed")

    with pytest.raises(ConfigError) as exc_info:
        collect_tasks(settings, session_factory=_tracking_factory)

    message = str(exc_info.value)
    assert "LMS_USERNAME" in message
    assert "LMS_PASSWORD" in message
    assert not factory_calls


def test_exit_code_login_failure_propagates(monkeypatch, sample_settings):
    """A login failure inside get_authenticated_page() propagates, not converted to a course error."""

    class FailingSession(FakeSession):
        def get_authenticated_page(self):
            raise AuthenticationError("login failed")

    monkeypatch.setattr(pipeline, "SessionManager", FailingSession)

    with pytest.raises(AuthenticationError):
        collect_tasks(sample_settings, now=NOW)


def test_exit_code_course_list_failure_propagates(monkeypatch, sample_settings):
    """A course-list failure propagates fatally instead of being isolated like a per-course error."""
    monkeypatch.setattr(pipeline, "SessionManager", FakeSession)

    def _raise_extract_courses(page, lms_url):
        raise RuntimeError("course list failed")

    monkeypatch.setattr(pipeline, "extract_courses", _raise_extract_courses)

    with pytest.raises(RuntimeError):
        collect_tasks(sample_settings, now=NOW)


def test_stderr_progress_once_per_course_in_order(monkeypatch, sample_settings):
    """progress(index, total, name) fires exactly once per course, in order, before scraping (D-11)."""
    courses = [_course("c1", "과목1"), _course("c2", "과목2"), _course("c3", "과목3")]

    monkeypatch.setattr(pipeline, "SessionManager", FakeSession)
    monkeypatch.setattr(pipeline, "extract_courses", lambda page, lms_url: courses)

    def _fake_scrape_course(page, course, navigator):
        if course.course_id == "c2":
            raise CourseAccessDeniedError("denied")
        return [_lecture(course.course_id)], []

    monkeypatch.setattr(pipeline, "scrape_course", _fake_scrape_course)

    calls: list[tuple[int, int, str]] = []

    def _progress(index, total, name):
        calls.append((index, total, name))

    collect_tasks(sample_settings, progress=_progress, now=NOW)

    assert calls == [(1, 3, "과목1"), (2, 3, "과목2"), (3, 3, "과목3")]


def test_relogin_deletes_only_session_cache(monkeypatch, sample_settings, tmp_path):
    """relogin=True deletes only the session cache file; relogin=False leaves it untouched (D-10)."""
    sample_settings.session_cache_path.write_text("{}", encoding="utf-8")
    sibling = tmp_path / "sibling.json"
    sibling.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(pipeline, "SessionManager", FakeSession)
    monkeypatch.setattr(pipeline, "extract_courses", lambda page, lms_url: [])

    collect_tasks(sample_settings, relogin=True, now=NOW)
    assert not sample_settings.session_cache_path.exists()
    assert sibling.exists()

    sample_settings.session_cache_path.write_text("{}", encoding="utf-8")
    collect_tasks(sample_settings, relogin=False, now=NOW)
    assert sample_settings.session_cache_path.exists()


def test_headed_forwarded_to_session(monkeypatch, sample_settings):
    """headed is forwarded to SessionManager(headful=...), default False, True when requested (D-10)."""
    recorded: dict[str, bool] = {}

    class RecordingSession(FakeSession):
        def __init__(self, *, settings, headful=False):
            super().__init__(settings=settings, headful=headful)
            recorded["headful"] = headful

    monkeypatch.setattr(pipeline, "SessionManager", RecordingSession)
    monkeypatch.setattr(pipeline, "extract_courses", lambda page, lms_url: [])

    collect_tasks(sample_settings, now=NOW)
    assert recorded["headful"] is False

    collect_tasks(sample_settings, headed=True, now=NOW)
    assert recorded["headful"] is True


def test_mappings_loaded_from_settings_path(monkeypatch, sample_settings):
    """Course mappings are loaded from settings.course_mappings_path and applied to task titles."""
    sample_settings.course_mappings_path.write_text(
        json.dumps({"테스트과목": "자구"}), encoding="utf-8"
    )
    courses = [_course("c1", "테스트과목")]

    monkeypatch.setattr(pipeline, "SessionManager", FakeSession)
    monkeypatch.setattr(pipeline, "extract_courses", lambda page, lms_url: courses)
    monkeypatch.setattr(
        pipeline,
        "scrape_course",
        lambda page, course, navigator: ([_lecture(course.course_id)], []),
    )

    result = collect_tasks(sample_settings, now=NOW)

    assert result.tasks
    assert all(t.title.startswith("[자구]") for t in result.tasks)


def test_zero_courses_warns_not_errors(monkeypatch, sample_settings, caplog):
    """Zero discovered courses is not an error: course_count 0 plus a stderr-bound WARNING log (A-05)."""
    monkeypatch.setattr(pipeline, "SessionManager", FakeSession)
    monkeypatch.setattr(pipeline, "extract_courses", lambda page, lms_url: [])

    with caplog.at_level(logging.WARNING, logger="kau_assistant.pipeline"):
        result = collect_tasks(sample_settings, now=NOW)

    assert result.course_count == 0
    assert result.tasks == []
    assert result.errors == []
    assert any(
        record.levelno == logging.WARNING and record.name == "kau_assistant.pipeline"
        for record in caplog.records
    )
