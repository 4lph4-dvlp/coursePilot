"""Domain models for CoursePilot task synchronization."""

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator

from coursepilot.scraper.date_parser import KST
from coursepilot.scraper.models import AssessmentItem, LectureItem


class TaskType(str, Enum):
    """Activity type of a task."""

    LECTURE = "lecture"
    ASSIGNMENT = "assignment"
    QUIZ = "quiz"
    FORUM = "forum"
    OTHER = "other"
    MATERIAL = "material"


class TaskPriority(str, Enum):
    """Notion priority level (D-06)."""

    P1 = "P1"  # 🔴 Urgent: <= 24 hours to deadline
    P2 = "P2"  # 🟠 Normal: Default for assessments/quizzes/forums
    P3 = "P3"  # 🟡 Normal: Default for video lectures
    P4 = "P4"  # ⚪ Low: Overdue items or completed


class TaskSelect(str, Enum):
    """Notion '선택' select property (D-05)."""

    ROUTINE = "루틴"  # Video lectures
    EVENT = "이벤트"  # Assignments, quizzes, exams, forums


class TaskStatus(str, Enum):
    """Notion '상태' status property (D-10)."""

    NOT_STARTED = "시작 전"
    IN_PROGRESS = "진행 중"
    COMPLETED = "완료"
    DISCARDED = "폐기"


class SyncTask(BaseModel):
    """Unified domain entity representing a schedulable task for Notion."""

    id: str
    course_id: str
    course_name: str
    course_abbr: str
    title: str
    raw_title: str
    task_type: TaskType
    selection: TaskSelect
    category: list[str] = Field(default_factory=lambda: ["학업"])
    due_date: datetime | None = None
    plan_date: datetime | None = None  # Always None by default (D-08)
    priority: TaskPriority
    status: TaskStatus = TaskStatus.NOT_STARTED  # D-10: '시작 전' even if overdue
    memo: str = ""
    is_completed: bool = False
    is_overdue: bool = False
    is_urgent: bool = False
    source_url: str = ""
    week_number: int | None = None
    clip_number: int | None = None
    start_date: datetime | None = None
    is_available: bool = True
    preparation_date: datetime | None = None

    @field_validator("due_date", "plan_date", "start_date", "preparation_date", mode="after")
    @classmethod
    def ensure_kst(cls, v: datetime | None) -> datetime | None:
        """Ensures that datetimes have KST timezone attached."""
        if v is not None:
            if v.tzinfo is None:
                return v.replace(tzinfo=KST)
            return v.astimezone(KST)
        return v

    @property
    def dedup_key(self) -> str:
        """Returns a stable deduplication key for Notion matching (Phase 4)."""
        due_str = self.due_date.strftime("%Y-%m-%d %H:%M") if self.due_date else "no_due"
        return f"{self.title}|{due_str}"


class Course(BaseModel):
    """Domain model representing a course with its activities and tasks."""

    course_id: str
    name: str
    abbreviation: str
    url: str = ""
    term: str = ""
    lectures: list[LectureItem] = Field(default_factory=list)
    assessments: list[AssessmentItem] = Field(default_factory=list)
    tasks: list[SyncTask] = Field(default_factory=list)
