"""Data models for VOD playback progress and execution options."""

from pydantic import BaseModel, Field


class PlaybackOptions(BaseModel):
    """Configuration options for automated VOD playback."""

    muted: bool = Field(default=True, description="Whether to mute video audio during background playback")
    poll_interval_seconds: float = Field(default=5.0, description="Interval in seconds between progress pollings")
    playback_rate: float = Field(default=1.0, description="Playback speed (1.0x required for first watch on LMS)")
    max_wait_seconds: float | None = Field(
        default=None, description="Maximum total wait time in seconds before aborting (None = duration + buffer)"
    )


class PlaybackProgress(BaseModel):
    """Snapshot of VOD playback progress."""

    vod_url: str
    title: str = ""
    duration: float = 0.0
    current_time: float = 0.0
    progress_percent: float = 0.0
    is_completed: bool = False
    is_paused: bool = False
    error_message: str | None = None
