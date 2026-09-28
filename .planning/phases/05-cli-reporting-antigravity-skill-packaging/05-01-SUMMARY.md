---
phase: 05-cli-reporting-antigravity-skill-packaging
plan: 01
subsystem: cli
tags: [click, rich, pydantic, cli, reporting, json-contract, exit-codes, secret-redaction]

# Dependency graph
requires:
  - phase: 04-notion-scheduler-integration-deduplication
    provides: SyncTask domain model, transform_to_sync_tasks, is_overdue/is_urgent classification, exceptions hierarchy, _safe_error masking pattern
provides:
  - "python -m coursepilot check [--json] [--headed] [--relogin]"
  - First end-to-end LMS orchestrator (pipeline.py: SessionManager -> extract_courses -> per-course scrape -> transform_to_sync_tasks)
  - Versioned JSON contract v1 (report_models.py: SCHEMA_VERSION=1, CheckReport envelope)
  - Pure urgency-grouped Rich reporter (reporter.py: build_check_report, format_remaining, to_json, render_check_report)
  - CLI failure contract with typed-allowlist secret redaction (errors.py: safe_cli_error, exit_code_for)
affects: [05-02-pipeline-resilience, 05-03-sync-command, 05-04-skill-packaging, 05-05-verification]

actuals:
  tokens: 11792
  tasks: 3
  commits: 5

tech-stack:
  added: []
  patterns:
    - "Pure reporter function: build_check_report/format_remaining/render_check_report take data in, return/write renderables, no I/O (mirrors domain/transformer.py's injectable-clock pure-function style)"
    - "Typed-allowlist error redaction: safe_cli_error() extends notion/engine.py's _safe_error shape across the full exceptions hierarchy + pydantic ValidationError, never regex scrubbing"
    - "Two-Console stdout/stderr separation instantiated at call time inside the command body, never at import time"
    - "Guarded top-level try/except in cli.check(): any Exception becomes a well-formed fatal CheckReport on the same output channel as success"

key-files:
  created:
    - src/coursepilot/report_models.py
    - src/coursepilot/reporter.py
    - src/coursepilot/pipeline.py
    - src/coursepilot/cli.py
    - src/coursepilot/__main__.py
    - src/coursepilot/errors.py
    - tests/test_cli.py
    - tests/test_reporter.py
    - tests/test_errors.py
  modified: []

key-decisions:
  - "Later section's memo/detail is intentionally dropped (ReportItem.detail=None) even when SyncTask.memo is non-empty, per D-02's 'only urgent+overdue get detail blocks'"
  - "remaining_minutes is a signed floor((due-now)/60) so overdue items carry negative values; format_remaining has exactly two overdue shapes (day+hour, hour+minute) and three forward shapes (day+hour, hour+minute, minute-only), matching the plan's literal examples"
  - "collect_tasks does not yet catch per-course exceptions (that isolation is explicitly Plan 05-02's slice); PipelineResult.errors is wired end-to-end so 05-02 only needs to populate it"
  - "safe_cli_error treats ConfigError/NotionIntegrationError as already-safe (their raise sites in this repo only ever embed key names or target metadata), so their str(error) passes through verbatim instead of being replaced with a generic message"

patterns-established:
  - "Pattern: any new CLI failure mode must route through safe_cli_error(..., scope=...) before it reaches an ErrorItem/output channel - never str(exception) directly"
  - "Pattern: JSON output always goes through model.model_dump_json(), never json.dumps(model.model_dump()), to keep Korean text unescaped"

requirements-completed: [SKIL-01, SKIL-02]

coverage:
  - id: D1
    description: "python -m coursepilot check runs LMS login -> course list -> per-course scrape -> transform_to_sync_tasks -> briefing, printing Rich by default and equivalent JSON with --json, never importing/constructing any Notion component"
    requirement: SKIL-02
    verification:
      - kind: unit
        ref: "tests/test_cli.py#test_json_contract_check_envelope"
        status: pass
      - kind: unit
        ref: "tests/test_cli.py#test_human_default_renders_sections"
        status: pass
    human_judgment: false
  - id: D2
    description: "--json stdout is exactly one v1 CheckReport with top-level keys {schema_version, command, generated_at, summary, items, errors}, schema_version==1, Korean text unescaped, never a raw SyncTask dump"
    requirement: SKIL-02
    verification:
      - kind: unit
        ref: "tests/test_cli.py#test_json_contract_check_envelope"
        status: pass
      - kind: unit
        ref: "tests/test_reporter.py#test_json_contract_korean_unescaped"
        status: pass
    human_judgment: false
  - id: D3
    description: "Items split overdue -> due_within_24h -> later from existing is_overdue/is_urgent flags, grouped by course, no N-day cutoff on overdue"
    requirement: SKIL-01
    verification:
      - kind: unit
        ref: "tests/test_reporter.py#test_grouping_sections_by_urgency_then_course"
        status: pass
      - kind: unit
        ref: "tests/test_reporter.py#test_grouping_includes_very_old_overdue"
        status: pass
      - kind: unit
        ref: "tests/test_reporter.py#test_grouping_summary_counts"
        status: pass
    human_judgment: false
  - id: D4
    description: "Rich report shows summary header, one four-column table per section, detail blocks only for overdue/within-24h/errors, never truncates or ellipsizes any row"
    requirement: SKIL-01
    verification:
      - kind: unit
        ref: "tests/test_reporter.py#test_detail_only_for_urgent_and_overdue"
        status: pass
      - kind: unit
        ref: "tests/test_reporter.py#test_no_truncation_sixty_items_json_and_rich"
        status: pass
      - kind: unit
        ref: "tests/test_reporter.py#test_no_truncation_narrow_console_no_ellipsis"
        status: pass
      - kind: unit
        ref: "tests/test_reporter.py#test_detail_bracketed_titles_render_literally"
        status: pass
      - kind: unit
        ref: "tests/test_reporter.py#test_detail_errors_section_rendered"
        status: pass
    human_judgment: false
  - id: D5
    description: "check accepts only --json/--headed/--relogin; per-course progress and all logging go to stderr; stdout is UTF-8 even behind a cp949 parent pipe"
    requirement: SKIL-02
    verification:
      - kind: unit
        ref: "tests/test_cli.py#test_check_rejects_unknown_option"
        status: pass
      - kind: unit
        ref: "tests/test_cli.py#test_stderr_only_progress"
        status: pass
      - kind: unit
        ref: "tests/test_cli.py#test_main_utf8_stdout_under_cp949"
        status: pass
    human_judgment: false
  - id: D6
    description: "Exit code 0 on full success, 1 when results carry course/item errors, 2 when settings loading or collection raises"
    requirement: SKIL-02
    verification:
      - kind: unit
        ref: "tests/test_cli.py#test_exit_code_zero_on_success"
        status: pass
      - kind: unit
        ref: "tests/test_cli.py#test_exit_code_one_on_course_errors"
        status: pass
      - kind: unit
        ref: "tests/test_cli.py#test_exit_code_two_on_config_error"
        status: pass
      - kind: unit
        ref: "tests/test_cli.py#test_exit_code_two_on_settings_validation_error"
        status: pass
      - kind: unit
        ref: "tests/test_errors.py#test_exit_code_for_mapping"
        status: pass
    human_judgment: false
  - id: D7
    description: "No stdout/stderr text on any check path contains the LMS username, LMS password, Notion token/API key, or cookie values; every error message comes from the typed allowlist"
    requirement: SKIL-02
    verification:
      - kind: unit
        ref: "tests/test_errors.py#test_redaction_allowlist_messages"
        status: pass
      - kind: unit
        ref: "tests/test_errors.py#test_redaction_validation_error_lists_field_names_only"
        status: pass
      - kind: unit
        ref: "tests/test_cli.py#test_redaction_fatal_auth_error_json_and_human"
        status: pass
      - kind: unit
        ref: "tests/test_cli.py#test_redaction_unexpected_exception"
        status: pass
      - kind: unit
        ref: "tests/test_cli.py#test_redaction_settings_values_never_printed"
        status: pass
    human_judgment: false

duration: 55min
completed: 2026-09-23
status: complete
---

# Phase 5 Plan 1: End-to-End CLI Reporting Summary

**`python -m coursepilot check` chains SessionManager -> course scrape -> transform_to_sync_tasks into a Rich/JSON v1 briefing with stderr-only progress, UTF-8 stdout, 0/1/2 exit codes, and typed-allowlist secret redaction — no Notion import anywhere on the path.**

## Performance

- **Duration:** 55 min
- **Started:** 2026-09-23T~14:30 (session start)
- **Completed:** 2026-09-23
- **Tasks:** 3 (1 tracer + 2 TDD)
- **Files created:** 9 (6 source, 3 test)

## Accomplishments

- First end-to-end LMS orchestrator (`pipeline.py`): `collect_tasks()` runs `SessionManager` login → `extract_courses` → per-course `scrape_course` (progress → course nav → assessments) → `transform_to_sync_tasks`, never writing to stdout.
- Versioned JSON contract v1 (`report_models.py`): `SCHEMA_VERSION = 1`, all `extra="forbid"` Pydantic models — `ReportSummary`, `ReportItem`, `CourseGroup`, `BriefingSections`, `ErrorItem`, `CheckReport` — never a raw `SyncTask` dump.
- Pure reporter (`reporter.py`): `build_check_report` classifies purely from existing `is_overdue`/`is_urgent` flags (no re-derivation, no N-day cutoff), `format_remaining` produces the five Korean time-remaining shapes, `to_json` uses Pydantic's own serializer (Korean unescaped), `render_check_report` draws the full urgency-grouped Rich briefing with `overflow="fold"` everywhere (no truncation) and `Text`-wrapped user data (no markup injection from bracketed titles).
- `cli.py` `check` command: exactly `--json`/`--headed`/`--relogin`, two `Console`s created at call time, progress lines only to `err`, guarded top-level exception boundary converts any `Exception` into a well-formed fatal `CheckReport`, every exit path goes through `exit_code_for()` (0/1/2).
- `errors.py`: `safe_cli_error()` typed allowlist covering `ConfigError`/`NotionIntegrationError` (own message), `AuthenticationError`/`NavigationTimeoutError`/`CourseAccessDeniedError`/bare `CoursePilotError`/any other `Exception` (fixed Korean messages), and pydantic `ValidationError` (field names only, never the rejected input value).
- `main()`/`_configure_streams()`/`_configure_logging()` + `__main__.py`: stdout/stderr reconfigured to UTF-8 (survives a cp949 parent pipe), stdlib logging routed to stderr once.

## Task Commits

Task 1 was `type="tracer"` (single production-quality commit + re-verified `<verify>` before expanding, per the tracer feedback gate — auto mode inactive, `human_verify_mode` default `end-of-phase`, tracer `<verify>` carried only `<automated>`, so it re-ran silently and continued to Task 2 with no checkpoint). Tasks 2 and 3 were `tdd="true"` (RED → GREEN, no REFACTOR needed — code was clean on first pass):

1. **Task 1: End-to-end `check --json`** - `72e497c` (feat)
2. **Task 2 RED: failing tests for Rich briefing / UTF-8 / stderr** - `0dbc9fe` (test)
2. **Task 2 GREEN: render_check_report, main(), __main__.py** - `625e379` (feat)
3. **Task 3 RED: failing tests for exit codes / redaction** - `bc1fc31` (test)
3. **Task 3 GREEN: errors.py, guarded exception boundary in cli.py** - `41c026a` (feat)

**Plan metadata:** committed after this SUMMARY.

## Files Created/Modified

- `src/coursepilot/report_models.py` - Versioned JSON contract v1 (SCHEMA_VERSION, CheckReport envelope)
- `src/coursepilot/reporter.py` - build_check_report, format_remaining, to_json, render_check_report (pure + Rich)
- `src/coursepilot/pipeline.py` - collect_tasks/scrape_course, first end-to-end orchestrator
- `src/coursepilot/cli.py` - click group, check command, main()/_configure_streams()/_configure_logging()
- `src/coursepilot/__main__.py` - `python -m coursepilot` entry
- `src/coursepilot/errors.py` - safe_cli_error, exit_code_for, EXIT_OK/EXIT_PARTIAL/EXIT_FATAL
- `tests/test_cli.py` - CliRunner coverage: JSON contract, stderr routing, flags, exit codes, redaction, UTF-8 entry
- `tests/test_reporter.py` - Pure reporter coverage: grouping, detail blocks, no truncation, JSON encoding
- `tests/test_errors.py` - Allowlist and exit-code unit coverage

## Decisions Made

- Reused `notion/engine.py`'s `_safe_error` *shape* (typed allowlist, not regex scrubbing) rather than a new redaction strategy, per RESEARCH.md's Don't Hand-Roll guidance — `errors.py` is a proper superset covering the full `coursepilot.exceptions` hierarchy plus pydantic `ValidationError`.
- `remaining_minutes` and `remaining_text` are computed once per `ReportItem` from the CLI's single `now` snapshot (never re-derived per render call), keeping the JSON and Rich outputs numerically identical for the same report.
- Per-course error isolation was deliberately left out of `pipeline.py`'s loop in this plan (explicitly Plan 05-02's slice per the plan text) — `PipelineResult.errors` and the entire `ErrorItem`/exit-code contract are already wired so 05-02 only needs to populate the list.

## Deviations from Plan

None - plan executed exactly as written. All `<action>` details (module boundaries, function signatures, allowlist branches, Rich column settings) were implemented as specified; no Rule 1-4 auto-fixes or architectural changes were needed.

## Issues Encountered

None. All three tasks' `<verify>` and `<acceptance_criteria>` passed on first implementation attempt per task; full suite grew from a 108-test baseline to 134 tests with zero regressions.

## User Setup Required

None - no external service configuration required. No new packages were installed (click/rich/pydantic were already locked dependencies).

## Next Phase Readiness

- `pipeline.py`, `report_models.py`, `reporter.py`, `cli.py`, `errors.py` are all in place with stable, tested signatures (`collect_tasks`, `build_check_report`, `render_check_report`, `safe_cli_error`, `exit_code_for`) ready for Plan 05-02 (per-course error isolation) to extend without touching the CLI/JSON contract boundary.
- Plan 05-03 (`sync` command) can reuse `errors.py`'s allowlist directly and extend `report_models.py` with the `sync`-specific DTOs already named in the plan's "Artifacts this phase produces" section.
- No blockers.

---
*Phase: 05-cli-reporting-antigravity-skill-packaging*
*Completed: 2026-09-23*
