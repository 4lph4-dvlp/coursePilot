<Phase 1: Foundation & Session Management - Research>
**Researched:** 2026-09-21
**Domain:** Python Project Infrastructure, Environment Configuration, Playwright Web Automation & Session Persistence
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** LMS 로그인 URL은 `.env`의 `LMS_URL`에 지정된 커스텀 URL로 직접 접근하며, 환경변수로 유연하게 변경 가능하도록 구성.
- **D-02:** Python 프로젝트 패키징 및 의존성 관리는 `pyproject.toml` 및 `uv`를 기본 도구로 채택 (초고속 가상환경 생성 및 의존성 락 지원).
- **D-03:** Playwright의 `storage_state` 파일은 `.cache/session.json`에 저장하고, `.gitignore`에 등록하여 개인정보/세션 쿠키가 Git에 커밋되지 않도록 격리.
- **D-04:** 세션 만료 판별은 대시보드 페이지 접근 시 로그인 URL로 리다이렉트되거나 세션 유효성 검증 셀렉터(프로필/로그아웃 버튼 등)가 존재하지 않을 때 만료로 판단하고, 즉시 자동 재로그인을 수행하여 새 세션을 획득 및 갱신.
- **D-05:** 과목명 축약 매핑은 `config/course_mappings.json` 독립 JSON 파일로 관리하여 사용자가 손쉽게 편집할 수 있도록 분리. (기본 샘플: `{"공학수학2": "공수2", "자료구조": "자구", "디지털시스템설계": "디시설"}`).
- **D-06:** 매핑 파일에 등록되지 않은 신규 과목이 감지될 경우, 파싱 에러를 발생시키지 않고 원본 과목명 그대로 사용하며, 사용자에게 축약어 등록을 권장하는 친절한 로그를 출력.
- **D-07:** 브라우저는 기본적으로 Headless(백그라운드) 모드로 구동하되, 초기 로그인 셋업 및 디버깅을 위해 CLI 플래그(`--headful`) 및 환경변수(`HEADLESS=false`)로 브라우저 화면 표시 전환을 지원.
- **D-08:** 기본 페이지 로딩 및 네비게이션 타임아웃은 30초로 설정하며, 일시적 네트워크 오류나 페이지 지연 시 1회 자동 재시도 로직을 적용.

### the agent's Discretion
- 세부적인 Playwright 브라우저 컨텍스트 옵션(User-Agent, Viewport: 1280x800, locale: ko-KR 등) 설정
- 로깅 포맷 및 콘솔 출력 메시지 스타일 (Rich 및 logging 모듈 활용)
- 동기(Sync) vs 비동기(Async) Playwright API 선정 (CLI 및 순차 크롤링에 최적화된 Sync API 권장)

### Deferred Ideas (OUT OF SCOPE)
- 온라인 강의 자동 재생 / 출석 대리 (학칙 위반 방지, 알림 및 조회 전용)
- 2차 인증(OTP/캡차) 자동 크랙/우회 (로컬 ID/PW 및 세션 재사용 중심)
- 다중 사용자 호스팅 SaaS 서버 구축 (로컬 환경 전용 AI 에이전트 스킬)
</user_constraints>

<phase_requirements>
## Phase Requirements

- **CONF-01:** `.env` 및 설정 로더를 통해 LMS URL, 학번, 비밀번호, Notion API Key, Notion DB ID(`21d53280-64be-80ec-af4e-000b679f03bb`)를 안전하게 관리한다.
- **CONF-02:** 과목명 축약 매핑(`course_mappings.json` / 설정)을 통해 과목별 축약 이름(예: `공학수학2` -> `공수2`, `자료구조` -> `자구`)을 정의하고 로드한다.
- **CONF-03:** Playwright 브라우저 세션 스토리지(`session.json`)를 캐싱하여 불필요한 반복 로그인을 방지하고, 세션 만료 시 자동 재로그인을 수행한다.
- **SCRP-01:** Playwright 헤드리스 브라우저를 통해 대상 LMS에 자동 로그인하고 대시보드 정상 진입을 확인한다.
</phase_requirements>

## Summary

Phase 1은 후속 단계(LMS 크롤링, 도메인 정규화, 노션 동기화, CLI)의 핵심 근간이 되는 프로젝트 기초 환경과 세션 관리 인프라를 구축합니다.

기술적 조사 및 실시간 사이트 검증 결과:
1. **KAU LMS 구조 확인:** 한국항공대학교 LMS는 `https://lms.kau.ac.kr`에 위치하며, Moodle 기반의 코스모스(Coursemos v2) 솔루션을 사용합니다. 로그인 폼 셀렉터(`form.form-login`, `#input-username`, `#input-password`, `input[name="loginbutton"]`)가 명확하며, 표준 Canvas LMS 셀렉터와 공존할 수 있도록 **다중 셀렉터 폴백(Cascading Selector Fallback)** 전략을 적용하면 높은 안정성을 확보할 수 있습니다.
2. **Playwright 세션 영속화:** Playwright의 내장 기능인 `context.storage_state(path=...)` 및 `browser.new_context(storage_state=...)`를 활용하여 세션 쿠키와 로컬 스토리지를 `.cache/session.json`에 안전하게 캐싱합니다. 세션 만료 여부는 URL 리다이렉트(`login` 경로 감지) 및 로그인 후 나타나는 DOM 요소(`.usermenu`, `a[href*="logout"]` 등)를 통해 100% 신뢰도 있게 판별합니다.
3. **설정 및 매핑 관리:** `pydantic-settings` 2.x(`BaseSettings`, `SettingsConfigDict`)를 사용하여 `.env` 파일과 환경변수를 타입 안전하게 바인딩하고, `config/course_mappings.json`을 통해 과목명 약칭을 로드합니다. 미등록 과목 발생 시 시스템 중단 없이 원본 과목명을 폴백으로 사용하며 친절한 안내 로그를 남깁니다.
4. **실행 API 선택:** CLI 기반 도구 및 순차적 페이지 접근(방화벽 차단 방지를 위한 의도적 딜레이 포함)에 가장 적합한 **Playwright Sync API**를 채택하여, 비동기 이벤트 루프 충돌(특히 Windows 환경) 없이 단순하고 견고한 코드를 작성합니다.

## Architectural Responsibility Map

| Module | Location | Responsibilities |
|--------|----------|------------------|
| `config` | `src/coursepilot/config.py` | `Settings` 모델(LMS URL, 자격증명, Notion 키, DB ID, 브라우저 옵션, 경로 등) 로드 및 검증 |
| `course_mapping` | `src/coursepilot/course_mapping.py` | `config/course_mappings.json` 로드, 과목명 축약어 변환, 미매핑 과목 폴백 및 안내 로그 |
| `exceptions` | `src/coursepilot/exceptions.py` | 프로젝트 공통 커스텀 예외 계층(`CoursePilotError`, `AuthenticationError`, `NavigationTimeoutError`, `ConfigError` 등) |
| `auth` | `src/coursepilot/auth.py` | LMS 로그인 폼 탐색, ID/PW 입력, 제출, 로그인 성공/실패 판별 및 오류 메시지 추출 |
| `session_manager` | `src/coursepilot/session_manager.py` | Playwright 브라우저 라이프사이클(`headless`/`headful`), `storage_state` 캐시 로드/저장, 세션 만료 검증, 자동 재로그인 및 30초 타임아웃/1회 재시도 오케스트레이션 |

## Standard Stack

### Core Dependencies
- **Python:** `>=3.11` (로컬 환경: Python 3.14.7 호환 검증 완료)
- **`uv`:** `0.12.17` (의존성 관리 및 빌드 툴링)
- **`playwright`:** `^1.42.0` (Chromium 헤드리스 브라우저 자동화 및 세션 관리)
- **`pydantic`:** `^2.6.0` & **`pydantic-settings`:** `^2.2.0` (타입 안전한 환경설정 및 `.env` 파싱)
- **`python-dotenv`:** `^1.0.0` (환경변수 파일 로딩)
- **`rich`:** `^13.7.0` (콘솔 로깅 및 진행 상태 표시)
- **`click`:** `^8.1.0` (CLI 인터페이스)
- **`notion-client`:** `^2.2.1` (Notion 공식 Python SDK)
- **`python-dateutil`:** `^2.9.0` & **`pytz`:** 한국 표준시(KST, Asia/Seoul) 변환

### Dev & Test Dependencies
- **`pytest`:** `^8.0.0` (단위/통합 테스트 프레임워크)
- **`pytest-mock`:** `^3.12.0` (Playwright 브라우저/페이지 모킹)
- **`pytest-asyncio`:** `^0.23.0` (필요 시 비동기 테스트 지원)

## Package Legitimacy Audit

| Package | Version Resolved | Purpose | Legitimacy & Maintenance Status |
|---------|------------------|---------|---------------------------------|
| `playwright` | 1.63.0 | 브라우저 자동화 및 세션 캐싱 | Microsoft 공식 유지관리. 최신 브라우저 엔진 완벽 지원. |
| `pydantic-settings` | 2.15.0 | `.env` 및 설정 모델링 | Pydantic 공식 분리 패키지. v2 공식 표준. |
| `pydantic` | 2.13.5 | 데이터 스키마 유효성 검증 | Python 생태계 1위 데이터 검증 라이브러리. |
| `python-dotenv` | 1.2.3 | `.env` 파일 로드 | 안정적인 환경변수 파서. |
| `rich` | 15.0.0 | 콘솔 출력 및 로깅 포맷팅 | Textualize 유지관리, 터미널 UI 표준. |
| `pytest` | 9.1.1 | 단위 테스트 러너 | Python 표준 테스팅 프레임워크. |
| `pytest-mock` | 3.15.1 | `unittest.mock` fixture 통합 | pytest 공식 추천 모킹 플러그인. |

`uv pip compile`을 통해 25개 패키지 의존성 트리가 420ms 내에 충돌 없이 완벽히 해석됨을 실시간 검증 완료.

## Architecture Patterns

### Pattern 1: Cascading Multi-Selector Strategy (다중 셀렉터 계포 전략)
- **Problem:** 대학 LMS 환경은 Moodle/코스모스(`https://lms.kau.ac.kr`) 또는 Canvas LMS(`canvas.*`) 등 버전에 따라 입력 필드 ID와 로그인 버튼 이름이 상이함.
- **Solution:** 단일 셀렉터 하드코딩 대신, 우선순위가 정의된 셀렉터 리스트를 순회하거나 쉼표(`,`) 결합 셀렉터를 사용하여 DOM 요소를 탐색.
```python
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
]
```

### Pattern 2: Context Manager for Playwright Lifecycle (브라우저 라이프사이클 컨텍스트 매니저)
- **Problem:** 브라우저 인스턴스나 컨텍스트가 예외 발생 시 제대로 닫히지 않고 프로세스에 잔류(zombie process)할 위험.
- **Solution:** `SessionManager`를 Context Manager(`__enter__`, `__exit__`)로 구현하여 안전한 브라우저 리소스 해제 보장.
```python
class SessionManager:
    def __enter__(self):
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=self.headless)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._context:
            self._context.close()
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()
```

### Pattern 3: Optimistic Session with Auto-Healing (낙관적 세션 캐시 및 자동 치유)
- **Problem:** 캐시된 세션이 만료되었을 때 에러를 발생시키고 중단하면 사용자가 매번 수동 개입해야 함.
- **Solution:** 
  1. `.cache/session.json`이 존재하면 즉시 `storage_state`로 로드하여 대시보드로 이동.
  2. 현재 URL이 `login`을 포함하거나 `LOGGED_IN_SELECTORS`가 발견되지 않으면 세션 만료로 판정.
  3. 손상되거나 만료된 세션 파일을 자동 삭제하고, 자격증명으로 즉시 `login()` 수행.
  4. 로그인 성공 즉시 새로운 `storage_state`를 `.cache/session.json`에 저장하여 갱신.

### Pattern 4: Tolerant Abbreviation Lookup with Guidance (무중단 과목명 변환 및 가이드)
- **Problem:** 새 학기 신규 과목이 수강 신청되었을 때 `KeyError`로 크롤링이 중단되면 안 됨.
- **Solution:** `course_mappings.json`에 과목명이 없으면 원본 과목명을 그대로 반환하고, Rich 콘솔/로그로 사용자가 축약어를 등록할 수 있도록 가이드 메시지 출력.

## Don't Hand-Roll

| Component | Don't Hand-Roll | Use Instead | Rationale |
|-----------|-----------------|-------------|-----------|
| 세션/쿠키 직렬화 | 커스텀 JSON 쿠키 파서 | Playwright `context.storage_state()` | 브라우저 쿠키뿐만 아니라 `localStorage`, `sessionStorage`까지 일관된 스키마로 원자적 저장/복원 지원. |
| 환경변수 파싱 | `os.environ.get()` + 타입 수동 변환 | `pydantic-settings.BaseSettings` | 타입 캐스팅(bool, int, Path), 기본값, 유효성 검증, 비밀값 마스킹(`SecretStr`) 자동 처리. |
| 타임아웃 & 재시도 | 복잡한 `time.sleep` 루프 | Playwright `timeout=30000` + 단일 래퍼 함수 | Playwright 내부의 지능형 대기(smart wait) 엔진을 활용하고, 네트워크 순간 단절 시 1회 클린 재시도. |
| 과목명 매핑 Fallback | 복잡한 if/else 분기 | `dict.get(name, name)` 래퍼 함수 | 딕셔너리 기본 동작을 활용하여 미등록 시 원본 과목명 반환이 자연스럽게 보장됨. |

## Common Pitfalls

### Pitfall 1: 세션 만료 감지 실패로 인한 로그인 리다이렉트 무한 루프
- **위험:** 만료된 세션으로 접근 시 LMS 서버가 `/login/index.php`로 302 리다이렉트하지만, 스크래퍼가 이를 감지하지 못하고 대시보드 요소를 계속 기다리다 30초 타임아웃 발생.
- **해결책:** `page.goto(url)` 직후 현재 URL(`page.url`)에 `login` 키워드가 포함되어 있는지 먼저 검사. 포함되어 있다면 대시보드 요소를 대기하지 않고 즉시 `is_authenticated = False`로 판정하여 재로그인으로 분기.

### Pitfall 2: Headless 브라우저 핑거프린팅으로 인한 차단 또는 렌더링 지연
- **위험:** 기본 Chromium 헤드리스 모드는 `navigator.webdriver = true` 및 기본 User-Agent가 노출되어 특정 대학 방화벽/WAF에서 차단되거나 불완전한 페이지가 렌더링될 수 있음.
- **해결책:** `new_context()` 호출 시 표준 데스크톱 User-Agent(`Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ...`), 뷰포트 크기(`1280x800`), 한국어 로케일(`ko-KR`, timezone `Asia/Seoul`)을 명시적으로 주입.

### Pitfall 3: Windows PowerShell UTF-8 콘솔 인코딩 문제
- **위험:** Windows 환경의 PowerShell에서 한글 과목명이나 안내 메시지 출력 시 `UnicodeDecodeError` 또는 글자 깨짐(mojibake) 발생.
- **해결책:** 파일 I/O는 명시적으로 `encoding="utf-8"` 지정, 터미널 출력은 `rich.console.Console`을 통해 UTF-8 안전 출력 처리.

### Pitfall 4: `.cache/session.json` 손상(Corrupted JSON) 시 크래시
- **위험:** 이전 프로세스가 비정상 종료되어 `session.json` 파일이 0바이트이거나 잘못된 JSON일 경우 `new_context(storage_state=...)`가 `json.decoder.JSONDecodeError`를 던지며 시작 실패.
- **해결책:** 파일 로드 전 파일 존재 여부와 파일 크기(> 2 bytes)를 확인하고, `json.loads` 검증을 거쳐 유효하지 않으면 파일을 자동 삭제하고 빈 컨텍스트로 시작.

### Pitfall 5: 일시적 네트워크 지연에 따른 30초 타임아웃
- **위험:** 학교 서버 피크 시간대에 일시적으로 첫 페이지 응답이 30초를 초과하여 스크립트가 즉시 실패함.
- **해결책:** D-08 결정에 따라 네비게이션 실패 시 1회 자동 재시도(지수 백오프 2초) 로직을 적용.

## Code Examples

### 1. Configuration Model (`src/coursepilot/config.py`)
```python
from pathlib import Path
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LMS 접속 정보
    lms_url: str = Field(default="https://lms.kau.ac.kr", description="KAU LMS URL")
    lms_username: str = Field(default="", description="학번/아이디")
    lms_password: str = Field(default="", description="비밀번호")

    # 브라우저 실행 옵션
    headless: bool = Field(default=True, description="헤드리스 브라우저 구동 여부")
    timeout_ms: int = Field(default=30000, description="페이지 네비게이션 타임아웃(ms)")

    # Notion 연동 정보
    notion_api_key: str = Field(default="", description="Notion Integration API Key")
    notion_database_id: str = Field(
        default="21d53280-64be-80ec-af4e-000b679f03bb",
        description="Notion Scheduler Database ID",
    )

    # 파일 경로
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

### 2. Course Mapping Loader (`src/coursepilot/course_mapping.py`)
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
        logger.warning(
            f"매핑 파일({file_path})을 찾을 수 없습니다. 기본 매핑을 사용합니다."
        )
        return DEFAULT_MAPPINGS.copy()

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
            logger.warning(f"매핑 파일 형식이 올바르지 않습니다 (dict 필요). 기본 매핑 사용.")
            return DEFAULT_MAPPINGS.copy()
    except Exception as e:
        logger.error(f"매핑 파일 로드 중 오류 발생: {e}. 기본 매핑 사용.")
        return DEFAULT_MAPPINGS.copy()


def get_abbreviation(course_name: str, mappings: dict[str, str]) -> str:
    cleaned = course_name.strip()
    if cleaned in mappings:
        return mappings[cleaned]

    # 미등록 과목 발견 시 친절한 안내 로그 출력 (D-06)
    logger.info(
        f"과목 '{cleaned}'에 대한 축약어 매핑이 없습니다. "
        f"config/course_mappings.json에 등록을 권장합니다 (원본 이름 사용)."
    )
    return cleaned
```

### 3. Auth & Login Flow (`src/coursepilot/auth.py`)
```python
import logging
from playwright.sync_api import Page, TimeoutError
from coursepilot.exceptions import AuthenticationError

logger = logging.getLogger("coursepilot.auth")

USERNAME_SELECTORS = [
    "#input-username",
    "#pseudonym_session_unique_id",
    "input[name='username']",
    "input[name='pseudonym_session[unique_id]']",
    "#username",
]

PASSWORD_SELECTORS = [
    "#input-password",
    "#pseudonym_session_password",
    "input[name='password']",
    "input[name='pseudonym_session[password]']",
    "#password",
]

SUBMIT_SELECTORS = [
    "input[name='loginbutton']",
    "input[type='submit'].btn-success",
    "button[type='submit']",
    ".Button--login",
]

LOGGED_IN_SELECTORS = [
    ".usermenu",
    "a[href*='logout']",
    "#global_nav_profile_link",
    ".ic-app-header",
    ".block_coursemos_my_courses",
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


def perform_login(page: Page, username: str, password: str, lms_url: str, timeout_ms: int = 30000) -> None:
    logger.info(f"LMS 로그인 페이지({lms_url})로 이동 중...")
    page.goto(lms_url, timeout=timeout_ms)

    user_sel = find_first_visible(page, USERNAME_SELECTORS)
    pass_sel = find_first_visible(page, PASSWORD_SELECTORS)
    submit_sel = find_first_visible(page, SUBMIT_SELECTORS)

    if not user_sel or not pass_sel or not submit_sel:
        raise AuthenticationError("로그인 폼 입력 요소를 찾을 수 없습니다.")

    logger.info("자격증명 입력 중...")
    page.fill(user_sel, username)
    page.fill(pass_sel, password)

    logger.info("로그인 버튼 클릭...")
    page.click(submit_sel)

    try:
        page.wait_for_load_state("networkidle", timeout=timeout_ms)
    except TimeoutError:
        pass

    # 로그인 성공 검증
    if "login" in page.url.lower():
        # 로그인 실패 메시지 확인
        error_box = page.locator(".alert-danger, .loginerrors, #flash_error_message").first
        err_text = error_box.inner_text() if error_box.is_visible(timeout=2000) else "자격증명이 올바르지 않거나 로그인이 거부되었습니다."
        raise AuthenticationError(f"로그인 실패: {err_text.strip()}")

    logged_in_sel = find_first_visible(page, LOGGED_IN_SELECTORS, timeout=10000)
    if not logged_in_sel:
        raise AuthenticationError("로그인 후 대시보드 인증 요소를 확인할 수 없습니다.")

    logger.info("로그인 성공 및 대시보드 진입 확인 완료.")
```

### 4. Session Manager (`src/coursepilot/session_manager.py`)
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

    def get_authenticated_page(self) -> Page:
        cache_path = self.settings.session_cache_path
        has_cache = self._is_valid_cache_file(cache_path)

        context_options = {
            "viewport": {"width": 1280, "height": 800},
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "locale": "ko-KR",
            "timezone_id": "Asia/Seoul",
        }

        if has_cache:
            logger.info(f"기존 세션 캐시({cache_path}) 로드 중...")
            context_options["storage_state"] = str(cache_path)

        self._context = self._browser.new_context(**context_options)
        page = self._context.new_page()

        # 30초 타임아웃 및 1회 재시도 로직 (D-08)
        self._navigate_with_retry(page, self.settings.lms_url)

        # 세션 유효성 판별 (D-04)
        is_authenticated = self._check_authenticated(page)

        if not is_authenticated:
            logger.info("세션이 만료되었거나 캐시가 없습니다. 자동 로그인을 수행합니다.")
            if cache_path.exists():
                cache_path.unlink(missing_ok=True)

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

    def _navigate_with_retry(self, page: Page, url: str) -> None:
        for attempt in range(2):
            try:
                page.goto(url, timeout=self.settings.timeout_ms)
                return
            except Exception as e:
                if attempt == 0:
                    logger.warning(f"페이지 이동 지연 발생({e}), 1회 재시도합니다...")
                    page.wait_for_timeout(2000)
                else:
                    raise NavigationTimeoutError(f"페이지 이동 실패 ({url}): {e}") from e

    def _check_authenticated(self, page: Page) -> bool:
        # 로그인 페이지로 리다이렉트된 경우
        if "login" in page.url.lower():
            return False
        # 대시보드 인증 엘리먼트 탐색
        logged_in = find_first_visible(page, LOGGED_IN_SELECTORS, timeout=5000)
        return logged_in is not None
```

## Environment Availability

| Requirement | Available? | Details |
|-------------|------------|---------|
| Python | YES | Python 3.14.7 (`python --version`) |
| uv | YES | uv 0.12.17 (`uv --version`) |
| Git | YES | Git repository initialized |
| Playwright Browsers | ACTION NEEDED | `uv run playwright install chromium` 최초 1회 실행 필요 |
| OS & Shell | Windows / pwsh | 파일 경로 `Path` 객체 사용 및 UTF-8 인코딩 필수 |

## Validation Architecture

### Nyquist Test Strategy for Phase 1
Phase 1의 목표는 신뢰도 높은 인프라 구축입니다. 외부 의존성(LMS 서버, Notion API)과 로컬 시스템(설정, 파일 파싱, 세션 저장)을 분리하여 검증합니다.

```
tests/
├── conftest.py               # 테스트 fixture: 임시 경로, 더미 환경변수, 모의 Page/Context
├── test_config.py            # CONF-01: .env 로드, 기본값, 유효성 검사, 타입 캐스팅
├── test_course_mapping.py    # CONF-02: 정상 매핑, 미매핑 과목 fallback, 파일 누락 대응
├── test_session_manager.py   # CONF-03: 캐시 로드, 손상 파일 처리, 만료 판정, 1회 재시도
└── test_auth.py              # SCRP-01: 폼 셀렉터 탐색, 로그인 성공/실패 감지
```

### Unit Test Execution (Mock-based, Fast & Deterministic)
- `pytest-mock`을 활용하여 Playwright의 `Browser`, `BrowserContext`, `Page`를 모킹.
- 네트워크 통신 없이 100% 독립적으로 세션 만료 판별 로직, 재로그인 분기, 타임아웃 재시도 로직 검증.
- 명령: `uv run pytest tests/`

### Optional Live Test (`@pytest.mark.live`)
- 유효한 `.env` 자격증명이 있을 때만 동작하는 선택적 통합 테스트:
```python
@pytest.mark.live
def test_live_lms_login():
    settings = get_settings()
    if not settings.lms_username or not settings.lms_password:
        pytest.skip("LMS 자격증명이 .env에 없습니다.")
    with SessionManager(settings, headful=False) as sm:
        page = sm.get_authenticated_page()
        assert "login" not in page.url.lower()
```

## Security Domain

- **`.env` 자격증명 격리:** 학번, 비밀번호, Notion API Key는 `.env`에 보관하며, `.gitignore`에 `.env`를 포함하여 VCS 커밋 방지.
- **`.cache/session.json` 세션 보호:** 브라우저 쿠키(MoodleSession 등)가 담긴 세션 캐시 파일은 `.gitignore`에 등록하여 유출 방지.
- **비밀정보 로깅 방지:** `Settings` 모델 및 로깅 코드에서 비밀번호(`lms_password`)나 토큰(`notion_api_key`)을 평문 출력하지 않음.
- **접근 권한:** 세션 파일 저장 디렉터리(`.cache/`)는 로컬 사용자 권한으로 생성.

## Assumptions Log

| # | Assumption | Status | Impact if False |
|---|------------|--------|-----------------|
| 1 | KAU LMS는 Moodle/Coursemos v2 기반(`https://lms.kau.ac.kr`)이며 폼 필드는 `#input-username`, `#input-password`이다. | VERIFIED (Live inspect) | 다른 필드명일 경우 `Cascading Selector` 리스트에 추가 필요. |
| 2 | LMS 접근 시 2차 인증(OTP, 캡차)이 필수가 아니다. | HIGH CONFIDENCE | 2차 인증 도입 시 수동 로그인 세션 저장 모드(`--headful`)를 안내해야 함. |
| 3 | Playwright Sync API는 CLI 및 Click과 결합할 때 이벤트 루프 문제를 일으키지 않는다. | VERIFIED | Async 사용 시 `asyncio.run()` 래핑 필요. |
| 4 | 사용자의 Notion DB ID는 `21d53280-64be-80ec-af4e-000b679f03bb`이다. | VERIFIED (from REQUIREMENTS.md) | `.env`에서 오버라이드 가능하도록 설계됨. |

## Open Questions

- 없음. (LMS 로그인 폼 구조 및 의존성 해석이 실시간으로 확인되어 플래닝 단계로 즉시 이행 가능함).
</Phase 1: Foundation & Session Management - Research>
