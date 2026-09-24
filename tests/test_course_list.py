import json
from pathlib import Path
from unittest.mock import MagicMock
import pytest
from click.testing import CliRunner

from kau_assistant.cli import cli
from kau_assistant.exceptions import UnsupportedLmsError
from kau_assistant.scraper.course_list import (
    clean_course_name,
    extract_courses,
    extract_courses_from_html,
    looks_like_coursemos,
)
from kau_assistant.scraper.models import CourseItem


def test_clean_course_name_various_patterns():
    # Pattern 1: division in parentheses with semester in brackets
    assert clean_course_name("공학수학2(01분반) [2026-1학기]") == "공학수학2"

    # Pattern 2: semester prefix and division suffix
    assert clean_course_name("2026-1 자료구조 02분반") == "자료구조"

    # Pattern 3: underscore division with academic year text
    assert clean_course_name("디지털시스템설계_01 [2026학년도 1학기]") == "디지털시스템설계"

    # Pattern 4: division prefix and semester suffix
    assert clean_course_name("[03분반] 캡스톤디자인 [2026-1]") == "캡스톤디자인"

    # Pattern 5: simple course name without noise
    assert clean_course_name("운영체제") == "운영체제"

    # Pattern 6: course name with number that is part of the subject
    assert clean_course_name("물리학및실험1 [2026-1]") == "물리학및실험1"


def test_extract_courses_from_html_fixture():
    fixture_path = Path(__file__).parent / "fixtures" / "dashboard_coursemos.html"
    html_content = fixture_path.read_text(encoding="utf-8")

    courses = extract_courses_from_html(html_content, base_url="https://canvas.kau.ac.kr")

    # There should be 4 active courses (duplicates and past courses filtered out)
    assert len(courses) == 4

    course_ids = [c.course_id for c in courses]
    assert course_ids == ["10101", "10102", "10103", "10104"]

    # Verify first course
    c1 = courses[0]
    assert c1.course_id == "10101"
    assert c1.clean_name == "공학수학2"
    assert "https://canvas.kau.ac.kr/course/view.php?id=10101" in c1.url
    assert c1.term == "2026-1학기"

    # Verify Canvas style course
    c4 = courses[3]
    assert c4.course_id == "10104"
    assert c4.clean_name == "캡스톤디자인"

    # Ensure expired courses (99901, 99902) are not in the list
    assert "99901" not in course_ids
    assert "99902" not in course_ids


def test_extract_courses_lxp_dashboard_clean_names():
    fixture_path = Path(__file__).parent / "fixtures" / "lxp_dashboard.html"
    html_content = fixture_path.read_text(encoding="utf-8")

    courses = extract_courses_from_html(html_content, base_url="https://lxp.kau.ac.kr")

    assert len(courses) == 3
    assert [c.clean_name for c in courses] == ["샘플과목II", "예시과목", "테스트과목A"]
    assert [c.course_id for c in courses] == ["91001", "91002", "91003"]

    for course in courses:
        assert not course.clean_name.startswith("홍")
        assert not course.raw_name.startswith("홍")
        assert course.url == f"https://lxp.kau.ac.kr/course/view.php?id={course.course_id}"


def test_extract_courses_waits_for_attached_course_link():
    mock_page = MagicMock()
    mock_page.content.return_value = """
    <html><body id="page-my-index"><script>var M = {cfg: {}};</script>
      <a href="/course/view.php?id=123">테스트과목(01)</a>
    </body></html>
    """
    courses = extract_courses(mock_page, "https://lxp.kau.ac.kr")
    mock_page.wait_for_selector.assert_called_once_with(
        "a[href*='/course/view.php?id=']",
        state="attached",
        timeout=5000,
    )
    assert len(courses) == 1
    assert courses[0].clean_name == "테스트과목"

    # Wait failure still parses whatever loaded
    mock_page.wait_for_selector.side_effect = TimeoutError("timed out")
    courses_fallback = extract_courses(mock_page, "https://lxp.kau.ac.kr")
    assert len(courses_fallback) == 1
    assert courses_fallback[0].clean_name == "테스트과목"


def test_looks_like_coursemos_markers():
    fixture_path = Path(__file__).parent / "fixtures" / "lxp_dashboard.html"
    assert looks_like_coursemos(fixture_path.read_text(encoding="utf-8")) is True
    assert looks_like_coursemos("<script>var M = {cfg: {}};</script>") is True
    assert looks_like_coursemos('<body id="page-my-index"></body>') is True
    assert looks_like_coursemos('<link rel="stylesheet" href="/theme/coursemos/style.css">') is True
    assert looks_like_coursemos('<body class="pagelayout-base"></body>') is True
    assert looks_like_coursemos('<div class="coursemos-header">LMS</div>') is True
    assert looks_like_coursemos('<div class="ubion-footer">Ubion</div>') is True
    assert looks_like_coursemos('<div id="application" class="ic-app"></div>') is False
    assert looks_like_coursemos("") is False


def test_extract_courses_non_coursemos_zero_courses_raises():
    mock_page = MagicMock()
    mock_page.content.return_value = '<div id="application" class="ic-app">Canvas LMS</div>'

    with pytest.raises(UnsupportedLmsError):
        extract_courses(mock_page, "https://canvas.kau.ac.kr")


def test_extract_courses_coursemos_zero_courses_returns_empty():
    mock_page = MagicMock()
    mock_page.content.return_value = (
        '<html><body id="page-my-index"><script>var M = {cfg: {}};</script>'
        '<div role="main">수강 과목이 없습니다.</div></body></html>'
    )
    result = extract_courses(mock_page, "https://lxp.kau.ac.kr")
    assert result == []


def test_check_json_unsupported_lms_is_fatal(monkeypatch, sample_settings):
    runner = CliRunner()
    monkeypatch.setattr("kau_assistant.cli.get_settings", lambda: sample_settings)

    class FakeSessionManager:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def get_authenticated_page(self):
            page = MagicMock()
            page.content.return_value = '<div id="application" class="ic-app">Canvas LMS</div>'
            return page

    monkeypatch.setattr("kau_assistant.pipeline.SessionManager", FakeSessionManager)

    result = runner.invoke(cli, ["check", "--json"])
    assert result.exit_code == 2

    payload = json.loads(result.stdout)
    assert len(payload["errors"]) == 1
    fatal_err = payload["errors"][0]
    assert fatal_err["scope"] == "fatal"
    assert fatal_err["code"] == "UnsupportedLmsError"
    assert "LMS_URL" in fatal_err["message"]
    assert sample_settings.lms_username not in result.output
    assert sample_settings.lms_password not in result.output


def test_extract_courses_with_cache_injection():
    mock_page = MagicMock()
    cached = [
        CourseItem(
            course_id="999",
            raw_name="테스트과목 [2026-1]",
            clean_name="테스트과목",
            url="https://canvas.kau.ac.kr/course/view.php?id=999",
        )
    ]

    result = extract_courses(mock_page, "https://canvas.kau.ac.kr", cached_courses=cached)
    assert result == cached
    mock_page.goto.assert_not_called()


def test_extract_courses_navigation(monkeypatch):
    mock_page = MagicMock()
    mock_page.content.return_value = """
    <html><body>
      <div class="course_box current">
        <a href="/course/view.php?id=777">알고리즘(01) [2026-1]</a>
      </div>
    </body></html>
    """

    result = extract_courses(mock_page, "https://canvas.kau.ac.kr")
    assert len(result) == 1
    assert result[0].course_id == "777"
    assert result[0].clean_name == "알고리즘"
    assert result[0].url == "https://canvas.kau.ac.kr/course/view.php?id=777"
    mock_page.goto.assert_called_once_with("https://canvas.kau.ac.kr/my/", wait_until="domcontentloaded")
