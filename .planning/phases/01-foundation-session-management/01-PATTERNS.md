# Phase 1: Foundation & Session Management - Pattern Mapping

**Generated:** 2026-09-21  
**Phase:** 01-foundation-session-management  
**Status:** Complete  

---

## 1. Codebase Status & Greenfield Context

This is a **greenfield project** with no pre-existing Python source files or test suites in the repository (`coursepilot`). Consequently:
- **No internal codebase analogs exist** for new Python files.
- All code patterns, structural conventions, and implementation signatures are derived directly from the technical specifications in [01-RESEARCH.md](01-RESEARCH.md) and locked user decisions in [01-CONTEXT.md](01-CONTEXT.md).
- This document establishes the **canonical blueprints** that downstream implementation phases (Phase 1 through Phase 5) must replicate.

---

## 2. File Pattern Mapping

The following table maps every file to be created in Phase 1 to its pattern archetype, canonical reference, and responsibilities.

| Target File | Pattern Archetype | Reference in 01-RESEARCH.md | Primary Responsibilities |
|-------------|-------------------|-----------------------------|--------------------------|
| `pyproject.toml` | Packaging / Dependency Spec | Section 6 (`Standard Stack`) & Section 7 (`Package Audit`) | Project metadata, build system, dependencies (`playwright`, `pydantic-settings`, `rich`, `click`, etc.), dev dependencies (`pytest`, `pytest-mock`). |
| `.env.example` | Environment Configuration Template | Section 1 (`User Constraints` D-01) & Section 8 (`Security Domain`) | Documents required and optional environment variables (`LMS_URL`, `LMS_USERNAME`, `LMS_PASSWORD`, `NOTION_API_KEY`, `NOTION_DATABASE_ID`, `HEADLESS`). |
| `.gitignore` | VCS Ignore Specification | Section 1 (`User Constraints` D-03) & Section 8 (`Security Domain`) | Excludes `.env`, `.cache/`, `*.pyc`, `__pycache__/`, `.pytest_cache/`, `.venv/`, `dist/`. |
| `config/course_mappings.json` | Configuration Data (JSON) | Section 1 (`User Constraints` D-05) & Section 5 (`Pattern 4`) | Decoupled JSON mapping for course names to abbreviations (`{"공학수학2": "공수2", ...}`). |
| `src/coursepilot/__init__.py` | Package Root | N/A (Standard Python package convention) | Package version (`__version__ = "0.1.0"`) and public API exports. |
| `src/coursepilot/exceptions.py` | Error Hierarchy | Section 4 (`Architectural Responsibility Map`) | Custom exceptions inheriting from `CoursePilotError` (`AuthenticationError`, `NavigationTimeoutError`, `ConfigError`). |
| `src/coursepilot/config.py` | Pydantic Settings Provider | Section 9.1 (`Configuration Model`) | Strongly typed `Settings` class using `pydantic-settings` (`BaseSettings`, `SettingsConfigDict`), singleton accessor `get_settings()`. |
| `src/coursepilot/course_mapping.py` | Tolerant Data Mapper | Section 9.2 (`Course Mapping Loader`) | `load_course_mappings()`, `get_abbreviation()`, non-breaking fallback with friendly guidance logging. |
| `src/coursepilot/auth.py` | Web Authentication Engine | Section 9.3 (`Auth & Login Flow`) | Multi-selector fallback lists, `find_first_visible()`, `perform_login()`, login error detection and verification. |
| `src/coursepilot/session_manager.py` | Playwright Resource Orchestrator | Section 9.4 (`Session Manager`) | Context manager (`__enter__`, `__exit__`), session caching (`storage_state`), session validity checking, auto-relogin, 30s timeout with 1 retry. |
| `tests/__init__.py` | Test Package Root | N/A (Standard Pytest convention) | Marks `tests/` directory as a package for test discovery. |
| `tests/conftest.py` | Pytest Shared Fixtures | Section 10 (`Validation Architecture`) | Reusable fixtures (`tmp_path`, dummy `Settings`, mock `Page`/`BrowserContext`/`Browser`). |
| `tests/test_config.py` | Settings Unit Tests | Section 10 (`test_config.py`) | Tests default values, `.env` file loading, environment variable precedence, type validation. |
| `tests/test_course_mapping.py` | Course Mapping Unit Tests | Section 10 (`test_course_mapping.py`) | Tests JSON loading, abbreviation lookup, missing key fallback, missing/corrupted file fallback. |
| `tests/test_auth.py` | Authentication Unit Tests | Section 10 (`test_auth.py`) | Tests cascading selector matching, login input execution, error box detection, success verification. |
| `tests/test_session_manager.py` | Session Orchestration Tests | Section 10 (`test_session_manager.py`) | Tests valid cache load, corrupted cache recovery, session expiry auto-relogin, 1-retry navigation error handling. |

---

## 3. Detailed Architectural Patterns & Code Blueprints

### Pattern 1: Pydantic Settings Single Source of Truth (`config.py`)
- **Archetype:** Type-safe settings with environment variable bindings.
- **Copy Pattern:**
  ```python
  from pathlib import Path
  from pydantic import Field
  from pydantic_settings import BaseSettings, SettingsConfigDict

  class Settings(BaseSettings):
      model_config = SettingsConfigDict(
          env_file=".env",
          env_file_encoding="utf-8",
          extra="ignore",
      )

      # LMS Settings
      lms_url: str = Field(default="https://lms.kau.ac.kr", description="KAU LMS URL")
      lms_username: str = Field(default="", description="학번/아이디")
      lms_password: str = Field(default="", description="비밀번호")

      # Execution Options
      headless: bool = Field(default=True, description="헤드리스 브라우저 구동 여부")
      timeout_ms: int = Field(default=30000, description="페이지 네비게이션 타임아웃(ms)")

      # Notion Settings
      notion_api_key: str = Field(default="", description="Notion Integration API Key")
      notion_database_id: str = Field(
          default="21d53280-64be-80ec-af4e-000b679f03bb",
          description="Notion Scheduler Database ID",
      )

      # Paths
      session_cache_path: Path = Field(
          default=Path(".cache/session.json"),
          description="세션 스토리지 파일 경로",
      )
      course_mappings_path: Path = Field(
          default=Path("config/course_mappings.json"),
          description="과목명 약칭 매핑 파일 경로",
      )

  _settings_instance: Settings | None = None

  def get_settings() -> Settings:
      global _settings_instance
      if _settings_instance is None:
          _settings_instance = Settings()
      return _settings_instance
  ```
- **Rules to Follow:**
  - Never use `os.environ.get()` directly in business modules; always inject `Settings` or call `get_settings()`.
  - Always use `pathlib.Path` for file path fields.
  - Set `extra="ignore"` to prevent unknown environment variables from raising validation errors.

---

### Pattern 2: Cascading Multi-Selector Strategy (`auth.py`)
- **Archetype:** Tolerant web element selector fallback.
- **Copy Pattern:**
  ```python
  import logging
  from playwright.sync_api import Page, TimeoutError
  from coursepilot.exceptions import AuthenticationError

  logger = logging.getLogger("coursepilot.auth")

  USERNAME_SELECTORS = [
      "#input-username",                           # KAU Coursemos/Moodle
      "#pseudonym_session_unique_id",              # Standard Canvas LMS
      "input[name='username']",
      "input[name='pseudonym_session[unique_id]']",
      "#username",
  ]
  PASSWORD_SELECTORS = [
      "#input-password",                           # KAU Coursemos/Moodle
      "#pseudonym_session_password",               # Standard Canvas LMS
      "input[name='password']",
      "input[name='pseudonym_session[password]']",
      "#password",
  ]
  SUBMIT_SELECTORS = [
      "input[name='loginbutton']",                 # KAU Coursemos/Moodle
      "input[type='submit'].btn-success",
      "button[type='submit']",
      ".Button--login",                            # Standard Canvas LMS
  ]
  LOGGED_IN_SELECTORS = [
      ".usermenu",                                 # Moodle/Coursemos profile menu
      "a[href*='logout']",                         # Logout link
      "#global_nav_profile_link",                  # Canvas global nav
      ".ic-app-header",                            # Canvas app header
      ".block_coursemos_my_courses",               # Coursemos course list block
      ".my-course",
      "#dashboard",
  ]

  def find_first_visible(page: Page, selectors: list[str], timeout: int = 5000) -> str | None:
      for selector in selectors:
          try:
              loc = page.locator(selector).first
              if loc.is_visible(timeout=timeout):
                  return selector
          except Exception:
              continue
      return None
  ```
- **Rules to Follow:**
  - Order selectors from most specific (KAU LMS Moodle/Coursemos) to generic fallback.
  - Always catch Playwright timeouts gracefully when testing visibility of alternative selectors.
  - Check for error banners (`.alert-danger`, `.loginerrors`, `#flash_error_message`) before declaring authentication failure.

---

### Pattern 3: Context Manager & Session Auto-Healing (`session_manager.py`)
- **Archetype:** Safe browser lifecycle management with optimistic cache recovery.
- **Copy Pattern:**
  ```python
  import json
  import logging
  from pathlib import Path
  from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page, Playwright
  from coursepilot.config import Settings, get_settings
  from coursepilot.auth import perform_login, find_first_visible, LOGGED_IN_SELECTORS
  from coursepilot.exceptions import NavigationTimeoutError

  logger = logging.getLogger("coursepilot.session_manager")

  class SessionManager:
      def __init__(self, settings: Settings | None = None, headful: bool = False):
          self.settings = settings or get_settings()
          self.headless = False if headful else self.settings.headless
          self._playwright: Playwright | None = None
          self._browser: Browser | None = None
          self._context: BrowserContext | None = None

      def __enter__(self):
          self._playwright = sync_playwright().start()
          self._browser = self._playwright.chromium.launch(headless=self.headless)
          return self

      def __exit__(self, exc_type, exc_val, exc_tb):
          if self._context:
              try:
                  self._context.close()
              except Exception:
                  pass
          if self._browser:
              try:
                  self._browser.close()
              except Exception:
                  pass
          if self._playwright:
              try:
                  self._playwright.stop()
              except Exception:
                  pass

      def _is_valid_cache_file(self, path: Path) -> bool:
          if not path.exists() or path.stat().st_size < 2:
              return False
          try:
              with open(path, "r", encoding="utf-8") as f:
                  data = json.load(f)
                  return isinstance(data, dict) and ("cookies" in data or "origins" in data)
          except Exception:
              return False
  ```
- **Rules to Follow:**
  - Clean up browser resources in `__exit__` in reverse order of creation: context -> browser -> playwright.
  - Never crash on a corrupted `.cache/session.json`; validate and discard before instantiating `BrowserContext(storage_state=...)`.
  - In `_navigate_with_retry`, attempt up to 2 times with a 2-second backoff before raising `NavigationTimeoutError`.
  - Check for session expiration both via URL pattern (`login` in `page.url.lower()`) and via missing `LOGGED_IN_SELECTORS`.

---

### Pattern 4: Tolerant Fallback with Guidance (`course_mapping.py`)
- **Archetype:** Non-breaking dictionary lookup with proactive user feedback.
- **Copy Pattern:**
  ```python
  import json
  import logging
  from pathlib import Path

  logger = logging.getLogger("coursepilot.course_mapping")

  DEFAULT_MAPPINGS = {
      "공학수학2": "공수2",
      "자료구조": "자구",
      "디지털시스템설계": "디시설",
  }

  def load_course_mappings(path: Path | str = "config/course_mappings.json") -> dict[str, str]:
      file_path = Path(path)
      if not file_path.exists():
          logger.warning(f"매핑 파일({file_path})을 찾을 수 없습니다. 기본 매핑을 사용합니다.")
          return DEFAULT_MAPPINGS.copy()
      try:
          with open(file_path, "r", encoding="utf-8") as f:
              data = json.load(f)
              if isinstance(data, dict):
                  return data
              logger.warning("매핑 파일 형식이 올바르지 않습니다 (dict 필요). 기본 매핑 사용.")
              return DEFAULT_MAPPINGS.copy()
      except Exception as e:
          logger.error(f"매핑 파일 로드 중 오류 발생: {e}. 기본 매핑 사용.")
          return DEFAULT_MAPPINGS.copy()

  def get_abbreviation(course_name: str, mappings: dict[str, str]) -> str:
      cleaned = course_name.strip()
      if cleaned in mappings:
          return mappings[cleaned]
      logger.info(
          f"과목 '{cleaned}'에 대한 축약어 매핑이 없습니다. "
          f"config/course_mappings.json에 등록을 권장합니다 (원본 이름 사용)."
      )
      return cleaned
  ```
- **Rules to Follow:**
  - Never raise `KeyError` or exit on unmapped course names; always return `cleaned` (original name).
  - Strip leading/trailing whitespace before dictionary lookup.
  - Provide a fallback default dictionary if the JSON file is missing or invalid.

---

### Pattern 5: Custom Exception Hierarchy (`exceptions.py`)
- **Archetype:** Domain-specific custom exceptions.
- **Copy Pattern:**
  ```python
  class CoursePilotError(Exception):
      """Base exception for all coursepilot errors."""
      pass

  class AuthenticationError(CoursePilotError):
      """Raised when LMS login fails or credentials are invalid."""
      pass

  class NavigationTimeoutError(CoursePilotError):
      """Raised when page navigation exceeds timeout even after retry."""
      pass

  class ConfigError(CoursePilotError):
      """Raised when essential configuration is missing or invalid."""
      pass
  ```
- **Rules to Follow:**
  - All project exceptions must inherit from `CoursePilotError`.
  - Distinguish operational errors (e.g., `AuthenticationError`, `NavigationTimeoutError`) from configuration errors (`ConfigError`).

---

## 4. Coding Conventions & Quality Guidelines

1. **Python Version & Type Annotations:**
   - Target Python `>= 3.11` (compatible with 3.14).
   - Use PEP 604 union types (`str | None`, `Path | str`) instead of `typing.Union` / `typing.Optional`.
   - Use built-in generics (`dict[str, str]`, `list[str]`) instead of `typing.Dict`, `typing.List`.

2. **Synchronous Playwright Standard:**
   - Use `playwright.sync_api` throughout.
   - Do NOT mix `async_api` into Phase 1 to prevent event-loop clashes with CLI/Windows runners.

3. **File I/O & Path Handling:**
   - Always instantiate `Path` from `pathlib`.
   - Always open text files with explicit `encoding="utf-8"`.

4. **Console Output & Logging:**
   - Standard logger names follow module hierarchy: `coursepilot.<module>`.
   - User-facing terminal messages should leverage `rich.console.Console` or informative logging levels (`logger.info`, `logger.warning`).

5. **Security & Secrets Handling:**
   - Never log or print `lms_password` or `notion_api_key`.
   - Ensure `.cache/` and `.env` are always listed in `.gitignore`.

---

## 5. Testing Patterns (`tests/`)

### Test Conventions:
- Every test file corresponds to a module in `src/coursepilot/`:
  - `tests/test_config.py` -> `src/coursepilot/config.py`
  - `tests/test_course_mapping.py` -> `src/coursepilot/course_mapping.py`
  - `tests/test_auth.py` -> `src/coursepilot/auth.py`
  - `tests/test_session_manager.py` -> `src/coursepilot/session_manager.py`
- Test function naming: `test_<function_or_method>_<scenario>_<expected_result>()`.

### Fixtures Pattern (`tests/conftest.py`):
```python
import pytest
from pathlib import Path
from coursepilot.config import Settings

@pytest.fixture
def dummy_settings(tmp_path: Path) -> Settings:
    return Settings(
        lms_url="https://lms.kau.ac.kr",
        lms_username="2023123456",
        lms_password="dummy_password",
        headless=True,
        timeout_ms=5000,
        session_cache_path=tmp_path / ".cache" / "session.json",
        course_mappings_path=tmp_path / "config" / "course_mappings.json",
    )
```

### Mocking Pattern for Playwright:
- Use `pytest-mock` (`mocker` fixture) to mock Playwright's `sync_playwright`, `Browser`, `BrowserContext`, and `Page` objects.
- Mock `page.goto`, `page.fill`, `page.click`, and locator queries so tests execute in milliseconds without launching actual browser instances or making real network requests.
- Live integration tests against real LMS servers should be decorated with `@pytest.mark.live` and skipped by default when credentials are unset.

---

*Phase: 1-Foundation & Session Management*  
*Pattern Mapping Completed: 2026-09-21*
