---
phase: 10-watch-pipeline-cli
plan: 01
status: completed
date: 2026-09-25
---

# Plan 10-01 Summary: Watch Pipeline, CLI Runner & Notion Completion Mode

## Overview

Plan 10-01 implemented the end-to-end `watch` runner pipeline and CLI command (`coursepilot watch`). It allows users and agents to target specific courses and weeks, filters for unwatched regular VODs (skipping already-completed and OT lectures), coordinates sequential playback via `VodPlayer`, and optionally updates corresponding Notion Scheduler tasks to '완료' (Done).

## Key Accomplishments

1. **Notion Completion Method (`src/coursepilot/notion/client.py`)**:
   - Added `mark_task_completed(page_id: str)` to safely update a task's `상태` to `완료` while leaving user-managed fields intact.

2. **Watch Runner Pipeline (`src/coursepilot/player/runner.py`)**:
   - `find_target_course`: Resolves course queries via exact name, raw name, course ID, or mapped abbreviation (e.g. `디시설` -> `디지털시스템설계`).
   - `resolve_candidate_vods`: Discovers VODs, filters by target week (`current` selects earliest incomplete regular week, `all`, or numeric week like `4`), excludes 0-week/OT videos, and counts completed videos to skip.
   - `watch_course_vods`: Coordinates course scraping, candidate resolution, sequential playback with progress callbacks, and optional Notion status updates.

3. **CLI Subcommand `watch` (`src/coursepilot/cli.py`)**:
   - Added `coursepilot watch` with `--course`, `--week`, `--update-notion`, `--dry-run`, `--json`, `--relogin`, and `--headed`.
   - Supports Rich console real-time status output as well as structured JSON output.

4. **Testing & Live Verification**:
   - Added unit tests in `tests/test_watch_runner.py` (5 passed).
   - Executed live `--dry-run` on real LXP courses (`기초전자실험`, `디시설` week 4) with zero errors.
   - Full regression suite: 253 passed in 6.64s.

## Verification

- `uv run pytest tests/test_watch_runner.py` (5 passed)
- Full regression suite `uv run pytest` (253 passed)
- Live dry-run tests verified against KAU LXP.
