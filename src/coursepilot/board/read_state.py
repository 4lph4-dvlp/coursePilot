"""Atomic local read state manager for tracking viewed board posts per course."""

import logging
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

from coursepilot.config import DATA_ROOT, resolve_data_path

logger = logging.getLogger(__name__)


class CourseReadState(BaseModel):
    """Read state tracking for a single course."""

    read_post_ids: list[str] = Field(default_factory=list)
    last_read_at: datetime | None = None


class BoardReadStateFile(BaseModel):
    """Schema for the board_read_state.json persistence file."""

    version: int = 1
    courses: dict[str, CourseReadState] = Field(default_factory=dict)


class BoardReadStateManager:
    """Manages atomic persistence of read post IDs with per-course LRU capping."""

    def __init__(
        self,
        state_file_path: Path | str | None = None,
        max_entries_per_course: int = 200,
    ) -> None:
        self.state_file_path = (
            resolve_data_path(Path(state_file_path)) if state_file_path else DATA_ROOT / ".cache/board_read_state.json"
        )
        self.max_entries = max_entries_per_course
        self._state = self._load()

    def _load(self) -> BoardReadStateFile:
        """Loads state from disk; safely returns empty state if missing or corrupted."""
        if not self.state_file_path.exists():
            return BoardReadStateFile()

        try:
            content = self.state_file_path.read_text(encoding="utf-8")
            return BoardReadStateFile.model_validate_json(content)
        except Exception as e:
            logger.warning(
                f"Failed to parse read state file {self.state_file_path}: {e}. Initializing fresh state."
            )
            return BoardReadStateFile()

    def save(self) -> None:
        """Atomically saves current read state to disk using a temporary file and replace."""
        self.state_file_path.parent.mkdir(parents=True, exist_ok=True)
        temp_file = self.state_file_path.with_suffix(".tmp")
        try:
            temp_file.write_text(self._state.model_dump_json(indent=2), encoding="utf-8")
            temp_file.replace(self.state_file_path)
        except Exception as e:
            logger.error(f"Failed to atomically write read state to {self.state_file_path}: {e}")
            if temp_file.exists():
                temp_file.unlink(missing_ok=True)
            raise

    def is_read(self, course_id: str | int, post_id: str) -> bool:
        """Checks if a given post has been marked as read in the specified course."""
        c_id = str(course_id)
        course_state = self._state.courses.get(c_id)
        if not course_state:
            return False
        return str(post_id) in course_state.read_post_ids

    def mark_as_read(self, course_id: str | int, post_ids: list[str]) -> None:
        """Marks a list of post IDs as read for a course, enforcing FIFO/LRU capping."""
        if not post_ids:
            return

        c_id = str(course_id)
        if c_id not in self._state.courses:
            self._state.courses[c_id] = CourseReadState()

        course_state = self._state.courses[c_id]
        existing_ids = course_state.read_post_ids
        seen = set(existing_ids)

        for pid in post_ids:
            pid_str = str(pid)
            if pid_str not in seen:
                existing_ids.append(pid_str)
                seen.add(pid_str)

        # Enforce LRU/FIFO limit (keep the most recent max_entries)
        if len(existing_ids) > self.max_entries:
            existing_ids = existing_ids[-self.max_entries :]

        course_state.read_post_ids = existing_ids
        course_state.last_read_at = datetime.now()
        self.save()

    def clear_course(self, course_id: str | int) -> None:
        """Clears read records for a specific course."""
        c_id = str(course_id)
        if c_id in self._state.courses:
            del self._state.courses[c_id]
            self.save()
