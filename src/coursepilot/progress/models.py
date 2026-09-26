"""Domain models and versioned JSON contract (schema_version: 1) for activity progress."""

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from coursepilot.report_models import ErrorItem, ReportNotice

SCHEMA_VERSION: Literal[1] = 1


class ActivityType(str, Enum):
    """Classification of learning activities within an LXP course."""

    VOD = "vod"
    ASSIGNMENT = "assignment"
    QUIZ = "quiz"
    MATERIAL = "material"


class ActivityItem(BaseModel):
    """Normalized activity item across all 4 learning activity types."""

    model_config = ConfigDict(extra="forbid")

    course_id: str
    activity_type: ActivityType
    week_number: int
    title: str
    is_completed: bool
    due_date: datetime | None = None
    start_date: datetime | None = None
    is_available: bool = True
    raw_due_date: str = ""
    is_overdue: bool = False
    is_urgent: bool = False
    url: str = ""
    module_id: str | None = None
    clip_number: int | None = None


class ActivityCount(BaseModel):
    """Counts and completion percentage for a specific activity type."""

    model_config = ConfigDict(extra="forbid")

    completed: int = 0
    total: int = 0
    rate: float = 0.0


class ActivityBreakdown(BaseModel):
    """4-tier activity breakdown (VOD, assignment, quiz, material)."""

    model_config = ConfigDict(extra="forbid")

    vod: ActivityCount = Field(default_factory=ActivityCount)
    assignment: ActivityCount = Field(default_factory=ActivityCount)
    quiz: ActivityCount = Field(default_factory=ActivityCount)
    material: ActivityCount = Field(default_factory=ActivityCount)


class CourseProgress(BaseModel):
    """Progress statistics and categorized activity items for a single course."""

    model_config = ConfigDict(extra="forbid")

    course_id: str
    course_name: str
    course_abbr: str
    current_week: int
    current_open_rate: float
    current_open_completed: int
    current_open_total: int
    past_weeks_rate: float
    past_weeks_completed: int
    past_weeks_total: int
    semester_overall_rate: float
    semester_completed: int
    semester_total: int
    activity_breakdown: ActivityBreakdown
    current_week_items: list[ActivityItem] = Field(default_factory=list)
    missed_past_items: list[ActivityItem] = Field(default_factory=list)
    all_items: list[ActivityItem] = Field(default_factory=list)
    status: Literal["ok", "error"] = "ok"
    error_message: str | None = None


class DashboardSummary(BaseModel):
    """Aggregated KPI summary across all enrolled courses."""

    model_config = ConfigDict(extra="forbid")

    total_courses: int
    current_open_rate: float
    current_open_completed: int
    current_open_total: int
    past_weeks_rate: float
    past_weeks_completed: int
    past_weeks_total: int
    semester_overall_rate: float
    semester_completed: int
    semester_total: int
    missed_past_count: int
    current_week_todo_count: int
    activity_totals: ActivityBreakdown


class ProgressReport(BaseModel):
    """Versioned JSON contract (schema_version: 1) for progress dashboard command."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = SCHEMA_VERSION
    command: Literal["progress"] = "progress"
    status: Literal["success", "partial_success", "error"]
    generated_at: datetime
    is_cached: bool = False
    summary: DashboardSummary
    courses: list[CourseProgress]
    errors: list[ErrorItem] = Field(default_factory=list)
    notices: list[ReportNotice] = Field(default_factory=list)
