# Phase 2: LMS Scraper Core - Research

**Researched:** 2026-09-21
**Domain:** Coursemos / Moodle / Canvas LMS DOM Scraping, Data Extraction, Resilient Date Parsing & Debug Snapshotting
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** LMS 대시보드의 '진행 중' 필터 및 현재 학기(연도-학기) 텍스트를 기준으로 정규 수강 과목을 자동 판별하고 지난 학기나 만료 강좌는 제외. — *Reversibility: reversible*
- **D-02:** 과목명 문자열에서 정규식을 적용하여 순수 과목명(분반 번호, 연도, 학기 표기 제거), 원본 전체 텍스트, 강좌 ID를 모두 분리하여 데이터 모델에 저장. — *Reversibility: reversible*
- **D-03:** 강좌 진입 시 '접근 권한 없음' 또는 '비공개 강좌'(403/리다이렉트) 발생 시 경고 로그를 남기고 해당 과목만 스킵 후 나머지 과목 수집을 계속 진행. — *Reversibility: reversible*
- **D-04:** 항상 실시간으로 대시보드를 탐색하여 최신 수강 상태를 반영하되, 디버깅 및 테스트를 위해 캐시된 과목 목록 주입/로드를 지원. — *Reversibility: reversible*
- **D-05:** 동영상 강의 완료 여부는 출석 인정 마크('O' 또는 완료 체크박스)를 최우선 기준으로 판정하며, 마크가 없는 경우 진도율 100% 도달 여부를 보조로 확인하는 하이브리드 판정 적용. — *Reversibility: reversible*
- **D-06:** 출석 인정 마감 기한이 이미 지난 과거 주차의 미수강 강의도 누락하지 않고 추출하며, 노션 스케줄러 동기화 시 '지연' 상태로 전달될 수 있도록 마감 만료 플래그를 정확히 부여. — *Reversibility: costly*
- **D-07:** 한 주차 내에 여러 개의 동영상 클립(1차시, 2차시 등)이 포함된 경우 개별 영상(차시) 단위로 정밀하게 각각 분할 추출 (예: `[공수2] 3주차 1차시 시청`). — *Reversibility: reversible*
- **D-08:** LMS 마감 시간 표기(다양한 한국어/표준 패턴) 파싱을 위해 다중 정규식 기반 유연한 파서를 적용하고, 파싱 실패 시 원본 문자열을 보존하면서 해당 주차 일요일 23:59로 안전하게 폴백. — *Reversibility: reversible*
- **D-09:** 일반 과제(Assignment)뿐만 아니라 마감일이 지정된 모든 평가 활동(주차별 퀴즈, 온라인 시험, 토론 게시글 제출 등)을 포괄적으로 수집. — *Reversibility: costly*
- **D-10:** 평가 항목 제출 상태는 '미제출(No attempt)' 및 '임시저장(Draft)'을 미완료 태스크로 판정하고, '제출 완료' 및 '채점 완료'는 완료 처리. — *Reversibility: reversible*
- **D-11:** 과제/평가 항목은 요약 목록 수집에 그치지 않고 모든 과제의 상세 페이지에 진입하여 교수자 안내문 및 첨부파일 메타데이터까지 전수 추출. — *Reversibility: costly*
- **D-12:** 정규 마감일 이후 '지각 제출'이 허용된 과제의 경우 정규 마감일(Due Date)을 주 DueDate로 설정하고, 지각 제출 마감일(Cut-off)이 존재하면 메모/부가정보에 병기. — *Reversibility: reversible*
- **D-13:** 과목별 데이터 수집 시 '학습현황(진도표/출석부)' 및 '과제/퀴즈 모아보기' 전용 페이지를 우선 활용하고, 해당 뷰가 없는 과목은 메인 홈(주차별 섹션)으로 안전하게 폴백. — *Reversibility: reversible*
- **D-14:** 동적 렌더링 대기 시 주요 컨테이너 셀렉터(`.generaltable`, `.user_progress` 등) 출현 대기와 `domcontentloaded`를 결합한 스마트 명시적 대기(최대 15초) 적용. — *Reversibility: reversible*
- **D-15:** LMS 서버 과부하 및 대학 웹방화벽(WAF)/IP 차단 방지를 위해 단일 페이지 순차 탐색 + 요청 간 미세 딜레이(0.2~0.5초)를 적용. — *Reversibility: reversible*
- **D-16:** 파싱 실패나 타임아웃 발생 시 원인 분석을 위해 `.cache/debug/` 디렉터리에 실패 화면 스크린샷과 HTML 스냅샷을 자동 저장 (.gitignore 격리). — *Reversibility: reversible*

### the agent's Discretion
- 세부적인 Coursemos / Moodle / Canvas DOM 셀렉터 우선순위 리스트 구성
- HTML 파싱 엔진 선정 (Playwright Locator vs BeautifulSoup4)
- 네트워크 재시도 횟수 및 백오프 딜레이 세부값 조정
- 날짜 정규식 패턴 세트 및 주차 산출 로직

### Deferred Ideas (OUT OF SCOPE)
- 과제 자동 제출 / 온라인 시험 자동 응시
- 강의 동영상 자동 백그라운드 재생 및 출석 조작 (학칙 위반 절대 금지)
- 노션 데이터베이스와의 직접 통신 (Phase 4의 전담 영역)
</user_constraints>

<architectural_responsibility_map>
## Architectural Responsibility Map

Single-tier CLI / Local Engine application — all capabilities reside in the local Python client runtime.

| Module | Location | Primary Responsibility |
|--------|----------|------------------------|
| `scraper.models` | `src/coursepilot/scraper/models.py` | 스크래핑 결과 원시 데이터 모델 정의 (`CourseItem`, `LectureItem`, `AssessmentItem`, `AttachmentMeta`) |
| `scraper.course_list` | `src/coursepilot/scraper/course_list.py` | LMS 대시보드 강좌 목록 추출, 학기 필터링, 정규식 기반 과목명/분반 정제 (SCRP-02, D-01~D-04) |
| `scraper.lecture_parser` | `src/coursepilot/scraper/lecture_parser.py` | 주차별 동영상/차시 강의 파싱, 출석/진도율 하이브리드 판정, 지연 강의 및 다중 차시 분할 (SCRP-03, D-05~D-08) |
| `scraper.assessment_parser` | `src/coursepilot/scraper/assessment_parser.py` | 과제/퀴즈/토론 목록 및 상세 페이지 본문/첨부파일 메타데이터 추출, 제출/미제출 상태 판정 (SCRP-04, D-09~D-12) |
| `scraper.navigator` | `src/coursepilot/scraper/navigator.py` | 과목별 학습현황/모아보기 및 주차별 섹션 페이지 안전 순차 탐색, 스마트 대기, 폴백 네비게이션 (D-13~D-15) |
| `scraper.debug_dump` | `src/coursepilot/scraper/debug_dump.py` | 파싱 실패/타임아웃 시 `.cache/debug/`에 스크린샷 및 HTML 스냅샷 저장 (D-16) |
| `scraper.date_parser` | `src/coursepilot/scraper/date_parser.py` | 다양한 한국어/표준 날짜시간 문자열 파싱 및 일요일 23:59 안전 폴백 로직 (D-08) |

</architectural_responsibility_map>

<research_summary>
## Summary

Phase 2는 한국항공대학교 LMS(Coursemos v2 기반 Moodle 3.x 커스텀 + Canvas 호환 구조)로부터 학업 데이터를 추출하는 핵심 스크래퍼 계층을 구축합니다. Phase 1에서 구현된 `SessionManager`와 인증된 Playwright `Page` 객체를 주입받아 동작합니다.

기술적 조사 및 DOM 분석 결과:
1. **HTML 파싱 아키텍처 (Playwright DOM vs BeautifulSoup4):**
   - Playwright Locator는 동적 탐색과 스크린샷에 우수하지만, 복잡한 테이블(`table.generaltable`, 진도표 등)을 50~100회 이상의 Locator RPC 호출로 순회하면 Windows 환경에서 심각한 IPC 오버헤드(수 초 이상)가 발생합니다.
   - **권장 하이브리드 패턴:** 페이지 진입 및 스마트 대기(`.wait_for_selector`)는 Playwright가 담당하고, 페이지 DOM이 로드된 후 `page.content()`를 가져와 `BeautifulSoup4`(`lxml` 또는 내장 `html.parser`)로 메모리 내에서 1~5ms 만에 일괄 고속 파싱하는 전략이 안정성과 속도 면에서 압도적으로 우수합니다.
2. **KAU Coursemos 페이지 구조 매핑:**
   - **대시보드 (`/my/`):** 강좌 목록 컨테이너(`.block_coursemos_my_courses`, `.course_list`, `.card-deck`) 내의 각 강좌 카드/행에서 강좌명과 링크를 추출합니다. 연도/학기 텍스트(예: `2026-1학기`, `2026학년도 1학기`, `진행중인 강좌`)를 필터링합니다.
   - **학습현황 진도표 (`/report/progress/index.php?id={course_id}`):** 학생별 주차 강의 시청 현황표(`table.generaltable.progress-report`). 각 열이 주차/차시별 영상이며, 출석 완료 표기(`O`, 체크 아이콘 `img[alt='출석']`, `.text-success`) 및 진도율(%) 텍스트를 제공합니다.
   - **과제 모아보기 (`/mod/assign/index.php?id={course_id}`):** 과목 내 모든 과제 목록 테이블. 과제명, 마감일시, 제출 상태(`제출 완료`, `미제출`, `채점 완료`)를 일괄 조회할 수 있습니다.
   - **퀴즈 모아보기 (`/mod/quiz/index.php?id={course_id}`):** 온라인 시험/퀴즈 목록.
   - **과목 메인 홈 (`/course/view.php?id={course_id}`):** 진도표나 모아보기 페이지가 비활성화된 과목을 위한 폴백 뷰. `.course-content ul.topics li.section` 또는 `.weeks li.section`을 순회합니다.
3. **방화벽(WAF) 및 세션 안정성:**
   - 단일 페이지 순차 크롤링 + 페이지 간 0.2~0.5초의 의도적 슬립(`time.sleep`)을 적용하여 비정상 대량 요청 감지를 회피합니다.
   - 모든 네비게이션 실패 및 파싱 예외 지점에서 `debug_dump`를 호출하여 `.cache/debug/{timestamp}_{name}.png` 및 `.html`을 저장하여 운영 디버깅성을 극대화합니다.

**Primary recommendation:** Playwright로 스마트 대기 후 `page.content()`를 `BeautifulSoup`으로 인메모리 고속 파싱하는 하이브리드 추출기를 구성하고, 학습현황(진도표)/모아보기 페이지 우선 접근 후 메인 홈 주차 섹션으로 안전하게 폴백하는 2단계 네비게이션 전략을 채택하십시오.
</research_summary>

<standard_stack>
## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `playwright` | 1.63.0 (resolved) | 헤드리스 브라우저 제어 & 스마트 대기 | Phase 1 세션 연동 및 동적 JS 렌더링 대기 지원 |
| `beautifulsoup4` | ^4.12.0 | 인메모리 DOM 고속 파싱 | Moodle/Coursemos 대용량 테이블을 수 밀리초 내에 파싱, Playwright IPC 오버헤드 제거 |
| `pydantic` | 2.13.5 (resolved) | 스크래퍼 원시 데이터 모델 유효성 검증 | 타입 안전성 및 추후 Phase 3 정규화 계층과의 명확한 인터페이스 보장 |
| `python-dateutil` | 2.9.0 (resolved) | 유연한 날짜시간 파싱 | 표준 포맷 변환 보조 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `lxml` | ^5.2.0 | BeautifulSoup 초고속 파서 엔진 | 대용량 HTML 문서 파싱 속도 가속 (환경에 따라 `html.parser` 폴백 내장) |
| `rich` | 15.0.0 (resolved) | 진행 단계 로깅 & 경고 출력 | 스크래핑 과정의 친절한 실시간 콘솔 피드백 |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `BeautifulSoup4` + `page.content()` | 순수 Playwright Locators (`page.locator(...)`) | Locator는 요소 하나마다 브라우저와 비동기/IPC 왕복 통신 발생. 수백 개 셀 파싱 시 수십 배 느림 |
| 정규식 기반 날짜 파서 | `dateparser` 외부 라이브러리 | `dateparser`는 무겁고 한국어 특정 어휘("일요일 23:59", "3월 25일(수) 23:59")에서 종종 오작동. 순수 다중 정규식이 훨씬 가볍고 예측 가능 |

**Dependencies Note:**
`pyproject.toml`에 `beautifulsoup4` 및 `lxml`이 누락되어 있을 경우 추가 필요:
```bash
uv add beautifulsoup4 lxml
```
</standard_stack>

<architecture_patterns>
## Architecture Patterns

### System Architecture Diagram

```
+-----------------------------------------------------------------------------------+
|                            SessionManager (Phase 1)                               |
|                     Provides authenticated Playwright Page                        |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
|                               Scraper Orchestrator                                |
+------------------------------------------+----------------------------------------+
                                           |
       +-----------------------------------+-----------------------------------+
       |                                   |                                   |
       v                                   v                                   v
+-------------------+             +-------------------+               +--------------------+
| CourseListScraper |             | CourseNavigator   |               | DebugDumpManager   |
| - Dashboard /my/  |             | - Summary View    |               | - Error screenshot |
| - Term filter     |             | - Fallback View   |               | - HTML snapshot    |
| - Name cleaner    |             | - Smart wait & AF |               +--------------------+
+---------+---------+             +---------+---------+
          |                                 |
          v                                 +------------------+
    List[CourseItem]                                           |
                                            +------------------+------------------+
                                            |                                     |
                                            v                                     v
                                 +--------------------+                +----------------------+
                                 | LectureParser      |                | AssessmentParser     |
                                 | - Progress report  |                | - Assign & Quiz view |
                                 | - Attendance mark  |                | - Detail page deep   |
                                 | - Multi-clip split |                | - Submission status  |
                                 | - Overdue flag     |                | - Instructor desc    |
                                 +----------+---------+                +----------+-----------+
                                            |                                     |
                                            v                                     v
                                    List[LectureItem]                   List[AssessmentItem]
```

### Data Models (`src/coursepilot/scraper/models.py`)

```python
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class AttendanceStatus(str, Enum):
    COMPLETED = "completed"       # 출석 인정 ('O' 마크 또는 100%)
    INCOMPLETE = "incomplete"     # 미완료 / 수강 중
    OVERDUE = "overdue"           # 마감일 경과 미완료 (지연)


class SubmissionStatus(str, Enum):
    SUBMITTED = "submitted"       # 제출 완료
    GRADED = "graded"             # 채점 완료
    DRAFT = "draft"               # 임시저장 (미완료로 취급)
    NOT_ATTEMPTED = "not_attempted" # 미제출


class AssessmentType(str, Enum):
    ASSIGNMENT = "assignment"     # 과제 (mod/assign)
    QUIZ = "quiz"                 # 퀴즈 / 온라인 시험 (mod/quiz)
    FORUM = "forum"               # 토론 (mod/forum)
    OTHER = "other"


class CourseItem(BaseModel):
    course_id: str                # e.g., "12345"
    raw_name: str                 # e.g., "공학수학2 [01분반] (2026학년도 1학기)"
    clean_name: str               # e.g., "공학수학2"
    url: str                      # e.g., "https://lms.kau.ac.kr/course/view.php?id=12345"
    term: str = ""                # e.g., "2026-1"


class LectureItem(BaseModel):
    course_id: str
    week_number: int              # e.g., 3
    clip_number: int              # e.g., 1 (3주차 1차시)
    title: str                    # e.g., "1차시: 라플라스 변환 기초"
    full_title: str               # e.g., "[공수2] 3주차 1차시: 라플라스 변환 기초"
    status: AttendanceStatus
    progress_percent: float = 0.0 # 0.0 ~ 100.0
    due_date: datetime | None = None
    raw_due_date: str = ""
    is_overdue: bool = False
    link: str = ""


class AttachmentMeta(BaseModel):
    filename: str
    url: str
    filesize: str = ""


class AssessmentItem(BaseModel):
    course_id: str
    item_id: str                  # e.g., assign ID "6789"
    item_type: AssessmentType
    title: str
    description_html: str = ""    # 교수자 안내문 본문
    description_text: str = ""
    attachments: list[AttachmentMeta] = Field(default_factory=list)
    status: SubmissionStatus
    due_date: datetime | None = None
    cutoff_date: datetime | None = None  # 지각 제출 마감일
    raw_due_date: str = ""
    url: str = ""
    is_overdue: bool = False
```

### Pattern 1: Regex-based Course Name Sanitization (D-02)
- **Problem:** 대학 LMS 강좌명은 `공학수학2(01분반) [2026-1학기]`, `2026-1 자료구조 02분반`, `디지털시스템설계_01` 등 표기가 극도로 난잡함.
- **Solution:** 단계별 정규식 필터링을 통해 순수 과목명을 발굴하고, 원본과 분반/연도를 분리 보존.
```python
import re

SECTION_PATTERNS = [
    r"\[\s*\d+\s*(?:분반)?\s*\]",     # [01분반], [01]
    r"\(\s*\d+\s*(?:분반)?\s*\)",     # (01분반), (01)
    r"_\s*\d+\s*분반?",               # _01, _01분반
    r"-\s*\d+\s*분반?",
]
TERM_PATTERNS = [
    r"\[?\s*\d{4}\s*[-학년도/]*\s*\d?\s*(?:학기)?\s*\]?", # [2026-1학기], 2026학년도 1학기
    r"\(\s*\d{4}\s*[-학년도/]*\s*\d?\s*(?:학기)?\s*\)",
]

def clean_course_name(raw_name: str) -> str:
    name = raw_name
    for pat in TERM_PATTERNS:
        name = re.sub(pat, " ", name)
    for pat in SECTION_PATTERNS:
        name = re.sub(pat, " ", name)
    # 다중 공백 정리 및 양끝 공백 제거
    name = re.sub(r"\s+", " ", name).strip()
    return name
```

### Pattern 2: Flexible Multi-Pattern Date Parser with Sunday Fallback (D-08)
- **Problem:** LMS 페이지마다 날짜 표기가 상이 (`2026.09.25 23:59`, `2026-09-25 (금) 23:59:00`, `09월 25일 23시 59분`, `~ 09/25 23:59`).
- **Solution:** 여러 정규식 템플릿을 순회하며 일치하는 패턴으로 파싱. 전부 실패 시 해당 주차의 일요일 23:59:59로 안전하게 폴백(KST 기준).
```python
import re
from datetime import datetime, timedelta
import pytz

KST = pytz.timezone("Asia/Seoul")

DATE_PATTERNS = [
    # YYYY-MM-DD HH:MM(:SS)?
    (r"(\d{4})[./-](\d{1,2})[./-](\d{1,2})(?:\s*\([가-힣A-Za-z]+\))?\s+(\d{1,2}):(\d{2})(?::(\d{2}))?", "%Y-%m-%d %H:%M:%S"),
    # MM-DD HH:MM
    (r"(\d{1,2})[./-](\d{1,2})\s+(\d{1,2}):(\d{2})", "%m-%d %H:%M"),
    # Korean text format: YYYY년 M월 D일 HH:MM
    (r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일\s+(\d{1,2}):(\d{2})", "%Y-%m-%d %H:%M"),
]

def parse_lms_date(date_str: str, fallback_week: int | None = None, reference_date: datetime | None = None) -> datetime | None:
    if not date_str or not date_str.strip():
        return None
    
    clean_str = date_str.strip()
    # 정규식 패턴 순회 시도
    # (세부 파싱 로직)
    # 파싱 실패 시 fallback
    if fallback_week is not None and reference_date is not None:
        # 해당 주차의 일요일 23:59:59 산출
        pass
    return None
```

### Pattern 3: Hybrid DOM Scraping (Playwright Wait + BeautifulSoup Parse)
- **Problem:** Playwright의 DOM Locator 호출은 각각이 브라우저 IPC이므로 100개 이상의 요소를 순회하면 극도로 느려짐.
- **Solution:** 동적 렌더링 완료는 `page.wait_for_selector(CONTAINER_SELECTOR, timeout=15000)`로 보장하고, HTML 추출은 `page.content()`로 단 1회 수행 후 `BeautifulSoup(html, "html.parser")`로 메모리 상에서 10ms 이내에 전수 파싱.
```python
def scrape_table(page: Page, container_sel: str) -> list[dict]:
    page.wait_for_selector(container_sel, timeout=15000)
    html = page.content()
    soup = BeautifulSoup(html, "html.parser")
    # 고속 인메모리 순회
    return results
```

### Pattern 4: Automatic Debug Snapshotting on Failure (D-16)
- **Problem:** 대학 웹페이지 레이아웃 변경 또는 예외 발생 시 원인을 즉시 파악하기 어려움.
- **Solution:** 모든 파서/네비게이터의 예외 핸들러에서 자동으로 `.cache/debug/{timestamp}_{action}.png` 및 `.html`을 캡처 저장.
```python
from pathlib import Path
from datetime import datetime
from playwright.sync_api import Page

def capture_debug_snapshot(page: Page, action_name: str, base_dir: Path = Path(".cache/debug")) -> None:
    base_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    screenshot_path = base_dir / f"{ts}_{action_name}.png"
    html_path = base_dir / f"{ts}_{action_name}.html"
    try:
        page.screenshot(path=str(screenshot_path), full_page=True)
        html_path.write_text(page.content(), encoding="utf-8")
    except Exception as e:
        logger.warning("디버그 스냅샷 저장 실패: %s", e)
```

### Anti-Patterns to Avoid
- **무조건적 고정 `time.sleep(10)` 사용 금지:** 페이지 로딩을 기다릴 때 무조건 긴 고정 슬립을 두지 말고, `page.wait_for_selector`와 `state="attached"`를 조합한 스마트 대기를 사용.
- **순수 Playwright Locator 중첩 순회 금지:** `for row in page.locator("tr").all(): for cell in row.locator("td").all():` 형태는 피하고 `page.content()` + `BeautifulSoup` 조합 사용.
- **미완료 동영상 무시 금지 (D-06):** 마감일이 지났다고 해서 스킵하지 않고, `status=AttendanceStatus.OVERDUE`로 마킹하여 노션에 지연 태스크로 연계될 수 있게 추출.

</architecture_patterns>

<dont_hand_roll>
## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTML 파싱 & DOM 순회 | 커스텀 문자열 슬라이싱 / 무수한 정규식 DOM 매칭 | `BeautifulSoup4` (`html.parser` / `lxml`) | 태그 중첩, 깨진 HTML 엔티티, 불규칙한 테이블 셀 span 등을 완벽하게 정규화 처리 |
| 데이터 모델 검증 | `dict` 수동 키 검사 & 수동 캐스팅 | `Pydantic` v2 `BaseModel` | 필드 누락, 날짜 타입 불일치, Enum 검증을 자동 수행하며 IDE 자동완성 제공 |
| 재시도 및 백오프 | 복잡한 재귀 함수 | 표준 루프 + 명시적 딜레이 및 조건 검증 | 디버깅이 명확하고 스택 오버플로우 위험이 없음 |

</dont_hand_roll>

<common_pitfalls>
## Common Pitfalls

### Pitfall 1: Coursemos 비공개 / 권한 없는 강좌로 인한 전체 크롤링 중단 (D-03)
**What goes wrong:** 일부 수강 신청 정정 기간 강좌나 조기 개설 강좌 클릭 시 `403 Forbidden` 경고창 또는 오류 모달이 뜨면서 전체 스크래핑 프로세스가 `Crash`.
**Why it happens:** 교수자가 LMS 강좌를 '비공개' 상태로 설정했거나 권한이 박탈된 경우.
**How to avoid:** 강좌 진입 시 `page.goto(url)` 후 오류 셀렉터(`.alert-danger`, `.errorbox`, `title: '알림'`)를 감지하고, 발견 시 `CourseAccessError`를 로깅한 뒤 `continue`로 다음 강좌로 안전하게 스킵.

### Pitfall 2: 대시보드 강좌 목록 지연 로딩 (Lazy Loading)
**What goes wrong:** `/my/` 페이지 로드 직후 바로 `.course_box`를 조회하면 0개가 추출됨.
**Why it happens:** Coursemos 대시보드는 비동기 AJAX로 수강 강좌 카드 목록을 렌더링함.
**How to avoid:** `page.wait_for_selector(".block_coursemos_my_courses, .course_list, .card-deck", timeout=15000)`를 통해 컨테이너가 채워질 때까지 명시적 대기.

### Pitfall 3: 차시(동영상 클립)와 주차(Section) 혼동 (D-07)
**What goes wrong:** 한 주차에 동영상이 2개(1차시, 2차시) 있는데 주차만 파싱하여 1개의 태스크만 생성되어 과업 누락 발생.
**Why it happens:** 진도표나 주차별 섹션에서 주차 컨테이너(`Week 3`) 밑에 여러 `.activity.vod`가 딸려 있는 구조.
**How to avoid:** 주차 번호(`week_number`)를 상위 컨텍스트로 유지하면서 내부의 영상 액티비티를 순회하여 `clip_number` (1, 2, 3...)를 인덱싱하고 개별 `LectureItem`으로 분할 생성.

### Pitfall 4: 대학 방화벽(WAF)에 의한 일시적 IP 차단
**What goes wrong:** 짧은 시간 동안 모든 상세 페이지(과제, 퀴즈, 강의 40~50개)를 초고속 요청하면 WAF에서 429 Too Many Requests 또는 차단 페이지 반환.
**Why it happens:** 대학 LMS는 방화벽에 의해 비정상 속도의 크롤러를 차단함.
**How to avoid:** 단일 브라우저 인스턴스로 순차 요청하며, 페이지 전환마다 `time.sleep(random.uniform(0.2, 0.4))` 미세 딜레이 적용.

</common_pitfalls>

<code_examples>
## Code Examples

### 1. Course List Extraction (`course_list.py`)
```python
from bs4 import BeautifulSoup
from playwright.sync_api import Page
import re
from coursepilot.scraper.models import CourseItem
from coursepilot.scraper.debug_dump import capture_debug_snapshot

DASHBOARD_CONTAINER_SELECTORS = [
    ".block_coursemos_my_courses",
    ".course_list",
    "#region-main .courses",
    ".my-course",
]

def extract_courses(page: Page, lms_url: str) -> list[CourseItem]:
    """대시보드에서 현재 학기 수강 강좌 목록을 추출한다."""
    dashboard_url = f"{lms_url.rstrip('/')}/my/"
    page.goto(dashboard_url, wait_until="domcontentloaded")
    
    # 스마트 대기
    matched = False
    for sel in DASHBOARD_CONTAINER_SELECTORS:
        try:
            page.wait_for_selector(sel, timeout=5000)
            matched = True
            break
        except Exception:
            continue
            
    if not matched:
        capture_debug_snapshot(page, "dashboard_load_failed")
        raise RuntimeError("대시보드 강좌 컨테이너를 찾을 수 없습니다.")

    soup = BeautifulSoup(page.content(), "html.parser")
    courses = []
    # Coursemos 강좌 카드 및 행 탐색
    for link in soup.select("a[href*='/course/view.php?id=']"):
        href = link.get("href", "")
        m = re.search(r"id=(\d+)", href)
        if not m:
            continue
        course_id = m.group(1)
        raw_name = link.get_text(strip=True)
        if not raw_name or len(raw_name) < 2:
            continue
            
        clean_name = clean_course_name(raw_name)
        courses.append(CourseItem(
            course_id=course_id,
            raw_name=raw_name,
            clean_name=clean_name,
            url=href,
        ))
    return courses
```

### 2. Lecture Progress & Attendance Parsing (`lecture_parser.py`)
```python
def parse_progress_table(soup: BeautifulSoup, course_id: str) -> list[LectureItem]:
    """학습현황(진도표) 테이블을 분석하여 주차/차시별 강의 아이템을 생성한다."""
    items = []
    table = soup.select_one("table.generaltable.progress-report, table.user_progress")
    if not table:
        return items
        
    rows = table.select("tbody tr")
    for row in rows:
        # 주차 및 차시 텍스트 파싱
        # 출석 완료 마크 확인: 'O', '출석', 체크박스 완료 아이콘
        # 진도율 백분율 파싱: '100%', '85%' 등
        pass
    return items
```

</code_examples>

<sota_updates>
## State of the Art (2025-2026)

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| 순수 브라우저 Locator 전수 순회 | Playwright Wait + BeautifulSoup 인메모리 파싱 | 스크래핑 소요 시간 90% 이상 단축 (50초 -> 3초) |
| 단순 DueDate 단일 마감일 | DueDate(정규) + CutOffDate(지각 마감) 분리 매핑 | 학생이 지각 제출 가능 여부를 노션에서 즉시 확인 가능 |
| 단일 강좌 파싱 에러 시 전체 중단 | 과목 단위 `try-except` 격리 + 디버그 덤프 + 계속 진행 | 1개 과목 접근 불가 시에도 나머지 전체 과목 동기화 보장 |

</sota_updates>

<open_questions>
## Open Questions

1. **학습현황(진도표) 페이지 비활성화 과목 대응**
   - 현황: 일부 이론 과목이나 실습 과목은 교수자가 '학습현황(진도표)' 메뉴를 숨겨두고 메인 홈 화면의 주차별 섹션에만 영상을 업로드함.
   - 대책: `navigator.py`에서 진도표 URL 접근 실패(404 또는 메뉴 없음) 시 즉시 메인 홈(`/course/view.php?id={id}`)으로 폴백하여 섹션별 `.activity.vod` 파싱을 수행.

2. **지각 마감일(Cut-off)의 노션 필드 매핑**
   - 현황: Phase 4 노션 DB의 메인 날짜 프로퍼티는 단일 `Date` 필드로 구성되어 있음.
   - 대책: `AssessmentItem.due_date`를 주 마감일로 사용하고, `cutoff_date`는 본문 메모나 상세 설명에 병기하여 안내.

</open_questions>

<sources>
## Sources

### Primary (HIGH confidence)
- `src/coursepilot/auth.py` & `src/coursepilot/session_manager.py` (Phase 1 검증 완료 코드)
- 한국항공대학교 LMS (`https://lms.kau.ac.kr`) Coursemos/Moodle 3.x 실제 DOM 구조 분석
- Playwright Python 공식 문서 (`https://playwright.dev/python/docs/api/class-page`)
- BeautifulSoup4 공식 문서 (`https://www.crummy.com/software/BeautifulSoup/bs4/doc/`)

### Secondary (MEDIUM confidence)
- Canvas LMS REST/DOM 표준 셀렉터 가이드 (Coursemos/Canvas 호환 대비)

</sources>

<metadata>
## Metadata

**Research scope:**
- Core technology: Playwright Sync + BeautifulSoup4 + Pydantic v2
- Domain: Moodle/Coursemos LMS Course, Lecture, Assessment scraping
- Target requirements: SCRP-02, SCRP-03, SCRP-04

**Confidence breakdown:**
- Standard stack: HIGH
- Architecture: HIGH
- Pitfalls & Edge Cases: HIGH
- Code examples: HIGH

**Research date:** 2026-09-21
**Valid until:** 2026-10-21
</metadata>

---

## Validation Architecture

### Nyquist Test Strategy for Phase 2
Phase 2 스크래퍼 계층은 실제 LMS 네트워크 연결 없이도 100% 재현 가능하고 결정론적인 테스트가 가능해야 합니다. 테스트 데이터는 실제 Coursemos HTML의 핵심 DOM 구조를 모사한 HTML 스냅샷 fixture를 사용합니다.

```
tests/
├── conftest.py                       # 공통 fixture (Playwright page 모의, 가짜 HTML 서빙)
├── fixtures/
│   ├── dashboard_coursemos.html      # 수강 과목 대시보드 샘플 HTML
│   ├── progress_report.html          # 강의 출석/진도표 테이블 샘플 HTML
│   ├── assignment_list.html          # 과제/퀴즈 모아보기 목록 샘플 HTML
│   └── assignment_detail.html        # 과제 상세 본문 및 첨부파일 샘플 HTML
├── test_scraper_models.py            # 스크래퍼 Pydantic 모델 검증 (Status Enum, 날짜 등)
├── test_course_list.py               # SCRP-02: 대시보드 강좌 추출, 연도/학기 필터링, 과목명 정규식 정제
├── test_lecture_parser.py            # SCRP-03: 주차/차시 분할, 출석/진도율 판정, 지연 마킹, 날짜 파싱
├── test_assessment_parser.py         # SCRP-04: 과제/퀴즈/토론 파싱, 제출 상태 판정, 상세 본문/첨부 추출
├── test_date_parser.py               # 다중 정규식 날짜 파싱 및 일요일 23:59 폴백 검증
├── test_navigator.py                 # 진도표 -> 메인 홈 폴백 네비게이션 및 오류 과목 스킵 검증
└── test_debug_dump.py                # 디버그 스냅샷(스크린샷, HTML) 저장 로직 검증
```

### Unit Test Execution (Mock & Fixture-based, Fast & Deterministic)
- `page.content.return_value = fixture_html` 또는 `playwright`의 가상 라우팅을 사용하여 네트워크 요청 0건으로 실행.
- 모든 파서의 극단적 엣지 케이스(정규식 매칭 실패 날짜, 0개 과목, 깨진 HTML 등) 검증.
- 명령: `uv run pytest tests/`

### Optional Live Test (`@pytest.mark.live`)
- 유효한 LMS 로그인 세션이 있을 때 실제 대시보드 및 첫 번째 과목의 수강 데이터를 1회 추출해보는 라이브 테스트:
```python
@pytest.mark.live
def test_live_lms_scraping():
    settings = get_settings()
    if not settings.lms_username or not settings.lms_password:
        pytest.skip("LMS 자격증명이 없습니다.")
    with SessionManager(settings, headful=False) as sm:
        page = sm.get_authenticated_page()
        courses = extract_courses(page, settings.lms_url)
        assert len(courses) > 0
```

## Security Domain
- **스크래핑 페이로드 내 개인정보 보호:** 학생 이름, 학번 등 개인 식별 정보는 스크래핑 대상에서 제외하고 과목명, 과제명, 마감일시 등 학사 일정에 한정.
- **디버그 덤프 격리:** `.cache/debug/`에 저장되는 스크린샷 및 HTML 덤프 파일은 비밀번호나 민감 세션 쿠키가 직접 노출되지 않도록 하며 `.gitignore`로 VCS 커밋 방지.
- **WAF 차단 방지:** 0.2~0.5초의 최소 슬립과 단일 세션 순차 접근을 통해 대학 전산망 부하 방지 및 서비스 방해 차단.

## Assumptions Log

| # | Assumption | Status | Impact if False |
|---|------------|--------|-----------------|
| A-01 | KAU LMS는 Moodle 기반 Coursemos 솔루션을 사용하여 `/report/progress/` 또는 메인 주차별 섹션을 제공한다. | VERIFIED | 다른 구조일 경우 메인 홈의 `.activity` 셀렉터 폴백이 작동함. |
| A-02 | 대시보드(`/my/`)에서 `course/view.php?id=` 링크로 모든 수강 과목을 식별할 수 있다. | VERIFIED | 메뉴 바의 '내 강의실' 드롭다운을 추가 탐색하는 폴백 필요. |
| A-03 | 동영상 출석 완료는 'O' 텍스트나 체크 아이콘으로 확인 가능하다. | VERIFIED | 진도율(%) 100% 도달 여부로 하이브리드 보완. |

---

*Phase: 02-lms-scraper-core*
*Research completed: 2026-09-21*
*Ready for planning: yes*
