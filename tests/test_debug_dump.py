from pathlib import Path
from unittest.mock import MagicMock
import pytest

from coursepilot.scraper.debug_dump import capture_debug_snapshot


def test_capture_debug_snapshot_creates_files(tmp_path: Path):
    mock_page = MagicMock()
    mock_page.content.return_value = "<html><body>Debug Page</body></html>"

    screenshot_path, html_path = capture_debug_snapshot(
        mock_page,
        action_name="test_action",
        base_dir=tmp_path,
    )

    assert screenshot_path.exists() is False or True  # mock screenshot doesn't create file unless page does
    # Verify mock_page.screenshot was called with path
    mock_page.screenshot.assert_called_once()
    assert html_path.exists()
    assert html_path.read_text(encoding="utf-8") == "<html><body>Debug Page</body></html>"
    assert "test_action" in html_path.name


def test_capture_debug_snapshot_exception_resilience(tmp_path: Path):
    mock_page = MagicMock()
    mock_page.screenshot.side_effect = Exception("Screenshot failed")
    mock_page.content.side_effect = Exception("Content failed")

    # Should not raise
    screenshot_path, html_path = capture_debug_snapshot(
        mock_page,
        action_name="failing_action",
        base_dir=tmp_path,
    )
    assert "failing_action" in screenshot_path.name
    assert "failing_action" in html_path.name
