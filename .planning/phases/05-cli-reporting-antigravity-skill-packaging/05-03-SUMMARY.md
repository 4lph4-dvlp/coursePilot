---
phase: 05-cli-reporting-antigravity-skill-packaging
plan: 03
subsystem: cli
tags: [click, rich, pydantic, notion, sync, json-contract, exit-codes, secret-redaction, tdd]

# Dependency graph
requires:
  - phase: 05-cli-reporting-antigravity-skill-packaging
    provides: "05-01's collect_tasks/_collect helper pattern, ReportSummary/ErrorItem, errors.py (safe_cli_error, exit_code_for), report_models.py SCHEMA_VERSION contract, reporter.py check renderer patterns (overflow=fold, Text, shared errors table)"
  - phase: 04-notion-scheduler-integration-deduplication
    provides: "NotionSyncEngine.sync(tasks, dry_run=...), SyncResult/CreateAction/UpdateAction/SkipAction/ErrorAction/FieldDiff DTOs, dry-run-after-real-reads pattern, _safe_error masking"
provides:
  - "python -m coursepilot sync [--json] [--headed] [--relogin] [--apply]"
  - "Sync half of JSON contract v1 (report_models.py: SyncChange/SyncCreateItem/SyncUpdateItem/SyncSkipItem/SyncCounts/SyncSection/SyncReport)"
  - "build_sync_report/render_sync_report/notion_page_url (reporter.py) mapping a real SyncResult into the create/update/skip approval-flow data (D-16)"
  - "Shared _collect_lms_tasks helper in cli.py reused by both check and sync"
affects: [05-04-skill-packaging, 05-05-verification]

actuals:
  tokens: 9054
  tasks: 2
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Shared urgency classification: _classify_by_urgency(tasks) extracted from build_check_report so build_sync_report's summary header agrees with check's counts from the same SyncTask flags"
    - "Shared Rich summary header: _summary_header(report) used by both render_check_report and render_sync_report (D-03), avoiding duplicated header-string construction"
    - "Explicit SyncResult -> SyncSection mapping, never model_dump(): CreateAction/UpdateAction/SkipAction/ErrorAction fields are named one-by-one into SyncCreateItem/SyncUpdateItem/SyncSkipItem, with FieldDiff before/after rendered through a private _display() helper (None/datetime.isoformat()/Enum.value/str fallback)"
    - "Static (non-dynamic) unconfigured-Notion notice: always names all three candidate keys (NOTION_TOKEN, NOTION_DATABASE_NAME, NOTION_DATABASE_ID) rather than computing which one is actually missing, so the message can never leak partial config state"
    - "Shared LMS collection: _collect_lms_tasks(...) in cli.py factors settings-load + progress-callback + collect_tasks() out of check, reused by sync, so both commands share one fatal-boundary contract"

key-files:
  created: []
  modified:
    - src/coursepilot/report_models.py
    - src/coursepilot/reporter.py
    - src/coursepilot/cli.py
    - tests/test_cli.py
    - tests/test_reporter.py

key-decisions:
  - "Task 1 (tracer) shipped build_sync_report with notice hardcoded to None and cli.py's non-JSON sync path printing only the summary line, exactly as the plan specified ('Task 2 adds the unconfigured notice' / 'Rich path arrives in Task 2') -- kept the tracer's production-quality real-engine dry-run path isolated from the not-yet-built Rich renderer"
  - "The unconfigured-Notion notice is a single static Korean string naming all three candidate .env keys, not a settings-aware dynamic message -- matches the plan's literal action text ('lists only the key names') and keeps build_sync_report's signature unchanged (no settings parameter needed) while still satisfying 'contains no setting values'"
  - "Extracted _classify_by_urgency and _summary_header as shared helpers between build_check_report/build_sync_report and render_check_report/render_sync_report respectively, per the plan's explicit 'extract a shared private helper rather than duplicating it' and 'factor it into a private helper both renderers call' instructions"

patterns-established:
  - "Pattern: any new CLI report envelope (check, sync, and future commands) should build its create/update/skip-style DTOs by naming fields explicitly off the source result object, never via model_dump() passthrough -- keeps the versioned JSON contract intentional and independent of internal DTO shape changes"

requirements-completed: [SKIL-02, SKIL-01]

coverage:
  - id: D1
    description: "python -m coursepilot sync --json runs the real NotionSyncEngine planning path (target resolve -> schema validate -> query existing -> plan) as a dry-run by default, making zero create_page/update_page calls"
    requirement: SKIL-02
    verification:
      - kind: unit
        ref: "tests/test_cli.py#test_sync_dry_run_default_never_writes"
        status: pass
    human_judgment: false
  - id: D2
    description: "sync --apply flips dry_run=False and the real engine actually calls create_page/update_page for the planned actions; sync.applied is True only then"
    requirement: SKIL-02
    verification:
      - kind: unit
        ref: "tests/test_cli.py#test_sync_apply_writes_planned_actions"
        status: pass
    human_judgment: false
  - id: D3
    description: "check never constructs NotionSyncEngine under any circumstance"
    requirement: SKIL-02
    verification:
      - kind: unit
        ref: "tests/test_cli.py#test_check_no_notion_engine_constructed"
        status: pass
    human_judgment: false
  - id: D4
    description: "sync --json emits exactly one v1 SyncReport {schema_version, command, generated_at, summary, sync, errors}; the sync section's keys are exactly {enabled, dry_run, applied, target_title, notice, create, update, skip, counts}; never a raw SyncResult dump"
    requirement: SKIL-02
    verification:
      - kind: unit
        ref: "tests/test_cli.py#test_sync_dry_run_default_never_writes"
        status: pass
      - kind: unit
        ref: "tests/test_reporter.py#test_json_contract_sync_envelope_keys"
        status: pass
    human_judgment: false
  - id: D5
    description: "With Notion unconfigured, sync still reports the LMS summary, sets sync.enabled=false with a notice naming only .env key names (no values), and exits 0 unless course errors exist (Phase 4 D-09 carried forward)"
    requirement: SKIL-02
    verification:
      - kind: unit
        ref: "tests/test_cli.py#test_sync_no_notion_configured_notice"
        status: pass
    human_judgment: false
  - id: D6
    description: "Exit codes hold across sync paths: 0 full success, 1 when Notion item/integration errors exist (LMS briefing still delivered), 2 when LMS collection is fatal and NotionSyncEngine is never constructed"
    requirement: SKIL-02
    verification:
      - kind: unit
        ref: "tests/test_cli.py#test_exit_code_sync_notion_error_is_partial"
        status: pass
      - kind: unit
        ref: "tests/test_cli.py#test_exit_code_sync_fatal_skips_notion"
        status: pass
    human_judgment: false
  - id: D7
    description: "No sync output (JSON or human, dry-run or --apply, stdout or stderr) ever contains the LMS username, LMS password, or Notion token"
    requirement: SKIL-02
    verification:
      - kind: unit
        ref: "tests/test_cli.py#test_redaction_sync_outputs"
        status: pass
    human_judgment: false
  - id: D8
    description: "The Rich sync report shows the shared summary header, a mode banner (미리보기/적용 완료/notice), untruncated create/update/skip tables (update shows DueDate before -> after, skip shows Korean reason labels), and the shared errors section -- no ellipsis at narrow width, every title present at wide width even with 40 rows"
    requirement: SKIL-01
    verification:
      - kind: unit
        ref: "tests/test_reporter.py#test_detail_sync_render_sections"
        status: pass
      - kind: unit
        ref: "tests/test_reporter.py#test_detail_sync_no_truncation"
        status: pass
    human_judgment: false

duration: ~40min (one session interruption/resume for an API rate limit; net active work time)
completed: 2026-09-23
status: complete
---

# Phase 5 Plan 3: `sync` Command — Notion Preview-then-Apply Summary

**`python -m coursepilot sync` runs the real Phase 4 `NotionSyncEngine` planning path as a dry-run by default, writes only with `--apply`, and reports the create/update/skip plan as both a Rich report and the sync half of JSON contract v1 — `check` still never touches Notion.**

## Performance

- **Duration:** ~40 min active work (session paused once mid-execution for an API rate limit and resumed)
- **Started:** 2026-09-23
- **Completed:** 2026-09-23
- **Tasks:** 2 (1 tracer + 1 TDD)
- **Files modified:** 5 (3 source, 2 test)

## Accomplishments

- `sync` command (`cli.py`): exactly `--json`/`--headed`/`--relogin`/`--apply` (D-10). Shares LMS collection with `check` through a new private `_collect_lms_tasks` helper (settings load + progress callback + `collect_tasks()`), keeping both commands' fatal-boundary contract identical. Flow: collect → `NotionSyncEngine(settings=settings).sync(tasks, dry_run=not apply)` → `build_sync_report(...)` → JSON on `--json` or `render_sync_report` otherwise → `exit_code_for(report.errors)`.
- Sync half of contract v1 (`report_models.py`): `SyncChange`, `SyncCreateItem`, `SyncUpdateItem`, `SyncSkipItem`, `SyncCounts`, `SyncSection`, `SyncReport` — all `extra="forbid"`, matching the plan's exact field lists.
- Pure mapper (`reporter.py`): `build_sync_report` maps a real `SyncResult` into `SyncSection` explicitly (never `model_dump()`), with `notion_page_url()` building hyphen-free Notion URLs and a private `_display()` helper rendering `FieldDiff` before/after values (`None`/`datetime.isoformat()`/`Enum.value`/`str` fallback). Every `ErrorAction` becomes a top-level `ErrorItem(scope="notion", ...)`. `applied = enabled and not dry_run`. Unconfigured Notion sets a static Korean `notice` naming only the candidate `.env` key names (no values).
- Rich renderer (`reporter.py`): `render_sync_report` shows the shared summary header (D-03, extracted into `_summary_header` and reused by `render_check_report`), a mode banner (미리보기 with `--apply` hint / 적용 완료 / the unconfigured notice), 생성/수정/건너뜀 tables (update shows `DueDate: before -> after`, skip shows Korean reason labels via `SKIP_REASON_LABELS`), and the shared `_render_errors` section — all `overflow="fold"` + `Text`-wrapped, matching 05-01's no-truncation/no-markup-injection rules.
- `check` continues to never import or construct `NotionSyncEngine`, now pinned by a dedicated test that patches `coursepilot.cli.NotionSyncEngine` to raise if called.
- Exit codes and redaction hold across every sync path (configured, unconfigured, Notion error, LMS-fatal), all covered by dedicated tests.

## Task Commits

Task 1 was `type="tracer"` (single production-quality commit + re-verified `<verify>` before expanding, per the tracer feedback gate — auto mode inactive, `human_verify_mode` default `end-of-phase`, tracer `<verify>` carried only `<automated>`, so it re-ran silently and continued to Task 2 with no checkpoint). Task 2 was `tdd="true"` (RED → GREEN → REFACTOR):

1. **Task 1: End-to-end `sync --json` dry-run** - `faa32bd` (feat)
2. **Task 2 RED: failing tests for --apply gate, unconfigured notice, Rich sync report** - `8442a2c` (test)
2. **Task 2 GREEN: notice logic, render_sync_report, wire non-JSON sync path** - `3edbd98` (feat)
2. **Task 2 REFACTOR: shared summary header between check/sync renderers** - `93b6871` (refactor)

**Plan metadata:** committed after this SUMMARY.

## Files Created/Modified

- `src/coursepilot/report_models.py` - Sync half of contract v1: SyncChange/SyncCreateItem/SyncUpdateItem/SyncSkipItem/SyncCounts/SyncSection/SyncReport
- `src/coursepilot/reporter.py` - notion_page_url, build_sync_report, render_sync_report, _classify_by_urgency and _summary_header extracted as shared helpers
- `src/coursepilot/cli.py` - sync command, _collect_lms_tasks shared helper
- `tests/test_cli.py` - 8 new tests: dry-run, apply, check-no-engine, no-Notion notice, exit codes (notion error, fatal), redaction
- `tests/test_reporter.py` - 3 new tests: sync envelope key contract, Rich section rendering, no-truncation at scale

## Decisions Made

- Kept Task 1's `notice=None` placeholder and minimal non-JSON summary-line output exactly as the plan specified, deferring the unconfigured-Notion notice and full `render_sync_report` to Task 2's GREEN step — this let the tracer commit stay a clean, isolated, production-quality slice (real engine, zero writes, proven end-to-end) before any Rich-rendering code existed.
- Chose a static (not settings-derived) unconfigured-Notion notice text that always names all three `.env` keys, per the plan's literal wording ("lists only the key names ... NOTION_TOKEN, and NOTION_DATABASE_NAME or NOTION_DATABASE_ID") — this avoided adding a `settings` parameter to `build_sync_report`'s already-fixed signature and trivially satisfies "contains no setting values" since the string has no interpolated content at all.
- Several of Task 2's RED-phase tests (apply-writes, check-never-constructs-engine, exit-code-notion-error, exit-code-fatal-skips-notion, redaction) passed immediately without any GREEN change, because Task 1's `dry_run=not apply` wiring and `build_sync_report`'s error-mapping already provided that behavior — the plan explicitly anticipated this ("--apply already flips dry_run in Task 1; add the tests that pin it"), so these are regression-pinning tests rather than TDD-driven new behavior. Only the notice test and the two Rich-rendering tests genuinely failed in RED and needed GREEN work.

## Deviations from Plan

None - plan executed exactly as written. All `<action>` details (module boundaries, function signatures, DTO field lists, Rich table columns, Korean copy) were implemented as specified; no Rule 1-4 auto-fixes or architectural changes were needed.

## Issues Encountered

- The session was interrupted mid-Task-2 (between writing the RED tests and committing them) by an API rate limit. On resume, git state was verified (`faa32bd` committed for Task 1, RED test changes present but uncommitted in the working tree) before continuing — no rework was needed, the RED tests were re-run to reconfirm expected failures, then committed and GREEN proceeded normally.

## User Setup Required

None - no external service configuration required. No new packages were installed.

## Next Phase Readiness

- `cli.py`, `report_models.py`, `reporter.py` now expose a stable, tested `sync` command alongside `check`, both sharing `_collect_lms_tasks` and the versioned JSON contract v1 envelope pattern (`{schema_version, command, generated_at, summary, items|sync, errors}`).
- Plan 05-04 (universal Agent Skill packaging) can document `check`/`sync` exactly as built: `--json`/`--headed`/`--relogin` shared, `--apply` sync-only, exit codes 0/1/2, and the D-16 preview→approve→apply conversation flow using `sync`'s create/update/skip JSON data.
- No blockers.

## Self-Check: PASSED

- FOUND: src/coursepilot/report_models.py
- FOUND: src/coursepilot/reporter.py
- FOUND: src/coursepilot/cli.py
- FOUND: tests/test_cli.py
- FOUND: tests/test_reporter.py
- FOUND commits: faa32bd, 8442a2c, 3edbd98, 93b6871
- `uv run pytest -q tests/test_cli.py tests/test_reporter.py -x` green (33 tests)
- `uv run pytest -q` green (full suite, 157 tests)

---
*Phase: 05-cli-reporting-antigravity-skill-packaging*
*Completed: 2026-09-23*
</content>
