---
phase: 05-cli-reporting-antigravity-skill-packaging
plan: 02
subsystem: pipeline
tags: [resilience, error-isolation, pytest, tdd, playwright-mock, exit-codes]

# Dependency graph
requires:
  - phase: 05-cli-reporting-antigravity-skill-packaging
    provides: "05-01's collect_tasks/scrape_course scaffolding, PipelineResult, safe_cli_error/exit_code_for contract"
provides:
  - "Per-course error isolation in collect_tasks (D-08): one failing course never hides the others, check exits 1 with the rest of the briefing intact"
  - "validate_lms_settings(settings) -> None: fatal ConfigError naming only missing LMS_URL/LMS_USERNAME/LMS_PASSWORD keys before any browser starts (D-18)"
  - "Fatal-stage classification pinned by tests: login and course-list failures propagate unconverted for the CLI's exit-2 handler"
  - "Per-course progress order, --relogin/--headed forwarding, and course-mapping loading pinned by tests (D-10, D-11)"
  - "Zero-course handling: course_count 0 with a WARNING log, not an error (A-05)"
  - "Real scrape_course() proven read-only and correct (progress-table path + course-home fallback) over fixture HTML (SKIL-02)"
affects: [05-03-sync-command, 05-05-verification]

actuals:
  tokens: 5147
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Per-course try/except Exception boundary inside collect_tasks's for-loop: convert to safe_cli_error(scope='course'), log a warning naming only course id/exception class (never the exception text), continue to the next course"
    - "Fatal-stage guard function (validate_lms_settings) called as the first statement of collect_tasks, before any I/O or session construction, mirroring the plan's 'nothing before this line touches a browser' contract"
    - "MagicMock page with goto()/content() side effects keyed on the last-visited URL, reused from tests/test_assessment_parser.py's fixture-serving idiom, to drive the real CourseNavigator + real parsers end to end without Playwright"

key-files:
  created: []
  modified:
    - src/coursepilot/pipeline.py
    - tests/test_pipeline.py

key-decisions:
  - "Zero-course handling returns PipelineResult early (inside the `with` session block) rather than falling through to transform_to_sync_tasks on empty lists - functionally equivalent output, but guarantees the WARNING is emitted through the coursepilot.pipeline logger specifically (not conflated with course_mapping's own missing-file warning), which the test pins by filtering on record.name"
  - "validate_lms_settings runs before the --relogin cache-deletion step and before the session factory is touched, so a missing-config run never deletes the user's cached session nor constructs SessionManager - confirmed via a tracking session_factory that raises if invoked"
  - "Task 3's real scrape_course() needed no production-code change - three tests were written against the unmodified 05-01 implementation and all passed immediately, so no scraper module was touched (verified via `git log --format=%s -- src/coursepilot/scraper` showing no 05-02 commits)"

patterns-established:
  - "Pattern: any new per-item collection failure inside a loop should isolate via try/except Exception -> safe_cli_error(scope=...) -> continue, never letting one item's failure abort the whole collection (mirrors this plan's per-course loop for future per-item loops, e.g. sync's per-task apply loop in 05-03)"

requirements-completed: [SKIL-02, SKIL-01]

coverage:
  - id: D1
    description: "A course whose collection fails (navigation timeout, access denied, parser crash, or any other Exception) is isolated per course: converted to an ErrorItem with course_id/course_name, the rest of the courses are still collected, and check exits 1 with all successful items still reported"
    requirement: SKIL-01
    verification:
      - kind: unit
        ref: "tests/test_pipeline.py#test_course_failure_is_isolated"
        status: pass
      - kind: unit
        ref: "tests/test_pipeline.py#test_exit_code_one_end_to_end_course_failure"
        status: pass
    human_judgment: false
  - id: D2
    description: "Missing LMS_URL/LMS_USERNAME/LMS_PASSWORD raises ConfigError naming only the missing keys before any browser starts; login and course-list failures propagate unconverted so check exits 2"
    requirement: SKIL-02
    verification:
      - kind: unit
        ref: "tests/test_pipeline.py#test_exit_code_config_error_before_browser"
        status: pass
      - kind: unit
        ref: "tests/test_pipeline.py#test_exit_code_login_failure_propagates"
        status: pass
      - kind: unit
        ref: "tests/test_pipeline.py#test_exit_code_course_list_failure_propagates"
        status: pass
    human_judgment: false
  - id: D3
    description: "Per-course progress fires exactly once per course, in order, before that course is scraped, including courses that later fail"
    requirement: SKIL-02
    verification:
      - kind: unit
        ref: "tests/test_pipeline.py#test_stderr_progress_once_per_course_in_order"
        status: pass
    human_judgment: false
  - id: D4
    description: "--relogin deletes only the session cache file before the session opens (sibling files untouched); --headed is forwarded as SessionManager(headful=...)"
    requirement: SKIL-02
    verification:
      - kind: unit
        ref: "tests/test_pipeline.py#test_relogin_deletes_only_session_cache"
        status: pass
      - kind: unit
        ref: "tests/test_pipeline.py#test_headed_forwarded_to_session"
        status: pass
    human_judgment: false
  - id: D5
    description: "Course-name mappings are loaded from settings.course_mappings_path and applied to task titles ([abbr] prefix)"
    requirement: SKIL-02
    verification:
      - kind: unit
        ref: "tests/test_pipeline.py#test_mappings_loaded_from_settings_path"
        status: pass
    human_judgment: false
  - id: D6
    description: "Zero discovered courses is not an error: course_count 0, empty tasks/errors, plus a WARNING log through the pipeline logger"
    requirement: SKIL-02
    verification:
      - kind: unit
        ref: "tests/test_pipeline.py#test_zero_courses_warns_not_errors"
        status: pass
    human_judgment: false
  - id: D7
    description: "The real per-course scraping sequence (progress-table path and course-home fallback path) is exercised end to end over fixture HTML and is mechanically proven read-only (no click/fill/press/etc on the page)"
    requirement: SKIL-02
    verification:
      - kind: unit
        ref: "tests/test_pipeline.py#test_scrape_course_uses_progress_report"
        status: pass
      - kind: unit
        ref: "tests/test_pipeline.py#test_scrape_course_falls_back_to_course_sections"
        status: pass
      - kind: unit
        ref: "tests/test_pipeline.py#test_scrape_course_is_read_only"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-09-23
status: complete
---

# Phase 5 Plan 2: Pipeline Resilience & Read-Only Scraping Summary

**`collect_tasks` isolates per-course failures instead of aborting the whole run, validates LMS settings before any browser starts, and the real per-course scraping sequence is mechanically proven read-only over fixture HTML.**

## Performance

- **Duration:** 45 min
- **Started:** 2026-09-23
- **Completed:** 2026-09-23
- **Tasks:** 3 (1 tracer + 2 TDD)
- **Files modified:** 2 (1 source, 1 test)

## Accomplishments

- Per-course error isolation (`pipeline.py`): each course's `scrape_course()` call is wrapped in `try`/`except Exception`, converting failures to `safe_cli_error(scope="course", course_id=..., course_name=...)` and continuing with the next course. A restricted or broken course no longer aborts the whole run or hides the other courses' items — `check` exits 1 with everything else intact.
- Fatal-stage classification pinned by tests: settings validation, session login, and `extract_courses` failures propagate out of `collect_tasks` unconverted, reaching the CLI's guarded top-level exception boundary (exit 2). Only the per-course scraping step is isolated.
- `validate_lms_settings(settings) -> None`: the first statement of `collect_tasks`, raising `ConfigError` naming only the missing `LMS_URL`/`LMS_USERNAME`/`LMS_PASSWORD` env-var keys — never a value — before the `--relogin` cache-deletion step or the session factory are touched.
- Zero-course handling: `extract_courses` returning `[]` is not an error — logs a Korean `WARNING` through the `coursepilot.pipeline` logger and returns `PipelineResult(course_count=0, tasks=[], errors=[])`.
- Progress order, `--relogin`/`--headed` forwarding, and course-mapping loading (already correct from 05-01) are now pinned by dedicated tests against regression.
- The real `scrape_course()` — progress-table path and course-home fallback path — is exercised end to end over fixture HTML via a `MagicMock` page whose `content()` reflects the last `goto()` URL, and mechanically proven read-only: `page.method_calls` across both scenarios stays a subset of `{goto, content, wait_for_selector, wait_for_timeout, screenshot}`.

## Task Commits

Task 1 was `type="tracer"` (single production-quality commit + re-verified `<verify>` before expanding, per the tracer feedback gate — auto mode inactive, `human_verify_mode` default `end-of-phase`, tracer `<verify>` carried only `<automated>`, so it re-ran silently and continued to Task 2 with no checkpoint). Task 2 was `tdd="true"` (RED → GREEN, no REFACTOR needed). Task 3 was `tdd="true"` but required no GREEN commit — all three tests passed against the unmodified 05-01 `scrape_course`, so there was no production code to change:

1. **Task 1 (tracer): per-course error isolation** - `3f4e214` (feat)
2. **Task 2 RED: failing tests for fatal-stage classification, zero-course warning** - `cf79703` (test)
2. **Task 2 GREEN: validate_lms_settings, zero-course warning** - `f66cedf` (feat)
3. **Task 3: real per-course scraping sequence, proven read-only** - `0b26832` (test)

**Plan metadata:** committed after this SUMMARY.

## Files Created/Modified

- `src/coursepilot/pipeline.py` - Per-course error isolation, `validate_lms_settings`, zero-course warning
- `tests/test_pipeline.py` - 13 tests: isolation, fatal-stage, progress order, relogin/headed, mappings, zero-course, read-only scraping

## Decisions Made

- Zero-course handling returns `PipelineResult` early inside the `with` session block instead of falling through to `transform_to_sync_tasks` on empty lists — functionally equivalent output, but guarantees the `WARNING` is attributable specifically to `coursepilot.pipeline` (not conflated with `course_mapping`'s own missing-file warning), which the test pins by filtering `record.name`.
- `validate_lms_settings` runs before the `--relogin` cache-deletion step and before the session factory is constructed, confirmed by a tracking `session_factory` that raises `AssertionError` if invoked — a missing-config run touches neither the cached session nor `SessionManager`.
- Task 3's real `scrape_course()` needed no production-code change: three tests were written against the unmodified 05-01 implementation and all passed immediately (no RED failure). Per the plan's explicit guard ("do not change scraper modules from Phases 1-4"), this is recorded as a finding, not a gap — `git log --format=%s -- src/coursepilot/scraper` shows no `05-02` commits, confirming Phase 1-4 scraper modules were untouched.

## Deviations from Plan

None - plan executed exactly as written. Task 3's TDD cycle produced no GREEN commit because no defect was found (the plan explicitly anticipated and permitted this outcome: "If the tests expose a wiring defect... fix `scrape_course`... If a fixture reveals a Phase 2 parser defect, record it in the SUMMARY as a gap instead" — no defect was found, so nothing to fix or record as a gap).

## Issues Encountered

- The first draft of `test_zero_courses_warns_not_errors` passed for the wrong reason: `caplog.records` captures every propagated log record, not just ones from the logger named in `caplog.at_level(...)`, so a pre-existing `WARNING` from `course_mapping`'s missing-mappings-file loader satisfied a loose `any(record.levelno == logging.WARNING ...)` assertion before `pipeline.py` had any zero-course warning at all. Tightened the assertion to filter on `record.name == "coursepilot.pipeline"`, which correctly failed until the real warning was added — caught during the RED-phase run, before GREEN.

## User Setup Required

None - no external service configuration required. No new packages were installed.

## Next Phase Readiness

- `pipeline.py`'s `collect_tasks`/`scrape_course`/`validate_lms_settings`/`PipelineResult` are hardened, tested, and stable for Plan 05-03 (`sync` command) and Plan 05-05 (live/E2E verification) to build on without further changes to this module.
- The per-course try/except-continue pattern established here (isolate, `safe_cli_error(scope=...)`, continue) is the template for 05-03's per-task `sync --apply` loop if it needs similar isolation.
- No blockers.

## Self-Check: PASSED

- FOUND: src/coursepilot/pipeline.py
- FOUND: tests/test_pipeline.py
- FOUND commits: 3f4e214, cf79703, f66cedf, 0b26832
- `uv run pytest -q tests/test_pipeline.py -x` green (13 tests)
- `uv run pytest` green (full suite, 147 tests)

---
*Phase: 05-cli-reporting-antigravity-skill-packaging*
*Completed: 2026-09-23*
