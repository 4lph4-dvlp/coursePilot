"""Unit tests for LMS authentication engine (SCRP-01)."""

import pytest
from unittest.mock import MagicMock
from kau_assistant.auth import (
    find_first_visible,
    perform_login,
    USERNAME_SELECTORS,
    PASSWORD_SELECTORS,
    SUBMIT_SELECTORS,
    LOGGED_IN_SELECTORS,
)
from kau_assistant.exceptions import AuthenticationError


def test_find_first_visible_first_match():
    """Verify first visible selector is returned immediately."""
    page = MagicMock()
    loc1 = MagicMock()
    loc1.is_visible.return_value = True
    page.locator.return_value.first = loc1

    result = find_first_visible(page, ["#sel1", "#sel2"])
    assert result == "#sel1"


def test_find_first_visible_fallback():
    """Verify fallback to second selector if first is not visible."""
    page = MagicMock()
    loc1 = MagicMock()
    loc1.is_visible.return_value = False
    loc2 = MagicMock()
    loc2.is_visible.return_value = True

    def locator_side_effect(selector):
        mock_loc = MagicMock()
        if selector == "#sel1":
            mock_loc.first = loc1
        elif selector == "#sel2":
            mock_loc.first = loc2
        return mock_loc

    page.locator.side_effect = locator_side_effect

    result = find_first_visible(page, ["#sel1", "#sel2"])
    assert result == "#sel2"


def test_find_first_visible_none_visible():
    """Verify None is returned when no selectors match or are visible."""
    page = MagicMock()
    loc = MagicMock()
    loc.is_visible.return_value = False
    page.locator.return_value.first = loc

    result = find_first_visible(page, ["#sel1", "#sel2"])
    assert result is None


def test_perform_login_success():
    """Verify complete successful login flow with mock page."""
    page = MagicMock()
    page.url = "https://lms.kau.ac.kr/my/"

    visible_selectors = {
        USERNAME_SELECTORS[0],
        PASSWORD_SELECTORS[0],
        SUBMIT_SELECTORS[0],
        LOGGED_IN_SELECTORS[0],
    }

    def locator_side_effect(selector):
        mock_loc = MagicMock()
        mock_first = MagicMock()
        mock_first.is_visible.return_value = selector in visible_selectors
        mock_loc.first = mock_first
        return mock_loc

    page.locator.side_effect = locator_side_effect

    perform_login(
        page=page,
        username="2020123456",
        password="secretpassword",
        lms_url="https://lms.kau.ac.kr",
    )

    page.goto.assert_called_once_with("https://lms.kau.ac.kr", timeout=30000)
    page.fill.assert_any_call(USERNAME_SELECTORS[0], "2020123456")
    page.fill.assert_any_call(PASSWORD_SELECTORS[0], "secretpassword")
    page.click.assert_called_once_with(SUBMIT_SELECTORS[0])


def test_perform_login_missing_form_elements():
    """Verify AuthenticationError is raised if login form elements cannot be found."""
    page = MagicMock()
    loc = MagicMock()
    loc.is_visible.return_value = False
    page.locator.return_value.first = loc

    with pytest.raises(AuthenticationError, match="로그인 폼 입력 요소를 찾을 수 없습니다"):
        perform_login(
            page=page,
            username="2020123456",
            password="secretpassword",
            lms_url="https://lms.kau.ac.kr",
        )


def test_perform_login_failure_error_message():
    """Verify AuthenticationError with extracted message when login URL remains with error box."""
    page = MagicMock()
    page.url = "https://lms.kau.ac.kr/login/index.php"

    visible_selectors = {
        USERNAME_SELECTORS[0],
        PASSWORD_SELECTORS[0],
        SUBMIT_SELECTORS[0],
    }

    error_box = MagicMock()
    error_box.is_visible.return_value = True
    error_box.inner_text.return_value = "잘못된 사용자명 또는 비밀번호입니다."

    def locator_side_effect(selector):
        mock_loc = MagicMock()
        mock_first = MagicMock()
        if ".alert-danger" in selector:
            return MagicMock(first=error_box)
        mock_first.is_visible.return_value = selector in visible_selectors
        mock_loc.first = mock_first
        return mock_loc

    page.locator.side_effect = locator_side_effect

    with pytest.raises(AuthenticationError, match="로그인 실패: 잘못된 사용자명 또는 비밀번호입니다"):
        perform_login(
            page=page,
            username="2020123456",
            password="wrongpassword",
            lms_url="https://lms.kau.ac.kr",
        )


def test_perform_login_failure_generic_when_no_error_box():
    """Verify fallback error message when URL has login but no error box is visible."""
    page = MagicMock()
    page.url = "https://lms.kau.ac.kr/login"

    visible_selectors = {
        USERNAME_SELECTORS[0],
        PASSWORD_SELECTORS[0],
        SUBMIT_SELECTORS[0],
    }

    def locator_side_effect(selector):
        mock_loc = MagicMock()
        mock_first = MagicMock()
        mock_first.is_visible.return_value = selector in visible_selectors
        mock_loc.first = mock_first
        return mock_loc

    page.locator.side_effect = locator_side_effect

    with pytest.raises(AuthenticationError, match="자격증명이 올바르지 않거나 로그인이 거부되었습니다"):
        perform_login(
            page=page,
            username="2020123456",
            password="wrongpassword",
            lms_url="https://lms.kau.ac.kr",
        )


def test_perform_login_failure_no_logged_in_selector():
    """Verify AuthenticationError when URL changed but dashboard element cannot be confirmed."""
    page = MagicMock()
    page.url = "https://lms.kau.ac.kr/unknown_page"

    # Only form selectors visible, but LOGGED_IN_SELECTORS are NOT visible
    visible_selectors = {
        USERNAME_SELECTORS[0],
        PASSWORD_SELECTORS[0],
        SUBMIT_SELECTORS[0],
    }

    def locator_side_effect(selector):
        mock_loc = MagicMock()
        mock_first = MagicMock()
        mock_first.is_visible.return_value = selector in visible_selectors
        mock_loc.first = mock_first
        return mock_loc

    page.locator.side_effect = locator_side_effect

    with pytest.raises(AuthenticationError, match="대시보드 인증 요소를 확인할 수 없습니다"):
        perform_login(
            page=page,
            username="2020123456",
            password="secretpassword",
            lms_url="https://lms.kau.ac.kr",
        )
