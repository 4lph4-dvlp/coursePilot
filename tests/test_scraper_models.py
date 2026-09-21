from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from kau_assistant.scraper.models import (
    AssessmentItem,
    AssessmentType,
    AttachmentMeta,
    AttendanceStatus,
    CourseItem,
    LectureItem,
    SubmissionStatus,
)


def test_attendance_status_enum():
    assert AttendanceStatus.COMPLETED == "completed"
    assert AttendanceStatus.INCOMPLETE == "incomplete"
    assert AttendanceStatus.OVERDUE == "overdue"


def test_submission_status_enum():
    assert SubmissionStatus.SUBMITTED == "submitted"
    assert SubmissionStatus.GRADED == "graded"
    assert SubmissionStatus.DRAFT == "draft"
    assert SubmissionStatus.NOT_ATTEMPTED == "not_attempted"


def test_assessment_type_enum():
    assert AssessmentType.ASSIGNMENT == "assignment"
    assert AssessmentType.QUIZ == "quiz"
    assert AssessmentType.FORUM == "forum"
    assert AssessmentType.OTHER == "other"


def test_course_item_creation():
    course = CourseItem(
        course_id="12345",
        raw_name="공학수학2(01분반) [2026-1학기]",
        clean_name="공학수학2",
        url="https://canvas.kau.ac.kr/course/view.php?id=12345",
        term="2026-1",
    )
    assert course.course_id == "12345"
    assert course.clean_name == "공학수학2"
    assert course.term == "2026-1"


def test_lecture_item_creation_and_defaults():
    now = datetime.now(timezone.utc)
    lecture = LectureItem(
        course_id="12345",
        week_number=3,
        clip_number=1,
        title="선형미분방정식 해법",
        full_title="[공학수학2] 3주차 1차시: 선형미분방정식 해법",
        status=AttendanceStatus.COMPLETED,
        progress_percent=100.0,
        due_date=now,
        raw_due_date="2026-09-25 23:59",
        is_overdue=False,
        link="https://canvas.kau.ac.kr/mod/vod/view.php?id=999",
    )
    assert lecture.status == AttendanceStatus.COMPLETED
    assert lecture.progress_percent == 100.0
    assert lecture.is_overdue is False

    # Check default values
    default_lecture = LectureItem(
        course_id="12345",
        week_number=1,
        clip_number=1,
        title="Intro",
        full_title="[공학수학2] 1주차 1차시: Intro",
        status=AttendanceStatus.INCOMPLETE,
    )
    assert default_lecture.progress_percent == 0.0
    assert default_lecture.due_date is None
    assert default_lecture.raw_due_date == ""
    assert default_lecture.is_overdue is False
    assert default_lecture.link == ""


def test_attachment_meta():
    attachment = AttachmentMeta(
        filename="homework1.pdf",
        url="https://canvas.kau.ac.kr/files/homework1.pdf",
        filesize="1.2MB",
    )
    assert attachment.filename == "homework1.pdf"
    assert attachment.filesize == "1.2MB"


def test_assessment_item_creation_and_serialization():
    attachment = AttachmentMeta(
        filename="spec.pdf",
        url="https://canvas.kau.ac.kr/files/spec.pdf",
    )
    item = AssessmentItem(
        course_id="12345",
        item_id="6789",
        item_type=AssessmentType.ASSIGNMENT,
        title="과제 1: 상미분방정식 모델링",
        description_html="<p>1번부터 5번까지 풀이 제출</p>",
        description_text="1번부터 5번까지 풀이 제출",
        attachments=[attachment],
        status=SubmissionStatus.NOT_ATTEMPTED,
        raw_due_date="2026-09-30 23:59",
    )
    assert item.item_type == AssessmentType.ASSIGNMENT
    assert item.status == SubmissionStatus.NOT_ATTEMPTED
    assert len(item.attachments) == 1
    assert item.attachments[0].filename == "spec.pdf"
    assert item.is_overdue is False

    # Verify serialization and round-trip
    dumped = item.model_dump()
    assert dumped["item_id"] == "6789"
    assert dumped["attachments"][0]["filename"] == "spec.pdf"

    reconstructed = AssessmentItem.model_validate(dumped)
    assert reconstructed.title == item.title
    assert reconstructed.item_type == AssessmentType.ASSIGNMENT


def test_model_validation_errors():
    with pytest.raises(ValidationError):
        CourseItem(course_id="123")  # missing required fields

    with pytest.raises(ValidationError):
        LectureItem(
            course_id="123",
            week_number=1,
            clip_number=1,
            title="test",
            full_title="test",
            status="invalid_status",
        )
