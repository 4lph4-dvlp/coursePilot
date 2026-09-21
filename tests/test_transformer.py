"""Unit tests for DTO transformer, deadline rescue, memo formatter, and package facade."""

from datetime import datetime, timezone, timedelta
import pytest

from kau_assistant.domain import (
    Course,
    SyncTask,
    TaskPriority,
    TaskSelect,
    TaskStatus,
    TaskType,
    calculate_priority,
    clean_task_title,
    extract_deadline_from_description,
    extract_week_and_title,
    format_memo,
    format_task_title,
    get_task_selection,
    transform_assessment_to_task,
    transform_lecture_to_task,
    transform_to_sync_tasks,
)
from kau_assistant.scraper.date_parser import KST
from kau_assistant.scraper.models import (
    AssessmentItem,
    AssessmentType,
    AttachmentMeta,
    AttendanceStatus,
    CourseItem,
    LectureItem,
    SubmissionStatus,
)


@pytest.fixture
def sample_course():
    return CourseItem(
        course_id="10101",
        raw_name="공학수학2(01분반)",
        clean_name="공학수학2",
        url="https://canvas.kau.ac.kr/course/view.php?id=10101",
    )


def test_domain_facade_imports():
    """Verify all expected symbols can be imported directly from kau_assistant.domain."""
    assert SyncTask is not None
    assert Course is not None
    assert TaskPriority is not None
    assert TaskSelect is not None
    assert TaskStatus is not None
    assert TaskType is not None
    assert callable(clean_task_title)
    assert callable(extract_week_and_title)
    assert callable(format_task_title)
    assert callable(calculate_priority)
    assert callable(get_task_selection)
    assert callable(extract_deadline_from_description)
    assert callable(format_memo)
    assert callable(transform_lecture_to_task)
    assert callable(transform_assessment_to_task)
    assert callable(transform_to_sync_tasks)


def test_transform_lecture_excluding_no_due_date(sample_course):
    """D-11: OT/open lectures without due date should be excluded (return None)."""
    lec_no_due = LectureItem(
        course_id="10101",
        week_number=1,
        clip_number=1,
        title="오리엔테이션",
        full_title="[공수2] 1주차 1차시: 오리엔테이션",
        status=AttendanceStatus.INCOMPLETE,
        due_date=None,
    )
    task = transform_lecture_to_task(sample_course, lec_no_due, {"공학수학2": "공수2"})
    assert task is None


def test_transform_lecture_with_due_date(sample_course):
    """Verify valid lecture transforms into SyncTask correctly."""
    due = datetime(2026, 9, 28, 23, 59, 0, tzinfo=KST)
    lec = LectureItem(
        course_id="10101",
        week_number=3,
        clip_number=1,
        title="1차시: 라플라스 변환",
        full_title="[공수2] 3주차 1차시: 라플라스 변환",
        status=AttendanceStatus.INCOMPLETE,
        due_date=due,
        link="https://canvas.kau.ac.kr/mod/vod/view.php?id=5001",
    )
    task = transform_lecture_to_task(sample_course, lec, {"공학수학2": "공수2"})
    assert task is not None
    assert task.id == "lec_10101_3_1"
    assert task.title == "[공수2] 3주차 1차시 강의 시청"
    assert task.selection == TaskSelect.ROUTINE
    assert task.task_type == TaskType.LECTURE
    assert task.is_completed is False
    assert task.status == TaskStatus.NOT_STARTED
    assert task.memo == "LMS 바로가기: https://canvas.kau.ac.kr/mod/vod/view.php?id=5001"


def test_deadline_rescue_from_description():
    """D-11: Rescue date from contextual Korean description when official due_date is absent."""
    # Pattern 1: YYYY-MM-DD HH:MM까지
    desc1 = "본 과제는 2026-10-15 23:59까지 담당 조교 이메일로 제출 바랍니다."
    assert extract_deadline_from_description(desc1) == datetime(
        2026, 10, 15, 23, 59, 0, tzinfo=KST
    )

    # Pattern 2: M월 D일 HH:MM까지 with 자정/24시
    desc2 = "제출기한: 10월 20일 자정까지"
    res2 = extract_deadline_from_description(desc2)
    assert res2 is not None
    assert res2.month == 10
    assert res2.day == 20
    assert res2.hour == 23
    assert res2.minute == 59

    # Pattern 3: 마감일시 keyword
    desc3 = "과제 마감 일시: 2026.11.05 18:00"
    assert extract_deadline_from_description(desc3) == datetime(
        2026, 11, 5, 18, 0, 0, tzinfo=KST
    )

    # No date in description
    assert extract_deadline_from_description("상세 내용은 수업 시간에 공지합니다.") is None
    assert extract_deadline_from_description("") is None


def test_transform_assessment_with_rescued_deadline(sample_course):
    """D-11: Assessment with no LMS due date has deadline rescued from description."""
    assess = AssessmentItem(
        course_id="10101",
        item_id="88",
        item_type=AssessmentType.ASSIGNMENT,
        title="보고서 제출",
        description_text="이메일 제출 기한: 2026-10-25 23:59:00",
        status=SubmissionStatus.NOT_ATTEMPTED,
        due_date=None,
    )
    task = transform_assessment_to_task(sample_course, assess, {"공학수학2": "공수2"})
    assert task is not None
    assert task.due_date == datetime(2026, 10, 25, 23, 59, 0, tzinfo=KST)
    assert task.title == "[공수2] 보고서 제출"
    assert task.selection == TaskSelect.EVENT


def test_format_memo_structure_and_truncation():
    """D-12 ~ D-14: Verify structured memo generation, safe 1500-char truncation, and 1950-char cap."""
    # 1. Lecture memo
    lec_memo = format_memo(TaskType.LECTURE, url="https://canvas.kau.ac.kr/video")
    assert lec_memo == "LMS 바로가기: https://canvas.kau.ac.kr/video"

    # 2. Assessment structured memo
    att = AttachmentMeta(filename="hw1.pdf", url="https://link/hw1.pdf", filesize="1.2MB")
    cutoff = datetime(2026, 10, 1, 23, 59, 0, tzinfo=KST)
    memo = format_memo(
        TaskType.ASSIGNMENT,
        url="https://canvas.kau.ac.kr/assign/1",
        cutoff_date=cutoff,
        attachments=[att],
        description_text="문제 1번부터 5번까지 풀이하여 제출하세요.",
    )
    assert "LMS 바로가기: https://canvas.kau.ac.kr/assign/1" in memo
    assert "지각 제출 마감: 2026-10-01 23:59:00 (KST)" in memo
    assert "첨부파일:\n- hw1.pdf (1.2MB): https://link/hw1.pdf" in memo
    assert "과제 안내:\n문제 1번부터 5번까지 풀이하여 제출하세요." in memo

    # 3. 1500-char safe description truncation
    long_desc = "가" * 2000
    trunc_memo = format_memo(
        TaskType.ASSIGNMENT,
        url="https://canvas.kau.ac.kr/assign/1",
        description_text=long_desc,
    )
    assert "... [이하 생략 - 전체 내용은 LMS 페이지 참조]" in trunc_memo
    assert len(trunc_memo) <= 1950

    # 4. 1950-char hard cap
    huge_desc = "X" * 5000
    hard_capped_memo = format_memo(TaskType.ASSIGNMENT, description_text=huge_desc)
    assert len(hard_capped_memo) <= 1950


def test_transform_to_sync_tasks_filtering_and_sorting(sample_course):
    """DOMN-01, D-09: Filter completed tasks when include_completed=False, sort ascending by due_date."""
    due_early = datetime(2026, 9, 22, 23, 59, 0, tzinfo=KST)
    due_late = datetime(2026, 9, 28, 23, 59, 0, tzinfo=KST)

    lec_incomplete = LectureItem(
        course_id="10101",
        week_number=3,
        clip_number=1,
        title="3주차 1차시",
        full_title="[공수2] 3주차 1차시",
        status=AttendanceStatus.INCOMPLETE,
        due_date=due_late,
    )
    lec_completed = LectureItem(
        course_id="10101",
        week_number=2,
        clip_number=1,
        title="2주차 1차시",
        full_title="[공수2] 2주차 1차시",
        status=AttendanceStatus.COMPLETED,
        due_date=due_early,
    )
    assess_pending = AssessmentItem(
        course_id="10101",
        item_id="99",
        item_type=AssessmentType.ASSIGNMENT,
        title="과제 2",
        status=SubmissionStatus.NOT_ATTEMPTED,
        due_date=due_early,
    )
    assess_submitted = AssessmentItem(
        course_id="10101",
        item_id="100",
        item_type=AssessmentType.ASSIGNMENT,
        title="과제 1",
        status=SubmissionStatus.SUBMITTED,
        due_date=due_early,
    )
    assess_no_due = AssessmentItem(
        course_id="10101",
        item_id="101",
        item_type=AssessmentType.ASSIGNMENT,
        title="추후 공지 과제",
        status=SubmissionStatus.NOT_ATTEMPTED,
        due_date=None,
    )

    # 1. include_completed=False (default)
    tasks = transform_to_sync_tasks(
        courses=[sample_course],
        lectures_by_course={"10101": [lec_incomplete, lec_completed]},
        assessments_by_course={"10101": [assess_pending, assess_submitted, assess_no_due]},
        include_completed=False,
        mappings={"공학수학2": "공수2"},
    )

    # Only incomplete items: lec_incomplete, assess_pending, assess_no_due
    assert len(tasks) == 3
    # Sorted by due_date: due_early first, due_late second, None last
    assert tasks[0].due_date == due_early
    assert tasks[0].id == "assess_10101_99"
    assert tasks[1].due_date == due_late
    assert tasks[1].id == "lec_10101_3_1"
    assert tasks[2].due_date is None
    assert tasks[2].id == "assess_10101_101"

    # 2. include_completed=True
    all_tasks = transform_to_sync_tasks(
        courses=[sample_course],
        lectures_by_course={"10101": [lec_incomplete, lec_completed]},
        assessments_by_course={"10101": [assess_pending, assess_submitted, assess_no_due]},
        include_completed=True,
        mappings={"공학수학2": "공수2"},
    )
    assert len(all_tasks) == 5
