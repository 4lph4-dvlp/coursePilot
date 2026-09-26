"""Pipeline resilience: per-course isolation, fatal-stage classification, progress,
relogin/headed forwarding, mappings, zero-course handling, and read-only scraping (05-02).
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

import coursepilot.pipeline as pipeline
from coursepilot.cli import cli
from coursepilot.exceptions import AuthenticationError, ConfigError, CourseAccessDeniedError
from coursepilot.pipeline import collect_tasks, scrape_course
from coursepilot.domain.transformer import transform_to_sync_tasks
from coursepilot.scraper.date_parser import KST
from coursepilot.scraper.models import AttendanceStatus, CourseItem, LectureItem
from coursepilot.scraper.navigator import CourseNavigator

NOW = datetime(2026, 9, 23, 12, 0, tzinfo=KST)

FIXTURES_DIR = Path(__file__).parent / "fixtures"
PROGRESS_REPORT_HTML = (FIXTURES_DIR / "progress_report.html").read_text(encoding="utf-8")
ASSIGNMENT_LIST_HTML = (FIXTURES_DIR / "assignment_list.html").read_text(encoding="utf-8")
ASSIGNMENT_DETAIL_HTML = (FIXTURES_DIR / "assignment_detail.html").read_text(encoding="utf-8")
LXP_COURSE_HOME_HTML = (FIXTURES_DIR / "lxp_course_home.html").read_text(encoding="utf-8")
LXP_UBCOMPLETION_PROGRESS_HTML = (FIXTURES_DIR / "lxp_ubcompletion_progress.html").read_text(encoding="utf-8")

EMPTY_QUIZ_HTML = "<html><body><div id='region-main'>등록된 퀴즈가 없습니다.</div></body></html>"
PLAIN_COURSE_HOME_HTML = "<html><body><div id='region-main'>강의실 홈</div></body></html>"
NO_PROGRESS_MARKERS_HTML = (
    "<html><body><div id='region-main'>진행 정보를 표시할 수 없습니다.</div></body></html>"
)
COURSE_SECTIONS_HTML = """
<div class="course-content">
  <ul class="topics">
    <li class="section main" id="section-1">
      <h3 class="sectionname">1주차</h3>
      <ul class="section img-text">
        <li class="activity vod modtype_vod" id="module-201">
          <div class="mod-indent-outer">
            <div class="activityinstance">
              <a href="/mod/vod/view.php?id=201">
                <span class="instancename">01차시: 강의 개요 (동영상)</span>
              </a>
            </div>
            <div class="availabilityinfo">
              마감일: 2026-09-30 23:59
            </div>
          </div>
        </li>
      </ul>
    </li>
  </ul>
</div>
"""


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

    monkeypatch.setattr("coursepilot.cli.get_settings", lambda: sample_settings)
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

    with caplog.at_level(logging.WARNING, logger="coursepilot.pipeline"):
        result = collect_tasks(sample_settings, now=NOW)

    assert result.course_count == 0
    assert result.tasks == []
    assert result.errors == []
    assert any(
        record.levelno == logging.WARNING and record.name == "coursepilot.pipeline"
        for record in caplog.records
    )


# --- Task 3: real per-course scraping sequence over fixture HTML, proven read-only ---


def _assessment_course() -> CourseItem:
    return CourseItem(
        course_id="10101",
        raw_name="공학수학2(01분반) [2026-1학기]",
        clean_name="공학수학2",
        url="https://canvas.kau.ac.kr/course/view.php?id=10101",
    )


def _make_mock_page(*, progress_html: str, course_home_html: str) -> MagicMock:
    """A MagicMock page whose content() reflects the last goto() URL (mirrors
    tests/test_assessment_parser.py::test_scrape_course_assessments_flow's idiom).
    """
    state = {"last_url": ""}

    def _goto(url, wait_until=None, timeout=None):
        state["last_url"] = url
        response = MagicMock()
        response.status = 200
        return response

    def _content():
        url = state["last_url"]
        if "/report/progress/" in url or "/report/ubcompletion/" in url:
            return progress_html
        if "/mod/assign/index.php" in url:
            return ASSIGNMENT_LIST_HTML
        if "/mod/quiz/index.php" in url:
            return EMPTY_QUIZ_HTML
        if "/mod/assign/view.php" in url:
            return ASSIGNMENT_DETAIL_HTML
        return course_home_html

    page = MagicMock()
    page.goto.side_effect = _goto
    page.content.side_effect = _content
    return page


def _method_call_names(page: MagicMock) -> set[str]:
    return {call[0] for call in page.method_calls}


def test_scrape_course_uses_progress_report(sample_settings):
    """scrape_course uses the progress report and collects assessments (SKIL-02)."""
    course = _assessment_course()
    page = _make_mock_page(
        progress_html=PROGRESS_REPORT_HTML, course_home_html=PLAIN_COURSE_HOME_HTML
    )
    navigator = CourseNavigator(sample_settings, min_delay=0, max_delay=0)

    lectures, assessments = scrape_course(page, course, navigator)

    assert len(lectures) >= 1
    assert len(assessments) == 4


def test_scrape_course_falls_back_to_course_sections(sample_settings):
    """When the progress page has no progress markers, lectures come from course-home sections."""
    course = _assessment_course()
    page = _make_mock_page(
        progress_html=NO_PROGRESS_MARKERS_HTML, course_home_html=COURSE_SECTIONS_HTML
    )
    navigator = CourseNavigator(sample_settings, min_delay=0, max_delay=0)

    lectures, assessments = scrape_course(page, course, navigator)

    assert len(lectures) == 1
    assert lectures[0].title == "01차시: 강의 개요"
    assert lectures[0].due_date is not None
    assert len(assessments) == 4


def test_scrape_course_is_read_only(sample_settings):
    """scrape_course never calls a page-mutation method (SKIL-02 ethics prohibition)."""
    course = _assessment_course()
    navigator = CourseNavigator(sample_settings, min_delay=0, max_delay=0)
    mutating_methods = {"click", "fill", "press", "check", "set_input_files"}
    allowed_methods = {"goto", "content", "wait_for_selector", "wait_for_timeout", "screenshot"}

    page_a = _make_mock_page(
        progress_html=PROGRESS_REPORT_HTML, course_home_html=PLAIN_COURSE_HOME_HTML
    )
    scrape_course(page_a, course, navigator)
    calls_a = _method_call_names(page_a)

    page_b = _make_mock_page(
        progress_html=NO_PROGRESS_MARKERS_HTML, course_home_html=COURSE_SECTIONS_HTML
    )
    scrape_course(page_b, course, navigator)
    calls_b = _method_call_names(page_b)

    all_calls = calls_a | calls_b
    assert all_calls.isdisjoint(mutating_methods)
    assert all_calls <= allowed_methods


def test_scrape_course_lxp_home_lectures_reach_tasks(sample_settings):
    """LXP course home VODs yield deduplicated tasks with deadlines reaching check/sync (SKIL-01)."""
    course = _assessment_course()
    page = _make_mock_page(
        progress_html=NO_PROGRESS_MARKERS_HTML,
        course_home_html=LXP_COURSE_HOME_HTML,
    )
    navigator = CourseNavigator(sample_settings, min_delay=0, max_delay=0)

    lectures, _ = scrape_course(page, course, navigator)
    tasks = transform_to_sync_tasks(
        [course],
        {course.course_id: lectures},
        {course.course_id: []},
        mappings={},
        now=NOW,
    )

    # 6 VODs in home fixture: OT has no due_date (dropped), leaving 5 lecture tasks
    assert len(tasks) == 5
    task_ids = {t.id for t in tasks}
    assert len(task_ids) == 5

    overdue_tasks = [t for t in tasks if t.is_overdue]
    non_overdue_tasks = [t for t in tasks if not t.is_overdue]
    assert len(overdue_tasks) == 3  # weeks 1, 2, 3
    assert len(non_overdue_tasks) == 2  # week 6 clips 1 & 2


def test_scrape_course_lxp_home_and_progress_merge(sample_settings):
    """Real run reading both LXP course home and ubcompletion progress report merges completion."""
    course = _assessment_course()
    page = _make_mock_page(
        progress_html=LXP_UBCOMPLETION_PROGRESS_HTML,
        course_home_html=LXP_COURSE_HOME_HTML,
    )
    navigator = CourseNavigator(sample_settings, min_delay=0, max_delay=0)

    lectures, assessments = scrape_course(page, course, navigator)
    assert len(lectures) == 6

    tasks = transform_to_sync_tasks(
        [course],
        {course.course_id: lectures},
        {course.course_id: []},
        mappings={},
        now=NOW,
    )

    # OT video is dropped (no due date).
    # Weeks 1, 3, 6-2 are COMPLETED (dropped by transformer).
    # Remaining: Week 2 (overdue) and Week 6-1 (not overdue).
    assert len(tasks) == 2
    task_ids = {t.id for t in tasks}
    assert len(task_ids) == 2

    raw_titles = [t.raw_title for t in tasks]
    assert any("샘플 강의 2" in t for t in raw_titles)
    assert any("샘플 강의 4-1" in t for t in raw_titles)

    t_w2 = next(t for t in tasks if "샘플 강의 2" in t.raw_title)
    assert t_w2.is_overdue is True

    t_w6_1 = next(t for t in tasks if "샘플 강의 4-1" in t.raw_title)
    assert t_w6_1.is_overdue is False

