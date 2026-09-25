"""State management and persistence for VOD playback lifecycle and history."""

from __future__ import annotations

import json
import logging
import os
import signal
import time
from datetime import datetime
from pathlib import Path

from kau_assistant.config import Settings, get_settings
from kau_assistant.player.models import WatchHistoryRecord, WatchState

logger = logging.getLogger(__name__)


class WatchStateManager:
    """Manages atomic state tracking, stop signals, and completed watch history."""

    def __init__(self, cache_dir: Path | None = None, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.cache_dir = Path(cache_dir) if cache_dir else self.settings.session_cache_path.parent

    def get_state_file_path(self) -> Path:
        """Returns the file path for real-time watch state."""
        return self.cache_dir / "watch_state.json"

    def get_history_file_path(self) -> Path:
        """Returns the file path for persistent watch history."""
        return self.cache_dir / "watch_history.json"

    def write_state(self, state: WatchState) -> None:
        """Atomically writes current watch state to JSON using a temp file and replace (D-12-04)."""
        path = self.get_state_file_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(".tmp")
        try:
            temp_path.write_text(state.model_dump_json(indent=2), encoding="utf-8")
            temp_path.replace(path)
        except Exception as e:
            logger.error(f"Failed to write watch state: {e}")
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)

    def read_state(self) -> WatchState | None:
        """Reads and parses current watch state; returns None if missing or corrupted."""
        path = self.get_state_file_path()
        if not path.exists():
            return None
        try:
            content = path.read_text(encoding="utf-8")
            return WatchState.model_validate_json(content)
        except Exception as e:
            logger.debug(f"Failed to parse watch state: {e}")
            return None

    def clear_state(self) -> None:
        """Cleans up the state file or resets state to idle."""
        path = self.get_state_file_path()
        if path.exists():
            try:
                path.unlink(missing_ok=True)
            except Exception as e:
                logger.debug(f"Failed to unlink state file: {e}")

    def record_completed_video(
        self,
        course_id: str,
        course_name: str,
        target_week: str,
        video_title: str,
        task_title: str,
        notion_completed: bool = False,
    ) -> None:
        """Appends a completed video playback record to watch_history.json (D-12-07)."""
        history_path = self.get_history_file_path()
        history_path.parent.mkdir(parents=True, exist_ok=True)

        records: list[dict] = []
        if history_path.exists():
            try:
                data = json.loads(history_path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    records = data
            except Exception as e:
                logger.warning(f"Failed to load existing watch history: {e}")
                records = []

        new_record = WatchHistoryRecord(
            course_id=course_id,
            course_name=course_name,
            target_week=target_week,
            video_title=video_title,
            task_title=task_title,
            watched_at=datetime.now(),
            notion_completed=notion_completed,
        )
        records.append(new_record.model_dump(mode="json"))

        temp_path = history_path.with_suffix(".tmp")
        try:
            temp_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
            temp_path.replace(history_path)
            logger.info(f"Recorded completed video to history: {video_title}")
        except Exception as e:
            logger.error(f"Failed to save watch history: {e}")
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)

    def get_recent_history(
        self,
        course_query: str | None = None,
        uncompleted_only: bool = True,
    ) -> list[WatchHistoryRecord]:
        """Reads history records, optionally filtering by course query and completion status."""
        history_path = self.get_history_file_path()
        if not history_path.exists():
            return []

        try:
            data = json.loads(history_path.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                return []
            parsed = [WatchHistoryRecord.model_validate(item) for item in data]
        except Exception as e:
            logger.error(f"Failed to read watch history: {e}")
            return []

        results = []
        q = course_query.strip().lower() if course_query else None

        for rec in parsed:
            if uncompleted_only and rec.notion_completed:
                continue
            if q:
                if q not in rec.course_name.lower() and q not in rec.task_title.lower():
                    continue
            results.append(rec)

        return results

    def mark_history_notion_synced(self, task_titles: list[str]) -> None:
        """Updates matching records in watch_history.json to notion_completed = True."""
        history_path = self.get_history_file_path()
        if not history_path.exists() or not task_titles:
            return

        title_set = set(task_titles)
        try:
            data = json.loads(history_path.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                return
            updated = False
            for item in data:
                if item.get("task_title") in title_set:
                    item["notion_completed"] = True
                    updated = True

            if updated:
                temp_path = history_path.with_suffix(".tmp")
                temp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                temp_path.replace(history_path)
        except Exception as e:
            logger.error(f"Failed to update watch history sync status: {e}")

    def _is_pid_alive(self, pid: int) -> bool:
        """Checks if a process with given PID is currently active."""
        if pid <= 0:
            return False
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        except OSError as e:
            if getattr(e, "winerror", None) == 87:
                return False
            return False

    def _terminate_pid(self, pid: int) -> bool:
        """Sends termination signal to the process."""
        if pid <= 0:
            return False
        try:
            os.kill(pid, signal.SIGTERM)
            return True
        except OSError:
            return False

    def stop_running_process(self) -> bool:
        """Terminates the active playback process if running and updates state (D-12-06)."""
        state = self.read_state()
        if not state or not state.pid:
            return False

        if not self._is_pid_alive(state.pid):
            if state.status == "running":
                state.status = "stopped"
                self.write_state(state)
            return False

        success = self._terminate_pid(state.pid)
        deadline = time.time() + 3.0
        while time.time() < deadline:
            if not self._is_pid_alive(state.pid):
                break
            time.sleep(0.2)

        state.status = "stopped"
        self.write_state(state)
        return success
