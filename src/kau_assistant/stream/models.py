"""Domain models for pure-Python VOD stream downloading."""

from __future__ import annotations

from enum import Enum
from typing import List, Optional, Tuple

from pydantic import BaseModel, Field


class StreamVariant(BaseModel):
    """M3U8 variant stream playlist info."""

    bandwidth: int
    resolution: Optional[Tuple[int, int]] = None
    uri: str


class StreamKeyInfo(BaseModel):
    """RFC 8216 encryption key specification."""

    method: str = "AES-128"
    uri: str
    iv: Optional[bytes] = None


class StreamSegment(BaseModel):
    """Individual media segment in an HLS playlist."""

    uri: str
    duration: float
    sequence_number: int
    key_info: Optional[StreamKeyInfo] = None


class StreamInfo(BaseModel):
    """Complete stream manifest metadata and segment collection."""

    master_url: str = ""
    media_url: str = ""
    is_direct_mp4: bool = False
    variants: List[StreamVariant] = Field(default_factory=list)
    segments: List[StreamSegment] = Field(default_factory=list)
    total_duration: float = 0.0


class VodDownloadStatus(str, Enum):
    """Status of an individual VOD clip download."""

    DOWNLOADED = "downloaded"
    SKIPPED = "skipped"
    FAILED = "failed"


class DownloadProgress(BaseModel):
    """Real-time progress telemetry for stream downloading."""

    current_segment: int
    total_segments: int
    downloaded_bytes: int
    percent: float


class VodDownloadItemResult(BaseModel):
    """Execution result for a single VOD lecture item."""

    course_name: str
    week_number: int
    clip_number: int
    title: str
    status: VodDownloadStatus
    saved_path: str = ""
    filesize: int = 0
    duration: float = 0.0
    error_message: Optional[str] = None


class CourseVodDownloadResult(BaseModel):
    """Aggregated VOD download results for a specific course."""

    course_id: str
    course_name: str
    target_week: str
    items: List[VodDownloadItemResult] = Field(default_factory=list)


class VodDownloadRunResult(BaseModel):
    """Top-level batch result of a VOD download execution run."""

    total_courses: int = 0
    total_vods: int = 0
    downloaded_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    dry_run: bool = False
    courses: List[CourseVodDownloadResult] = Field(default_factory=list)
