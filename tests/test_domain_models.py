"""Unit tests for domain models, Notion enums, and KST validation."""

from datetime import datetime, timezone, timedelta
import pytest
from pydantic import ValidationError

from kau_assistant.domain.models import (
    Course,
    SyncTask,
    TaskPriority,
    TaskSelect,
    TaskStatus,
    TaskType,
)
from kau_assistant.scraper.date_parser import KST
from kau_assistant.scraper.models import AttendanceStatus, LectureItem


def test_task_enums():
    """Verify all domain enums map to expected string values."""
    assert TaskType.LECTURE == "lecture"
    assert TaskType.ASSIGNMENT == "assignment"
    assert TaskType.QUIZ == "quiz"
    assert TaskType.FORUM == "forum"
    assert TaskType.OTHER == "other"

    assert TaskPriority.P1 == "P1"
    assert TaskPriority.P2 == "P2"
    assert TaskPriority.P3 == "P3"
    assert TaskPriority.P4 == "P4"

    assert TaskSelect.ROUTINE == "루틴"
    assert TaskSelect.EVENT == "이벤트"

    assert TaskStatus.NOT_STARTED == "시작 전"
    assert TaskStatus.IN_PROGRESS == "진행 중"
    assert TaskStatus.COMPLETED == "완료"
    assert TaskStatus.DISCARDED == "폐기"


def test_sync_task_creation_and_defaults():
    """Verify default values and basic fields of SyncTask."""
    task = SyncTask(
        id="task_1",
        course_id="10101",
        course_name="공학수학2",
        course_abbr="공수2",
        title="[공수2] 3주차 1차시 강의 시청",
        raw_title="1차시: 미분방정식",
        task_type=TaskType.LECTURE,
        selection=TaskSelect.ROUTINE,
        priority=TaskPriority.P3,
    )

    # Category defaults to ["학업"] (D-08)
    assert task.category == ["학업"]
    # Plan date defaults to None (D-08)
    assert task.plan_date is None
    # Status defaults to "시작 전" (D-10)
    assert task.status == TaskStatus.NOT_STARTED
    assert task.is_completed is False
    assert task.is_overdue is False
    assert task.is_urgent is False
    assert task.memo == ""
    assert task.source_url == ""
    assert task.week_number is None
    assert task.clip_number is None
    # dedup_key when due_date is None
    assert task.dedup_key == "[공수2] 3주차 1차시 강의 시청|no_due"


def test_sync_task_kst_enforcement():
    """Verify ensure_kst validator attaches KST to naive datetime or converts timezone-aware datetime."""
    # 1. Naive datetime
    naive_dt = datetime(2026, 9, 25, 23, 59, 0)
    task = SyncTask(
        id="task_2",
        course_id="10101",
        course_name="공학수학2",
        course_abbr="공수2",
        title="[공수2] 3주차 과제 제출",
        raw_title="3주차 과제",
        task_type=TaskType.ASSIGNMENT,
        selection=TaskSelect.EVENT,
        due_date=naive_dt,
        priority=TaskPriority.P2,
    )
    assert task.due_date is not None
    assert task.due_date.tzinfo == KST
    assert task.due_date.year == 2026
    assert task.due_date.month == 9
    assert task.due_date.day == 25
    assert task.due_date.hour == 23
    assert task.due_date.minute == 59
    assert task.dedup_key == "[공수2] 3주차 과제 제출|2026-09-25 23:59"

    # 2. Naive plan_date
    task_plan = SyncTask(
        id="task_2_plan",
        course_id="10101",
        course_name="공학수학2",
        course_abbr="공수2",
        title="[공수2] 3주차 과제 제출",
        raw_title="3주차 과제",
        task_type=TaskType.ASSIGNMENT,
        selection=TaskSelect.EVENT,
        plan_date=datetime(2026, 9, 24, 14, 0),
        priority=TaskPriority.P2,
    )
    assert task_plan.plan_date is not None
    assert task_plan.plan_date.tzinfo == KST

    # 3. Timezone-aware UTC datetime converts to KST
    utc_dt = datetime(2026, 9, 25, 14, 59, 0, tzinfo=timezone.utc)
    task_utc = SyncTask(
        id="task_3",
        course_id="10101",
        course_name="공학수학2",
        course_abbr="공수2",
        title="[공수2] 3주차 과제 제출",
        raw_title="3주차 과제",
        task_type=TaskType.ASSIGNMENT,
        selection=TaskSelect.EVENT,
        due_date=utc_dt,
        priority=TaskPriority.P2,
    )
    assert task_utc.due_date.tzinfo == KST
    # 14:59 UTC == 23:59 KST
    assert task_utc.due_date.hour == 23
    assert task_utc.due_date.minute == 59


def test_course_model():
    """Verify Course model instantiation and relationship fields."""
    lecture = LectureItem(
        course_id="10101",
        week_number=1,
        clip_number=1,
        title="1차시: 소개",
        full_title="[공수2] 1주차 1차시: 소개",
        status=AttendanceStatus.COMPLETED,
    )

    course = Course(
        course_id="10101",
        name="공학수학2",
        abbreviation="공수2",
        url="https://canvas.kau.ac.kr/course/view.php?id=10101",
        term="2026-2",
        lectures=[lecture],
    )

    assert course.course_id == "10101"
    assert course.name == "공학수학2"
    assert course.abbreviation == "공수2"
    assert len(course.lectures) == 1
    assert len(course.assessments) == 0
    assert len(course.tasks) == 0
