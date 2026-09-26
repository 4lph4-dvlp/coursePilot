from datetime import datetime
from pathlib import Path
import pytest

from coursepilot.scraper.date_parser import KST
from coursepilot.scraper.lecture_parser import (
    LectureProgress,
    UblogsActivityStatus,
    _parse_duration_seconds,
    clean_lecture_title,
    merge_lecture_progress,
    merge_ublogs_completion,
    parse_lectures_from_course_sections,
    parse_lectures_from_progress_table,
    parse_ubcompletion_progress,
    parse_ublogs_completion,
)
from coursepilot.scraper.models import AttendanceStatus, CourseItem


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


def test_lxp_course_home_dedupes_vods_and_uses_section_weeks(course):
    fixture_path = Path(__file__).parent / "fixtures" / "lxp_course_home.html"
    html_content = fixture_path.read_text(encoding="utf-8")

    lectures = parse_lectures_from_course_sections(html_content, course)

    # Exactly 6 lectures (OT + 1, 2, 3, 4-1, 4-2)
    assert len(lectures) == 6

    assert lectures[0].title == "OT 안내 영상"
    assert lectures[0].week_number == 0
    assert lectures[0].clip_number == 1
    assert lectures[0].due_date is None

    assert lectures[1].title == "샘플 강의 1"
    assert lectures[1].week_number == 1
    assert lectures[1].clip_number == 1

    assert lectures[2].title == "샘플 강의 2"
    assert lectures[2].week_number == 2
    assert lectures[2].clip_number == 1

    assert lectures[3].title == "샘플 강의 3"
    assert lectures[3].week_number == 3
    assert lectures[3].clip_number == 1

    assert lectures[4].title == "샘플 강의 4-1"
    assert lectures[4].week_number == 6
    assert lectures[4].clip_number == 1

    assert lectures[5].title == "샘플 강의 4-2"
    assert lectures[5].week_number == 6
    assert lectures[5].clip_number == 2


def test_lxp_course_home_period_end_is_due_date(course):
    fixture_path = Path(__file__).parent / "fixtures" / "lxp_course_home.html"
    html_content = fixture_path.read_text(encoding="utf-8")

    lectures = parse_lectures_from_course_sections(html_content, course)

    assert lectures[0].due_date is None

    assert lectures[1].due_date == datetime(2026, 9, 7, 23, 59, 59, tzinfo=KST)
    assert "2026-09-01 00:00:00 ~ 2026-09-07 23:59:59" in lectures[1].raw_due_date

    assert lectures[2].due_date == datetime(2026, 9, 14, 23, 59, 59, tzinfo=KST)
    assert lectures[3].due_date == datetime(2026, 9, 21, 23, 59, 59, tzinfo=KST)
    assert lectures[4].due_date == datetime(2026, 10, 12, 23, 59, 59, tzinfo=KST)
    assert lectures[5].due_date == datetime(2026, 10, 12, 23, 59, 59, tzinfo=KST)


def test_lxp_course_home_titles_drop_accesshide_label(course):
    fixture_path = Path(__file__).parent / "fixtures" / "lxp_course_home.html"
    html_content = fixture_path.read_text(encoding="utf-8")

    lectures = parse_lectures_from_course_sections(html_content, course)
    for lec in lectures:
        assert not lec.title.endswith("동영상")
        assert not lec.title.endswith(" 동영상")


def test_parse_ubcompletion_progress_rowspan_weeks_and_completion():
    fixture_path = Path(__file__).parent / "fixtures" / "lxp_ubcompletion_progress.html"
    html_content = fixture_path.read_text(encoding="utf-8")

    rows = parse_ubcompletion_progress(html_content)
    assert len(rows) == 5

    weeks = [r.week_number for r in rows]
    assert weeks == [1, 2, 3, 6, 6]

    titles = [r.title for r in rows]
    assert titles == ["샘플 강의 1", "샘플 강의 2", "샘플 강의 3", "샘플 강의 4-1", "샘플 강의 4-2"]

    completions = [r.is_completed for r in rows]
    assert completions == [True, False, True, False, True]


def test_parse_ubcompletion_progress_duration_formats():
    assert _parse_duration_seconds("00:25:00") == 1500
    assert _parse_duration_seconds("25:00") == 1500
    assert _parse_duration_seconds("01:10:05") == 4205
    assert _parse_duration_seconds("1시간 10분 5초") == 4205
    assert _parse_duration_seconds("20분") == 1200
    assert _parse_duration_seconds("45초") == 45
    assert _parse_duration_seconds("-") is None
    assert _parse_duration_seconds("") is None
    assert _parse_duration_seconds("   ") is None


def test_parse_ubcompletion_progress_ignores_legacy_table():
    fixture_path = Path(__file__).parent / "fixtures" / "progress_report.html"
    html_content = fixture_path.read_text(encoding="utf-8")

    rows = parse_ubcompletion_progress(html_content)
    assert rows == []


def test_merge_lecture_progress_by_module_id_or_title(course):
    home_path = Path(__file__).parent / "fixtures" / "lxp_course_home.html"
    progress_path = Path(__file__).parent / "fixtures" / "lxp_ubcompletion_progress.html"

    lectures = parse_lectures_from_course_sections(home_path.read_text(encoding="utf-8"), course)
    rows = parse_ubcompletion_progress(progress_path.read_text(encoding="utf-8"))

    now = datetime(2026, 9, 23, 12, 0, tzinfo=KST)
    merged = merge_lecture_progress(lectures, rows, now=now)

    assert len(merged) == 6

    # 7000 (OT): unmatched, remains incomplete, progress 0
    assert merged[0].title == "OT 안내 영상"
    assert merged[0].status == AttendanceStatus.INCOMPLETE
    assert merged[0].is_overdue is False

    # 7001 (샘플 강의 1): completed
    assert merged[1].title == "샘플 강의 1"
    assert merged[1].status == AttendanceStatus.COMPLETED
    assert merged[1].progress_percent == 100.0
    assert merged[1].is_overdue is False

    # 7002 (샘플 강의 2): 10m / 40m = 25%, past deadline at NOW -> OVERDUE
    assert merged[2].title == "샘플 강의 2"
    assert merged[2].status == AttendanceStatus.OVERDUE
    assert merged[2].progress_percent == 25.0
    assert merged[2].is_overdue is True

    # 7003 (샘플 강의 3): completed (30m / 30m)
    assert merged[3].title == "샘플 강의 3"
    assert merged[3].status == AttendanceStatus.COMPLETED
    assert merged[3].progress_percent == 100.0
    assert merged[3].is_overdue is False

    # 7004 (샘플 강의 4-1): 0m / 20m, future deadline (10-12) -> INCOMPLETE
    assert merged[4].title == "샘플 강의 4-1"
    assert merged[4].status == AttendanceStatus.INCOMPLETE
    assert merged[4].progress_percent == 0.0
    assert merged[4].is_overdue is False

    # 7005 (샘플 강의 4-2): completed (21m / 20m)
    assert merged[5].title == "샘플 강의 4-2"
    assert merged[5].status == AttendanceStatus.COMPLETED
    assert merged[5].progress_percent == 100.0
    assert merged[5].is_overdue is False


def test_merge_lecture_progress_order_fallback_and_unmatched(course):
    now = datetime(2026, 9, 23, 12, 0, tzinfo=KST)

    home_path = Path(__file__).parent / "fixtures" / "lxp_course_home.html"
    lectures = parse_lectures_from_course_sections(home_path.read_text(encoding="utf-8"), course)

    # Create synthetic rows with NO module_id and different titles to test order-based fallback
    # In week 6 we have 2 lectures. Provide 2 rows for week 6 with non-matching titles:
    fallback_rows = [
        LectureProgress(
            week_number=6,
            title="다른이름 A",
            module_id=None,
            required_seconds=1200,
            studied_seconds=1200,
            is_completed=True,
        ),
        LectureProgress(
            week_number=6,
            title="다른이름 B",
            module_id=None,
            required_seconds=1200,
            studied_seconds=0,
            is_completed=False,
        ),
    ]

    merged = merge_lecture_progress(lectures, fallback_rows, now=now)
    # week 6 clip 1 should get first row (completed)
    assert merged[4].week_number == 6 and merged[4].clip_number == 1
    assert merged[4].status == AttendanceStatus.COMPLETED

    # week 6 clip 2 should get second row (incomplete)
    assert merged[5].week_number == 6 and merged[5].clip_number == 2
    assert merged[5].status == AttendanceStatus.INCOMPLETE


def test_parse_ublogs_completion():
    html = """
    <table class="table table-bordered table-learning-student-activity">
      <thead>
        <tr>
          <th>주차</th>
          <th>학습활동명</th>
          <th>완료 상태</th>
          <th>완료 일시</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>1주차</td>
          <td>Ch01 논리회로 기초</td>
          <td><span class="label label-success">완료</span></td>
          <td>2026-09-10 14:20:00</td>
        </tr>
        <tr>
          <td>1주차</td>
          <td>Ch02 불 대수와 게이트</td>
          <td><span class="label label-danger">미완료</span></td>
          <td>-</td>
        </tr>
        <tr>
          <td>2주차</td>
          <td>Ch03 카르노 맵</td>
          <td><span class="label label-success">완료</span></td>
          <td>2026-09-17 18:30:00</td>
        </tr>
      </tbody>
    </table>
    """
    records = parse_ublogs_completion(html)
    assert len(records) == 3
    assert records[0].week_number == 1
    assert records[0].activity_title == "Ch01 논리회로 기초"
    assert records[0].is_completed is True
    assert records[0].completion_time == "2026-09-10 14:20:00"

    assert records[1].week_number == 1
    assert records[1].activity_title == "Ch02 불 대수와 게이트"
    assert records[1].is_completed is False

    assert records[2].week_number == 2
    assert records[2].activity_title == "Ch03 카르노 맵"
    assert records[2].is_completed is True


def test_merge_ublogs_completion(course):
    from coursepilot.scraper.models import LectureItem

    lectures = [
        LectureItem(
            course_id=course.course_id,
            week_number=1,
            clip_number=1,
            title="Ch01 논리회로 기초 (동영상)",
            full_title="1주차 1차시",
            status=AttendanceStatus.INCOMPLETE,
        ),
        LectureItem(
            course_id=course.course_id,
            week_number=1,
            clip_number=2,
            title="Ch02 불 대수와 게이트 (동영상)",
            full_title="1주차 2차시",
            status=AttendanceStatus.INCOMPLETE,
        ),
    ]

    records = [
        UblogsActivityStatus(
            week_number=1,
            activity_title="Ch01 논리회로 기초",
            status="완료",
            is_completed=True,
        ),
        UblogsActivityStatus(
            week_number=1,
            activity_title="Ch02 불 대수와 게이트",
            status="미완료",
            is_completed=False,
        ),
    ]

    merged = merge_ublogs_completion(lectures, records)
    assert len(merged) == 2
    assert merged[0].status == AttendanceStatus.COMPLETED
    assert merged[0].progress_percent == 100.0
    assert merged[0].is_overdue is False

    assert merged[1].status == AttendanceStatus.INCOMPLETE
    assert merged[1].progress_percent == 0.0

