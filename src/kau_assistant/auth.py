"""LMS authentication engine with cascading multi-selector strategy (SCRP-01)."""

import logging
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from kau_assistant.exceptions import AuthenticationError

logger = logging.getLogger("kau_assistant.auth")

USERNAME_SELECTORS: list[str] = [
    "#input-username",                           # KAU Coursemos/Moodle
    "#pseudonym_session_unique_id",              # Standard Canvas LMS
    "input[name='username']",
    "input[name='pseudonym_session[unique_id]']",
    "#username",
]

PASSWORD_SELECTORS: list[str] = [
    "#input-password",                           # KAU Coursemos/Moodle
    "#pseudonym_session_password",               # Standard Canvas LMS
    "input[name='password']",
    "input[name='pseudonym_session[password]']",
    "#password",
]

SUBMIT_SELECTORS: list[str] = [
    "input[name='loginbutton']",                 # KAU Coursemos/Moodle
    "input[type='submit'].btn-success",
    "button[type='submit']",
    ".Button--login",                            # Standard Canvas LMS
]

LOGGED_IN_SELECTORS: list[str] = [
    ".usermenu",                                 # Moodle/Coursemos profile menu
    "a[href*='logout']",                         # Logout link
    "#global_nav_profile_link",                  # Canvas global nav
    ".ic-app-header",                            # Canvas app header
    ".block_coursemos_my_courses",               # Coursemos course list block
    ".my-course",
    "#dashboard",
]

ERROR_SELECTORS: str = ".alert-danger, .loginerrors, #flash_error_message"


def find_first_visible(page: Page, selectors: list[str], timeout: int = 5000) -> str | None:
    """Find the first selector in the given list that is visible on the page."""
    for selector in selectors:
        try:
            loc = page.locator(selector).first
            if loc.is_visible(timeout=timeout):
                return selector
        except Exception:
            continue
    return None


def is_logged_in(page: Page, timeout: int = 5000) -> bool:
    """Check if the current page indicates an authenticated session.

    Returns True if any LOGGED_IN_SELECTORS element is visible, or if an attached
    logout link exists in the DOM and the body tag does not have the 'notloggedin' class.
    """
    if find_first_visible(page, LOGGED_IN_SELECTORS, timeout=timeout):
        return True

    try:
        logout_count = page.locator("a[href*='logout']").count()
        notloggedin_count = page.locator("body.notloggedin").count()
        return logout_count >= 1 and notloggedin_count == 0
    except Exception:
        return False


def perform_login(
    page: Page,
    username: str,
    password: str,
    lms_url: str,
    timeout_ms: int = 30000,
) -> None:
    """Perform LMS login using cascading multi-selector strategy.

    Raises:
        AuthenticationError: If form elements are missing, credentials fail, or dashboard check fails.
    """
    logger.info(f"LMS 로그인 페이지({lms_url})로 이동 중...")
    page.goto(lms_url, timeout=timeout_ms)

    user_sel = find_first_visible(page, USERNAME_SELECTORS, timeout=5000)
    pass_sel = find_first_visible(page, PASSWORD_SELECTORS, timeout=5000)
    submit_sel = find_first_visible(page, SUBMIT_SELECTORS, timeout=5000)

    if not user_sel or not pass_sel or not submit_sel:
        raise AuthenticationError("로그인 폼 입력 요소를 찾을 수 없습니다.")

    logger.info("자격증명 입력 중...")
    page.fill(user_sel, username)
    page.fill(pass_sel, password)

    logger.info("로그인 버튼 클릭...")
    page.click(submit_sel)

    try:
        page.wait_for_load_state("networkidle", timeout=timeout_ms)
    except PlaywrightTimeoutError:
        pass

    # Verify if still on login page or if an error message is visible
    if "login" in page.url.lower():
        error_box = page.locator(ERROR_SELECTORS).first
        is_err_visible = False
        try:
            is_err_visible = error_box.is_visible(timeout=2000)
        except Exception:
            pass

        if is_err_visible:
            err_text = error_box.inner_text().strip()
        else:
            err_text = "자격증명이 올바르지 않거나 로그인이 거부되었습니다."

        raise AuthenticationError(f"로그인 실패: {err_text}")

    if not is_logged_in(page, timeout=10000):
        raise AuthenticationError("로그인 후 대시보드 인증 요소를 확인할 수 없습니다.")

    logger.info("로그인 성공 및 대시보드 진입 확인 완료.")
