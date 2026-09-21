from pathlib import Path
from unittest.mock import MagicMock
import pytest

from kau_assistant.scraper.course_list import (
    clean_course_name,
    extract_courses,
    extract_courses_from_html,
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
