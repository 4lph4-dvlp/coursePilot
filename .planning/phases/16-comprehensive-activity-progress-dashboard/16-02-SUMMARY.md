---
phase: 16-comprehensive-activity-progress-dashboard
plan: "02"
subsystem: progress
tags:
  - runner
  - cache
  - terminal-ui
  - rich
  - cli
requires:
  - "16-01"
provides:
  - progress-pipeline-runner
  - atomic-progress-cache
  - 3-tier-progress-dashboard
  - progress-cli-command
affects: []
tech-stack.added: []
patterns:
  - Single-trip HTML scraping for lectures, materials, sections
  - 10-minute TTL atomic cache replacement (.tmp -> replace)
  - Course-level error isolation with partial success status
  - 3-tier Rich terminal dashboard (Summary Table, To-Do Actions, Alert/All-Clear Panel)
  - Strict stdout/stderr stream separation for clean JSON output
key-files.created:
  - src/coursepilot/progress/runner.py
  - src/coursepilot/progress/reporter.py
  - tests/test_progress_runner.py
  - tests/test_progress_reporter.py
  - tests/test_cli_progress.py
key-files.modified:
  - src/coursepilot/reporter.py
  - src/coursepilot/cli.py
key-decisions:
  - "D-16-05: 3-tier visual hierarchy with [1] summary table, [2] this week action items, [3] past weeks alert or all-clear panel."
  - "D-16-06: Color-coded progress bar and percentage style (100% green, 80-99% blue, 50-79% yellow, <50% red)."
  - "D-16-07: Prioritized To-Do activities with [VOD], [과제], [퀴즈], [자료] color tags and completed items trailing."
  - "D-16-08: Conditional rendering of red warning panel on missed past items vs green All Clear badge when 0 missed."
  - "D-16-09: Single entry point `coursepilot progress` CLI command with flags."
  - "D-16-10: 1~16 week matrix roadmap table when querying specific course (--course)."
  - "D-16-11: Expanded individual activity details on --detail."
  - "D-16-12: Standard JSON contract output with schema_version: 1 on --json."
  - "D-16-13: Single-trip course home extraction to minimize network requests."
  - "D-16-14: 10-minute TTL atomic file cache with --cached and --refresh."
  - "D-16-15: Complete stream separation: stderr for progress callbacks, stdout exclusively for reports/JSON."
  - "D-16-16: Per-course try-except error isolation preventing single failure from crashing dashboard."
requirements:
  - PROG-01
  - PROG-02
coverage:
  - deliverable: "Single-trip HTML scraping and atomic file cache"
    human_judgment: false
    verification:
      kind: test
      ref: "tests/test_progress_runner.py#test_load_save_progress_cache"
      status: pass
  - deliverable: "Per-course error isolation"
    human_judgment: false
    verification:
      kind: test
      ref: "tests/test_progress_runner.py#test_progress_runner_course_error_isolation"
      status: pass
  - deliverable: "3-tier Rich terminal dashboard layout"
    human_judgment: false
    verification:
      kind: test
      ref: "tests/test_progress_reporter.py#test_render_progress_dashboard_sections"
      status: pass
  - deliverable: "Weekly course matrix roadmap"
    human_judgment: false
    verification:
      kind: test
      ref: "tests/test_progress_reporter.py#test_render_course_matrix"
      status: pass
  - deliverable: "Click CLI progress command and stream separation"
    human_judgment: false
    verification:
      kind: test
      ref: "tests/test_cli_progress.py#test_cli_progress_stream_separation"
      status: pass
  - deliverable: "schema_version: 1 JSON contract validation"
    human_judgment: false
    verification:
      kind: test
      ref: "tests/test_cli_progress.py#test_cli_progress_json_contract"
      status: pass
---

# Phase 16 Plan 02 Summary: Progress Pipeline Runner, 3-Tier Dashboard, and CLI Command

## Key Achievements
1. **Pipeline Runner (`runner.py`)**:
   - Single-trip course home scraping collecting VODs, materials, sections metadata, ublogs, and assessments.
   - Atomic 10-minute TTL caching (`progress_cache.json`) via `.tmp` file replacement.
   - Per-course independent error isolation with `status="partial_success"` when individual courses fail.
2. **3-Tier Visual Terminal Dashboard (`reporter.py`)**:
   - Tier 1: Summary table with color-coded completion rates, counts, and 4-tier activity breakdown.
   - Tier 2: This week action items table prioritizing incomplete To-Do tasks by deadline with colored tags (`[VOD]`, `[과제]`, `[퀴즈]`, `[자료]`).
   - Tier 3: Conditional Alert panel (`⚠️`) on past missed items vs green All-Clear badge (`🎉`) when zero missed items exist.
   - 1~16 week matrix roadmap table when specifying `--course`.
3. **CLI Integration (`cli.py`)**:
   - Registered `coursepilot progress` command with `--course`, `--week`, `--detail`, `--cached`, `--refresh`, `--json`, `--relogin`, and `--headed`.
   - Strict stdout/stderr separation guaranteeing zero spinner noise in stdout JSON contract.
   - Exit codes aligned with assistant standard (0 for clean, 1 for missed items or errors, 2 for fatal exceptions).

## Verification
- `uv run pytest tests/test_progress_models.py tests/test_progress_calculator.py tests/test_progress_runner.py tests/test_progress_reporter.py tests/test_cli_progress.py`: 32 passed.
- Entire project test suite: 395 passed in 13.77s.
