"""Stable DTOs for the Notion synchronization boundary."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from kau_assistant.domain.models import SyncTask, TaskPriority, TaskStatus


class NotionTarget(BaseModel):
    """Resolved Notion database container and child data source."""

    database_id: str
    data_source_id: str
    title: str


class ExistingPage(BaseModel):
    """Canonical subset of an existing Scheduler page."""

    page_id: str
    title: str
    due_date: datetime | None = None
    priority: TaskPriority | None = None
    memo: str = ""
    status: TaskStatus | str | None = None
    plan_date: datetime | None = None


class FieldDiff(BaseModel):
    """One changed Scheduler property."""

    property_name: str
    before: Any = None
    after: Any = None


class CreateAction(BaseModel):
    """A page that should be created."""

    task_id: str
    title: str
    task: SyncTask
    executed: bool = False


class UpdateAction(BaseModel):
    """An existing page that should receive an allowlisted partial update."""

    task_id: str
    title: str
    page_id: str
    properties: dict[str, Any] = Field(default_factory=dict)
    diffs: list[FieldDiff] = Field(default_factory=list)
    executed: bool = False


class SkipAction(BaseModel):
    """A task intentionally left unchanged."""

    task_id: str
    title: str
    page_id: str | None = None
    reason: str
    executed: bool = False


class ErrorAction(BaseModel):
    """A safe, reportable per-task or integration error."""

    task_id: str | None = None
    title: str = ""
    page_id: str | None = None
    code: str
    message: str
    executed: bool = False


class SyncStats(BaseModel):
    """Aggregate action counts consumed by the Phase 5 reporter."""

    total: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: int = 0


class SyncResult(BaseModel):
    """Complete result of one Notion synchronization attempt."""

    enabled: bool
    dry_run: bool = False
    target: NotionTarget | None = None
    created: list[CreateAction] = Field(default_factory=list)
    updated: list[UpdateAction] = Field(default_factory=list)
    skipped: list[SkipAction] = Field(default_factory=list)
    errors: list[ErrorAction] = Field(default_factory=list)
    stats: SyncStats = Field(default_factory=SyncStats)

