"""DTO data models for LMS scraper."""

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class AttendanceStatus(str, Enum):
    """Attendance / completion status for video lectures."""

    COMPLETED = "completed"
    INCOMPLETE = "incomplete"
    OVERDUE = "overdue"


class SubmissionStatus(str, Enum):
    """Submission status for assignments and quizzes."""

    SUBMITTED = "submitted"
    GRADED = "graded"
    DRAFT = "draft"
    NOT_ATTEMPTED = "not_attempted"


class AssessmentType(str, Enum):
    """Type of assessment activity in LMS."""

    ASSIGNMENT = "assignment"
    QUIZ = "quiz"
    FORUM = "forum"
    OTHER = "other"


class CourseItem(BaseModel):
    """LMS course / subject metadata."""

    course_id: str
    raw_name: str
    clean_name: str
    url: str
    term: str = ""


class LectureItem(BaseModel):
    """Individual video lecture clip item within a course week."""

    course_id: str
    week_number: int
    clip_number: int
    title: str
    full_title: str
    status: AttendanceStatus
    progress_percent: float = 0.0
    due_date: datetime | None = None
    raw_due_date: str = ""
    is_overdue: bool = False
    link: str = ""


class AttachmentMeta(BaseModel):
    """Attachment metadata associated with an assessment or course activity."""

    filename: str
    url: str
    filesize: str = ""


class AssessmentItem(BaseModel):
    """Assessment item (assignment, quiz, exam, discussion) in LMS."""

    course_id: str
    item_id: str
    item_type: AssessmentType
    title: str
    description_html: str = ""
    description_text: str = ""
    attachments: list[AttachmentMeta] = Field(default_factory=list)
    status: SubmissionStatus
    due_date: datetime | None = None
    cutoff_date: datetime | None = None
    raw_due_date: str = ""
    url: str = ""
    is_overdue: bool = False
