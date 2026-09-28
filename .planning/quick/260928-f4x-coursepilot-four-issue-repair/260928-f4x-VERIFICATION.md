---
quick_id: 260928-f4x
status: passed_with_external_limit
verified: 2026-09-28
---

# Verification

| Requirement | Evidence | Result |
|---|---|---|
| Material 2847 is visible and its two states are distinct | Fresh live `check --include-completed --course-week 공학수학II:4 --json`: one module 2847 material, `is_completed=true`, no due date, zero errors. Fresh `materials --dry-run` returns `planned`, zero downloaded/viewed. | Passed |
| Real module handling is truthful | Actual `materials --course 공학수학II --week 4 --json`: exit 0, `viewed_only`, `view_success=true`, `downloaded_count=0`, `failed_count=0`, empty `saved_path`. The LMS redirects its viewer to `/local/csmsdoc/` and exposes no original file link. | Passed with external file limit |
| Paths stay under one root | Relative session, mapping, and download paths resolve to the CoursePilot project root; debug and board state defaults are anchored there. CWD variation is covered by `test_relative_storage_overrides_use_project_root`. | Passed |
| Short titles and safe migration | Current course aliases are tested; duplicate course/week labels are removed. Source matched title updates and collision refusal are covered by focused tests. | Passed |
| One Scheduler route | Original Phase 04 plan and current code both use `.env` token + notion-client SDK. Skill now routes sync and retroactive completion through CLI. Hermes skill junction points to this repository skill. Live Scheduler preview reported `dry_run=true`, `applied=false`, zero errors; the selected scope had zero actions. | Passed; no live rename proven |
| Full regression | `uv run --extra dev python -m pytest -o addopts= -q --disable-warnings` | 426 passed |

No Notion write or replacement title was applied. The original CSMSDoc file is not available through a download link; no local file was created. The empty ignored download directory from the first smoke attempt was left in place because automatic approval review blocked its removal. Pre-existing `src/coursepilot/player/runner.py` changes and root output files were not staged.
