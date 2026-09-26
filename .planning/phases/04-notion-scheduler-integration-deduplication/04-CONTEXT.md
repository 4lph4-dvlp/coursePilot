# Phase 4: Notion Scheduler Integration & Deduplication - Context

**Gathered:** 2026-09-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 4는 사용자의 기존 개인 Notion Scheduler 데이터베이스(`21d53280-64be-80ec-af4e-000b679f03bb` 또는 `NOTION_DATABASE_NAME`)와 연동하여, Phase 3에서 정규화된 `SyncTask` 목록을 기등록 페이지와 비교하여 중복을 방지하고 스마트하게 업서트(Smart Upsert)하는 전용 노션 동기화 엔진(`src/coursepilot/notion/`)을 구축합니다:
1. 공식 Python `notion-client` 기반 API 클라이언트 및 인증/에러 핸들러 (`client.py`)
2. 데이터베이스 이름 기반 자동 탐색 및 ID 매핑 모듈 (`NOTION_DATABASE_NAME` 지원)
3. 정규화된 작업명(`title`) 기준 기존 페이지 쿼리 및 중복 판별 엔진 (`deduplicator.py`)
4. Notion Scheduler DB 스키마(`이름`, `선택`, `구분`, `DueDate`, `Plan`, `우선순위`, `상태`, `메모`) 속성 매퍼 (`mapper.py`)
5. 신규 생성 및 스마트 부분 업데이트를 총괄하는 동기화 오케스트레이터 (`engine.py`)
6. 실제 쓰기 없이 변경 예정 사항을 사전 검증하는 완전한 드라이런(Dry-run) 시뮬레이션 및 결과 DTO (`SyncResult`)
7. 노션 토큰이 없거나 동기화를 원치 않는 사용자를 위한 독립 실행 안전 폴백 모드

*CLI 인수 파싱(`--dry-run` 등), 콘솔 색상 터미널 표 출력 및 Antigravity Skill 패키징은 Phase 5의 영역입니다.*

</domain>

<decisions>
## Implementation Decisions

### 1. 중복 감지 및 기존 페이지 동기화 정책 (Deduplication & Upsert Strategy)
- **D-01:** 스마트 부분 업데이트(Smart Upsert) 정책 적용. 노션 DB에 동일 작업명의 페이지가 이미 존재할 경우, `DueDate`(마감일), `우선순위`, `메모`는 최신 상태로 업데이트하되 사용자가 노션에서 직접 수정한 `상태`('완료', '진행 중' 등)와 직접 기입한 `Plan`(계획일)은 덮어쓰지 않고 안전하게 보존. — **Reversibility:** costly — 노션 기등록 데이터 상태 보존 및 사용자 편의성에 직접 영향
- **D-02:** 중복 판별 고유 식별자로 정규화된 작업명(`title`, 예: `[공수2] 3주차 행렬 연산 과제 제출`) 사용. 교수자가 과제 마감 기한을 연장하더라도 제목이 일치하면 동일 작업으로 정확히 매칭되어 중복 페이지가 생성되지 않고 기존 페이지의 마감일만 최신으로 갱신. — **Reversibility:** costly — 노션 DB 내 검색 쿼리 및 페이지 타이틀 매칭 구조에 영향
- **D-03:** 노션 DB 조회 시 최근 90일(3개월) 이내 `DueDate` 또는 미완료(`상태` != '완료') 필터 쿼리를 적용하여, 과거 학기 전체 데이터를 매번 다운로드하지 않고 API 호출 수와 응답 속도를 최적화. — **Reversibility:** reversible

### 2. 드라이런(Dry-run) 시뮬레이션 및 결과 모델 (Dry-run & Sync Result Reporting)
- **D-04:** 완전한 시뮬레이션(Real Read, Mocked Write) 방식 채택. `--dry-run` 모드 실행 시 노션 DB 읽기는 실제로 수행하여 중복 여부를 정밀 판별하되, 노션 API의 생성(`pages.create`) 및 수정(`pages.update`) 호출만 차단하고 생성 예정/수정 예정/건너뜀 목록을 담은 상세 `SyncResult` 반환. — **Reversibility:** reversible
- **D-05:** Phase 5의 CLI Rich 리포터와 연동하기 위해 상세 계층형 `SyncResult` DTO 모델 제공 (`created`, `updated`(변경 필드 diff 포함), `skipped`(스킵 사유 포함), `errors`, `stats`). — **Reversibility:** reversible

### 3. Notion API 연동 라이브러리 및 DB 자동 검색 (API Client & Database Auto-Discovery)
- **D-06:** 공식 Python `notion-client` SDK를 사용하며, 노션 공식 초당 3회 제한 방어를 위한 미세 딜레이(약 0.35초) 및 429(Too Many Requests) 발생 시 `Retry-After` 헤더 기반 지수 백오프(최대 3회) 재시도 로직을 내장. — **Reversibility:** costly — 의존성 패키지 및 통신 계층 구조
- **D-07:** 데이터베이스 이름 기반 자동 탐색(Auto-Discovery by Title) 지원. 일반 사용자가 32자리 UUID ID를 찾기 어렵더라도 `.env`에 `NOTION_DATABASE_NAME="Scheduler"`(또는 `"스케줄러"`)만 입력하면, Notion API의 `POST /v1/search`를 통해 database_id를 자동 검색·해결. (단, 명시적 `NOTION_DATABASE_ID`가 지정되어 있다면 이를 최우선 사용) — **Reversibility:** reversible

### 4. 페이지 본문 블록 vs 메모 속성 (Page Properties vs Body Content)
- **D-08:** 과제 설명, 첨부파일 목록, LMS 바로가기 링크는 DB 테이블의 `메모`(`rich_text`) 속성에만 1500/1950자 안전 절삭하여 기록하고 페이지 본문(block children)은 비워둠. 노션 캘린더/보드/테이블 뷰에서 페이지를 열지 않고도 카드 미리보기에서 바로 확인 가능하며, 페이지당 단 1회의 API 호출로 생성이 완료되어 성능과 효율 극대화. — **Reversibility:** reversible

### 5. 노션 미연동 사용자를 위한 독립 실행 및 안전 폴백 (Decoupled / Standalone Fallback)
- **D-09:** `NOTION_TOKEN` 또는 DB 설정이 누락되어 있거나 비활성화된 경우, 에러로 중단되지 않고 안전 폴백 모드로 동작. LXP 로그인, 수강 진도 및 과제 마감일 분석은 정상 완결한 후 노션 동기화 단계만 안전하게 스킵하여 LXP 정보만 확인하려는 사용자도 완전하게 지원. — **Reversibility:** reversible

### the agent's Discretion
- `notion-client` 내부 요청 시 `httpx.Timeout` 세부 수치 설정 (기본 30초)
- 노션 API 에러 코드(401 Unauthorized, 404 Not Found) 발생 시 친절한 한국어 가이드 메시지 포맷팅

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project & Roadmap Specs
- `.planning/PROJECT.md` — 프로젝트 개요, 노션 Scheduler DB 스키마(`이름`, `선택`, `구분`, `DueDate`, `Plan`, `우선순위`, `상태`, `메모`), 중복 방지 제약
- `.planning/REQUIREMENTS.md` — `NOTN-01` (Notion 연결/인증), `NOTN-02` (스키마 매핑), `NOTN-03` (기등록 조회 기반 중복 방지), `NOTN-04` (드라이런 모드)
- `.planning/ROADMAP.md` — Phase 4 목표 및 마일스톤 성공 기준
- `.planning/phases/03-domain-modeling-naming-rules/03-CONTEXT.md` — Phase 3 도메인 모델 결정사항 (D-01~D-15)

### Source Code References
- `src/coursepilot/domain/models.py` — `SyncTask`, `TaskPriority`, `TaskSelect`, `TaskStatus`, `TaskType`
- `src/coursepilot/domain/naming.py` — `format_task_title` (매칭 키 생성)
- `src/coursepilot/domain/transformer.py` — `transform_to_sync_tasks`, `format_memo`
- `src/coursepilot/config.py` — `AppConfig`, `get_config` (환경변수 관리)

### External API References
- Notion API Query Database: `https://developers.notion.com/reference/post-database-query`
- Notion API Create Page: `https://developers.notion.com/reference/post-page`
- Notion API Update Page: `https://developers.notion.com/reference/patch-page`
- Notion API Search: `https://developers.notion.com/reference/post-search`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/coursepilot/domain/models.py`: `SyncTask` 객체가 노션 스케줄러 스키마의 8개 필드와 완벽히 정합하도록 설계되어 있음 (`selection`, `category`, `due_date`, `priority`, `status`, `memo`).
- `src/coursepilot/config.py`: `NOTION_TOKEN`, `NOTION_DATABASE_ID` 필드가 기정의되어 있으며, `NOTION_DATABASE_NAME`을 추가하여 이름 기반 탐색 지원 가능.
- `src/coursepilot/scraper/date_parser.py`: `KST` 타임존을 통해 노션 날짜 ISO 8601 포맷팅(`YYYY-MM-DDTHH:MM:SS+09:00`) 시 타임존 오차 차단.

### Established Patterns
- Pydantic BaseModel 기반 엄격한 스키마 및 결과 DTO 모델 정의
- Politeness / Throttling 딜레이를 통한 타겟 서비스(LMS 및 Notion API) 부하 방지
- 환경변수 누락 시 프로그램이 크래시되지 않고 친절한 경고와 함께 안전 폴백(Graceful degradation)

### Integration Points
- `src/coursepilot/notion/`: 이번 Phase 4에서 구축되는 노션 통합 모듈 (`client.py`, `mapper.py`, `deduplicator.py`, `engine.py`, `__init__.py`).
- Phase 5 CLI 진입점(`src/coursepilot/cli.py`)에서 `NotionSyncEngine`을 호출하여 `sync` 및 `check` 명령 수행.

</code_context>

<specifics>
## Specific Ideas

- **노션 DB 이름 자동 탐색**: 사용자가 번거롭게 Notion URL에서 복잡한 ID를 복사하지 않아도, `.env`에 `NOTION_DATABASE_NAME="Scheduler"`만 적으면 알아서 ID를 찾아 연결할 것.
- **노션 미연동 사용자 배려**: 노션 토큰이 없거나 스케줄러를 쓰지 않는 학생도 LXP 강의/과제 확인 용도로 단독 사용할 수 있도록 에러 없이 깔끔히 리포트만 출력하는 폴백을 보장할 것.
- **사용자 수동 상태 존중**: 학생이 노션에서 과제를 이미 '진행 중'이나 '완료'로 바꿨다면, LXP에서 아직 미제출 상태라도 노션 상태를 '시작 전'으로 강제 덮어쓰지 않고 학생의 노션 입력을 최우선 존중할 것.

</specifics>

<deferred>
## Deferred Ideas

- None — 모든 논의가 Phase 4 Notion Scheduler Integration & Deduplication 범위 내에서 집중적으로 완료됨.

</deferred>

---

*Phase: 4-Notion Scheduler Integration & Deduplication*
*Context gathered: 2026-09-21*
