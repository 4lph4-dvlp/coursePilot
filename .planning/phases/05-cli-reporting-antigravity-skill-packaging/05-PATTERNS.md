# Phase 5: CLI Reporting & Universal Agent Skill Packaging - Pattern Map

**Mapped:** 2026-09-23
**Files analyzed:** 11 (new) + 3 (modified docs)
**Analogs found:** 8 / 11 (3 have no true in-tree analog: `cli.py`, `installer.py`, `SKILL.md` — first-of-kind in this repo; nearest partial patterns still identified below)

**Tracked-source gate:** `.claude/skills/`, `.agents/skills/`, `.pi/skills/`, `.gsd/`, `.alpha-aos/` are all untracked (`git status` shows them as `??`; confirmed with `git ls-files` returning no results under any of those prefixes). None of those paths are cited below as analogs — they are evidence-only for SKILL.md frontmatter shape, and RESEARCH.md already flags this. No tracked mirror-of-mirror paths exist in this repo for this phase.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|---------------|
| `src/coursepilot/pipeline.py` | service (orchestrator) | request-response (chained calls) + event-driven (per-course try/except) | `src/coursepilot/session_manager.py` (retry/error-isolation style) + `src/coursepilot/domain/transformer.py` (`transform_to_sync_tasks`, pure aggregation over a list) | role-match (no orchestrator exists yet; closest compositional style) |
| `src/coursepilot/reporter.py` | transform (pure function) | transform | `src/coursepilot/domain/transformer.py` (`transform_to_sync_tasks`) | exact (pure function, `now: datetime \| None` injectable clock, list-in/model-out) |
| `src/coursepilot/report_models.py` | model | CRUD (read-only view) | `src/coursepilot/notion/models.py` (`SyncResult`, `SyncStats`, `ErrorAction`) | exact (Pydantic DTO envelope with nested action/stat sub-models) |
| `src/coursepilot/cli.py` | controller (CLI command group) | request-response | `src/coursepilot/notion/engine.py` (`NotionSyncEngine.sync` dry_run branch + `_safe_error`) for the safety/exit-code logic; no existing `click`/entrypoint file in repo | role-match (no CLI exists yet — first-of-kind) |
| `src/coursepilot/__main__.py` | config/entrypoint | request-response | none (no existing `__main__.py`) | no analog |
| `src/coursepilot/installer.py` | utility (filesystem) | CRUD (copy/link to disk) | `src/coursepilot/session_manager.py::_is_valid_cache_file` (path/file existence checks) + `src/coursepilot/config.py` (`Path` fields, data-driven settings) | role-match (path handling conventions only; no prior data-table+filesystem-copy module exists) |
| `src/coursepilot/exceptions.py` (MODIFIED — no new file) | model (exception hierarchy) | error propagation | itself — extend existing hierarchy in place | exact (existing file, additive) |
| `skills/coursepilot/SKILL.md` | config (agent instruction doc) | n/a | `.claude/skills/inherit-legacy-style/SKILL.md` (untracked, evidence-only — see gate note) | no tracked analog; use RESEARCH.md Code Examples §"SKILL.md minimal agent-neutral shape" instead |
| `skills/coursepilot/JSON_CONTRACT.md` | config (doc) | n/a | none in-tree | no analog — author fresh from `report_models.py` field docstrings |
| `skills/coursepilot/README.md` | config (doc) | n/a | root `README.md` (style/tone reference only) | partial match |
| `tests/test_reporter.py` | test | transform | `tests/test_transformer.py` | exact |
| `tests/test_cli.py` | test | request-response | `tests/test_notion_engine.py` (MagicMock client injection, dry_run assertions) | role-match |
| `tests/test_pipeline.py` | test | event-driven (error isolation) | `tests/test_notion_engine.py` + `tests/test_session_manager.py` | role-match |
| `tests/test_installer.py` | test | file-I/O | `tests/test_config.py` (Path-based Settings fields) | partial match |

## Pattern Assignments

### `src/coursepilot/reporter.py` (transform, pure function)

**Analog:** `src/coursepilot/domain/transformer.py`

**Imports pattern** (transformer.py lines 1-25):
```python
"""Scraper DTO to domain SyncTask transformer with memo building and deadline rescue (D-09 ~ D-15)."""

from datetime import datetime
import re

from coursepilot.domain.models import (
    Course, SyncTask, TaskPriority, TaskSelect, TaskStatus, TaskType,
)
from coursepilot.scraper.date_parser import KST, parse_lms_date
from coursepilot.scraper.models import AssessmentItem, AssessmentType, ...
```
Apply the same style to `reporter.py`: module docstring naming the decisions it satisfies (D-01~D-05), stdlib imports first, then `domain.models` / `notion.models` imports, then any local sibling modules (`report_models`).

**Core transform pattern — pure function with injectable clock** (transformer.py lines 215-254, `transform_to_sync_tasks`):
```python
def transform_to_sync_tasks(
    courses: list[CourseItem],
    lectures_by_course: dict[str, list[LectureItem]],
    assessments_by_course: dict[str, list[AssessmentItem]],
    include_completed: bool = False,
    mappings: dict[str, str] | None = None,
    now: datetime | None = None,
) -> list[SyncTask]:
    ...
    tasks.sort(key=lambda t: (t.due_date is None, t.due_date or datetime.max.replace(tzinfo=KST)))
    return tasks
```
Copy this shape exactly for `reporter.build_report(tasks, *, sync_result=None, course_errors=None, now=None) -> BriefingReport`: no I/O, `now` defaults via a helper (see `get_current_kst_time` used in RESEARCH.md's own example), pure list comprehension grouping (mirrors `is_completed`/`is_overdue` boolean-flag filtering already on `SyncTask` — reuse `t.is_overdue` / `t.is_urgent` directly, do not recompute).

**Grouping-by-course helper pattern** — mirror `transform_to_sync_tasks`'s `lectures_by_course.get(cid, [])` dict-bucketing idiom for the required `_group_by_course()` helper (D-01: "Inside each section, items are grouped by course").

**No-truncation / D-04 pitfall guard:** transformer.py's `format_memo` (lines 82-95) is the repo's only precedent for truncation logic — and it exists specifically for Notion's 2000-char API limit, which does NOT apply to the CLI report. Do **not** reuse `format_memo`'s truncation numbers or pattern in `reporter.py`; D-04 explicitly forbids truncating the briefing.

---

### `src/coursepilot/report_models.py` (model, versioned DTO envelope)

**Analog:** `src/coursepilot/notion/models.py`

**Nested DTO + stats envelope pattern** (notion/models.py lines 80-101):
```python
class SyncStats(BaseModel):
    """Aggregate action counts consumed by the Phase 5 reporter."""
    total: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: int = 0


class SyncResult(BaseModel):
    """Complete result of one Notion synchronization attempt."""
    enabled: bool
    dry_run: bool = False
    target: NotionTarget | None = None
    created: list[CreateAction] = Field(default_factory=list)
    updated: list[UpdateAction] = Field(default_factory=list)
    skipped: list[SkipAction] = Field(default_factory=list)
    errors: list[ErrorAction] = Field(default_factory=list)
    stats: SyncStats = Field(default_factory=SyncStats)
```
Copy this exact composition style for `BriefingReport`/`Summary` in `report_models.py`:
```python
class Summary(BaseModel):
    course_count: int = 0
    overdue_count: int = 0
    urgent_count: int = 0
    later_count: int = 0

class BriefingReport(BaseModel):
    schema_version: int = 1          # D-13: literal version field, bump on breaking change
    command: str
    generated_at: datetime
    summary: Summary
    overdue: list[CourseGroup] = Field(default_factory=list)
    urgent: list[CourseGroup] = Field(default_factory=list)
    later: list[CourseGroup] = Field(default_factory=list)
    errors: list[ErrorItem] = Field(default_factory=list)
    sync: SyncResult | None = None    # reuse notion.models.SyncResult directly, D-13 "items | sync"
```
Reuse `notion.models.SyncResult` as-is for the `sync` field (do not redefine); it already has `stats`/`created`/`updated`/`skipped`/`errors` shaped correctly for D-13's contract.

**Field-level docstrings as documentation source:** notion/models.py's one-line class docstrings (e.g. `"""Aggregate action counts consumed by the Phase 5 reporter."""` — literally already anticipates Phase 5) are the intended source for `skills/coursepilot/JSON_CONTRACT.md`; write that doc by walking `report_models.py`'s docstrings, not by hand-describing the JSON separately.

---

### `src/coursepilot/cli.py` (controller, request-response) and `pipeline.py` (orchestrator)

**Analog for dry-run / exit-code / safe-error branching:** `src/coursepilot/notion/engine.py`

**Dry-run gate pattern** (engine.py lines 77-97) — copy directly for `sync`'s `--apply` gate (D-06):
```python
def sync(self, tasks: list[SyncTask], *, dry_run: bool = False) -> SyncResult:
    if not self.settings.is_notion_configured:
        ...
        return _result(tasks, actions, enabled=False, dry_run=dry_run)

    client = self.client or NotionClient(settings=self.settings)
    try:
        target = client.resolve_target()
        ...
        planned = plan_sync(tasks, existing_pages)
    except Exception as error:
        return _result(tasks, [_safe_error(error)], enabled=True, dry_run=dry_run)

    if dry_run:
        return _result(tasks, planned, enabled=True, dry_run=True, target=target)
    # ... only reaches write calls past this point when dry_run is False
```
`cli.py`'s `sync` command must follow the identical two-gate shape: (1) never call `client.create_page`/`update_page` unless `--apply` was passed, (2) always read/plan first regardless of `--apply` so the dry-run and apply paths share the same planning code — this is exactly D-06's "reuses the Phase 4 real-read / blocked-write dry-run path."

**Safe error masking pattern** (engine.py lines 19-37) — extend, do not duplicate, per D-14 and RESEARCH.md Pitfall 2:
```python
def _safe_error(
    error: Exception, *, task_id: str | None = None, title: str = "", page_id: str | None = None,
) -> ErrorAction:
    message = (
        str(error)
        if isinstance(error, NotionIntegrationError)
        else "Notion 작업을 완료하지 못했습니다. 설정과 연결 상태를 확인하세요."
    )
    return ErrorAction(task_id=task_id, title=title, page_id=page_id, code=type(error).__name__, message=message)
```
Build `_safe_cli_error()` in `cli.py` (or a shared `errors.py`) with the same typed-allowlist shape but covering the full `coursepilot.exceptions` hierarchy (`ConfigError`, `AuthenticationError`, `NavigationTimeoutError`, `CourseAccessDeniedError` all need an allowed, generic-message branch — none of these currently exist in `_safe_error`, which only recognizes `NotionIntegrationError`). This is the single most load-bearing pattern-reuse point for D-14.

**Exit-code mapping source:** `src/coursepilot/exceptions.py` (full file, unmodified hierarchy) — `ConfigError`/`AuthenticationError` map to exit code 2 (fatal, per D-08/D-12 and RESEARCH.md's "Config/login failure aborts"); `NavigationTimeoutError`/`CourseAccessDeniedError`/any `NotionIntegrationError` subclass map to exit code 1 (partial failure, collected and continued). `cli.py` should catch `ConfigError | AuthenticationError` at the top level (outside the per-course loop) and catch everything else inside `pipeline.py`'s per-course loop, converting to `ErrorAction`/`ErrorItem` via `_safe_cli_error`.

**Per-course error-isolation pattern (for `pipeline.py`):** No existing loop in this repo isolates per-item errors while continuing (closest precedent is `session_manager.py`'s `_navigate_with_retry`, lines 68-82, which catches, logs via `logger.warning`, and retries once before raising). `pipeline.py`'s per-course loop should follow the same catch-log-continue shape but append to an `errors: list[ErrorItem]` instead of retrying:
```python
# Pattern derived from session_manager.py's catch/log/continue-or-raise structure
errors: list[ErrorItem] = []
tasks: list[SyncTask] = []
for course in courses:
    try:
        lectures, assessments = scrape_course(course)  # navigator/lecture_parser/assessment_parser
    except (NavigationTimeoutError, CourseAccessDeniedError) as error:
        errors.append(_safe_cli_error(error, course_id=course.course_id))
        continue
    tasks.extend(transform_to_sync_tasks([course], {course.course_id: lectures}, {course.course_id: assessments}))
```

**Settings/config access pattern:** `src/coursepilot/config.py` — `get_settings()` singleton and the `__repr__`/`__str__` masking of `lms_password`/`notion_token`/`notion_api_key` (lines 60-74) is the existing precedent for "never print secrets" — `cli.py` must never call `str(settings)` or log `settings` directly in a context that bypasses this masked `__repr__`; use it as evidence that `Settings.__repr__` is already safe to print if a debug dump is ever needed.

**Session/browser lifecycle pattern:** `src/coursepilot/session_manager.py::SessionManager` (`__enter__`/`__exit__`/`headful` param) — `pipeline.run_pipeline(headed: bool, relogin: bool)` should construct `SessionManager(headful=headed)` as a context manager exactly as any future caller would, and `relogin` should trigger the same cache-invalidation path already implemented at lines 124-130 (unlink `cache_path` before calling `get_authenticated_page`) — expose a `force_relogin` parameter or call `cache_path.unlink()` before `get_authenticated_page()` if `--relogin` is set (no existing public method does this from outside; likely a small addition to `SessionManager`, verify in RESEARCH/planning whether to add `relogin` param to `SessionManager.get_authenticated_page`).

---

### `src/coursepilot/installer.py` (utility, CRUD file operations)

**No strong in-tree analog** (first filesystem-copy/data-table module). Closest structural precedent for "path fields via `pathlib.Path`, data-driven config" is `src/coursepilot/config.py`:
```python
session_cache_path: Path = Field(default=Path(".cache/session.json"), description="세션 스토리지 파일 경로")
course_mappings_path: Path = Field(default=Path("config/course_mappings.json"), description="과목명 약칭 매핑 파일 경로")
```
Use this as the precedent for keeping all path values as `Path` objects (never string concatenation) in the `AGENT_SKILL_PATHS` table (RESEARCH.md Pattern 3 already gives the target shape).

**File-existence/validation pattern to imitate:** `session_manager.py::_is_valid_cache_file` (lines 57-66) — same defensive shape (existence check, then guarded parse, `except Exception: return False`) is the right precedent for `installer.py`'s pre-copy source-path validation (RESEARCH.md's threat-model requirement: "validate the source path exists and is inside the repo root before linking").

---

## Shared Patterns

### Secret redaction / safe error masking
**Source:** `src/coursepilot/notion/engine.py` lines 19-37 (`_safe_error`) + `src/coursepilot/config.py` lines 60-74 (`Settings.__repr__` masking)
**Apply to:** `cli.py`, `pipeline.py`, `installer.py` (any error path that could embed `lms_username`/`lms_password`/`notion_token`/session cookie paths)
```python
def _safe_error(error: Exception, *, task_id=None, title="", page_id=None) -> ErrorAction:
    message = (
        str(error) if isinstance(error, NotionIntegrationError)
        else "Notion 작업을 완료하지 못했습니다. 설정과 연결 상태를 확인하세요."
    )
    return ErrorAction(task_id=task_id, title=title, page_id=page_id, code=type(error).__name__, message=message)
```
Extend the *typed-allowlist* pattern (not regex scrubbing, per RESEARCH.md's Don't Hand-Roll table) to cover `coursepilot.exceptions.CoursePilotError` subclasses broadly.

### Pydantic DTOs everywhere, never raw dicts
**Source:** `src/coursepilot/notion/models.py`, `src/coursepilot/domain/models.py`
**Apply to:** `report_models.py` (`BriefingReport`, `Summary`, `CourseGroup`, `ErrorItem`) — every one of these must be a `pydantic.BaseModel` subclass, matching the project-wide convention; `--json` output must be `model.model_dump_json()`, never `json.dumps(model.model_dump())` (Pitfall 3 in RESEARCH.md — Pydantic v2's own serializer doesn't `ensure_ascii`-escape Korean text).

### Settings singleton access
**Source:** `src/coursepilot/config.py` lines 80-85 (`get_settings()`)
**Apply to:** `pipeline.py`, `cli.py`, `installer.py` — always obtain `Settings` via `get_settings()` (optionally injected for tests, matching `NotionSyncEngine.__init__(self, settings: Settings | None = None, ...)` pattern in engine.py line 73), never construct `Settings()` directly inside command bodies (breaks testability shown in `tests/test_notion_engine.py`'s `Settings(notion_api_key=..., _env_file=None)` override idiom).

### KST-aware datetime defaults
**Source:** `src/coursepilot/scraper/date_parser.py` (`KST` constant, used throughout `domain/transformer.py` and `domain/models.py`'s `ensure_kst` validator)
**Apply to:** `reporter.build_report(..., now: datetime | None = None)` — default via the same `KST`-aware "now" helper already used by `calculate_priority`/`transform_to_sync_tasks`, not a naive `datetime.now()`.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `src/coursepilot/__main__.py` | entrypoint | request-response | No existing entrypoint module in this repo; RESEARCH.md's own Pattern 2 code example is the reference implementation to follow instead |
| `skills/coursepilot/SKILL.md` | agent-instruction doc | n/a | No tracked SKILL.md exists in this repo (only untracked `.claude/skills/`, `.agents/skills/`, `.pi/skills/` mirrors, excluded per the tracked-source gate); use RESEARCH.md's "SKILL.md minimal agent-neutral shape" Code Example verbatim as the starting template |
| `skills/coursepilot/JSON_CONTRACT.md` | doc | n/a | No prior JSON-contract doc in repo; derive directly from `report_models.py` docstrings once written |

## Metadata

**Analog search scope:** `src/coursepilot/**` (all modules), `tests/**` (all test files), root `pyproject.toml`, README.md; explicitly excluded `.claude/`, `.agents/`, `.pi/`, `.gsd/`, `.alpha-aos/` from analog citation per the tracked-source gate (all confirmed untracked via `git ls-files`).
**Files scanned:** 24 source files + 24 test files (via `git ls-files`), 6 read in full for pattern extraction (`notion/engine.py`, `notion/models.py`, `domain/models.py`, `domain/transformer.py`, `exceptions.py`, `session_manager.py`, `config.py`, `test_notion_engine.py`, `scraper/course_list.py`).
**Pattern extraction date:** 2026-09-23
