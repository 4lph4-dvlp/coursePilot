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


def test_parse_lxp_quiz_index_titles_and_due_dates():
    fixture_path = Path(__file__).parent / "fixtures" / "lxp_quiz_index.html"
    html_content = fixture_path.read_text(encoding="utf-8")

    items = parse_assessment_list(html_content, course_id="10101", item_type=AssessmentType.QUIZ)
    assert len(items) == 3

    # Row 1: Sample Quiz 1 - not attempted, due Oct 6
    assert items[0].item_id == "9001"
    assert items[0].title == "샘플 퀴즈 1"
    assert items[0].due_date == datetime(2026, 10, 6, 13, 0, 0, tzinfo=KST)
    assert items[0].status == SubmissionStatus.NOT_ATTEMPTED

    # Row 2: Sample Quiz 2 - grade 8.00 -> GRADED, due Sep 14
    assert items[1].item_id == "9002"
    assert items[1].title == "샘플 퀴즈 2"
    assert items[1].due_date == datetime(2026, 9, 14, 15, 20, 0, tzinfo=KST)
    assert items[1].status == SubmissionStatus.GRADED

    # Row 3: Sample Quiz 3 - grade '-' -> NOT_ATTEMPTED, due Sep 30
    assert items[2].item_id == "9003"
    assert items[2].title == "샘플 퀴즈 3"
    assert items[2].due_date == datetime(2026, 9, 30, 23, 59, 0, tzinfo=KST)
    assert items[2].status == SubmissionStatus.NOT_ATTEMPTED

    # Ensure no title was mistaken for a date
    for item in items:
        assert not any(day in item.title for day in ("화요일", "월요일", "수요일"))


def test_header_mapping_deadline_before_title():
    # Table where header has "시험 마감" (which contains "시험", a title keyword, and "마감", a due keyword)
    # and "이름" (title keyword)
    html = """
    <table class="generaltable">
      <thead>
        <tr>
          <th>주</th>
          <th>이름</th>
          <th>시험 마감</th>
          <th>성적</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>1</td>
          <td><a href="https://lxp.kau.ac.kr/mod/quiz/view.php?id=999">특별 시험</a></td>
          <td>2026-10-15 23:59</td>
          <td>-</td>
        </tr>
      </tbody>
    </table>
    """
    items = parse_assessment_list(html, course_id="10101", item_type=AssessmentType.QUIZ)
    assert len(items) == 1
    assert items[0].title == "특별 시험"
    assert items[0].due_date == datetime(2026, 10, 15, 23, 59, 0, tzinfo=KST)


def test_lxp_quiz_index_reaches_check_report(course):
    from kau_assistant.domain.transformer import transform_to_sync_tasks
    from kau_assistant.reporter import build_check_report

    fixture_path = Path(__file__).parent / "fixtures" / "lxp_quiz_index.html"
    html_content = fixture_path.read_text(encoding="utf-8")
    items = parse_assessment_list(html_content, course_id=course.course_id, item_type=AssessmentType.QUIZ)

    now = datetime(2026, 9, 24, 12, 0, 0, tzinfo=KST)
    tasks = transform_to_sync_tasks([course], {}, {course.course_id: items}, mappings={}, now=now)
    report = build_check_report(tasks, course_count=1, now=now)

    # Graded quiz (9002) is completed and excluded; 2 pending quizzes remain
    later_items = [item for group in report.items.later for item in group.items]
    assert len(later_items) == 2
    assert report.summary.later_count == 2

    later_titles = [item.title for item in later_items]
    assert any("샘플 퀴즈 1" in t for t in later_titles)
    assert any("샘플 퀴즈 3" in t for t in later_titles)
    for item in later_items:
        assert item.due_date is not None
        assert not any(day in item.title for day in ("화요일", "월요일", "수요일", "PM", "AM"))


def test_is_quiz_attempt_completed():
    from kau_assistant.scraper.assessment_parser import is_quiz_attempt_completed

    # 1. Review button
    html_review = '<div class="singlebutton"><a href="review.php?attempt=123" class="btn btn-secondary">답안 검토</a></div>'
    assert is_quiz_attempt_completed(html_review) is True

    # 2. Exceeded attempts notice
    html_exceeded = '<div class="box alert alert-info">응시 가능 횟수를 초과하여 더 이상 응시할 수 없습니다.</div>'
    assert is_quiz_attempt_completed(html_exceeded) is True

    # 3. Attempt summary table with 완료됨
    html_table = '<table class="generaltable quizattemptsummary"><tr><th>응시</th><th>상태</th></tr><tr><td>1</td><td>완료됨</td></tr></table>'
    assert is_quiz_attempt_completed(html_table) is True

    # 4. Genuinely unattempted quiz
    html_unattempted = '<div class="box quizinfo"><p>응시 가능 횟수: 1</p></div><div class="singlebutton"><button class="btn btn-primary">지금 퀴즈 응시</button></div>'
    assert is_quiz_attempt_completed(html_unattempted) is False


def test_enrich_assessment_detail_marks_hidden_grade_quiz_as_submitted():
    item = AssessmentItem(
        course_id="1103",
        item_id="2910",
        item_type=AssessmentType.QUIZ,
        title="W01-퀴즈",
        status=SubmissionStatus.NOT_ATTEMPTED,
        due_date=datetime(2026, 9, 11, 9, 0, 0, tzinfo=KST),
        url="https://lxp.kau.ac.kr/mod/quiz/view.php?id=2910",
        is_overdue=True,
    )

    detail_html = """
    <div id="page">
      <div class="box alert alert-info">응시 가능 횟수를 초과하여 더 이상 응시할 수 없습니다.</div>
      <div class="singlebutton"><a href="review.php" class="btn btn-secondary">답안 검토</a></div>
    </div>
    """

    enriched = enrich_assessment_detail(item, detail_html, base_url="https://lxp.kau.ac.kr")
    assert enriched.status == SubmissionStatus.SUBMITTED
    assert enriched.is_overdue is False

