"""Playwright session manager with cache invalidation, auto-healing, and retry (CONF-03, SCRP-01)."""

import json
import logging
from pathlib import Path
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page, Playwright
from kau_assistant.config import Settings, get_settings
from kau_assistant.auth import perform_login, find_first_visible, LOGGED_IN_SELECTORS
from kau_assistant.exceptions import NavigationTimeoutError

logger = logging.getLogger("kau_assistant.session_manager")


class SessionManager:
    """Manages browser lifecycle, session caching, and automated re-authentication."""

    def __init__(self, settings: Settings | None = None, headful: bool = False):
        self.settings = settings or get_settings()
        self.headless = False if headful else self.settings.headless
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None

    def __enter__(self) -> "SessionManager":
        if self._playwright is None:
            self._playwright = sync_playwright().start()
        if self._browser is None:
            self._browser = self._playwright.chromium.launch(headless=self.headless)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def close(self) -> None:
        """Safely release all browser and Playwright resources in reverse order."""
        if self._context:
            try:
                self._context.close()
            except Exception:
                pass
            self._context = None

        if self._browser:
            try:
                self._browser.close()
            except Exception:
                pass
            self._browser = None

        if self._playwright:
            try:
                self._playwright.stop()
            except Exception:
                pass
            self._playwright = None

    def _is_valid_cache_file(self, path: Path) -> bool:
        """Validate if the given file exists, is non-empty, and has valid storage_state JSON schema."""
        if not path.exists() or path.stat().st_size < 2:
            return False
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return isinstance(data, dict) and ("cookies" in data or "origins" in data)
        except Exception:
            return False

    def _navigate_with_retry(self, page: Page, url: str) -> None:
        """Navigate to a URL with 30s timeout and 1 automatic retry after 2s backoff."""
        for attempt in range(2):
            try:
                page.goto(url, timeout=self.settings.timeout_ms)
                return
            except Exception as e:
                if attempt == 0:
                    logger.warning(f"페이지 이동 지연 발생({e}), 1회 재시도합니다...")
                    try:
                        page.wait_for_timeout(2000)
                    except Exception:
                        pass
                else:
                    raise NavigationTimeoutError(f"페이지 이동 실패 ({url}): {e}") from e

    def _check_authenticated(self, page: Page) -> bool:
        """Check if the current page indicates an active authenticated session."""
        if "login" in page.url.lower():
            return False
        logged_in = find_first_visible(page, LOGGED_IN_SELECTORS, timeout=5000)
        return logged_in is not None

    def get_authenticated_page(self) -> Page:
        """Obtain an authenticated Page, reusing existing cached session or performing auto-login."""
        if self._browser is None:
            self.__enter__()

        assert self._browser is not None

        cache_path = self.settings.session_cache_path
        has_cache = self._is_valid_cache_file(cache_path)

        context_options: dict = {
            "viewport": {"width": 1280, "height": 800},
            "user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ),
            "locale": "ko-KR",
            "timezone_id": "Asia/Seoul",
        }

        if has_cache:
            logger.info(f"기존 세션 캐시({cache_path}) 로드 중...")
            context_options["storage_state"] = str(cache_path)

        self._context = self._browser.new_context(**context_options)
        page = self._context.new_page()

        # 30초 타임아웃 및 1회 재시도 로직으로 LMS 진입 (D-08)
        self._navigate_with_retry(page, self.settings.lms_url)

        # 세션 유효성 판별 (D-04)
        is_authenticated = self._check_authenticated(page)

        if not is_authenticated:
            logger.info("세션이 만료되었거나 캐시가 없습니다. 자동 로그인을 수행합니다.")
            if cache_path.exists():
                try:
                    cache_path.unlink(missing_ok=True)
                except Exception:
                    pass

            perform_login(
                page=page,
                username=self.settings.lms_username,
                password=self.settings.lms_password,
                lms_url=self.settings.lms_url,
                timeout_ms=self.settings.timeout_ms,
            )

            # 새 세션 저장 (D-03)
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            self._context.storage_state(path=str(cache_path))
            logger.info(f"새 세션이 {cache_path}에 저장되었습니다.")
        else:
            logger.info("기존 캐시된 세션이 유효합니다. 로그인을 건너뜁니다.")

        return page
