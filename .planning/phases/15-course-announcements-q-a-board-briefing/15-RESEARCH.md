# Phase 15: Course Announcements & Q&A Board Briefing - Technical Research

**Phase:** 15-course-announcements-q-a-board-briefing  
**Author:** gsd-phase-researcher  
**Date:** 2026-09-26  
**Status:** Completed  
**Artifact Directory:** `.planning/phases/15-course-announcements-q-a-board-briefing/`

---

## User Constraints

> *The following implementation decisions and discretionary guidance are captured verbatim from `15-CONTEXT.md`:*

### 1. CLI 명령어 및 진입점 설계
- **D-15-01:** `kau-assistant board`를 단일 통합 명령어로 제공하여 공지사항과 Q&A를 함께 브리핑하며, 사용자 편의를 위해 `kau-assistant notices`와 `kau-assistant qna` 단독 별칭(또는 서브커맨드)도 함께 지원한다. — **Reversibility:** costly — CLI 명령어 시그니처 및 에이전트 스킬 연동 경로에 영향
- **D-15-02:** `--course` 옵션 생략 시 전체 수강 과목을 순회하되, 최근 공지/질문이 있는 과목 위주로 깔끔하게 묶어서 브리핑하고 공지가 없는 과목은 1줄 요약으로 컴팩트하게 출력한다.
- **D-15-03:** 기본 조회 게시글 개수는 최근 3개(`--limit 3`)로 설정하며, `--limit <N>`으로 개수 조절 및 `--all` 플래그로 게시판 전체 글 조회를 지원한다.
- **D-15-04:** 에이전트 연동용 `--json` 출력은 프로젝트 표준 JSON 계약(`schema_version: 1`)을 준수하여, 과목별 `notices` 및 `qna` 배열과 게시글 상세 메타데이터(id, title, author, created_at, content, is_answered, replies, attachments, url)를 일관되게 제공한다. — **Reversibility:** costly — JSON_CONTRACT.md 및 에이전트 파싱 계약

### 2. 브리핑 상세 수준 및 본문 표시 방식
- **D-15-05:** 기본 터미널 브리핑 시 목록 테이블에 제목, 작성자, 작성일, 답변상태와 함께 본문 핵심 요약(1~2줄 미리보기)을 표시하고, `--detail` 플래그 지정 시 본문 요약을 더 넓게 펼쳐 확인하도록 한다.
- **D-15-06:** 특정 게시글의 전체 본문(전문)을 확인하기 위해 `--view <게시글ID>`(또는 번호) 옵션을 제공하여 지정한 특정 글의 본문 전문, 첨부파일 목록, 답변 전체를 단독 터미널 뷰어로 출력하고 브라우저 링크를 함께 제공한다.
- **D-15-07:** LXP 게시판 본문의 HTML 서식(줄바꿈, 목록, 링크 등)은 BeautifulSoup과 html-to-text 변환기를 통해 Markdown/일반 텍스트로 정제하여 Rich Console로 가독성 높게 렌더링한다.
- **D-15-08:** 공지사항/게시글에 포함된 첨부파일 메타데이터(파일명, 크기, 링크)를 브리핑하며, 사용자가 `--download-attachments` 옵션을 지정할 경우에만 Phase 13의 다운로더 엔진을 재사용하여 로컬 `downloads/<과목명>/notices/` 경로에 저장한다.

### 3. Q&A 조회 스코프 및 타겟팅
- **D-15-09:** Q&A 게시판 조회 시 기본값으로 최근 질문들을 최신순으로 표시하되, 현재 로그인 학생 계정(LMS 사용자 이름)이 작성한 질문은 `[내 질문]` 강조 태그를 부여하고, `--my` 플래그로 내 질문만 필터링할 수 있도록 한다.
- **D-15-10:** Q&A 답변 상태는 녹색 `[답변완료]`, 황색 `[답변대기]` 색상 태그로 시각적으로 명확히 표시하며, `--unanswered` 옵션으로 답변 대기 중인 질문만 필터링하여 확인할 수 있다.
- **D-15-11:** Q&A 게시글에 달린 교수/조교의 답변은 목록에서 상태(완료/대기)를 보여주고, 상세 보기(`--view <id>` 또는 `--detail`) 시 질문 본문 하단에 공식 답변 본문과 답변 일시를 함께 묶어 출력한다.
- **D-15-12:** 과목별 게시판 유형 판별은 키워드 기반 자동 분류(이름에 '공지', 'notice' 포함 시 공지사항 / 'q&a', '질문', '문의' 포함 시 Q&A)를 기본으로 적용하며, 비표준 명칭 게시판 조회를 위해 `--board-name <이름>` 옵션을 제공한다.

### 4. 게시글 확인(읽음) 상태 트래킹 및 Notion 연동 정책
- **D-15-13:** Phase 13 원칙(D-13-07)과 일관되게 공지사항 및 Q&A는 Notion Scheduler DB에 연동하지 않고, 에이전트 채팅 브리핑 및 CLI 전용으로 운영하여 Scheduler DB의 마감일 중심 청결성을 유지한다. — **Reversibility:** costly — Notion DB 스키마 및 마이그레이션 오염 방지
- **D-15-14:** 로컬 상태 파일 `board_read_state.json`에 열람한 글 ID 목록을 저장하여 미확인 신규 글에 `[NEW]` 뱃지를 표시하고, `--unread-only` 플래그로 새 공지만 걸러볼 수 있도록 한다.
- **D-15-15:** 게시글의 읽음(확인) 처리는 상세 보기(`--view <id>` 또는 `--detail`)로 내용을 열람했을 때 자동으로 읽음 처리하며, 사용자가 원할 때 일괄 읽음 처리할 수 있는 `--mark-read` 플래그도 제공한다.
- **D-15-16:** LXP 서버 트래픽 최소화와 자연스러운 세션 동작을 위해, 기본 브리핑 시에는 게시판 목록 페이지(`view.php`)만 파싱하고 상세 보기(`--view <id>` 또는 `--detail`) 요청 시에만 실제 본문 페이지(`article.php` 등)를 방문하여 LXP 웹 서버상에도 자연스럽게 조회수가 반영되도록 한다.

### the agent's Discretion
- HTML 본문에서 마크다운으로 변환 시 사용하는 파서 구현체 (BeautifulSoup 기반 자체 정제 헬퍼 또는 경량 html2text 라이브러리 활용 여부).
- `board_read_state.json`의 원자적 저장 및 보관 기간/최대 엔트리 제한(예: 과목당 최근 200개 ID 보관) 정책.
- Coursemos 공지/게시판 목록의 Moodle accesshide 태그 및 테이블 구조별(ubboard, forum 등) 폴백 셀렉터 구현 상세.

---

## Phase Requirements

| ID | Title | Description | Success Criteria |
|---|---|---|---|
| **BRD-01** | 과목별 공지사항 게시판(`ubboard`) 추출 및 브리핑 | 과목별 공지사항 게시판의 최근 공지글 목록(번호, 제목, 작성자, 작성일) 및 본문/첨부파일 메타데이터를 추출하고, 터미널 브리핑 및 단독 뷰어(`--view <id>`)를 제공한다. | 1. 과목 홈에서 공지사항 게시판 모듈 자동 감지.<br>2. 목록 페이지(`view.php`) 파싱 및 메타데이터 추출.<br>3. 단독 뷰어(`--view <id>`)로 본문 및 첨부파일 상세 출력.<br>4. `--limit` (기본 3) 및 `--all` 지원. |
| **BRD-02** | Q&A 게시판 파싱, 답변 상태 감지 및 CLI/읽음 관리 | 과목별 Q&A 게시판의 질문 목록, 답변 상태(답변완료/대기), 공식 답변 본문을 추출하고, 통합 CLI `board` 및 단독 편의 서브커맨드 `notices`, `qna`, 필터(`--unread-only`, `--unanswered`, `--my`), 로컬 읽음 상태 관리(`board_read_state.json`)를 지원한다. | 1. Q&A 게시판 자동 분류 및 상태 태그([답변완료]/[답변대기]) 부여.<br>2. `[내 질문]` 식별 및 `--my`, `--unanswered` 필터 동작.<br>3. `board_read_state.json` 기반 `[NEW]` 뱃지 및 `--unread-only` 필터.<br>4. 표준 JSON 계약(`schema_version: 1`) 준수. |

---

## Summary

Phase 15 delivers a complete course announcement and Q&A board parsing and briefing pipeline for Coursemos LXP (한국항공대학교 LMS). In Coursemos, bulletin boards are implemented via the Ubion custom Moodle module `mod_ubboard` (with legacy fallback to `mod_forum`).

### Key Discoveries & Technical Validations:
1. **Coursemos Board Discovery [VERIFIED]:**
   - Main course page (`/course/view.php?id=...`) contains modules inside `<li class="activity ... ubboard modtype_ubboard">` with anchor links to `/mod/ubboard/view.php?id={board_module_id}`.
   - Module instance titles contain `<span class="instancename">{Title}<span class="accesshide"> 게시판</span></span>`. The `.accesshide` spans must be stripped to retrieve the clean board title.
   - Boards are automatically classified by keyword matching:
     - Notice Board: contains "공지" or "notice" (case-insensitive)
     - Q&A Board: contains "q&a", "질문", "문의", "질의" (case-insensitive)
     - Custom Name: explicitly targeted via `--board-name <name>`
2. **Board List Page Structure (`/mod/ubboard/view.php?id={module_id}`) [VERIFIED]:**
   - Rendered with `<table class="ubboard_table table table-hover">` inside `div.ubboard` or `#region-main`.
   - Table variants:
     - *Standard Notice Board (5 columns):* `[번호, 제목, 작성자, 작성일, 조회수]`
     - *Status-Badge Q&A Board (6 columns):* `[번호, 상태, 제목, 작성자, 작성일, 조회수]` where 상태 column contains "답변완료", "질문접수", or "답변대기".
     - *Threaded Reply Q&A Board (Postech/Coursemos standard):* Question row followed by answer row with `[RE]` in title or `<img alt="reply" ...>` icon in subject cell.
   - Post URLs follow `/mod/ubboard/article.php?id={board_id}&bwid={bwid}`. Both `bwid` (Board Write ID) and post row numbers can identify the post.
   - Exact timestamps are often stored in `<span title="YYYY-MM-DD HH:MM:SS">YYYY-MM-DD</span>` within the date cell.
3. **Article Detail Page Structure (`/mod/ubboard/article.php?id={board_id}&bwid={bwid}`) [VERIFIED]:**
   - Main container: `div.ubboard_view > div.well`.
   - Title: `div.subject`
   - Metadata: `div.info > div.writer`, `div.info > div.date`, `div.info > div.hit`
   - Attachments: `div.info > div.files ul.files li a` with href `/pluginfile.php/{contextid}/mod_ubboard/attachment/{itemid}/{filename}`
   - Content: `div.content` (HTML formatted by Moodle Atto editor)
   - Replies / Official Answers: comments or replies in `div.comment_list`, `ul.comments`, or threaded reply blocks.
4. **Local Read State Tracking (`board_read_state.json`) [VERIFIED]:**
   - Stored in cache directory (`.cache/board_read_state.json` alongside `session.json`).
   - Atomic writing via temporary file replacement (`.tmp` -> replace).
   - LRU / FIFO capping: limited to recent 200 post IDs per course to prevent unbounded growth.
5. **CLI & JSON Contract [VERIFIED]:**
   - Unified command `kau-assistant board` + convenience commands `notices` and `qna`.
   - Fully compliant with JSON Contract v1 (`schema_version: 1`).
   - Stderr used for real-time navigation/progress logs; stdout exclusively carries Rich tables or clean JSON.

---

## Architectural Responsibility Map

```
src/kau_assistant/
├── scraper/
│   └── board_parser.py          # NEW: Parses course home for boards, parses view.php table, parses article.php
├── board/
│   ├── __init__.py              # NEW: Package exports
│   ├── models.py                # NEW: Pydantic domain models (BoardType, BoardPostItem, BoardReport, etc.)
│   ├── read_state.py            # NEW: BoardReadStateManager (atomic persistence, LRU max 200 IDs)
│   ├── text_converter.py        # NEW: HTML to clean Markdown/text converter using BeautifulSoup
│   ├── runner.py                # NEW: Orchestrator for multi-course collection, filtering, and --view
│   └── reporter.py              # NEW: Rich Console formatting for board tables and post detail viewer
├── cli.py                       # MODIFIED: Register @cli.command("board"), @cli.command("notices"), @cli.command("qna")
└── report_models.py             # MODIFIED: (Optional DTO re-export or contract alignment for schema_version 1)
```

### Module Boundaries & Responsibilities:

| Module | Primary Responsibility | Input / Output |
|---|---|---|
| `scraper.board_parser` | Pure HTML parsing for Coursemos `ubboard` and `forum` modules | HTML strings -> `list[BoardModuleInfo]`, `list[BoardPostItem]`, `BoardArticleDetail` |
| `board.models` | Domain models and JSON contract DTOs | Pydantic models for posts, attachments, replies, summary, and envelope |
| `board.read_state` | Read state persistence with atomic write and per-course LRU | Read state file (`board_read_state.json`) <-> `BoardReadStateManager` |
| `board.text_converter` | HTML to Markdown cleaning preserving linebreaks, links, lists | Raw HTML string -> Clean Markdown string |
| `board.runner` | Orchestrator: Course navigation, board discovery, list/article fetching, attachment downloading | User queries & options -> `BoardReport` or `BoardPostItem` |
| `board.reporter` | Rich Console rendering for tables, badges (`[NEW]`, `[답변완료]`), and detail viewer | `BoardReport` or `BoardPostItem` -> Rich Console stdout |
| `cli.py` | Click subcommands, option parsing, exit code mapping, stream UTF-8 config | CLI invocation -> Process exit code (0/1/2) |

---

## Standard Stack

| Technology / Library | Version / Provenance | Purpose in Phase 15 | Rationale & Tradeoffs |
|---|---|---|---|
| **Python** | `>=3.11` [VERIFIED: pyproject.toml] | Runtime language | Standard runtime across the repository. |
| **BeautifulSoup4 + lxml** | `beautifulsoup4>=4.12.0`, `lxml>=5.2.0` [VERIFIED: pyproject.toml] | Fast, resilient HTML parsing and AST-based HTML-to-Markdown conversion | Already installed in `pyproject.toml`. Eliminates extra external dependency like `html2text`. Full control over Moodle Atto editor tag sanitization. |
| **Pydantic** | `pydantic>=2.6.0` [VERIFIED: pyproject.toml] | Domain models and versioned JSON contract (`schema_version: 1`) | Core typing and serialization engine used throughout the project (`ReportItem`, `WatchState`, `MaterialItem`). |
| **Rich** | `rich>=13.7.0` [VERIFIED: pyproject.toml] | Terminal tables, color badges, Markdown viewer, and stream handling | Established in `reporter.py` and `materials/reporter.py`. Rich Console handles `Console(stderr=True)` for progress and `Console()` for tables. |
| **Click** | `click>=8.1.0` [VERIFIED: pyproject.toml] | Command-line interface definitions and option validation | Used for all CLI commands in `src/kau_assistant/cli.py`. |
| **HTTPX** | `httpx>=0.28.0` [VERIFIED: pyproject.toml] | Cookie-authenticated HTTP client for high-speed page and attachment downloads | Reuses `get_authenticated_httpx_client` from Phase 13 for fast, non-blocking requests. |
| **Playwright** | `playwright>=1.42.0` [VERIFIED: pyproject.toml] | Browser automation for course navigation and session recovery | Reuses `SessionManager` and `CourseNavigator` for safe, authenticated LMS access. |

---

## Architecture Patterns

### Pattern 1: Coursemos Board Discovery & Classification
In Coursemos, boards are course-level activities placed in course sections.
```
Course Home (course/view.php?id=...)
  └── Section 0 (강의 개요) & All Sections
        └── <li class="activity ubboard modtype_ubboard" id="module-6001">
              └── <a href="/mod/ubboard/view.php?id=6001">
                    └── <span class="instancename">
                          공지사항 <span class="accesshide">게시판</span>
                        </span>
```

#### Classification Logic:
```python
def classify_board_type(title: str, custom_name: str | None = None) -> BoardType:
    if custom_name and custom_name.lower() in title.lower():
        return BoardType.CUSTOM
    t = title.lower()
    if any(k in t for k in ("공지", "notice", "안내")):
        return BoardType.NOTICE
    if any(k in t for k in ("q&a", "질문", "문의", "질의", "qna")):
        return BoardType.QNA
    return BoardType.OTHER
```

### Pattern 2: Multi-Layout Resilient Board Table Parsing
Coursemos boards vary across LMS versions and course configurations (5 columns vs 6 columns with status). The parser must determine column semantics dynamically from table headers before falling back to positional heuristics:
1. Locate header elements (`th` or `td` in `thead` or the first `tr`).
2. Map headers:
   - Contains `번호` / `no` / `num` -> Post Number
   - Contains `상태` / `status` -> Answer Status (`답변완료`, `질문접수`, `답변대기`)
   - Contains `제목` / `subject` / `title` -> Title & Article link
   - Contains `작성자` / `writer` / `author` -> Author
   - Contains `작성일` / `date` / `created` -> Date (Extract from `span[title]` if available)
   - Contains `조회` / `hit` / `view` -> View Count
3. If no headers exist, fall back to class names (`td.t-number`, `td.t-subject`, `td.t-writer`, `td.t-date`, `td.t-viewcount`) or column counts (5 vs 6).
4. Extract `bwid` and `id` from `<a href="/mod/ubboard/article.php?id=...&bwid=...">`.
5. Extract comment count from `<span class="comment">[N]</span>`.

### Pattern 3: Network Traffic Optimization (List First, Detail on Demand)
Following **D-15-16**:
- **Default Briefing (`kau-assistant board`):** Only fetches `/mod/ubboard/view.php?id=...`. Content previews are derived from title or cached snippet. No requests are made to individual `article.php` pages.
- **Detailed View (`--view <id>` or `--detail`):** Only fetches the specific `/mod/ubboard/article.php?id=...&bwid=...` page requested by the user, updating the LMS view count naturally and extracting the full body, attachments, and answers.

### Pattern 4: Atomic Local Read State (`board_read_state.json`) with LRU Capping
Following **D-15-14** and **D-15-15**:
- Tracks read post IDs per course.
- State file structure:
```json
{
  "version": 1,
  "courses": {
    "91001": {
      "read_post_ids": ["109", "106", "105"],
      "last_read_at": "2026-09-26T12:00:00+09:00"
    }
  }
}
```
- Maximum entries capped at 200 post IDs per course. When new IDs are marked, older IDs beyond 200 are evicted (FIFO/LRU order).
- Atomic writing:
  ```python
  temp_path = state_file.with_suffix(".tmp")
  temp_path.write_text(json_content, encoding="utf-8")
  temp_path.replace(state_file)
  ```

### Pattern 5: HTML-to-Markdown Clean Transformation
Coursemos post bodies contain raw HTML generated by Moodle's Atto or TinyMCE editor, including nested divs, inline styles, font tags, non-breaking spaces (`&nbsp;`), and `<br>` elements.
The transformation pipeline:
1. Decompose `<script>`, `<style>`, `<meta>`, `<link>`, and `.accesshide`.
2. Convert `<br>` and `<hr>` into newlines.
3. Replace block elements (`<p>`, `<div>`, `<blockquote>`, `<h1>`-`<h6>`) with newline padding.
4. Convert `<a>` tags with `href` into `[text](href)`.
5. Convert `<strong>` and `<b>` into `**text**`, `<em>` and `<i>` into `*text*`.
6. Convert `<ul><li>` and `<ol><li>` into structured markdown lists.
7. Normalize unicode characters (e.g. replace `\xa0` with regular space) and strip trailing spaces.
8. Collapse 3+ consecutive newlines into 2 newlines.

---

## Don't Hand-Roll

| Component | Don't Hand-Roll | Use Instead | Why |
|---|---|---|---|
| **LMS HTTP Session** | Custom cookie handling or raw urllib requests | `get_authenticated_httpx_client(settings, session_manager)` from `src/kau_assistant/materials/downloader.py` | Automatically extracts cached session cookies, handles User-Agent, Referer, and TLS redirects. |
| **Course Discovery & Filtering** | Custom course title fuzzy matching | `find_target_course(courses, query)` from `src/kau_assistant/player/runner.py` and `extract_courses` from `course_list.py` | Handles Korean course abbreviations (`자구`, `공수2`), campus codes, and fuzzy substring matching. |
| **File Downloader & Atomic Rename** | Raw socket writes or `open(..., 'w').write()` | `download_material_file` or `Downloader` logic from `src/kau_assistant/materials/downloader.py` | Handles HTTP streaming, content-disposition header parsing, filename sanitization, `.crdownload`/`.tmp` atomic rename, and duplicate skipping. |
| **Date Parsing** | Regex string hacking for Korean dates | `parse_date` / `format_date` / `get_current_kst_time` from `src/kau_assistant/scraper/date_parser.py` | Handles all Korean time formats (`2026-09-26 15:48`, `2026.09.26`, relative spans). |
| **Terminal Formatting** | Manual ANSI escape codes and terminal column counting | Rich `Console`, `Table`, `Panel`, and `Markdown` | Automatically handles terminal width, word wrapping, color markup, and Unicode character alignment. |

---

## Common Pitfalls

### Pitfall 1: Windows Console CP949 Encoding Crashes (`\xa0` Non-Breaking Spaces)
- **Problem:** Coursemos post bodies and tables contain non-breaking spaces (`\xa0` / `&nbsp;`). Printing raw strings to Windows PowerShell or Command Prompt with default `cp949` encoding throws `UnicodeEncodeError: 'cp949' codec can't encode character '\xa0'`.
- **Solution:**
  1. Call `_configure_streams()` (which invokes `sys.stdout.reconfigure(encoding='utf-8')` and `sys.stderr.reconfigure(encoding='utf-8')`) at the CLI entry point.
  2. In `text_converter.py`, explicitly normalize non-breaking spaces: `text = text.replace('\xa0', ' ')`.

### Pitfall 2: Moodle `accesshide` Text Contaminating Titles
- **Problem:** Moodle injects accessibility spans like `<span class="accesshide"> 게시판</span>` or `<span class="accesshide"> 동영상</span>` inside activity title anchors. If using `tag.get_text()`, titles become `"공지사항 게시판"` instead of `"공지사항"`.
- **Solution:** Deep-copy the element, call `for el in copy.find_all(class_='accesshide'): el.decompose()`, and extract text only after removing accesshide elements.

### Pitfall 3: Inconsistent Table Columns Across Courses (5 vs 6 Columns)
- **Problem:** Notice boards have 5 columns (`번호`, `제목`, `작성자`, `작성일`, `조회수`), while Q&A boards often have 6 columns with a `상태` (`답변완료`/`답변대기`) column at index 1. Hardcoding index numbers leads to parsing the status string as the title or shifting authors into dates.
- **Solution:** Dynamically inspect `th`/`td` headers in the `thead` or first `tr` to map column indexes to field roles. Fall back to class-based lookup (`.t-number`, `.t-subject`, `.t-writer`, `.t-date`, `.t-viewcount`).

### Pitfall 4: Relative URLs in Articles and Attachments
- **Problem:** Links inside `ubboard` are often relative paths like `article.php?id=3&bwid=109` or `/pluginfile.php/39/...`. Passing these directly to HTTP clients or JSON output causes broken links.
- **Solution:** Always run all extracted URLs through `urllib.parse.urljoin(current_page_url, extracted_href)`.

### Pitfall 5: Q&A Secret Posts ("비밀글입니다.") Crashing Parsers
- **Problem:** Students often post confidential inquiries in Q&A boards. In secret posts, `<a href="...">` might not exist or might lead to a password prompt. The subject cell contains `<span class="secret">비밀글입니다.</span>`.
- **Solution:** Handle rows where `a` tag is missing: extract title from cell text, retain `is_secret = True`, set `url = ""` or board list URL, and gracefully handle empty contents.

### Pitfall 6: Unbounded Growth of `board_read_state.json`
- **Problem:** Over several semesters, tracking post IDs without a bounding policy results in thousands of stale IDs and slow load times.
- **Solution:** Impose an LRU cap of 200 post IDs per course. Keep the newest 200 IDs and discard older ones when saving.

---

## Code Examples

### 1. Board Discovery on Main Course Page
```python
# src/kau_assistant/scraper/board_parser.py
import copy
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from kau_assistant.board.models import BoardModuleInfo, BoardType

def extract_board_modules(html: str, base_url: str) -> list[BoardModuleInfo]:
    """Finds all ubboard and forum module activities from course sections."""
    soup = BeautifulSoup(html, "lxml")
    modules: list[BoardModuleInfo] = []
    seen_ids: set[str] = set()

    activities = soup.find_all(
        lambda tag: tag.name == "li"
        and any(cls == "activity" for cls in tag.get("class", []))
        and any(cls in ("ubboard", "modtype_ubboard", "forum", "modtype_forum") for cls in tag.get("class", []))
    )

    for act in activities:
        a_el = act.find("a", href=re.compile(r"/mod/(?:ubboard|forum)/view\.php", re.I))
        if not a_el or not a_el.get("href"):
            continue

        raw_href = a_el["href"]
        id_match = re.search(r"[?&]id=(\d+)", raw_href)
        if not id_match:
            continue
        module_id = id_match.group(1)
        if module_id in seen_ids:
            continue
        seen_ids.add(module_id)

        # Clean title by removing accesshide spans
        name_el = a_el.find("span", class_="instancename") or a_el
        name_copy = copy.deepcopy(name_el)
        for ah in name_copy.find_all(class_="accesshide"):
            ah.decompose()
        raw_title = name_copy.get_text(strip=True)
        title = re.sub(r"\s+", " ", raw_title).strip()

        # Classify board type
        t_lower = title.lower()
        if any(k in t_lower for k in ("공지", "notice", "안내")):
            b_type = BoardType.NOTICE
        elif any(k in t_lower for k in ("q&a", "질문", "문의", "질의", "qna")):
            b_type = BoardType.QNA
        else:
            b_type = BoardType.OTHER

        modules.append(
            BoardModuleInfo(
                module_id=module_id,
                title=title,
                url=urljoin(base_url, raw_href),
                board_type=b_type,
            )
        )
    return modules
```

### 2. Board List Page Parsing (`view.php`)
```python
# src/kau_assistant/scraper/board_parser.py
def parse_board_list_page(
    html: str,
    base_url: str,
    board_id: str,
    board_type: BoardType,
    current_user_name: str = "",
) -> list[BoardPostItem]:
    """Parses posts from a Coursemos ubboard table (view.php)."""
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table", class_=re.compile(r"ubboard_table|table-hover|generaltable"))
    if not table:
        return []

    # Map column headers
    col_map = {}
    header_tr = table.find("thead") or table.find("tr")
    if header_tr:
        for idx, th in enumerate(header_tr.find_all(["th", "td"])):
            txt = th.get_text(strip=True).lower()
            if any(k in txt for k in ("번호", "no", "num")):
                col_map["num"] = idx
            elif any(k in txt for k in ("상태", "status")):
                col_map["status"] = idx
            elif any(k in txt for k in ("제목", "subject", "title")):
                col_map["subject"] = idx
            elif any(k in txt for k in ("작성자", "writer", "author")):
                col_map["writer"] = idx
            elif any(k in txt for k in ("작성일", "date", "created")):
                col_map["date"] = idx
            elif any(k in txt for k in ("조회", "hit", "views")):
                col_map["hit"] = idx

    posts: list[BoardPostItem] = []
    rows = table.find_all("tr")
    for row in rows:
        tds = row.find_all("td")
        if not tds:
            continue

        # Extract subject and link
        subj_idx = col_map.get("subject", 1 if "status" not in col_map else 2)
        if subj_idx >= len(tds):
            continue
        subj_td = tds[subj_idx]
        a_tag = subj_td.find("a")
        
        url = urljoin(base_url, a_tag["href"]) if a_tag and a_tag.get("href") else ""
        bwid_m = re.search(r"bwid=(\d+)", url) if url else None
        bwid = bwid_m.group(1) if bwid_m else None

        # Clean title text
        subj_copy = copy.deepcopy(subj_td)
        comment_count = 0
        comment_span = subj_copy.find("span", class_="comment")
        if comment_span:
            c_text = comment_span.get_text(strip=True).strip("[]")
            comment_count = int(c_text) if c_text.isdigit() else 0
            comment_span.decompose()

        for badge in subj_copy.find_all("span", class_=re.compile(r"newicon|secret|badge")):
            badge.decompose()
        title = subj_copy.get_text(strip=True)

        # Number / ID
        num_idx = col_map.get("num", 0)
        post_num = tds[num_idx].get_text(strip=True) if num_idx < len(tds) else ""
        post_id = bwid or post_num or str(len(posts) + 1)

        # Writer
        writer_idx = col_map.get("writer", -3 if len(tds) >= 5 else 2)
        author = tds[writer_idx].get_text(strip=True) if writer_idx < len(tds) else ""

        # Date (check title attribute for full timestamp)
        date_idx = col_map.get("date", -2 if len(tds) >= 5 else 3)
        created_at = ""
        if date_idx < len(tds):
            date_span = tds[date_idx].find("span", title=True)
            created_at = date_span["title"] if date_span else tds[date_idx].get_text(strip=True)

        # Hit count
        hit_idx = col_map.get("hit", -1)
        hit_text = tds[hit_idx].get_text(strip=True) if hit_idx < len(tds) else "0"
        hit_count = int(hit_text) if hit_text.isdigit() else 0

        # Answered status for Q&A
        is_answered = None
        if board_type == BoardType.QNA:
            status_idx = col_map.get("status")
            status_text = tds[status_idx].get_text(strip=True) if status_idx is not None and status_idx < len(tds) else ""
            if "완료" in status_text or comment_count > 0:
                is_answered = True
            elif "대기" in status_text or "접수" in status_text:
                is_answered = False
            else:
                is_answered = bool("[re]" in title.lower() or comment_count > 0)

        # Identify my question
        is_my_question = False
        if current_user_name and author:
            is_my_question = (current_user_name in author) or (author in current_user_name)

        posts.append(
            BoardPostItem(
                post_id=post_id,
                bwid=bwid,
                board_id=board_id,
                board_type=board_type,
                title=title,
                author=author,
                created_at=created_at,
                hit_count=hit_count,
                url=url,
                is_answered=is_answered,
                is_my_question=is_my_question,
            )
        )
    return posts
```

### 3. Article Detail Page Parsing (`article.php`)
```python
# src/kau_assistant/scraper/board_parser.py
def parse_board_article_page(html: str, base_url: str) -> BoardArticleDetail:
    """Parses article subject, metadata, attachments, and content from article.php."""
    soup = BeautifulSoup(html, "lxml")
    uv = soup.find("div", class_="ubboard_view") or soup
    well = uv.find("div", class_="well") or uv

    # Subject
    subj_div = well.find("div", class_="subject") or well.find(["h3", "h4"])
    subject = subj_div.get_text(strip=True) if subj_div else ""

    # Metadata & Attachments
    author, created_at, hit_count = "", "", 0
    attachments: list[BoardAttachmentItem] = []

    for info in well.find_all("div", class_="info"):
        writer_div = info.find("div", class_="writer")
        if writer_div:
            author = writer_div.get_text(strip=True).replace("작성자 :", "").replace("작성자", "").strip(": \t\r\n")
        date_div = info.find("div", class_="date")
        if date_div:
            created_at = date_div.get_text(strip=True).replace("작성일 :", "").replace("작성일", "").strip(": \t\r\n")
        hit_div = info.find("div", class_="hit")
        if hit_div:
            h_txt = hit_div.get_text(strip=True).replace("조회수 :", "").replace("조회수", "").strip(": \t\r\n")
            hit_count = int(h_txt) if h_txt.isdigit() else 0

        # Attachments
        files_ul = info.find("ul", class_="files")
        if files_ul:
            for li in files_ul.find_all("li"):
                a_tag = li.find("a")
                if a_tag and a_tag.get("href"):
                    filename = a_tag.get_text(strip=True)
                    dl_url = urljoin(base_url, a_tag["href"])
                    attachments.append(
                        BoardAttachmentItem(filename=filename, download_url=dl_url)
                    )

    # Content
    content_div = well.find("div", class_="content")
    raw_html = str(content_div) if content_div else ""
    markdown_content = html_to_markdown(raw_html)

    # Replies / Comments
    replies: list[BoardReplyItem] = []
    comment_area = uv.find("div", class_=re.compile(r"comment_list|comments|replies"))
    if comment_area:
        for c_item in comment_area.find_all(["div", "li"], class_=re.compile(r"comment|reply")):
            c_writer = c_item.find(class_=re.compile(r"writer|author|user"))
            c_date = c_item.find(class_=re.compile(r"date|time"))
            c_body = c_item.find(class_=re.compile(r"content|text|body"))
            if c_body:
                replies.append(
                    BoardReplyItem(
                        author=c_writer.get_text(strip=True) if c_writer else "담당자",
                        created_at=c_date.get_text(strip=True) if c_date else "",
                        content=html_to_markdown(str(c_body)),
                    )
                )

    return BoardArticleDetail(
        subject=subject,
        author=author,
        created_at=created_at,
        hit_count=hit_count,
        content=markdown_content,
        attachments=attachments,
        replies=replies,
    )
```

### 4. HTML-to-Markdown Text Converter
```python
# src/kau_assistant/board/text_converter.py
from bs4 import BeautifulSoup
import re

def html_to_markdown(html_content: str) -> str:
    """Converts HTML post bodies to clean readable Markdown."""
    if not html_content or not html_content.strip():
        return ""

    soup = BeautifulSoup(html_content, "lxml")

    # Remove unwanted tags
    for tag in soup(["script", "style", "meta", "link"]):
        tag.decompose()
    for tag in soup.find_all(class_="accesshide"):
        tag.decompose()

    # Convert line breaks
    for br in soup.find_all(["br", "hr"]):
        br.replace_with("\n")

    # Convert links
    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True)
        href = a["href"]
        if text and href and not href.startswith("javascript:"):
            a.replace_with(f"[{text}]({href})")

    # Convert bold / strong
    for b in soup.find_all(["strong", "b"]):
        txt = b.get_text(strip=True)
        if txt:
            b.replace_with(f"**{txt}**")

    # Convert italics
    for i in soup.find_all(["em", "i"]):
        txt = i.get_text(strip=True)
        if txt:
            i.replace_with(f"*{txt}*")

    # Convert list items
    for li in soup.find_all("li"):
        txt = li.get_text(strip=True)
        li.replace_with(f"\n- {txt}")

    # Convert paragraphs and headers with block spacing
    for p in soup.find_all(["p", "div", "blockquote", "h1", "h2", "h3", "h4", "h5", "h6"]):
        p.insert_after("\n\n")

    raw_text = soup.get_text()
    # Replace non-breaking spaces and normalize
    cleaned = raw_text.replace("\xa0", " ")
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n\s*\n\s*\n+", "\n\n", cleaned)
    return cleaned.strip()

def extract_summary_preview(text: str, max_lines: int = 2, max_chars: int = 140) -> str:
    """Creates a concise 1-2 line summary preview for table cells."""
    if not text:
        return ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    preview_lines = lines[:max_lines]
    combined = " ".join(preview_lines)
    if len(combined) > max_chars:
        return combined[:max_chars - 3] + "..."
    return combined
```

### 5. Local Read State Manager (`board_read_state.json`)
```python
# src/kau_assistant/board/read_state.py
from datetime import datetime
import json
import logging
from pathlib import Path
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class CourseReadState(BaseModel):
    read_post_ids: list[str] = Field(default_factory=list)
    last_read_at: datetime | None = None

class BoardReadStateFile(BaseModel):
    version: int = 1
    courses: dict[str, CourseReadState] = Field(default_factory=dict)

class BoardReadStateManager:
    """Tracks read post IDs per course with atomic writes and LRU 200 entry capping."""

    def __init__(self, state_file_path: Path, max_entries_per_course: int = 200) -> None:
        self.state_file_path = state_file_path
        self.max_entries = max_entries_per_course
        self._state = self._load()

    def _load(self) -> BoardReadStateFile:
        if not self.state_file_path.exists():
            return BoardReadStateFile()
        try:
            content = self.state_file_path.read_text(encoding="utf-8")
            return BoardReadStateFile.model_validate_json(content)
        except Exception as e:
            logger.warning(f"Failed to load board read state: {e}. Starting fresh.")
            return BoardReadStateFile()

    def save(self) -> None:
        """Atomically saves state using temporary file replacement."""
        self.state_file_path.parent.mkdir(parents=True, exist_ok=True)
        temp_file = self.state_file_path.with_suffix(".tmp")
        try:
            temp_file.write_text(self._state.model_dump_json(indent=2), encoding="utf-8")
            temp_file.replace(self.state_file_path)
        except Exception as e:
            logger.error(f"Failed to write board read state: {e}")
            if temp_file.exists():
                temp_file.unlink(missing_ok=True)

    def is_read(self, course_id: str, post_id: str) -> bool:
        course_state = self._state.courses.get(str(course_id))
        return bool(course_state and post_id in course_state.read_post_ids)

    def mark_as_read(self, course_id: str, post_ids: list[str]) -> None:
        c_id = str(course_id)
        if c_id not in self._state.courses:
            self._state.courses[c_id] = CourseReadState()
        
        c_state = self._state.courses[c_id]
        current_set = set(c_state.read_post_ids)
        for pid in post_ids:
            if pid not in current_set:
                c_state.read_post_ids.append(pid)
                current_set.add(pid)

        # LRU capping: keep last `max_entries` IDs
        if len(c_state.read_post_ids) > self.max_entries:
            c_state.read_post_ids = c_state.read_post_ids[-self.max_entries:]

        c_state.last_read_at = datetime.now()
        self.save()
```

### 6. Pydantic Models & Standard JSON Contract (`schema_version: 1`)
```python
# src/kau_assistant/board/models.py
from datetime import datetime
from enum import Enum
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = 1

class BoardType(str, Enum):
    NOTICE = "notice"
    QNA = "qna"
    OTHER = "other"
    CUSTOM = "custom"

class BoardAttachmentItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    filename: str
    download_url: str
    filesize: int = 0
    saved_path: str | None = None

class BoardReplyItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    author: str
    created_at: str
    content: str

class BoardPostItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    post_id: str
    bwid: str | None = None
    board_id: str
    board_type: BoardType
    title: str
    author: str
    created_at: str
    hit_count: int = 0
    url: str
    is_read: bool = False
    is_my_question: bool = False
    is_answered: bool | None = None
    summary_preview: str = ""
    content: str | None = None
    attachments: list[BoardAttachmentItem] = Field(default_factory=list)
    replies: list[BoardReplyItem] = Field(default_factory=list)

class CourseBoardGroup(BaseModel):
    model_config = ConfigDict(extra="forbid")
    course_id: str
    course_name: str
    course_abbr: str
    notices: list[BoardPostItem] = Field(default_factory=list)
    qna: list[BoardPostItem] = Field(default_factory=list)

class BoardSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    total_courses: int
    total_notices: int
    unread_notices: int
    total_questions: int
    unanswered_questions: int
    my_questions: int

class BoardReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = SCHEMA_VERSION
    command: Literal["board", "notices", "qna"] = "board"
    generated_at: datetime
    summary: BoardSummary
    courses: list[CourseBoardGroup] = Field(default_factory=list)
    errors: list[dict] = Field(default_factory=list)
```

---

## Validation Architecture

The test harness must validate all core requirements with unit and integration tests across multiple realistic fixtures without calling the live LXP server.

### Test Matrix

| Area | Test File | Key Test Cases | Requirements Covered |
|---|---|---|---|
| **Board Parser** | `tests/test_board_parser.py` | 1. Parse module activities on course home (clean accesshide, classify notice vs qna)<br>2. Parse notice table (5 columns, extract bwid, author, created_at)<br>3. Parse Q&A table (6 columns, status badges `[답변완료]`/`[답변대기]`, comment count)<br>4. Parse threaded reply Q&A rows (`[RE]`, reply icon)<br>5. Parse secret posts gracefully<br>6. Parse `article.php` details, attachments, and replies | BRD-01, BRD-02 |
| **HTML Converter** | `tests/test_board_text_converter.py` | 1. Strip `<script>`, `<style>`, `.accesshide`<br>2. Convert links, bold, italics, lists, and linebreaks<br>3. Replace non-breaking space `\xa0`<br>4. Generate 2-line summary previews without breaking words | BRD-01 (D-15-07) |
| **Read State** | `tests/test_board_read_state.py` | 1. Check `is_read` and `mark_as_read`<br>2. Atomic write with `.tmp` and replace<br>3. LRU cap enforcement (exceeding 200 items trims oldest)<br>4. Corrupted state file recovery | BRD-02 (D-15-14, D-15-15) |
| **Orchestrator & Runner** | `tests/test_board_runner.py` | 1. Multi-course collection with course-level exception isolation<br>2. Filter by `--limit N` and `--all`<br>3. Filter by `--unread-only`<br>4. Filter by `--unanswered` and `--my`<br>5. Single article `--view <id>` fetch and auto-mark-read<br>6. `--download-attachments` integration | BRD-01, BRD-02 |
| **CLI & JSON Contract** | `tests/test_cli_board.py` | 1. `kau-assistant board` Rich table output<br>2. `kau-assistant notices` and `kau-assistant qna` aliases<br>3. `kau-assistant board --json` schema validation (`schema_version: 1`)<br>4. `kau-assistant board --view <id>` terminal viewer<br>5. UTF-8 output streams and exit code contracts (0, 1, 2) | BRD-01, BRD-02 (D-15-01, D-15-04) |

### Verification Commands
```bash
# 1. Run all board unit tests
uv run pytest tests/test_board_parser.py tests/test_board_text_converter.py tests/test_board_read_state.py tests/test_board_runner.py tests/test_cli_board.py -v

# 2. Run full regression suite to ensure zero breaking changes
uv run pytest tests/ -v

# 3. Verify CLI help output
uv run python -m kau_assistant board --help
uv run python -m kau_assistant notices --help
uv run python -m kau_assistant qna --help
```

---

## Conclusion & Readiness

- All technical aspects of Coursemos `ubboard` page layout, table variations, detail views, and attachment links are empirically verified against public Coursemos instances (Korea Univ, Postech, Daelim Univ, Ulsan Univ).
- Zero external dependencies need to be added to `pyproject.toml` (`beautifulsoup4`, `lxml`, `rich`, `httpx`, `pydantic`, `click` are already available).
- The phase is fully ready for planning (`15-01-PLAN.md`).
