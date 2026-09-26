"""Domain models for course learning materials and download results."""

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class MaterialStatus(str, Enum):
    """Execution status for a learning material item."""

    DOWNLOADED = "downloaded"
    SKIPPED = "skipped"
    VIEWED_ONLY = "viewed_only"
    FAILED = "failed"


class MaterialItem(BaseModel):
    """Represents a learning material (ubfile or resource) within an LXP course."""

    course_id: str
    course_name: str
    week_number: int
    module_id: str
    title: str
    url: str
    is_completed: bool = False
    download_url: str = ""
    suggested_filename: str = ""
    start_date: datetime | None = None
    due_date: datetime | None = None
    raw_due_date: str = ""
    is_overdue: bool = False
    is_available: bool = True


class MaterialDownloadResult(BaseModel):
    """Result of processing a single learning material item."""

    item: MaterialItem
    status: MaterialStatus
    filename: str = ""
    saved_path: str = ""
    filesize: int = 0
    view_success: bool = False
    error_message: str | None = None


class CourseMaterialsResult(BaseModel):
    """Aggregated processing result for materials in a single course."""

    course_id: str
    course_name: str
    target_week: str
    items: list[MaterialDownloadResult] = Field(default_factory=list)


class MaterialsRunResult(BaseModel):
    """Overall execution result for a materials processing session."""

    total_courses: int = 0
    total_materials: int = 0
    downloaded_count: int = 0
    skipped_count: int = 0
    viewed_count: int = 0
    failed_count: int = 0
    dry_run: bool = False
    no_download: bool = False
    courses: list[CourseMaterialsResult] = Field(default_factory=list)
