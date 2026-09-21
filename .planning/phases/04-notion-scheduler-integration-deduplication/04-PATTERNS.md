# Phase 4: Notion Scheduler Integration & Deduplication - Pattern Map

**Mapped:** 2026-09-22
**Files analyzed:** 14 new/modified files
**Analogs found:** 14 / 14 (all analogs verified with `git ls-files`)

## File Classification

| New/Modified File | Role | Data Flow | Closest Tracked Analog | Match Quality |
|---|---|---|---|---|
| `.env.example` | config | transform | `.env.example` | exact, modify in place |
| `src/kau_assistant/config.py` | config | transform | `src/kau_assistant/config.py` | exact, modify in place |
| `src/kau_assistant/notion/__init__.py` | provider/facade | request-response | `src/kau_assistant/domain/__init__.py` | exact role |
| `src/kau_assistant/notion/models.py` | model | transform | `src/kau_assistant/domain/models.py` | exact role |
| `src/kau_assistant/notion/client.py` | service | request-response + CRUD | `src/kau_assistant/session_manager.py` | role/data-flow match |
| `src/kau_assistant/notion/mapper.py` | utility | transform | `src/kau_assistant/domain/transformer.py` | exact data-flow |
| `src/kau_assistant/notion/deduplicator.py` | service | batch + transform | `src/kau_assistant/domain/transformer.py`; `src/kau_assistant/course_mapping.py` | data-flow match |
| `src/kau_assistant/notion/engine.py` | service/orchestrator | batch + request-response | `src/kau_assistant/session_manager.py` | role match |
| `tests/conftest.py` | test fixture/config | transform | `tests/conftest.py` | exact, modify in place |
| `tests/test_config.py` | test | transform | `tests/test_config.py` | exact, modify in place |
| `tests/test_notion_client.py` | test | request-response + CRUD | `tests/test_session_manager.py` | role/data-flow match |
| `tests/test_notion_mapper.py` | test | transform | `tests/test_transformer.py` | exact data-flow |
| `tests/test_notion_deduplicator.py` | test | batch + transform | `tests/test_course_mapping.py`; `tests/test_transformer.py` | data-flow match |
| `tests/test_notion_engine.py` | test | batch + request-response | `tests/test_session_manager.py` | role match |

## Pattern Assignments

### `.env.example` (config, transform)

**Analog:** `.env.example` lines 6-8 (tracked)

```dotenv
# Notion Integration
NOTION_API_KEY=secret_your_notion_integration_token
NOTION_DATABASE_ID=21d53280-64be-80ec-af4e-000b679f03bb
```

Keep the grouped, uppercase environment-variable style. Add `NOTION_TOKEN` as the preferred spelling and `NOTION_DATABASE_NAME`; retain `NOTION_API_KEY` as a documented legacy alias. The personal UUID belongs here as an example, not as the `Settings` model default. Never place a real token in this file.

---

### `src/kau_assistant/config.py` (config, transform)

**Analog:** itself, especially settings declaration and secret masking.

**Settings pattern** (lines 8-15, 26-31):

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    notion_api_key: str = Field(default="", description="Notion Integration API Key")
    notion_database_id: str = Field(
        default="21d53280-64be-80ec-af4e-000b679f03bb",
        description="Notion Scheduler Database ID",
    )
```

**Secret masking and singleton pattern** (lines 43-65):

```python
def __repr__(self) -> str:
    masked_key = "***" if self.notion_api_key else ""
    # ... render masked_key, never the actual token

_settings_instance: Settings | None = None

def get_settings(reload: bool = False) -> Settings:
    global _settings_instance
    if _settings_instance is None or reload:
        _settings_instance = Settings()
    return _settings_instance
```

Extend the existing `Settings`/`get_settings` API; do not introduce the stale `AppConfig`/`get_config` names mentioned in older context. Add an effective-token property or validation normalization that prefers `NOTION_TOKEN` and falls back to `NOTION_API_KEY`. Make `notion_database_id` default to `""`, add `notion_database_name: str = ""`, and expose a boolean such as `is_notion_configured` that requires a token plus either target selector. Update `__repr__` so both token spellings remain secret.

**Landmine:** aliases in Pydantic Settings can alter accepted constructor names. Tests must cover environment names and direct construction separately, including both variables set (preferred token wins).

---

### `src/kau_assistant/notion/__init__.py` (provider/facade, request-response)

**Analog:** `src/kau_assistant/domain/__init__.py` lines 3-45.

```python
from kau_assistant.domain.models import (
    Course,
    SyncTask,
    TaskPriority,
)
from kau_assistant.domain.transformer import (
    format_memo,
    transform_to_sync_tasks,
)

__all__ = [
    "Course",
    "SyncTask",
    "TaskPriority",
    "format_memo",
    "transform_to_sync_tasks",
]
```

Use absolute `kau_assistant...` imports, group imports by defining module, and publish a deliberate alphabetized `__all__`. Export only the stable Phase 5 surface (engine, result/action DTOs, and necessary client errors); keep private mapper helpers and SDK details out. Add a facade-import test like `tests/test_transformer.py:46-63`.

---

### `src/kau_assistant/notion/models.py` (model, transform)

**Analog:** `src/kau_assistant/domain/models.py` lines 3-8 and 46-78.

```python
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator

class SyncTask(BaseModel):
    category: list[str] = Field(default_factory=lambda: ["학업"])
    due_date: datetime | None = None
    status: TaskStatus = TaskStatus.NOT_STARTED

    @field_validator("due_date", "plan_date", mode="after")
    @classmethod
    def ensure_kst(cls, v: datetime | None) -> datetime | None:
        if v is not None:
            if v.tzinfo is None:
                return v.replace(tzinfo=KST)
            return v.astimezone(KST)
        return v
```

Use Pydantic `BaseModel`, typed fields, `Field(default_factory=...)` for every list/dict, string enums for bounded reasons/statuses, and explicit optional fields. Model at least `NotionTarget`, `ExistingPage`, `FieldDiff`, create/update/skip/error actions, `SyncStats`, and `SyncResult`. Keep raw SDK dictionaries at the client/mapper boundary; result DTOs must be stable for Phase 5.

Prefer immutable action DTOs (`ConfigDict(frozen=True)`) because planning output should not mutate between dry-run and execution. Each action/result item should retain `task_id`, `title`, optional `page_id`, `executed`, and its diff/reason/error metadata.

**Landmine:** `src/kau_assistant/domain/models.py:80-84` defines `dedup_key` as `title|due_date`. Phase 4 identity is `SyncTask.title` only. Never import or reference `dedup_key` from `notion/`.

---

### `src/kau_assistant/notion/client.py` (service, request-response + CRUD)

**Primary analog:** `src/kau_assistant/session_manager.py` lines 14-19 and 68-82. **Error analog:** `src/kau_assistant/exceptions.py` lines 3-20.

**Constructor injection** (session manager lines 14-19):

```python
class SessionManager:
    def __init__(self, settings: Settings | None = None, headful: bool = False):
        self.settings = settings or get_settings()
        self.headless = False if headful else self.settings.headless
```

**Bounded retry and exception chaining** (lines 68-82):

```python
for attempt in range(2):
    try:
        page.goto(url, timeout=self.settings.timeout_ms)
        return
    except Exception as e:
        if attempt == 0:
            logger.warning(f"페이지 이동 지연 발생({e}), 1회 재시도합니다...")
        else:
            raise NavigationTimeoutError(f"페이지 이동 실패 ({url}): {e}") from e
```

Follow the constructor-injection shape, but inject the SDK client and timing functions as test seams: `NotionClient(settings=None, sdk=None, sleep_fn=time.sleep, monotonic_fn=time.monotonic)`. The wrapper alone owns search/retrieve/query/create/update, request spacing, retry configuration, and translation into project exceptions. Prefer `settings or get_settings()` only when no explicit settings are supplied.

Required public flow/signatures:

```python
resolve_target() -> NotionTarget
validate_scheduler_schema(data_source_id: str) -> None
query_existing_pages(data_source_id: str, *, now: datetime | None = None) -> list[ExistingPage]
create_page(data_source_id: str, properties: dict) -> dict
update_page(page_id: str, properties: dict) -> dict
```

Use the locked SDK 3.1 data-source API: explicit database ID -> `databases.retrieve` -> exactly one/matched child data source; name discovery -> paginated `search` filtered to `data_source` -> reconstructed exact title -> unique match. Query with the locked OR filter (`DueDate >= 90-day KST cutoff` OR `상태 != 완료`) and paginate every response. Configure SDK `RetryOptions(max_retries=3)` for 429 instead of layering a second 429 loop. A separate narrow 529 retry may use injected sleep and bounded attempts. Apply the 0.35-second spacing at one low-level request boundary so calls are neither skipped nor double-delayed.

Add typed Notion exceptions under `kau_assistant.exceptions.KauAssistantError`; translate 401/403/404/validation failures into Korean recovery guidance and chain the original exception. Do not include tokens, auth headers, or full secret-bearing request bodies in logs/results. Do not retry uncertain create/update outcomes after a 5xx.

---

### `src/kau_assistant/notion/mapper.py` (utility, transform)

**Analog:** `src/kau_assistant/domain/transformer.py` lines 51-95 and 215-254.

**Pure, typed transformation pattern** (lines 51-57, 91-95):

```python
def format_memo(
    task_type: TaskType,
    url: str = "",
    cutoff_date: datetime | None = None,
    attachments: list | None = None,
    description_text: str = "",
) -> str:
    # ... pure construction ...
    memo_text = "\n\n".join(sections).strip()
    if len(memo_text) > 1950:
        memo_text = memo_text[:1900] + "\n... [내용 초과 절삭]"
    return memo_text
```

Implement module-level pure functions: parse complete page titles by concatenating all `plain_text` title segments; parse canonical current values; serialize create properties; and build an update payload plus `FieldDiff`s. Keep the exact Korean property names in module constants.

Create payload maps `이름`, `선택`, `구분`, optional `DueDate`, `우선순위`, `상태`, and `메모`; omit `Plan` and omit page `children`. Update payload must be constructed from the allowlist `("DueDate", "우선순위", "메모")` only. Never call `SyncTask.model_dump()` to form an update, because default `상태="시작 전"` and `plan_date=None` would overwrite user-owned values. Use KST-aware `datetime.isoformat(timespec="seconds")` and preserve the existing 1950-character memo cap.

---

### `src/kau_assistant/notion/deduplicator.py` (service, batch + transform)

**Primary analog:** `src/kau_assistant/domain/transformer.py` lines 215-254. **Fallback/exact lookup analog:** `src/kau_assistant/course_mapping.py` lines 38-51.

```python
def transform_to_sync_tasks(...) -> list[SyncTask]:
    active_mappings = mappings if mappings is not None else load_course_mappings()
    tasks: list[SyncTask] = []
    for course in courses:
        for lec in lectures_by_course.get(course.course_id, []):
            task = transform_lecture_to_task(...)
            if task is not None:
                tasks.append(task)
    tasks.sort(key=lambda t: (...))
    return tasks
```

```python
clean_name = course_name.strip()
if clean_name in mappings:
    return mappings[clean_name]
return clean_name
```

Make `plan_sync(tasks, existing_pages) -> list[SyncAction]` pure and deterministic: build indexes once, preserve input order, exact-match `task.title`, and produce create/update/unchanged/error actions without any SDK call or logging side effect. Reject duplicate titles in either incoming tasks or existing pages as conflicts; never select the first duplicate. A same-title/different-due-date case is an update, not a create. Use mapper-produced canonical values/diffs so comparison and wire serialization cannot drift.

---

### `src/kau_assistant/notion/engine.py` (service/orchestrator, batch + request-response)

**Analog:** `src/kau_assistant/session_manager.py` lines 17-19 and 91-147.

The analog injects `Settings`, lazily establishes the external boundary, sequences validation before side effects, and returns the acquired result. Follow that shape with explicit collaborators:

```python
class NotionSyncEngine:
    def __init__(
        self,
        settings: Settings | None = None,
        client: NotionClient | None = None,
    ): ...

    def sync(self, tasks: list[SyncTask], *, dry_run: bool = False) -> SyncResult: ...
```

Required order is configuration gate -> resolve target -> schema preflight -> real query -> parse/index/plan -> dry-run return or writes -> aggregate `SyncResult`. If unconfigured, return a successful disabled/skipped result and do not construct the SDK client. Dry-run branches only after the real read and planning and marks planned writes `executed=False`. Live execution dispatches only create/update actions, catches failures per action so later independent actions can proceed, and reports stable stats. Configured credential/target failures are structured errors, not the same as disabled fallback.

**Landmine:** do not put CLI parsing or Rich rendering here; Phase 5 consumes `SyncResult`.

---

### `tests/conftest.py` (test fixture/config, transform)

**Analog:** itself, lines 8-24 and 27-40.

```python
@pytest.fixture
def clean_env(monkeypatch):
    for key in ["NOTION_API_KEY", "NOTION_DATABASE_ID"]:
        monkeypatch.delenv(key, raising=False)
    get_settings(reload=True)
    yield monkeypatch
    get_settings(reload=True)

@pytest.fixture
def sample_settings(tmp_path: Path) -> Settings:
    return Settings(...)
```

Extend isolation to `NOTION_TOKEN` and `NOTION_DATABASE_NAME`; keep singleton reset before and after yield. Update `sample_settings` to opt into an explicit target. Add a compact `sample_sync_task` fixture only if used by multiple Notion test modules; API-shaped dictionaries can remain local to mapper/client tests.

---

### `tests/test_config.py` (test, transform)

**Analog:** itself, lines 7-18, 21-42, and 60-76.

Retain direct `Settings(_env_file=None)` default tests and temporary `.env` integration tests. Change the ID default assertion to empty, then cover preferred `NOTION_TOKEN`, legacy `NOTION_API_KEY`, preference when both are set, ID-only/name-only target selection, disabled states, and `NOTION_DATABASE_NAME`. Extend the existing negative secret assertions:

```python
repr_str = repr(settings)
assert "supersecretpassword" not in repr_str
assert "secret_token_123" not in repr_str
assert "***" in repr_str
```

Assert neither preferred nor legacy token appears in `repr()` or `str()`.

---

### `tests/test_notion_client.py` (test, request-response + CRUD)

**Analog:** `tests/test_session_manager.py` lines 12-31 and 137-163.

```python
@pytest.fixture
def mock_playwright_stack():
    with patch("kau_assistant.session_manager.sync_playwright") as mock_sync:
        mock_p = MagicMock()
        # ... connect the complete mocked external stack ...
        yield {"playwright": mock_p, "browser": mock_browser, "page": mock_page}
```

```python
page.goto.side_effect = [Exception("Network lag"), None]
sm._navigate_with_retry(page, "https://lms.kau.ac.kr")
assert page.goto.call_count == 2
```

Prefer injecting a `MagicMock` SDK object over patching global SDK state; inject `sleep_fn` and assert spacing/backoff calls without real waits. Cover explicit-ID priority, database -> data-source resolution, exact unique name match, zero/multiple matches, search and query pagination (`has_more=True`), exact filter shape, schema validation, 0.35 spacing, configured RetryOptions, 401/403/404 Korean messages, 529 exhaustion, and token non-disclosure. Assert write calls receive `data_source_id`, while database retrieval receives `database_id`.

---

### `tests/test_notion_mapper.py` (test, transform)

**Analog:** `tests/test_transformer.py` lines 81-102 and 151-185.

Use literal inputs and exact property-dictionary assertions; no mocks or network. Test all eight schema property types/options, title-segment concatenation, null/non-null due dates, KST ISO output, memo cap, and create payload omission of `Plan`/children. For update diffs, assert exact keys and always assert:

```python
assert "상태" not in update_properties
assert "Plan" not in update_properties
```

Mirror the transform tests' boundary coverage: normal value, absent value, and truncation/limit cases.

---

### `tests/test_notion_deduplicator.py` (test, batch + transform)

**Analogs:** `tests/test_course_mapping.py` lines 13-34 and `tests/test_transformer.py` lines 188-263.

Use table-like direct cases with no mocks: exact known match, fallback/new create, and ordered multi-item batch. Required regression: identical title plus changed deadline yields exactly one update action. Also cover unchanged skip, duplicate incoming title conflict, duplicate existing title conflict, malformed existing page, and stable action ordering. Explicitly assert no test or implementation relies on `SyncTask.dedup_key`.

---

### `tests/test_notion_engine.py` (test, batch + request-response)

**Analog:** `tests/test_session_manager.py` lines 66-87 and 90-111.

The analog injects settings, patches one external boundary, and verifies both result and calls. Do the same with a mocked `NotionClient` plus real mapper/deduplicator where practical. Required assertions:

- unconfigured settings return disabled success and never construct/call the SDK boundary;
- dry-run calls resolve/schema/query but `create_page.assert_not_called()` and `update_page.assert_not_called()`;
- live mode dispatches the correct write per action with partial update keys only;
- one action failure is accumulated with safe metadata while independent later actions continue;
- `created`, `updated`, `skipped`, `errors`, and `stats` agree, including `executed=False` during dry-run.

## Shared Patterns

### Imports and Package Surface

**Source:** `src/kau_assistant/domain/__init__.py:3-45`, `src/kau_assistant/domain/transformer.py:6-25`

Use absolute imports (`from kau_assistant...`) and explicit `__all__`. Keep imports at module top and keep SDK types confined to `notion/client.py` and client tests.

### Dependency Injection

**Source:** `src/kau_assistant/session_manager.py:17-19`, `tests/test_session_manager.py:12-31`

Construct production defaults only when collaborators are absent. Inject `Settings`, SDK wrapper, sleep, and clock at the boundary. Pure mapper/deduplicator functions receive all inputs directly and need no global configuration.

### Errors and Safe Fallback

**Source:** `src/kau_assistant/exceptions.py:3-20`, `src/kau_assistant/course_mapping.py:16-35`, `src/kau_assistant/session_manager.py:68-82`

Use project exception subclasses and `raise ... from e` at the transport boundary. Reserve graceful non-error fallback for genuinely absent Notion configuration. Configured failures become structured errors with Korean guidance. Log actionable context, but never secrets. Broad `except Exception` from legacy cleanup/fallback code is not the pattern for transport classification.

### Validation and Canonicalization

**Source:** `src/kau_assistant/domain/models.py:46-78`, `src/kau_assistant/domain/transformer.py:51-95`

Use Pydantic for stable DTO contracts and pure functions for API dictionary conversion. Canonicalize titles/dates/select values before diffing. Validate the live Scheduler schema before query/write; never auto-create or mutate user schema/options.

### Test Style

**Source:** `tests/conftest.py:8-40`, `tests/test_transformer.py:36-63`, `tests/test_session_manager.py:12-31`

Use pytest functions and fixtures, direct exact assertions for pure code, and one injected/mock external boundary for orchestration. Use `side_effect` for retry sequences and `assert_not_called()` to prove dry-run safety. No credentialed Notion call belongs in the unit suite.

## Landmines and Non-Copyable Legacy Details

1. Do not copy `SyncTask.dedup_key` (`domain/models.py:80-84`); its due date violates title-only identity.
2. Do not copy the current non-empty database-ID default (`config.py:28-31`); it makes name-only discovery and missing-target fallback indistinguishable.
3. Do not copy generic `model_dump()` output into updates; it can overwrite protected `상태` and `Plan`.
4. Do not use pre-2025 `databases.query` examples. With the locked SDK, resolve both IDs and use `data_sources.retrieve/query` plus a data-source parent for creates.
5. Do not choose search result zero or query only the first page. Paginate, reconstruct full titles, exact-match locally, and fail closed on ambiguity.
6. Do not branch early for dry-run. Reads and planning are real; only `pages.create`/`pages.update` are suppressed.
7. Do not duplicate the SDK's 429 retry loop. Configure it; add only the deliberately narrow missing 529 policy.
8. The 90-day-or-incomplete filter intentionally cannot see completed pages older than 90 days. Preserve the locked behavior and document/test the historical blind spot.
9. Treat v1 as single-writer. In-batch duplicate rejection does not prevent two concurrent processes racing.

## No Exact Analog Found

There is no existing in-repo Notion SDK wrapper or plan-then-execute dry-run engine. `notion/client.py` and `notion/engine.py` therefore use strong role/data-flow analogs (`session_manager.py`) plus the locked Phase 4 research contracts above. The planner should not infer SDK payload details from the Playwright analog.

## Metadata

**Analog search scope:** tracked files under `src/kau_assistant/`, `tests/`, root config files, and Phase 4 context/research
**Strong source analogs:** `config.py`, `domain/__init__.py`, `domain/models.py`, `domain/transformer.py`, `session_manager.py`, `course_mapping.py` (plus shared exception hierarchy)
**Tracked-source verification:** every named analog returned non-empty output from `git ls-files -- <path>`; no `.gsd`/plugin mirror path is used
**Framework:** Python 3.11+, Pydantic 2, pydantic-settings, notion-client (lock resolves 3.1.0), pytest/pytest-mock
**Pattern extraction date:** 2026-09-22
