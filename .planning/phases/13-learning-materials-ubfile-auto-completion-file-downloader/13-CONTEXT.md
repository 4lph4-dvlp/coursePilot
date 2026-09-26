# Phase 13: Learning Materials (ubfile) Auto-Completion & File Downloader - Context

**Gathered:** 2026-09-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 13 delivers automated completion of unviewed course materials (`ubfile`) on Coursemos LXP and an organized local hierarchical downloader for lecture documents (PDF, PPT, ZIP, HWP, etc.):
1. 미열람 상태의 `ubfile` 학습자료 페이지를 방문(열람)하여 LXP 진도율을 100% 완료 상태로 자동 갱신.
2. 첨부 파일을 과목명 및 주차별 계층 폴더(`downloads/<과목명>/W{주차}/`) 구조로 로컬에 다운로드 및 정리.
3. CLI 명령어 `coursepilot materials` (별칭 `files`) 및 `--course`, `--week`, `--output-dir`, `--no-download`, `--dry-run`, `--json` 옵션 지원.
4. LXP 세션 인증 쿠키를 재사용하는 안전한 스트림/파일 다운로드 파이프라인 구축.

</domain>

<decisions>
## Implementation Decisions

### 1. 저장 경로 및 폴더 구조
- **D-13-01:** 기본 저장 디렉터리는 프로젝트 하위 `downloads/<과목명>/W{주차}/`로 계층화하며, `.env`의 `DOWNLOAD_DIR` 설정으로 기본 경로를 커스텀할 수 있도록 지원한다. CLI의 `--output-dir <경로>` 옵션이나 에이전트 프롬프트 요청으로 특정 경로가 전달되면 이를 최우선으로 적용한다.
- **D-13-02:** 중복 파일 처리 시 로컬 파일 크기와 원격 파일 크기를 비교하여, 동일할 경우 다운로드를 건너뛰고(Skip) 크기 차이 발생 시 덮어쓴다(Overwrite).

### 2. 열람 및 다운로드 실행 정책
- **D-13-03:** 기본 실행 시 LXP 진도율 이수(열람 방문)와 첨부 파일 다운로드를 함께 수행한다. 파일 저장을 원치 않고 출석/진도만 채우고자 할 때는 `--no-download` 플래그를 통해 열람만 수행할 수 있다.
- **D-13-04:** 스마트 처리 정책을 적용하여, LXP 열람(방문) 처리는 '미열람' 상태인 자료만 방문하여 불필요한 반복 트래픽을 방지하고, 파일 다운로드는 로컬에 파일이 없는 모든 자료를 빠짐없이 받아준다.

### 3. CLI 명령어 인터페이스 및 Notion 연동 정책
- **D-13-05:** CLI 명령어는 `coursepilot materials`를 표준으로 제공하며, 사용자 편의를 위해 `files` 별칭도 함께 지원한다.
- **D-13-06:** `--course` 옵션 생략 시 전체 수강 과목을 순차적으로 처리하고, 특정 과목 지정 시 해당 과목만 처리한다(기존 `check` 명령어와 일관된 패턴). 주차 필터링은 `--week` ('current', 'all', 또는 주차 번호)를 지원한다.
- **D-13-07:** 학습자료는 과제나 시험과 달리 마감 일정이 없으므로, 개인 스케줄러 DB 오염 방지를 위해 Notion 연동 대상에서 제외하고 LXP 진도 100% 이수 및 로컬 다운로드로 범위를 한정한다.
- **D-13-08:** 실제 네트워크 다운로드나 페이지 방문 없이 대상 자료 목록, 파일명, 예상 저장 경로를 미리 확인할 수 있는 `--dry-run` 모드 및 에이전트 연동용 `--json` 출력을 지원한다.

### the agent's Discretion
- 세션 유지 방식: Playwright 컨텍스트의 쿠키를 추출하여 `httpx` 또는 `urllib`로 직접 스트리밍 다운로드할지, Playwright `download` 이벤트를 활용할지는 다운로드 성능과 신뢰성을 고려하여 플래너 및 리서처가 최적의 방식을 결정.
- 파일명 특수문자/공백 정규화(sanitization) 및 HTTP `Content-Disposition` 헤더 인코딩 파싱 구현 상세.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Roadmap & Requirements
- `.planning/ROADMAP.md` § Phase 13 — Phase boundary and success criteria
- `.planning/REQUIREMENTS.md` § RES-01, RES-02 — Learning materials requirements

### Existing Scraper & Session Core
- `src/coursepilot/scraper/navigator.py` — Course navigation and page fetching patterns
- `src/coursepilot/scraper/course_list.py` — Course extraction and clean_name resolution
- `src/coursepilot/session_manager.py` — Playwright session caching and authentication cookies
- `src/coursepilot/config.py` — Configuration loading and `.env` settings

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `CourseNavigator`: 과목 홈 진입 및 주차별 섹션 페이지 탐색.
- `SessionManager`: 인증된 브라우저 컨텍스트 및 쿠키 제공.
- `extract_courses` / `find_target_course`: 과목 목록 파싱 및 퍼지 과목명 매칭.
- `AttachmentMeta`: 파일명, URL, 파일 크기 메타데이터 모델.

### Established Patterns
- Click 기반 CLI 그룹 및 옵션 패턴 (`--course`, `--week`, `--dry-run`, `--json`).
- `Console(stderr=True)`로 진행 상태 출력, stdout은 최종 결과 리포트 또는 JSON만 출력하는 스트림 분리 패턴.

### Integration Points
- `src/coursepilot/scraper/materials_parser.py` (또는 기존 scraper 확장): `ubfile` 학습자료 링크 및 첨부파일 정보 추출.
- `src/coursepilot/materials/downloader.py` (신규): 세션 쿠키 기반 파일 다운로드 및 로컬 디렉터리 저장 관리.
- `src/coursepilot/cli.py`: `@cli.command("materials")` 등록.

</code_context>

<specifics>
## Specific Ideas

- 사용자가 "기초전자실험 이번주 자료 받아줘"라고 했을 때, 2주차 `ubfile`을 방문하여 진도율을 100%로 만들고 `downloads/기초전자실험/W2/실험매뉴얼.pdf` 형태로 저장.
- "자료만 열람해줘"라고 했을 때 `--no-download`로 파일 용량 소모 없이 진도율만 신속하게 100% 처리.

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope.

</deferred>

---

*Phase: 13-learning-materials-ubfile-auto-completion-file-downloader*
*Context gathered: 2026-09-25*
