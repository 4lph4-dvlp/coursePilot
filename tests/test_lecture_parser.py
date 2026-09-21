from pathlib import Path
import pytest

from kau_assistant.scraper.lecture_parser import (
    clean_lecture_title,
    parse_lectures_from_course_sections,
    parse_lectures_from_progress_table,
)
from kau_assistant.scraper.models import AttendanceStatus, CourseItem


@pytest.fixture
def course():
    return CourseItem(
        course_id="10101",
        raw_name="공학수학2(01분반) [2026-1학기]",
        clean_name="공학수학2",
        url="https://canvas.kau.ac.kr/course/view.php?id=10101",
    )


def test_clean_lecture_title():
    assert clean_lecture_title("2장 가우스 소거법 (동영상)") == "2장 가우스 소거법"
    assert clean_lecture_title("[VOD] 행렬의 랭크와 역행렬") == "행렬의 랭크와 역행렬"
    assert clean_lecture_title("3차시 미분방정식 개요 (웹콘텐츠)") == "3차시 미분방정식 개요"


def test_parse_lectures_from_progress_table(course):
    fixture_path = Path(__file__).parent / "fixtures" / "progress_report.html"
    html_content = fixture_path.read_text(encoding="utf-8")

    lectures = parse_lectures_from_progress_table(html_content, course)

    # Total 6 lecture clips in fixture
    assert len(lectures) == 6

    # 1주차 1차시 & 2차시: Both COMPLETED (attendance 'O')
    l1 = lectures[0]
    assert l1.week_number == 1
    assert l1.clip_number == 1
    assert l1.title == "강의 소개 및 오리엔테이션"
    assert l1.full_title == "[공학수학2] 1주차 1차시: 강의 소개 및 오리엔테이션"
    assert l1.status == AttendanceStatus.COMPLETED
    assert l1.progress_percent == 100.0
    assert l1.is_overdue is False

    l2 = lectures[1]
    assert l2.week_number == 1
    assert l2.clip_number == 2
    assert l2.status == AttendanceStatus.COMPLETED

    # 2주차 1차시: 80% watched, absent 'X', past deadline -> OVERDUE
    l3 = lectures[2]
    assert l3.week_number == 2
    assert l3.clip_number == 1
    assert l3.title == "2장 가우스 소거법"
    assert l3.status == AttendanceStatus.OVERDUE
    assert l3.is_overdue is True
    assert l3.progress_percent == 80.0

    # 2주차 2차시: 0% watched, past deadline -> OVERDUE
    l4 = lectures[3]
    assert l4.week_number == 2
    assert l4.clip_number == 2
    assert l4.status == AttendanceStatus.OVERDUE
    assert l4.is_overdue is True

    # 3주차 1차시: No 'O' mark, but progress is 100% -> COMPLETED (hybrid rule)
    l5 = lectures[4]
    assert l5.week_number == 3
    assert l5.clip_number == 1
    assert l5.status == AttendanceStatus.COMPLETED
    assert l5.progress_percent == 100.0
    assert l5.is_overdue is False

    # 3주차 2차시: 25% watched, future deadline -> INCOMPLETE
    l6 = lectures[5]
    assert l6.week_number == 3
    assert l6.clip_number == 2
    assert l6.status == AttendanceStatus.INCOMPLETE
    assert l6.progress_percent == 25.0
    assert l6.is_overdue is False


def test_parse_lectures_from_course_sections_fallback(course):
    mock_section_html = """
    <div class="course-content">
      <ul class="topics">
        <li class="section main" id="section-1">
          <h3 class="sectionname">1주차</h3>
          <ul class="section img-text">
            <li class="activity vod modtype_vod" id="module-101">
              <div class="mod-indent-outer">
                <div class="activityinstance">
                  <a href="/mod/vod/view.php?id=101">
                    <span class="instancename">01차시: 강의 개요 (동영상)</span>
                  </a>
                </div>
                <div class="completion-info">
                  <span class="badge badge-success">수강 완료</span>
                </div>
              </div>
            </li>
            <li class="activity vod modtype_vod" id="module-102">
              <div class="mod-indent-outer">
                <div class="activityinstance">
                  <a href="/mod/vod/view.php?id=102">
                    <span class="instancename">02차시: 파이썬 기본기</span>
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

    lectures = parse_lectures_from_course_sections(mock_section_html, course)
    assert len(lectures) == 2

    assert lectures[0].week_number == 1
    assert lectures[0].clip_number == 1
    assert lectures[0].title == "01차시: 강의 개요"
    assert lectures[0].status == AttendanceStatus.COMPLETED

    assert lectures[1].week_number == 1
    assert lectures[1].clip_number == 2
    assert lectures[1].title == "02차시: 파이썬 기본기"
    assert lectures[1].status == AttendanceStatus.INCOMPLETE
