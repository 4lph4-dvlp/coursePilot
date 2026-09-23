"""Pipeline resilience: per-course isolation, fatal-stage classification, progress,
relogin/headed forwarding, mappings, zero-course handling, and read-only scraping (05-02).
"""

import json
from datetime import datetime, timedelta

from click.testing import CliRunner

import kau_assistant.pipeline as pipeline
from kau_assistant.cli import cli
from kau_assistant.exceptions import CourseAccessDeniedError
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
