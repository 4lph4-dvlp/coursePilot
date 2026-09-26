# Phase 15: Course Announcements & Q&A Board Briefing - Context

**Gathered:** 2026-09-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 15 delivers Coursemos LXP course board parsing and interactive CLI briefing for announcements and Q&A:
1. 과목별 공지사항 게시판(`ubboard`)의 최근 공지글 목록(번호, 제목, 작성자, 작성일) 및 본문/첨부파일 메타데이터 추출.
2. Q&A 게시판의 질문글 및 답변 상태(답변완료/답변대기), 교수/조교의 공식 답변 본문 파싱.
3. 통합 CLI 명령어 `coursepilot board` 및 단독 편의 서브커맨드 `notices`, `qna` 제공.
4. 기본 과목당 최근 3개(`--limit 3`), 개수 지정(`--limit N`), 전체 조회(`--all`), 상세 전문 뷰어(`--view <id>`), 미확인 공지 필터(`--unread-only`), 답변 대기 질문 필터(`--unanswered`), 내 질문 필터(`--my`) 지원.
5. 로컬 읽음 상태 파일(`board_read_state.json`) 기반 `[NEW]` 태그 및 읽음(`--mark-read`) 관리.
6. 표준 JSON 계약(`schema_version: 1`) 기반 에이전트 연동 지원.
7. Notion Scheduler에는 연동하지 않으며(Phase 13 원칙 준수), LXP 서버 트래픽 최소화(목록 우선, 전문 요청 시 상세 페이지 방문)를 보장.

</domain>

<decisions>
## Implementation Decisions

### 1. CLI 명령어 및 진입점 설계
- **D-15-01:** `coursepilot board`를 단일 통합 명령어로 제공하여 공지사항과 Q&A를 함께 브리핑하며, 사용자 편의를 위해 `coursepilot notices`와 `coursepilot qna` 단독 별칭(또는 서브커맨드)도 함께 지원한다. — **Reversibility:** costly — CLI 명령어 시그니처 및 에이전트 스킬 연동 경로에 영향
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

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Roadmap & Requirements
- `.planning/ROADMAP.md` § Phase 15 — Course Announcements & Q&A Board Briefing requirements and success criteria
- `.planning/REQUIREMENTS.md` § BRD-01, BRD-02 — Board requirements

### Scraper Core & Navigation Patterns
- `src/coursepilot/scraper/navigator.py` — Course navigation and page fetching patterns
- `src/coursepilot/scraper/course_list.py` — Course extraction and clean_name resolution
- `src/coursepilot/scraper/material_parser.py` — Section/module activity inspection and accesshide cleaning patterns
- `src/coursepilot/scraper/date_parser.py` — Korean date string parsing utilities
- `src/coursepilot/session_manager.py` — Playwright session caching and authentication cookies
- `src/coursepilot/config.py` — Configuration loading and settings

### CLI & Reporting Architecture
- `src/coursepilot/cli.py` — Click CLI command groups, option patterns, and error handling
- `src/coursepilot/reporter.py` — Rich table formatting and console stream separation (stderr vs stdout)
- `src/coursepilot/report_models.py` — JSON contract models and serialization conventions
- `src/coursepilot/materials/downloader.py` — File downloader engine reusable for `--download-attachments`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `CourseNavigator`: 과목 홈 방문 및 Coursemos 내부 페이지 접근 세션 제어.
- `SessionManager`: 인증 쿠키 및 헤드리스 브라우저 컨텍스트 제공.
- `extract_courses` / `find_target_course`: 수강 과목 목록 추출 및 퍼지 매칭.
- `parse_date` / `format_date`: 한국어 날짜/시간 정규화.
- `Downloader`: Phase 13에서 구현된 세션 쿠키 기반 다운로더 엔진 (`--download-attachments` 재사용).

### Established Patterns
- Click 기반 명령/서브커맨드 (`coursepilot <command>`) 구조.
- `Console(stderr=True)`로 실시간 진행 상태/로그를 출력하고 stdout은 최종 브리핑 리포트 또는 JSON만 단독 출력.
- Course-level try-except 예외 격리: 한 과목의 게시판 조회에 실패해도 다른 과목의 브리핑이 중단되지 않고 결과에 경고만 포함.
- 정규화된 과목 약칭 매핑 및 깔끔한 과목명(`clean_name`) 사용.

### Integration Points
- `src/coursepilot/scraper/board_parser.py` (신규): `ubboard` 목록 파싱, 글 번호/제목/작성자/작성일/답변여부/본문/첨부파일 추출.
- `src/coursepilot/board/` (신규 패키지): `models.py` (도메인 모델), `runner.py` (수집 및 뷰어 로직), `read_state.py` (로컬 읽음 상태 관리).
- `src/coursepilot/cli.py`: `@cli.command("board")` 및 `@cli.command("notices")`, `@cli.command("qna")` 서브커맨드 등록.

</code_context>

<specifics>
## Specific Ideas

- 사용자가 `coursepilot board` 실행 시: "최근 공지가 있는 과목들의 중요 공지와 질문 답변 현황을 깔끔한 Rich Table로 한눈에 요약 브리핑."
- 사용자가 `coursepilot board --view 1234` 실행 시: "1234번 게시글의 본문 전문, 첨부파일 목록, 교수님 답변을 터미널에서 읽기 좋은 마크다운 뷰어로 렌더링하고 자동으로 읽음 처리."
- 사용자가 `coursepilot notices --unread-only` 실행 시: "아직 내가 확인하지 않은 [NEW] 공지사항만 쏙 골라서 출력."
- 사용자가 `coursepilot qna --unanswered --my` 실행 시: "내가 질문한 것 중 아직 교수님/조교님 답변이 달리지 않은 대기 질문만 필터링."

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope.

</deferred>

---

*Phase: 15-course-announcements-q-a-board-briefing*
*Context gathered: 2026-09-26*
