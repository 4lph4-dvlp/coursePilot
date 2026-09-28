"""Debug snapshot utility to capture failure screenshot and HTML dumps."""

from datetime import datetime
import logging
from pathlib import Path
import re
from playwright.sync_api import Page

from coursepilot.config import DATA_ROOT, resolve_data_path

logger = logging.getLogger(__name__)


def capture_debug_snapshot(
    page: Page,
    action_name: str,
    base_dir: Path = DATA_ROOT / ".cache/debug",
) -> tuple[Path, Path]:
    """Captures a full-page screenshot and HTML content for debugging purposes.

    Saved to base_dir/{YYYYMMDD_HHMMSS}_{action_name}.png and .html.
    Never raises an exception; failures during capture are logged as warnings.
    """
    try:
        base_dir = resolve_data_path(base_dir)
        base_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        clean_action = re.sub(r"[^\w\-]", "_", action_name).strip("_") or "snapshot"

        screenshot_path = base_dir / f"{timestamp}_{clean_action}.png"
        html_path = base_dir / f"{timestamp}_{clean_action}.html"

        try:
            page.screenshot(path=str(screenshot_path), full_page=True)
        except Exception as e:
            logger.warning(f"Failed to capture debug screenshot: {e}")

        try:
            content = page.content()
            html_path.write_text(content, encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to save debug HTML content: {e}")

        logger.info(f"Saved debug snapshot: {screenshot_path.name}, {html_path.name}")
        return screenshot_path, html_path

    except Exception as e:
        logger.warning(f"Failed to prepare debug snapshot: {e}")
        fallback = base_dir / f"failed_{action_name}"
        return fallback.with_suffix(".png"), fallback.with_suffix(".html")
