"""Unit tests for atomic local read state manager and LRU capping."""

from pathlib import Path
from unittest.mock import patch
import pytest

from coursepilot.board.read_state import BoardReadStateManager


def test_read_state_lifecycle(tmp_path: Path):
    """Verify state initialization, is_read check, mark_as_read update, and disk reload."""
    state_file = tmp_path / "board_read_state.json"
    mgr = BoardReadStateManager(state_file_path=state_file, max_entries_per_course=200)

    # Initial state
    assert mgr.is_read(course_id="101", post_id="1001") is False

    # Mark as read
    mgr.mark_as_read(course_id="101", post_ids=["1001", "1002"])
    assert mgr.is_read(course_id="101", post_id="1001") is True
    assert mgr.is_read(course_id="101", post_id="1002") is True
    assert mgr.is_read(course_id="101", post_id="1003") is False

    # File exists and contains valid JSON
    assert state_file.exists()

    # Re-instantiate from disk
    mgr2 = BoardReadStateManager(state_file_path=state_file, max_entries_per_course=200)
    assert mgr2.is_read(course_id="101", post_id="1001") is True
    assert mgr2.is_read(course_id="101", post_id="1002") is True
    assert mgr2.is_read(course_id="101", post_id="1003") is False

    # Clear course
    mgr2.clear_course("101")
    assert mgr2.is_read(course_id="101", post_id="1001") is False


def test_read_state_lru_capping(tmp_path: Path):
    """Verify that adding more than max_entries evicts oldest entries and keeps newest."""
    state_file = tmp_path / "board_read_state.json"
    mgr = BoardReadStateManager(state_file_path=state_file, max_entries_per_course=200)

    # Add 250 post IDs in sequential order (1 to 250)
    post_ids = [str(i) for i in range(1, 251)]
    mgr.mark_as_read(course_id="202", post_ids=post_ids)

    # Reload from disk to verify persisted state
    mgr2 = BoardReadStateManager(state_file_path=state_file, max_entries_per_course=200)
    stored_ids = mgr2._state.courses["202"].read_post_ids
    assert len(stored_ids) == 200

    # Oldest 50 (1..50) must be evicted
    for i in range(1, 51):
        assert mgr2.is_read("202", str(i)) is False

    # Newest 200 (51..250) must be retained
    for i in range(51, 251):
        assert mgr2.is_read("202", str(i)) is True


def test_read_state_corrupted_file_recovery(tmp_path: Path):
    """Verify corrupted JSON file does not crash the manager and initializes empty state."""
    state_file = tmp_path / "corrupted_state.json"
    state_file.write_text("{this is not valid json!}", encoding="utf-8")

    mgr = BoardReadStateManager(state_file_path=state_file)
    assert mgr.is_read("101", "1") is False

    # Should be able to write valid state over it
    mgr.mark_as_read("101", ["1"])
    assert mgr.is_read("101", "1") is True


def test_read_state_atomic_write_error_cleanup(tmp_path: Path):
    """Verify parent directory is created automatically and temp file is cleaned up on error."""
    nested_dir = tmp_path / "nested" / "sub"
    state_file = nested_dir / "board_read_state.json"

    mgr = BoardReadStateManager(state_file_path=state_file)
    mgr.mark_as_read("101", ["10"])
    assert state_file.exists()

    temp_file = state_file.with_suffix(".tmp")
    assert not temp_file.exists()

    # Simulate error during replace
    with patch.object(Path, "replace", side_effect=OSError("Disk write error")):
        with pytest.raises(OSError):
            mgr.save()
        # Verify temp file was cleaned up
        assert not temp_file.exists()
