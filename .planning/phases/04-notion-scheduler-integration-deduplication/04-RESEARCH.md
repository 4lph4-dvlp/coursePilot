# Phase 4: Notion Scheduler Integration & Deduplication - Research

**Researched:** 2026-09-22
**Domain:** Notion API data-source integration, title-keyed deduplication, partial upsert, and dry-run orchestration
**Confidence:** MEDIUM

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

<!-- DATA_41C8A2F7_START -->
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
<!-- DATA_41C8A2F7_END -->

### the agent's Discretion

<!-- DATA_9E31B6D4_START -->
- `notion-client` 내부 요청 시 `httpx.Timeout` 세부 수치 설정 (기본 30초)
- 노션 API 에러 코드(401 Unauthorized, 404 Not Found) 발생 시 친절한 한국어 가이드 메시지 포맷팅
<!-- DATA_9E31B6D4_END -->

### Deferred Ideas (OUT OF SCOPE)

<!-- DATA_C7F240A9_START -->
- None — 모든 논의가 Phase 4 Notion Scheduler Integration & Deduplication 범위 내에서 집중적으로 완료됨.
<!-- DATA_C7F240A9_END -->
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| NOTN-01 | Notion Scheduler DB의 기존 페이지를 조회하여 작업명과 DueDate를 확인한다. | Resolve database → data source, validate schema, query the locked 90-day-or-incomplete window, paginate, and parse exact title/date properties. [VERIFIED: .planning/REQUIREMENTS.md:29-29] |
| NOTN-02 | 기존 항목은 건너뛰고 신규 미완료 항목만 등록한다. | Build a title-only index, classify create/update/unchanged/conflict, and apply D-01 partial-update semantics without creating a second page. [VERIFIED: .planning/REQUIREMENTS.md:30-30] |
| NOTN-03 | Scheduler 속성을 정확히 매핑하여 새 페이지를 생성한다. | Preflight the eight-property schema, build a typed page property payload, omit Plan on create, and leave page body empty. [VERIFIED: .planning/REQUIREMENTS.md:31-31] |
| NOTN-04 | 실제 등록 전에 등록 대상과 스킵 목록을 보는 dry-run을 지원한다. | Split planning from write execution; dry-run performs the same live reads and diffs while proving pages.create/pages.update are never called. [VERIFIED: .planning/REQUIREMENTS.md:32-32] |
</phase_requirements>

## Project Constraints

No physical `AGENTS.md` exists at the workspace root as of this research run. The task-injected execution guidance remains authoritative: GSD owns lifecycle/state, searches and outputs must stay bounded, delegation requires authorization, targeted checks precede the final full suite, and quota failures must stop blind retries. [VERIFIED: workspace probe 2026-09-22]

The project requires Python 3.11 or newer and already declares notion-client, Pydantic, pytest, pytest-mock, and pytest-asyncio; Phase 4 should extend this stack rather than introduce a parallel HTTP or validation framework. [VERIFIED: pyproject.toml:6-25]

## Summary

Implement Phase 4 as a synchronous integration layer with five separable responsibilities: configuration/target resolution, SDK transport, pure property mapping, pure deduplication/action planning, and orchestration/write execution. The critical sequence is: configuration gate → resolve database and data-source IDs → retrieve and validate the live data-source schema → query and paginate existing pages → parse and index exact normalized titles → compute create/update/skip/error actions → stop for dry-run or execute writes → return one hierarchical `SyncResult`. [VERIFIED: .planning/phases/04-notion-scheduler-integration-deduplication/04-CONTEXT.md:7-16] [CITED: https://developers.notion.com/guides/get-started/upgrade-guide-2025-09-03]

Notion API version `2025-09-03` changed the model from “database ID is queryable” to “database is a container; data source is queryable.” The locked explicit database UUID therefore must first go through `databases.retrieve` to discover its child `data_source_id`; name-based search should filter for `data_source` objects and return both the data-source ID and its parent database ID. Schema comes from `data_sources.retrieve`, entries from `data_sources.query`, and new pages should use a `data_source_id` parent. [CITED: https://developers.notion.com/guides/get-started/upgrade-guide-2025-09-03] [CITED: https://developers.notion.com/reference/retrieve-database]

The primary codebase hazard is the existing `SyncTask.dedup_key`, which currently combines title and due time. That contradicts D-02, under which a deadline change must update the same page. The Notion deduplicator must key on `SyncTask.title` alone, and the plan should either redefine/remove the misleading property or explicitly ban its use in Phase 4 tests. [VERIFIED: src/kau_assistant/domain/models.py:80-84]

**Primary recommendation:** implement a pure `plan_sync` stage and a narrow write executor; configure the official SDK for three 429 retries, keep the locked 0.35-second request spacing, and make target/schema validation mandatory before either dry-run or live writes. [CITED: https://github.com/ramnes/notion-sdk-py] [CITED: https://developers.notion.com/reference/request-limits]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Configuration gate and safe fallback | Application / API backend | — | The local application decides whether the external integration is enabled; no Notion call should be constructed when token or target is absent. [VERIFIED: src/kau_assistant/config.py:26-31] |
| Database/data-source discovery | API / Backend | Notion external service | Search/retrieve are transport concerns and must remain outside pure domain logic. [CITED: https://developers.notion.com/reference/post-search] |
| Scheduler schema validation | API / Backend | Notion data source | The live data-source schema is authoritative for property names/types/options. [CITED: https://developers.notion.com/reference/retrieve-a-data-source] |
| Title-key deduplication and diff planning | Domain / Application | — | Given SyncTasks and parsed existing pages, classification is deterministic and requires no I/O. [VERIFIED: src/kau_assistant/domain/models.py:46-68] |
| Page create/update | API / Backend | Notion external service | Only the client wrapper owns SDK writes, throttling, retries, and error translation. [CITED: https://github.com/ramnes/notion-sdk-py] |
| User-owned Status/Plan preservation | Domain / Application | Notion external service | The planner enforces an update allowlist; the transport sends only that prepared partial payload. [CITED: https://developers.notion.com/reference/patch-page] |
| Dry-run result reporting | Application / API backend | Phase 5 CLI | Phase 4 returns DTOs; Phase 5 renders them and owns CLI parsing/output. [VERIFIED: .planning/phases/04-notion-scheduler-integration-deduplication/04-CONTEXT.md:7-18] |

## Verified In-Repo Contracts

The live mapper must use the following property names/types and option values verbatim; these are the project’s declared Scheduler contract, not inferred English translations. [VERIFIED: .planning/PROJECT.md:38-40]

<!-- DATA_6B1D94E3_START -->
> - **Notion 데이터베이스**: `Scheduler` (ID: `21d53280-64be-80ec-af4e-000b679f03bb`)
>   - 필드: `이름`(Title), `선택`(Select: 루틴/이벤트), `구분`(Multi-select: 학업 등), `DueDate`(Date), `Plan`(Date), `우선순위`(Select: P1~P4), `상태`(Status: 시작 전/진행 중/완료/폐기), `메모`(Text)
<!-- DATA_6B1D94E3_END -->

The enum values consumed by the mapper are quoted verbatim below. [VERIFIED: src/kau_assistant/domain/models.py:21-43]

<!-- DATA_A83F5C20_START -->
> P1 = "P1"
> P2 = "P2"
> P3 = "P3"
> P4 = "P4"
>
> ROUTINE = "루틴"
> EVENT = "이벤트"
>
> NOT_STARTED = "시작 전"
> IN_PROGRESS = "진행 중"
> COMPLETED = "완료"
> DISCARDED = "폐기"
<!-- DATA_A83F5C20_END -->

The source model already fixes category, optional dates, default status, memo, and title fields as follows. [VERIFIED: src/kau_assistant/domain/models.py:46-66]

<!-- DATA_2F70C4B9_START -->
> title: str
> selection: TaskSelect
> category: list[str] = Field(default_factory=lambda: ["학업"])
> due_date: datetime | None = None
> plan_date: datetime | None = None  # Always None by default (D-08)
> priority: TaskPriority
> status: TaskStatus = TaskStatus.NOT_STARTED  # D-10: '시작 전' even if overdue
> memo: str = ""
<!-- DATA_2F70C4B9_END -->

Current configuration uses a different token name from D-09, has no database-name field, and gives the personal database ID a non-empty default. These exact definitions make “name only” and “DB setting missing” impossible to distinguish without a config change. [VERIFIED: src/kau_assistant/config.py:26-31]

<!-- DATA_D49A31B8_START -->
> notion_api_key: str = Field(default="", description="Notion Integration API Key")
> notion_database_id: str = Field(
>     default="21d53280-64be-80ec-af4e-000b679f03bb",
>     description="Notion Scheduler Database ID",
> )
<!-- DATA_D49A31B8_END -->

The existing due-date-bearing key is quoted because it must not be reused for D-02. [VERIFIED: src/kau_assistant/domain/models.py:80-84]

<!-- DATA_F5127E6C_START -->
> def dedup_key(self) -> str:
>     """Returns a stable deduplication key for Notion matching (Phase 4)."""
>     due_str = self.due_date.strftime("%Y-%m-%d %H:%M") if self.due_date else "no_due"
>     return f"{self.title}|{due_str}"
<!-- DATA_F5127E6C_END -->

## Standard Stack

### Core

| Library | Version / publish date | Purpose | Why Standard |
|---------|------------------------|---------|--------------|
| `notion-client` **[WARNING: flagged as suspicious — verify before using.]** | 3.1.0, 2026-05-12 | Official-style synchronous Notion SDK surface for search, database/data-source retrieval/query, and page create/update. | Locked by D-06 and already resolved in `uv.lock`; the warning is solely the legitimacy seam’s `SUS` result caused by unavailable download-count telemetry. [CITED: https://github.com/ramnes/notion-sdk-py] [VERIFIED: uv.lock:397-405] |
| Pydantic | 2.13.5, 2026-08-28 | `ExistingPage`, action DTOs, `SyncResult`, error and stats models. | Matches the established project model pattern and installed environment. [VERIFIED: src/kau_assistant/domain/models.py:5-5] [VERIFIED: environment probe 2026-09-22] |
| Python | 3.11+ project floor; 3.14.7 available | Synchronous application runtime. | The repository declares ≥3.11 and the current environment satisfies it. [VERIFIED: pyproject.toml:6-6] [VERIFIED: environment probe 2026-09-22] |

### Supporting

| Library | Version / publish date | Purpose | When to Use |
|---------|------------------------|---------|-------------|
| pytest | 9.1.1, 2026-06-19 | Unit/integration-style tests around injected SDK mocks and pure planners. | All Phase 4 automated verification. [VERIFIED: pyproject.toml:21-25] [VERIFIED: environment probe 2026-09-22] |
| pytest-mock | 3.15.1, 2025-09-16 | Spy/Mock verification that dry-run reads but never writes. | Client and engine tests. [VERIFIED: pyproject.toml:21-25] [VERIFIED: environment probe 2026-09-22] |
| notion-client pagination helpers | bundled with 3.1.0 | Cursor iteration for search and data-source queries. | Use `iterate_paginated_api` or `collect_paginated_api` instead of a second pagination implementation. [CITED: https://github.com/ramnes/notion-sdk-py/blob/main/notion_client/helpers.py] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Official Python SDK | Raw `httpx` REST calls | Not evaluated as a candidate because D-06 is locked; raw HTTP would duplicate auth headers, endpoint construction, error parsing, and retry behavior. [VERIFIED: .planning/phases/04-notion-scheduler-integration-deduplication/04-CONTEXT.md:35-35] |

**Installation:** no new package is required; use the locked environment.

    uv sync --extra dev

The manifest allows `notion-client>=2.2.1` while the lock resolves 3.1.0; implementation and tests must target the locked 3.1 API surface, especially `data_sources` and `RetryOptions`. [VERIFIED: pyproject.toml:7-19] [VERIFIED: uv.lock:397-405]

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| notion-client | PyPI | first release 2021-05-14; current 3.1.0 published 2026-05-12 | unavailable to seam | github.com/ramnes/notion-sdk-py | SUS | Already locked; retain, but planner must add `checkpoint:human-verify` before any install/upgrade. [CITED: https://pypi.org/project/notion-client/] |

**Packages removed due to [SLOP] verdict:** none. [VERIFIED: package-legitimacy seam 2026-09-22]

**Packages flagged as suspicious [SUS]:** notion-client; the seam reason was exactly `unknown-downloads`, while the package is linked from the project lock and official repository documentation. This does not upgrade the verdict to OK. [VERIFIED: package-legitimacy seam 2026-09-22] [CITED: https://github.com/ramnes/notion-sdk-py]

## Architecture Patterns

### System Architecture Diagram

    Phase 3 SyncTask[]
            |
            v
    NotionSyncEngine.sync(tasks, dry_run)
            |
            +--> configuration gate -- missing token/target --> disabled SyncResult
            |
            v
    NotionClient.resolve_target()
       explicit database ID --> databases.retrieve --> child data_source_id
       configured name ------> search(data_source) --> exact unique title match
            |
            v
    data_sources.retrieve --> schema/options preflight
            |
            v
    data_sources.query(filter = recent 90 days OR status != 완료)
            |
            v
    mapper.parse_existing_pages --> deduplicator.plan_sync
            |
            +--> create actions
            +--> update actions (DueDate/우선순위/메모 only)
            +--> unchanged/conflict/error actions
            |
            +--> dry_run=True  --> return planned SyncResult; zero writes
            |
            +--> dry_run=False --> throttled pages.create/pages.update
                                      |
                                      v
                                final SyncResult

This flow keeps Notion as an external service boundary and makes every dry-run decision use the same real read and pure planning path as a live run. [VERIFIED: .planning/phases/04-notion-scheduler-integration-deduplication/04-CONTEXT.md:30-32]

### Recommended Project Structure

    src/kau_assistant/
    ├── config.py                 # add token alias, database name, empty-ID semantics
    └── notion/
        ├── __init__.py           # stable public facade
        ├── models.py             # ExistingPage, actions, diffs, errors, SyncStats, SyncResult
        ├── client.py             # SDK ownership, target/schema/read/write, throttle/error mapping
        ├── mapper.py             # pure Notion property serialization/parsing/diff payloads
        ├── deduplicator.py       # pure title index and action-plan classification
        └── engine.py             # orchestration, dry-run branch, write execution
    tests/
    ├── test_notion_client.py
    ├── test_notion_mapper.py
    ├── test_notion_deduplicator.py
    └── test_notion_engine.py

This preserves the project’s existing “models + pure transformation + orchestrator” shape and keeps SDK dictionaries from leaking into Phase 3 domain models or Phase 5 reporting. [VERIFIED: src/kau_assistant/domain/models.py:1-97] [VERIFIED: src/kau_assistant/domain/transformer.py:215-254]

### Pattern 1: Resolve Both Database and Data-Source IDs

**What:** represent the target as a DTO containing `database_id`, `data_source_id`, and display title. Explicit database ID wins; it is not itself passed to `data_sources.query`. [CITED: https://developers.notion.com/guides/get-started/upgrade-guide-2025-09-03]

**Algorithm:**

1. If an explicit `NOTION_DATABASE_ID` exists, call `databases.retrieve(database_id=...)` and read `data_sources`. [CITED: https://developers.notion.com/reference/retrieve-database]
2. If exactly one child exists, use it; if several exist, require an exact configured data-source/database name or return an ambiguity error rather than selecting index zero. [ASSUMED]
3. Otherwise paginate `search(query=name, filter={"property": "object", "value": "data_source"})`, reconstruct each title, require exact equality locally, and require exactly one match. Search itself uses substring matching and is eventually consistent. [CITED: https://developers.notion.com/reference/post-search] [CITED: https://developers.notion.com/reference/search-optimizations-and-limitations]
4. Return both the matched data source ID and `parent.database_id`. [CITED: https://developers.notion.com/reference/data-source]

### Pattern 2: Preflight the Live Schema

Before querying or writing, retrieve the data source and compare exact names, types, and required options:

| Property | Required API type | Required options / policy |
|----------|-------------------|---------------------------|
| 이름 | title | required identity field |
| 선택 | select | 루틴, 이벤트 |
| 구분 | multi_select | 학업 |
| DueDate | date | optional value permitted |
| Plan | date | omit on create; never update |
| 우선순위 | select | P1, P2, P3, P4 |
| 상태 | status | 시작 전, 진행 중, 완료, 폐기 |
| 메모 | rich_text | one text segment, ≤1950 project cap |

The names/options are the in-repo contract quoted above; the API types are the official page/data-source property types. [VERIFIED: .planning/PROJECT.md:38-40] [VERIFIED: src/kau_assistant/domain/models.py:21-62] [CITED: https://developers.notion.com/reference/property-object]

Fail the Notion stage safely with a structured schema error listing missing/mismatched fields; do not mutate the user’s database schema or silently create new select options. [ASSUMED]

### Pattern 3: Query Broadly, Match Exactly In Memory

Use one compound OR filter and paginate all results:

    {
        "or": [
            {"property": "DueDate", "date": {"on_or_after": cutoff_kst_date}},
            {"property": "상태", "status": {"does_not_equal": "완료"}},
        ]
    }

The official filter API supports date `on_or_after`, status `does_not_equal`, and compound OR nesting; the property/value spellings come from the verified project contract. [CITED: https://developers.notion.com/reference/filter-data-source-entries] [VERIFIED: .planning/PROJECT.md:38-40]

Use `page_size=100` and the SDK pagination helper. Search/query list endpoints use opaque cursors and can return fewer than the requested page size. [CITED: https://developers.notion.com/reference/pagination] [CITED: https://github.com/ramnes/notion-sdk-py/blob/main/notion_client/helpers.py]

Extract a page title by concatenating every `plain_text` segment in `properties["이름"]["title"]`. Index by that complete string, not a Notion “contains” filter. Treat duplicate existing titles as a conflict and perform no write for that key; arbitrary first-match selection risks updating the wrong user page. [CITED: https://developers.notion.com/reference/page-property-values] [ASSUMED]

### Pattern 4: Allowlisted Partial Update

For a matched title, compare canonical values and build an update dictionary from only:

    UPDATEABLE_PROPERTIES = ("DueDate", "우선순위", "메모")
    PROTECTED_PROPERTIES = ("상태", "Plan")

These exact fields are locked by D-01. [VERIFIED: .planning/phases/04-notion-scheduler-integration-deduplication/04-CONTEXT.md:25-26]

Omit unchanged values and call `pages.update` only when the diff is non-empty. The API updates property values supplied in the `properties` body, so omission is the enforceable preservation mechanism for user-owned Status and Plan. [CITED: https://developers.notion.com/reference/patch-page]

### Pattern 5: Plan Then Execute

`deduplicator.plan_sync(tasks, existing_pages)` should return an ordered list of immutable actions:

- `CreateAction`: no matching title.
- `UpdateAction`: matching title with one or more allowed-field diffs.
- `SkipAction(reason="unchanged")`: matching title and no allowed-field diff.
- `ErrorAction`: duplicate incoming title, duplicate existing title, malformed page, or schema/transport failure.

The engine converts these actions to the locked `created`, `updated`, `skipped`, `errors`, and `stats` collections. Every item should carry `task_id`, `title`, `page_id` when known, `executed`, and either field diffs, skip reason, or safe error metadata. [VERIFIED: .planning/phases/04-notion-scheduler-integration-deduplication/04-CONTEXT.md:30-32]

Dry-run executes discovery/schema/query/planning and then returns with `executed=False` for create/update actions. Tests must spy on both write methods and assert zero calls, not merely assert that the result says “dry-run.” [VERIFIED: .planning/phases/04-notion-scheduler-integration-deduplication/04-CONTEXT.md:30-31]

### Pattern 6: Safe Configuration Gate

Support `NOTION_TOKEN` while retaining `NOTION_API_KEY` as a legacy validation alias; prefer `NOTION_TOKEN` when both exist. Add `notion_database_name`. Change the database-ID default to empty and keep the personal UUID in `.env.example`, otherwise “name only” can never be selected because the current default ID is always non-empty. [VERIFIED: src/kau_assistant/config.py:26-31] [VERIFIED: .env.example:6-8] [VERIFIED: .planning/phases/04-notion-scheduler-integration-deduplication/04-CONTEXT.md:35-46]

When the token or both target selectors are absent, return a successful disabled/skipped `SyncResult` without constructing a client. Invalid configured credentials or a configured-but-inaccessible target should instead become structured errors with Korean recovery guidance; the outer LXP workflow must continue. [VERIFIED: .planning/phases/04-notion-scheduler-integration-deduplication/04-CONTEXT.md:41-46]

### Anti-Patterns to Avoid

- **Using `SyncTask.dedup_key`:** it includes due time and breaks deadline-extension matching. [VERIFIED: src/kau_assistant/domain/models.py:80-84]
- **Calling `databases.query` or creating with only a database parent:** current 2025-09-03+ data operations are data-source scoped. [CITED: https://developers.notion.com/guides/get-started/upgrade-guide-2025-09-03]
- **Selecting `search["results"][0]`:** search is substring-based, paginated, permission-scoped, and eventually consistent. [CITED: https://developers.notion.com/reference/post-search] [CITED: https://developers.notion.com/reference/search-optimizations-and-limitations]
- **Sending all properties on update:** this would overwrite Plan/Status and violate D-01. [VERIFIED: .planning/phases/04-notion-scheduler-integration-deduplication/04-CONTEXT.md:25-26]
- **Mocking reads in production dry-run:** D-04 requires real reads; only writes are suppressed. [VERIFIED: .planning/phases/04-notion-scheduler-integration-deduplication/04-CONTEXT.md:30-31]
- **Catching `Exception` and reporting success:** distinguish unconfigured fallback from configured integration failures and preserve error code/request ID without exposing credentials. [CITED: https://github.com/ramnes/notion-sdk-py]
- **A second custom 429 retry loop around SDK 3.1:** it would multiply attempts; configure `RetryOptions(max_retries=3)` and add only the missing policy deliberately. [CITED: https://github.com/ramnes/notion-sdk-py]

## Retry, Rate-Limit, and Error Policy

The current official limits are 180 requests/minute for non-Business plans and 600/minute for Business/Enterprise, plus a separate shared workspace limit. The locked 0.35-second delay is about 171 requests/minute, so it remains a conservative single-process pace for the lower tier. [CITED: https://developers.notion.com/reference/request-limits]

Initialize the synchronous client with `timeout_ms=30_000` and `RetryOptions(max_retries=3)`. SDK 3.1.0 automatically retries `rate_limited` (429) for every method, respects `Retry-After`, and uses exponential backoff with jitter; it retries 500/503 only for GET/DELETE. [CITED: https://github.com/ramnes/notion-sdk-py] The 30-second timeout is a project recommendation within the user-delegated discretion, not an official optimum. [ASSUMED]

Current Notion docs also require handling 529 `service_overload` like 429, but notion-client 3.1.0’s installed `APIErrorCode` does not include that code and therefore surfaces it as `UnknownHTTPResponseError` rather than applying its automatic retry. Add a narrow wrapper that recognizes HTTP status 529, respects `Retry-After`, applies capped jittered backoff, and stops after three retries; do not duplicate SDK handling for 429. [CITED: https://developers.notion.com/reference/request-limits] [VERIFIED: installed notion-client 3.1.0 source probe 2026-09-22]

| Condition | Behavior | User-facing guidance |
|-----------|----------|----------------------|
| Missing token/target | No client, no reads/writes, non-error disabled result. | “Notion 설정이 없어 동기화를 건너뜁니다.” [VERIFIED: D-09 in CONTEXT.md] |
| 401 unauthorized | No retry; structured error. | Check `NOTION_TOKEN` / legacy `NOTION_API_KEY` and recreate token if needed. [CITED: https://developers.notion.com/reference/status-codes] |
| 403 restricted_resource | No blind retry; inspect message/capabilities. | Share Scheduler with the connection and enable read/insert/update content; also surface workspace block-limit messages. [CITED: https://developers.notion.com/reference/capabilities] |
| 404 object_not_found | No retry; structured error. | Verify ID/name and that Scheduler is shared with the connection. [CITED: https://developers.notion.com/reference/retrieve-database] |
| 400 validation_error | No retry. | Report exact missing/mismatched property or invalid payload, without token/body secrets. [CITED: https://developers.notion.com/reference/status-codes] |
| 429 rate_limited | SDK retries at most three times using Retry-After/backoff. | Final failure goes to `errors` with request ID. [CITED: https://github.com/ramnes/notion-sdk-py] |
| 529 service_overload | Narrow wrapper retries at most three times using Retry-After/backoff. | Final failure is temporary-service error. [CITED: https://developers.notion.com/reference/request-limits] |
| Timeout/network error | Bounded failure, no write replay beyond known-safe retry policy. | Suggest retry; retain task-level context. [CITED: https://github.com/ramnes/notion-sdk-py] |
| 5xx after a write attempt | Do not automatically replay create/update because outcome may be uncertain. | Report “write outcome unknown” and page/task title for manual inspection. [CITED: https://developers.notion.com/reference/request-limits] |

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| REST auth/endpoints/errors | A raw httpx Notion client | Official `notion-client` wrapper | Locked stack; SDK already owns headers, endpoint paths, response errors, and timeout behavior. [CITED: https://github.com/ramnes/notion-sdk-py] |
| Cursor pagination | Repeated per-endpoint while loops | SDK pagination helpers | One tested path handles `has_more` and opaque `next_cursor`. [CITED: https://github.com/ramnes/notion-sdk-py/blob/main/notion_client/helpers.py] |
| 429 backoff | A parallel retry loop | SDK `RetryOptions` | SDK already respects Retry-After and jitter; a second loop multiplies attempts. [CITED: https://github.com/ramnes/notion-sdk-py] |
| Notion schema creation/migration | Automatic column/option mutation | Read-only preflight validator | This phase integrates an existing user-owned Scheduler and should fail safely on drift. [VERIFIED: .planning/PROJECT.md:38-40] |
| Dry-run shadow implementation | A second mock-only sync path | Shared read/plan path + write gate | Prevents preview/live decision drift. [VERIFIED: D-04 in CONTEXT.md] |
| Ad hoc result dictionaries | Loosely shaped nested dicts | Pydantic DTOs | Phase 5 needs stable created/updated/skipped/errors/stats contracts. [VERIFIED: D-05 in CONTEXT.md] |

**Key insight:** correctness comes from minimizing what can write. Discovery and planning should be read-only/pure; only two client methods should cross the write boundary, and dry-run should never reach them. [VERIFIED: D-04 in CONTEXT.md]

## Common Pitfalls

### Pitfall 1: Database ID / Data-Source ID Confusion
**What goes wrong:** query or create receives the personal database UUID where a data-source ID is required. [CITED: https://developers.notion.com/guides/get-started/upgrade-guide-2025-09-03]
**How to avoid:** always resolve a `NotionTarget` containing both IDs and use the data-source ID for schema/query/create.
**Warning sign:** 400 validation errors or 404s despite a visible database.

### Pitfall 2: Due Date Sneaks Back Into Identity
**What goes wrong:** an extended deadline becomes a new page instead of an update. [VERIFIED: src/kau_assistant/domain/models.py:80-84]
**How to avoid:** assert matching is title-only, with a regression test where identical title/different due date yields one UpdateAction.
**Warning sign:** code references `task.dedup_key` in `notion/`.

### Pitfall 3: Protected Fields Are Serialized Before Diffing
**What goes wrong:** `SyncTask.status` defaults to “시작 전” and `plan_date` defaults to null, so generic model serialization overwrites user changes. [VERIFIED: src/kau_assistant/domain/models.py:57-62]
**How to avoid:** the update mapper must construct an explicit three-field allowlist; never call `model_dump()` to produce update properties.
**Warning sign:** update payload snapshots contain `상태` or `Plan`.

### Pitfall 4: Name Search Is Treated as Exact/Immediate
**What goes wrong:** a partial or stale search hit is selected, especially when several workspaces/data sources use “Scheduler.” [CITED: https://developers.notion.com/reference/search-optimizations-and-limitations]
**How to avoid:** paginate, exact-match reconstructed titles, require uniqueness, and instruct the user to configure ID on ambiguity.
**Warning sign:** index-zero selection or tests with only one response.

### Pitfall 5: First Page Only
**What goes wrong:** duplicates after the first page are not seen and get recreated. [CITED: https://developers.notion.com/reference/pagination]
**How to avoid:** use SDK pagination helpers for both search and data-source query.
**Warning sign:** no test with `has_more=True` and `next_cursor`.

### Pitfall 6: Dry-Run Skips the Live Read
**What goes wrong:** preview says “create,” but live run sees an existing page and updates/skips. [VERIFIED: D-04 in CONTEXT.md]
**How to avoid:** branch only after action planning; spy that query was called and create/update were not.
**Warning sign:** an early `if dry_run: return` before target/query logic.

### Pitfall 7: Query Window Creates an Intentional Blind Spot
**What goes wrong:** a completed page older than 90 days is outside D-03’s read set, so the same normalized title can be created again in a later term. [VERIFIED: D-03 in CONTEXT.md]
**How to avoid:** preserve D-03 as locked, document the behavior, and include a test showing exactly what the filter includes/excludes; do not silently widen it.
**Warning sign:** stakeholders assume title uniqueness across all historical semesters.

### Pitfall 8: Concurrent Runs Race
**What goes wrong:** two processes read the same “missing” title before either creates it, then both write. [ASSUMED]
**How to avoid:** treat v1 as single-writer and document that assumption; reject duplicate titles within one incoming batch.
**Warning sign:** parallel sync invocations or scheduler automation before a cross-process lock/idempotency design exists.

## Code Examples

### Exact Page Property Mapping

    # Sources:
    # https://developers.notion.com/reference/page-property-values
    # In-repo names/values are quoted in “Verified In-Repo Contracts”.
    def to_create_properties(task: SyncTask) -> dict:
        properties = {
            "이름": {"title": [{"text": {"content": task.title}}]},
            "선택": {"select": {"name": task.selection.value}},
            "구분": {"multi_select": [{"name": name} for name in task.category]},
            "우선순위": {"select": {"name": task.priority.value}},
            "상태": {"status": {"name": task.status.value}},
            "메모": {"rich_text": [{"text": {"content": task.memo}}]},
        }
        if task.due_date is not None:
            properties["DueDate"] = {
                "date": {"start": task.due_date.isoformat(timespec="seconds")}
            }
        return properties

`Plan` is intentionally absent and no `children` argument is passed to `pages.create`. D-08’s 1950-character cap is already enforced by `format_memo`, below the official 2000-character `text.content` limit. [VERIFIED: src/kau_assistant/domain/transformer.py:82-95] [CITED: https://developers.notion.com/reference/request-limits]

### Partial Diff Payload

    # Source: https://developers.notion.com/reference/patch-page
    def to_update_properties(task: SyncTask, existing: ExistingPage) -> tuple[dict, list[FieldDiff]]:
        desired = {
            "DueDate": encode_date(task.due_date),
            "우선순위": {"select": {"name": task.priority.value}},
            "메모": {"rich_text": [{"text": {"content": task.memo}}]},
        }
        current = existing.comparable_properties()
        changed = {name: value for name, value in desired.items() if current[name] != value}
        return changed, build_diffs(current, desired, changed.keys())

The update call receives only `changed`. Tests must assert `"상태" not in changed` and `"Plan" not in changed` for every fixture. [VERIFIED: D-01 in CONTEXT.md]

### Real-Read / Mocked-Write Branch

    def sync(self, tasks: list[SyncTask], *, dry_run: bool = False) -> SyncResult:
        if not self.config.is_notion_configured:
            return SyncResult.disabled(tasks)

        target = self.client.resolve_target()
        self.client.validate_scheduler_schema(target.data_source_id)
        existing = self.client.query_existing_pages(target.data_source_id)
        actions = self.deduplicator.plan_sync(tasks, existing)

        if dry_run:
            return SyncResult.from_actions(actions, dry_run=True)

        return self.execute(actions, target.data_source_id)

This is the only allowed dry-run branching location: after real read/planning and before any write. [VERIFIED: D-04 in CONTEXT.md]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Query database by `database_id` | Retrieve database container, then query child `data_source_id` | API `2025-09-03` | Phase 4 must carry both IDs and use `data_sources.query`. [CITED: https://developers.notion.com/guides/get-started/upgrade-guide-2025-09-03] |
| Search returns database objects | Search returns `data_source` objects on 2025-09-03+ | API `2025-09-03` | D-07 discovery must filter/match data sources and recover parent database ID. [CITED: https://developers.notion.com/reference/post-search] |
| Custom 429 retry required in older SDKs | notion-client 3.1.0 has configurable automatic retry | SDK 3.1.0, 2026-05-12 | Configure max retries; do not wrap 429 twice. [CITED: https://github.com/ramnes/notion-sdk-py/releases/tag/3.1.0] |
| `archived` field | `in_trash` field | API `2026-03-11` | Phase 4 does not need either field, so stay on the SDK’s 2025-09-03 default unless a separate upgrade is tested. [CITED: https://developers.notion.com/guides/get-started/upgrade-guide-2026-03-11] |

**Deprecated/outdated:** `databases.query` and `database_id` page-parent examples from pre-2025 API docs are not appropriate for this locked SDK version/data-source design. [CITED: https://developers.notion.com/guides/get-started/upgrade-guide-2025-09-03]

## Testing and Mocking Strategy

Use constructor injection: `NotionSyncEngine(client: NotionClient, ...)` and inject a mocked wrapper, not a global patched SDK singleton. Mapper and deduplicator tests should be pure and use literal API-shaped fixtures. Client tests may mock the underlying `notion_client.Client` endpoints and injected sleep/monotonic functions. [VERIFIED: tests/conftest.py:1-40]

Required test groups:

- Client: explicit-ID priority, database→data-source resolution, exact unique name match, zero/multiple matches, pagination, locked filter shape, 0.35 spacing, 401/404 Korean messages, exhausted 429, 529 wrapper, and no token leakage.
- Mapper: all eight schema types/options, create payload, KST ISO date, null due date, title segment concatenation, memo limit, and three-field-only update diff.
- Deduplicator: title-only match with changed due date, unchanged skip, new create, duplicate incoming title conflict, duplicate existing title conflict, malformed existing page.
- Engine: disabled fallback, live read in dry-run, zero writes in dry-run, correct create/update write dispatch in live mode, partial failure accumulation, stable stats.

The existing suite passes 81 tests in 1.37 seconds before Phase 4 changes. [VERIFIED: `uv run pytest -p no:cacheprovider` on 2026-09-22]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | A 30-second total SDK timeout is suitable for this local workflow. | Retry policy | Slow networks may require configuration rather than a fixed value. |
| A2 | v1 runs as a single writer; simultaneous sync processes are unsupported. | Common Pitfalls | Concurrent read-before-write runs can still create duplicates. |
| A3 | On a database with multiple data sources, ambiguity should fail safely rather than choose the first child. | Target resolution | A user may expect an implicit default data source; selecting wrong is more damaging than requiring ID/name. |
| A4 | Schema drift should be reported, not automatically repaired. | Schema preflight | Users would need to fix columns/options manually; automatic mutation is outside the locked phase boundary. |

## Open Questions / Unresolved Risks

1. **The live Scheduler schema has not been read in this environment.**
   - What we know: the repository declares exact names/types/options. [VERIFIED: .planning/PROJECT.md:38-40]
   - Gap: `NOTION_TOKEN`/`NOTION_API_KEY` is not configured here, so actual column IDs, current types/options, database sharing, child data-source count, and pre-existing duplicate titles remain unverified. [VERIFIED: environment probe 2026-09-22]
   - Plan response: include a read-only schema/discovery acceptance checkpoint and make dry-run the first credentialed end-to-end test.
   - **Disposition: RESOLVED — accepted as an execution-time credentialed uncertainty.** Plan 04-02 Task 3 is a blocking human checkpoint and may approve only after its redacted live evidence proves unique target resolution, all eight schema properties/options, full read/planning behavior, and zero writes. Lack of credentials stops at that gate; it does not permit an inferred pass.

2. **The current config default conflicts with name-only discovery semantics.**
   - What we know: `notion_database_id` defaults to the personal UUID and `notion_database_name` does not exist. [VERIFIED: src/kau_assistant/config.py:26-31]
   - Plan response: make ID empty by default, retain the personal UUID in `.env.example`, add database name, and update config tests.
   - **Disposition: RESOLVED — implement and test the configuration contract in Plan 04-01 Task 2.** An explicit ID remains highest priority, name-only configuration becomes reachable, and missing credential/target remains D-09's successful disabled state.

3. **SDK 3.1.0 does not automatically classify/retry current 529 responses.**
   - What we know: official docs require 529 handling; the installed error enum omits `service_overload`. [CITED: https://developers.notion.com/reference/request-limits] [VERIFIED: installed notion-client 3.1.0 source probe 2026-09-22]
   - Plan response: add the narrow status-529 wrapper and tests without duplicating 429 retries.
   - **Disposition: RESOLVED — implement the bounded read-only 529 wrapper in Plan 04-01 Task 3.** Retain SDK-owned `RetryOptions(max_retries=3)` for 429, cap 529 attempts separately, and never replay an uncertain write.

4. **D-03 intentionally limits historical dedup coverage.**
   - What we know: completed pages older than 90 days are excluded, while titles do not contain a term identifier. [VERIFIED: D-03 in CONTEXT.md] [VERIFIED: src/kau_assistant/domain/naming.py:48-97]
   - Plan response: preserve the locked filter and document the cross-semester collision risk for future discussion rather than silently changing identity/scope.
   - **Disposition: RESOLVED — accept the documented blind spot as the explicit D-03 boundary.** Plan 04-01 Task 3 asserts the exact 90-day-or-incomplete filter and does not widen history or alter D-02 title identity; any cross-semester identity change requires a later user decision.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Python | Runtime/tests | ✓ | 3.14.7 | Project floor is 3.11+. [VERIFIED: environment probe 2026-09-22] |
| uv | Dependency/test commands | ✓ | 0.12.17 | Standard Python tooling if needed. [VERIFIED: environment probe 2026-09-22] |
| notion-client | Notion transport | ✓ | 3.1.0 | None; D-06 locks it. [VERIFIED: environment probe 2026-09-22] |
| Notion API network | Official-doc reachability | ✓ | HTTPS reachable | Unit tests use mocks; credentialed acceptance still required. [VERIFIED: official docs fetch 2026-09-22] |
| Notion token | Live Scheduler read/write | ✗ | — | Unit tests and safe fallback; cannot complete live acceptance here. [VERIFIED: environment probe 2026-09-22] |
| Database ID | Target configuration | nominal only | personal UUID is a model default | Name discovery after config change; default does not prove access. [VERIFIED: src/kau_assistant/config.py:26-31] |
| Database name setting | D-07 discovery | ✗ | field absent | Add in Wave 0/implementation. [VERIFIED: environment probe 2026-09-22] |

**Missing dependency with no fallback:** a real token/shared Scheduler is required only for credentialed dry-run/live acceptance; it does not block implementation or automated tests. [VERIFIED: environment probe 2026-09-22]

**Missing dependencies with fallback:** unit tests inject mocks; unconfigured runtime returns D-09’s safe disabled result. [VERIFIED: D-09 in CONTEXT.md]

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 + pytest-mock 3.15.1 [VERIFIED: environment probe 2026-09-22] |
| Config file | `pyproject.toml` (`testpaths=["tests"]`, `pythonpath=["src"]`, `-ra -q`) [VERIFIED: pyproject.toml:32-35] |
| Quick run command | `uv run pytest -q tests/test_notion_client.py tests/test_notion_mapper.py tests/test_notion_deduplicator.py tests/test_notion_engine.py` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| NOTN-01 | Resolve target; schema-check; paginate filtered pages; parse title/DueDate | unit/integration-mock | `uv run pytest -q tests/test_notion_client.py -x` | ❌ Wave 0 |
| NOTN-02 | Title-only classification; changed deadline updates; unchanged skips; new creates; duplicate conflicts | unit | `uv run pytest -q tests/test_notion_deduplicator.py tests/test_notion_engine.py -x` | ❌ Wave 0 |
| NOTN-03 | Exact create payload and three-field partial update preserving Status/Plan | unit | `uv run pytest -q tests/test_notion_mapper.py -x` | ❌ Wave 0 |
| NOTN-04 | Real-read mocked-write dry-run and detailed result/stats | integration-mock | `uv run pytest -q tests/test_notion_engine.py -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** run the test file(s) owned by that task, keeping the command under 30 seconds.
- **Per wave merge:** `uv run pytest -q tests/test_config.py tests/test_domain_models.py tests/test_notion_client.py tests/test_notion_mapper.py tests/test_notion_deduplicator.py tests/test_notion_engine.py`.
- **Phase gate:** `uv run pytest` must be green, then run one credentialed `dry_run=True` against the shared Scheduler and verify zero writes before `$gsd-verify-work`. [VERIFIED: workflow.nyquist_validation=true in .planning/config.json]

### Wave 0 Gaps

- [ ] `tests/test_notion_client.py` — target resolution, pagination, throttle/retry/errors, live schema contract via fixtures.
- [ ] `tests/test_notion_mapper.py` — property parse/create/update mapping.
- [ ] `tests/test_notion_deduplicator.py` — title-only action planning and conflict cases.
- [ ] `tests/test_notion_engine.py` — fallback, dry-run write prohibition, result aggregation.
- [ ] Extend `tests/test_config.py` and `tests/conftest.py` for `NOTION_TOKEN`, legacy alias, empty ID, and `NOTION_DATABASE_NAME`.
- [ ] Credentialed manual/acceptance fixture: direct share/access to the user’s Scheduler; do not commit token or live response data.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Bearer token loaded through Pydantic Settings; never hardcode or serialize token. [VERIFIED: src/kau_assistant/config.py:8-31] |
| V3 Session Management | no | Phase 4 has no user session; LMS session management remains outside this phase. [VERIFIED: phase boundary in CONTEXT.md] |
| V4 Access Control | yes | Least-privilege Notion connection capabilities and explicit sharing of Scheduler; distinguish permission errors from missing objects. [CITED: https://developers.notion.com/reference/capabilities] |
| V5 Input Validation | yes | Validate config, target uniqueness, live schema/property types/options, API response shapes, and memo size before writes. [CITED: https://developers.notion.com/reference/request-limits] |
| V6 Cryptography | no custom crypto | Use HTTPS/SDK; never build token encryption or transport crypto in this phase. [CITED: https://developers.notion.com/reference/authentication] |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Token exposure in logs/repr/errors | Information Disclosure | Reuse masking pattern, never include auth headers/request bodies in user results, test secret absence. [VERIFIED: src/kau_assistant/config.py:43-54] |
| Wrong similarly named Scheduler selected | Tampering | Exact unique local match; explicit ID priority; fail closed on ambiguity. [CITED: https://developers.notion.com/reference/post-search] |
| Schema drift writes to unintended fields | Tampering | Retrieve/validate data-source schema before planning writes; explicit property allowlists. [CITED: https://developers.notion.com/reference/retrieve-a-data-source] |
| Duplicate writes after uncertain failure/concurrency | Tampering / Repudiation | Never replay ambiguous write failures; include request ID/page/task context; assume single writer. [CITED: https://developers.notion.com/reference/request-limits] |
| Untrusted Notion/LMS text entering output | Injection / Information Disclosure | Treat text as data only, never evaluate it, escape at the Phase 5 renderer, and cap memo content. [VERIFIED: src/kau_assistant/domain/transformer.py:51-95] |

## Sources

### Primary / authoritative

- [Notion API 2025-09-03 upgrade guide](https://developers.notion.com/guides/get-started/upgrade-guide-2025-09-03) — database/data-source split, discovery, query, create-parent migration.
- [Notion API 2026-03-11 upgrade guide](https://developers.notion.com/guides/get-started/upgrade-guide-2026-03-11) — current version delta and archived→in_trash change.
- [Retrieve a database](https://developers.notion.com/reference/retrieve-database) — child data_sources.
- [Query a data source](https://developers.notion.com/reference/query-a-data-source) and [filters](https://developers.notion.com/reference/filter-data-source-entries) — D-03 filter/pagination behavior.
- [Search by title](https://developers.notion.com/reference/post-search) and [search limitations](https://developers.notion.com/reference/search-optimizations-and-limitations) — name discovery semantics.
- [Create page](https://developers.notion.com/reference/post-page), [Update page](https://developers.notion.com/reference/patch-page), and [page properties](https://developers.notion.com/reference/page-property-values) — payload and partial-update behavior.
- [Request limits](https://developers.notion.com/reference/request-limits) and [status codes](https://developers.notion.com/reference/status-codes) — rate limits, retry, size, failures.
- [notion-sdk-py official repository](https://github.com/ramnes/notion-sdk-py) and [3.1.0 release](https://github.com/ramnes/notion-sdk-py/releases/tag/3.1.0) — Python SDK client/retry/API surface.

### In-repo primary

- `.planning/phases/04-notion-scheduler-integration-deduplication/04-CONTEXT.md` — D-01 through D-09.
- `.planning/PROJECT.md` — exact Scheduler schema.
- `src/kau_assistant/domain/models.py` — exact enum/model values and current conflicting dedup key.
- `src/kau_assistant/domain/transformer.py` — memo cap and SyncTask construction.
- `src/kau_assistant/config.py` and `.env.example` — current settings behavior.
- `pyproject.toml` and `uv.lock` — dependency/test/runtime versions.

### Tertiary

- None. No community source was used for implementation claims.

## Metadata

**Confidence breakdown:**
- Standard stack: MEDIUM — official documentation and locked environment agree, but the package-legitimacy seam returned SUS solely because download telemetry was unavailable.
- Architecture: HIGH — derived from locked D-01–D-09, current API migration docs, and opened source-of-truth files.
- API behavior: MEDIUM — sourced from current official docs/Context7; the Python SDK intentionally defaults to 2025-09-03 while the latest API reference is 2026-03-11.
- Pitfalls: HIGH — each critical pitfall is tied to a locked decision, opened code, or official API constraint.
- Live database compatibility: LOW — no token was available, so the real Scheduler schema/options/sharing and stored duplicates were not inspected.

**Research date:** 2026-09-22
**Valid until:** 2026-10-22 for the chosen SDK/API version; re-check sooner if `notion-client` or Notion-Version changes.
