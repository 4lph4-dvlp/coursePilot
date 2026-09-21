from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock
import pytest

from kau_assistant.scraper.assessment_parser import (
    enrich_assessment_detail,
    parse_assessment_list,
    scrape_course_assessments,
)
from kau_assistant.scraper.date_parser import KST
from kau_assistant.scraper.models import (
    AssessmentItem,
    AssessmentType,
    CourseItem,
    SubmissionStatus,
)


@pytest.fixture
def course():
    return CourseItem(
        course_id="10101",
        raw_name="공학수학2(01분반) [2026-1학기]",
        clean_name="공학수학2",
        url="https://canvas.kau.ac.kr/course/view.php?id=10101",
    )


def test_parse_assessment_list():
    fixture_path = Path(__file__).parent / "fixtures" / "assignment_list.html"
    html_content = fixture_path.read_text(encoding="utf-8")

    items = parse_assessment_list(html_content, course_id="10101", item_type=AssessmentType.ASSIGNMENT)

    assert len(items) == 4

    # Item 1: Submitted
    i1 = items[0]
    assert i1.item_id == "5001"
    assert i1.title == "과제 1: 상미분방정식 풀이"
    assert i1.status == SubmissionStatus.SUBMITTED
    assert i1.is_overdue is False
    assert i1.due_date == datetime(2026, 9, 15, 23, 59, 0, tzinfo=KST)

    # Item 2: Draft (Incomplete)
    i2 = items[1]
    assert i2.item_id == "5002"
    assert i2.title == "과제 2: 연립방정식 구현"
    assert i2.status == SubmissionStatus.DRAFT
    assert i2.is_overdue is False

    # Item 3: Not Attempted & Overdue (Due 2026-09-10)
    i3 = items[2]
    assert i3.item_id == "5003"
    assert i3.title == "과제 3: 라플라스 변환 연습"
    assert i3.status == SubmissionStatus.NOT_ATTEMPTED
    assert i3.is_overdue is True

    # Item 4: Not Attempted & Upcoming (Due 2026-10-05)
    i4 = items[3]
    assert i4.item_id == "5004"
    assert i4.title == "과제 4: 푸리에 급수 보고서"
    assert i4.status == SubmissionStatus.NOT_ATTEMPTED
    assert i4.is_overdue is False


def test_enrich_assessment_detail():
    fixture_path = Path(__file__).parent / "fixtures" / "assignment_detail.html"
    html_content = fixture_path.read_text(encoding="utf-8")

    item = AssessmentItem(
        course_id="10101",
        item_id="5002",
        item_type=AssessmentType.ASSIGNMENT,
        title="과제 2: 연립방정식 구현",
        status=SubmissionStatus.DRAFT,
        url="https://canvas.kau.ac.kr/mod/assign/view.php?id=5002",
    )

    enriched = enrich_assessment_detail(item, html_content, base_url="https://canvas.kau.ac.kr")

    # Description text and HTML
    assert "가우스 조던 소거법 코드를 작성하고" in enriched.description_text
    assert "<div class=\"box generalbox\" id=\"intro\">" in enriched.description_html

    # Attachments
    assert len(enriched.attachments) == 2
    att1 = enriched.attachments[0]
    assert att1.filename == "spec_v1.pdf"
    assert att1.filesize == "250KB"
    assert "spec_v1.pdf" in att1.url

    att2 = enriched.attachments[1]
    assert att2.filename == "template.py"

    # Cutoff date (지각 제출 마감일)
    assert enriched.cutoff_date == datetime(2026, 10, 1, 23, 59, 0, tzinfo=KST)


def test_scrape_course_assessments_flow(course):
    mock_page = MagicMock()
    mock_navigator = MagicMock()

    list_fixture = (Path(__file__).parent / "fixtures" / "assignment_list.html").read_text(encoding="utf-8")
    detail_fixture = (Path(__file__).parent / "fixtures" / "assignment_detail.html").read_text(encoding="utf-8")

    # Mock navigator responses: return assignment HTML on assign, None on quiz
    def mock_nav_page(page, crs, item_type):
        if item_type == "assign":
            return list_fixture
        return None

    mock_navigator.navigate_assessment_page.side_effect = mock_nav_page
    mock_page.content.return_value = detail_fixture

    results = scrape_course_assessments(mock_page, course, mock_navigator)

    # 4 assignments scraped
    assert len(results) == 4
    # Check that deep scraping visited item URLs
    assert mock_page.goto.call_count == 4
    # Check that details were enriched
    assert results[0].attachments is not None
    assert results[0].cutoff_date is not None
