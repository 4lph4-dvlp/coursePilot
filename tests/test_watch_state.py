"""Unit tests for WatchStateManager and watch state/history persistence."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from kau_assistant.player.models import WatchHistoryRecord, WatchState
from kau_assistant.player.state import WatchStateManager


def test_watch_state_lifecycle(tmp_path: Path):
    manager = WatchStateManager(cache_dir=tmp_path)

    # Initial state should be None
    assert manager.read_state() is None

    # Write running state
    state = WatchState(
        status="running",
        course_name="기초전자실험",
        course_id="1103",
        target_week="2주차",
        video_index=1,
        total_videos=2,
        current_video_title="2주차 1차시 실험",
        duration=300.0,
        current_time=150.0,
        progress_percent=50.0,
        remaining_seconds=150.0,
        pid=12345,
    )
    manager.write_state(state)

    # Read back
    read_back = manager.read_state()
    assert read_back is not None
    assert read_back.status == "running"
    assert read_back.course_name == "기초전자실험"
    assert read_back.video_index == 1
    assert read_back.progress_percent == 50.0
    assert read_back.pid == 12345

    # Clear state
    manager.clear_state()
    assert manager.read_state() is None


def test_watch_state_corrupted_file(tmp_path: Path):
    manager = WatchStateManager(cache_dir=tmp_path)
    state_file = manager.get_state_file_path()
    state_file.write_text("invalid json content", encoding="utf-8")

    assert manager.read_state() is None


def test_watch_history_recording_and_sync(tmp_path: Path):
    manager = WatchStateManager(cache_dir=tmp_path)

    # Empty history initially
    assert manager.get_recent_history() == []

    # Record 2 completed videos
    manager.record_completed_video(
        course_id="1103",
        course_name="기초전자실험",
        target_week="2주차",
        video_title="2주차 1차시",
        task_title="[기전실] 2주차 1차시 강의 시청",
        notion_completed=False,
    )
    manager.record_completed_video(
        course_id="1113",
        course_name="디지털시스템설계",
        target_week="3주차",
        video_title="3주차 1차시",
        task_title="[디시설] 3주차 1차시 강의 시청",
        notion_completed=False,
    )

    uncompleted = manager.get_recent_history(uncompleted_only=True)
    assert len(uncompleted) == 2

    # Query with course filter
    filtered = manager.get_recent_history(course_query="디시설")
    assert len(filtered) == 1
    assert filtered[0].course_name == "디지털시스템설계"

    # Mark first task as synced in Notion
    manager.mark_history_notion_synced(["[기전실] 2주차 1차시 강의 시청"])

    # Check uncompleted again
    uncompleted_after = manager.get_recent_history(uncompleted_only=True)
    assert len(uncompleted_after) == 1
    assert uncompleted_after[0].task_title == "[디시설] 3주차 1차시 강의 시청"

    # Check all history
    all_history = manager.get_recent_history(uncompleted_only=False)
    assert len(all_history) == 2
    assert all_history[0].notion_completed is True
    assert all_history[1].notion_completed is False


def test_stop_running_process_active(tmp_path: Path, monkeypatch):
    manager = WatchStateManager(cache_dir=tmp_path)

    state = WatchState(
        status="running",
        course_name="기초전자실험",
        pid=99999,
    )
    manager.write_state(state)

    # Mock _is_pid_alive: first True, then False after termination
    alive_calls = [True, False]
    monkeypatch.setattr(manager, "_is_pid_alive", lambda pid: alive_calls.pop(0) if alive_calls else False)
    mock_term = MagicMock(return_value=True)
    monkeypatch.setattr(manager, "_terminate_pid", mock_term)

    stopped = manager.stop_running_process()
    assert stopped is True
    mock_term.assert_called_once_with(99999)

    final_state = manager.read_state()
    assert final_state is not None
    assert final_state.status == "stopped"


def test_stop_running_process_inactive(tmp_path: Path, monkeypatch):
    manager = WatchStateManager(cache_dir=tmp_path)

    state = WatchState(
        status="running",
        course_name="기초전자실험",
        pid=88888,
    )
    manager.write_state(state)

    # Process already dead
    monkeypatch.setattr(manager, "_is_pid_alive", lambda pid: False)
    mock_term = MagicMock()
    monkeypatch.setattr(manager, "_terminate_pid", mock_term)

    stopped = manager.stop_running_process()
    assert stopped is False
    assert mock_term.call_count == 0

    final_state = manager.read_state()
    assert final_state is not None
    assert final_state.status == "stopped"
