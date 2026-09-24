"""Versioned JSON contract v1 for CLI reports, not a raw model dump (D-13)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = 1


class ReportNotice(BaseModel):
    """A user-facing, non-error notice agents must relay before the briefing (for example no courses found)."""

    model_config = ConfigDict(extra="forbid")

    code: str
    message: str


class ReportSummary(BaseModel):
    """Course and urgency-bucket counts shown in the briefing header (D-03)."""

    model_config = ConfigDict(extra="forbid")

    course_count: int
    total_count: int
    overdue_count: int
    due_within_24h_count: int
    later_count: int
    error_count: int


class ReportItem(BaseModel):
    """One incomplete lecture/assignment/quiz entry in the briefing (D-01, D-02)."""

    model_config = ConfigDict(extra="forbid")

    task_id: str
    title: str
    course_id: str
    course_name: str
    course_abbr: str
    task_type: str
    due_date: datetime | None
    remaining_minutes: int | None
    remaining_text: str
    lms_url: str
    detail: str | None


class CourseGroup(BaseModel):
    """Items for one course, ordered as they appear within a briefing section (D-01)."""

    model_config = ConfigDict(extra="forbid")

    course_id: str
    course_name: str
    course_abbr: str
    items: list[ReportItem]


class BriefingSections(BaseModel):
    """Urgency-ordered sections: overdue, due within 24h, then later (D-01, D-05)."""

    model_config = ConfigDict(extra="forbid")

    overdue: list[CourseGroup]
    due_within_24h: list[CourseGroup]
    later: list[CourseGroup]


class ErrorItem(BaseModel):
    """A collection or fatal error surfaced through the safe-error allowlist (D-14)."""

    model_config = ConfigDict(extra="forbid")

    scope: Literal["fatal", "course", "notion"]
    code: str
    message: str
    course_id: str | None = None
    course_name: str | None = None
    task_title: str | None = None


class CheckReport(BaseModel):
    """Versioned `check` command JSON envelope, never a raw SyncTask dump (D-13)."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = SCHEMA_VERSION
    command: Literal["check"] = "check"
    generated_at: datetime
    summary: ReportSummary
    items: BriefingSections
    errors: list[ErrorItem]
    notices: list[ReportNotice] = Field(default_factory=list)


class SyncChange(BaseModel):
    """One changed Scheduler property, rendered before/after as display strings."""

    model_config = ConfigDict(extra="forbid")

    field: str
    before: str | None
    after: str | None


class SyncCreateItem(BaseModel):
    """A task that will become a new Scheduler page."""

    model_config = ConfigDict(extra="forbid")

    task_id: str
    title: str
    course_name: str
    due_date: datetime | None


class SyncUpdateItem(BaseModel):
    """An existing Scheduler page that will receive an allowlisted partial update."""

    model_config = ConfigDict(extra="forbid")

    task_id: str
    title: str
    page_id: str
    notion_url: str
    changes: list[SyncChange]


class SyncSkipItem(BaseModel):
    """A task intentionally left unchanged."""

    model_config = ConfigDict(extra="forbid")

    task_id: str
    title: str
    page_id: str | None
    notion_url: str | None
    reason: str


class SyncCounts(BaseModel):
    """Aggregate create/update/skip/error counts for the sync plan."""

    model_config = ConfigDict(extra="forbid")

    total: int
    create: int
    update: int
    skip: int
    error: int


class SyncSection(BaseModel):
    """Sync half of the JSON contract v1: the create/update/skip plan (D-13, D-16)."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool
    dry_run: bool
    applied: bool
    target_title: str | None
    notice: str | None
    create: list[SyncCreateItem]
    update: list[SyncUpdateItem]
    skip: list[SyncSkipItem]
    counts: SyncCounts


class SyncReport(BaseModel):
    """Versioned `sync` command JSON envelope, never a raw SyncResult dump (D-13)."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = SCHEMA_VERSION
    command: Literal["sync"] = "sync"
    generated_at: datetime
    summary: ReportSummary
    sync: SyncSection | None
    errors: list[ErrorItem]
    notices: list[ReportNotice] = Field(default_factory=list)
