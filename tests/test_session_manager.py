"""Unit tests for Playwright SessionManager (CONF-03, SCRP-01)."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from coursepilot.config import Settings
from coursepilot.exceptions import NavigationTimeoutError
from coursepilot.session_manager import SessionManager


@pytest.fixture
def mock_playwright_stack():
    """Mock the entire Playwright sync stack (playwright, browser, context, page)."""
    with patch("coursepilot.session_manager.sync_playwright") as mock_sync:
        mock_p = MagicMock()
        mock_sync.return_value.start.return_value = mock_p
        mock_browser = MagicMock()
        mock_p.chromium.launch.return_value = mock_browser
        mock_context = MagicMock()
        mock_browser.new_context.return_value = mock_context
        mock_page = MagicMock()
        mock_context.new_page.return_value = mock_page

        yield {
            "sync": mock_sync,
            "playwright": mock_p,
            "browser": mock_browser,
            "context": mock_context,
            "page": mock_page,
        }


def test_is_valid_cache_file(tmp_path: Path):
    """Verify cache file validation logic."""
    sm = SessionManager(settings=Settings(_env_file=None))

    non_existent = tmp_path / "does_not_exist.json"
    assert sm._is_valid_cache_file(non_existent) is False

    empty_file = tmp_path / "empty.json"
    empty_file.write_text("", encoding="utf-8")
    assert sm._is_valid_cache_file(empty_file) is False

    corrupt_file = tmp_path / "corrupt.json"
    corrupt_file.write_text("{bad json", encoding="utf-8")
    assert sm._is_valid_cache_file(corrupt_file) is False

    non_dict_file = tmp_path / "list.json"
    non_dict_file.write_text("[]", encoding="utf-8")
    assert sm._is_valid_cache_file(non_dict_file) is False

    missing_keys = tmp_path / "other.json"
    missing_keys.write_text(json.dumps({"key": "val"}), encoding="utf-8")
    assert sm._is_valid_cache_file(missing_keys) is False

    valid_cookies = tmp_path / "valid_cookies.json"
    valid_cookies.write_text(json.dumps({"cookies": [{"name": "MoodleSession"}]}), encoding="utf-8")
    assert sm._is_valid_cache_file(valid_cookies) is True

    valid_origins = tmp_path / "valid_origins.json"
    valid_origins.write_text(json.dumps({"origins": []}), encoding="utf-8")
    assert sm._is_valid_cache_file(valid_origins) is True


def test_valid_cache_skips_login(tmp_path: Path, mock_playwright_stack):
    """Verify that when a valid cache exists and user is authenticated, login is skipped."""
    cache_file = tmp_path / "session.json"
    cache_file.write_text(json.dumps({"cookies": [{"name": "MoodleSession"}]}), encoding="utf-8")

    settings = Settings(
        session_cache_path=cache_file,
        lms_url="https://lms.kau.ac.kr",
        _env_file=None,
    )

    with patch("coursepilot.session_manager.perform_login") as mock_login:
        with SessionManager(settings=settings) as sm:
            # Mock authentication check returning True
            sm._check_authenticated = MagicMock(return_value=True)
            page = sm.get_authenticated_page()

            mock_playwright_stack["browser"].new_context.assert_called_once()
            call_kwargs = mock_playwright_stack["browser"].new_context.call_args.kwargs
            assert call_kwargs["storage_state"] == str(cache_file)
            mock_login.assert_not_called()
            assert page is mock_playwright_stack["page"]


def test_expired_cache_auto_healing(tmp_path: Path, mock_playwright_stack):
    """Verify that when cache exists but session is expired, old cache is removed and login is called."""
    cache_file = tmp_path / "session.json"
    cache_file.write_text(json.dumps({"cookies": [{"name": "MoodleSession"}]}), encoding="utf-8")

    settings = Settings(
        session_cache_path=cache_file,
        lms_url="https://lms.kau.ac.kr",
        lms_username="2020123456",
        lms_password="password",
        _env_file=None,
    )

    with patch("coursepilot.session_manager.perform_login") as mock_login:
        with SessionManager(settings=settings) as sm:
            # First check returns False (session expired)
            sm._check_authenticated = MagicMock(return_value=False)
            page = sm.get_authenticated_page()

            mock_login.assert_called_once()
            mock_playwright_stack["context"].storage_state.assert_called_once_with(path=str(cache_file))
            assert page is mock_playwright_stack["page"]


def test_corrupted_cache_fallback(tmp_path: Path, mock_playwright_stack):
    """Verify that corrupted cache is ignored and auto-login runs to recreate valid cache."""
    cache_file = tmp_path / "corrupt.json"
    cache_file.write_text("{corrupted", encoding="utf-8")

    settings = Settings(
        session_cache_path=cache_file,
        lms_url="https://lms.kau.ac.kr",
        _env_file=None,
    )

    with patch("coursepilot.session_manager.perform_login") as mock_login:
        with SessionManager(settings=settings) as sm:
            sm._check_authenticated = MagicMock(return_value=False)
            page = sm.get_authenticated_page()

            call_kwargs = mock_playwright_stack["browser"].new_context.call_args.kwargs
            assert "storage_state" not in call_kwargs
            mock_login.assert_called_once()
            mock_playwright_stack["context"].storage_state.assert_called_once_with(path=str(cache_file))
            assert page is mock_playwright_stack["page"]


def test_navigation_retry_success(mock_playwright_stack):
    """Verify 1 retry on temporary failure before succeeding."""
    settings = Settings(timeout_ms=30000, _env_file=None)
    sm = SessionManager(settings=settings)

    page = mock_playwright_stack["page"]
    # Fail on first attempt, succeed on second attempt
    page.goto.side_effect = [Exception("Network lag"), None]

    sm._navigate_with_retry(page, "https://lms.kau.ac.kr")

    assert page.goto.call_count == 2
    page.wait_for_timeout.assert_called_once_with(2000)


def test_navigation_retry_exhausted(mock_playwright_stack):
    """Verify NavigationTimeoutError when all retries are exhausted."""
    settings = Settings(timeout_ms=30000, _env_file=None)
    sm = SessionManager(settings=settings)

    page = mock_playwright_stack["page"]
    page.goto.side_effect = Exception("Persistent timeout")

    with pytest.raises(NavigationTimeoutError, match="페이지 이동 실패"):
        sm._navigate_with_retry(page, "https://lms.kau.ac.kr")

    assert page.goto.call_count == 2


def test_context_manager_lifecycle(mock_playwright_stack):
    """Verify browser and context are properly closed upon exit."""
    settings = Settings(headless=True, lms_profile="kau", _env_file=None)
    with SessionManager(settings=settings) as sm:
        # Simulate creating a context
        sm._context = mock_playwright_stack["context"]

    mock_playwright_stack["context"].close.assert_called_once()
    mock_playwright_stack["browser"].close.assert_called_once()
    mock_playwright_stack["playwright"].stop.assert_called_once()


def test_check_authenticated_lxp_attached_logout():
    """Verify _check_authenticated returns True for LXP-shaped page with attached logout."""
    settings = Settings(_env_file=None)
    sm = SessionManager(settings=settings)

    page = MagicMock()
    page.url = "https://lxp.kau.ac.kr/"

    def locator_side_effect(selector):
        mock_loc = MagicMock()
        mock_loc.first.is_visible.return_value = False
        if selector == "a[href*='logout']":
            mock_loc.count.return_value = 1
        elif selector == "body.notloggedin":
            mock_loc.count.return_value = 0
        else:
            mock_loc.count.return_value = 0
        return mock_loc

    page.locator.side_effect = locator_side_effect
    assert sm._check_authenticated(page) is True


def test_check_authenticated_login_url_is_false():
    """Verify _check_authenticated returns False when URL contains login."""
    settings = Settings(_env_file=None)
    sm = SessionManager(settings=settings)

    page = MagicMock()
    page.url = "https://lxp.kau.ac.kr/login/index.php"
    assert sm._check_authenticated(page) is False
