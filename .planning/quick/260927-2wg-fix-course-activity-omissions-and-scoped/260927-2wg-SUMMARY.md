---
quick_id: 260927-2wg
status: complete
completed: 2026-09-27
execution: inline-codex-adapter
---

# Complete course inventories and scoped preparation

Implemented the user's approved diagnosis through alpha-AOS and GSD quick --validate. Capability inspection was CURRENT; no capability installation, model switch or subagent dispatch occurred. Plan checking, execution and verification ran inline under the Codex adapter.

## Delivered

- Dashboard courses resolve to the full sections view; current and legacy activities share title, source module, section week, completion, dates and availability parsing. Unsupported supported-activity layouts fail explicitly and per-course errors preserve other courses.
- Check/sync include material tasks, support complete-item inventory and repeated course/week selections, and store a preparation target separately from official deadlines and protected Notion Plan/status.
- Stable LMS URL identity matches existing Notion pages before legacy-title fallback; ambiguous sources/titles fail closed and completed LMS items are skipped.
- Progress uses the correct completion report, supports material date fields and carries source module IDs. Unreleased activities are inventoried but are not automatically watched or visited/downloaded.
- Hermes/pi skill junctions both target the edited repository skill. Guidance requires explicit preparation scope, actual section weeks, fresh CLI JSON, error handling and identical preview/apply selection.

## Task commits

1. `6fb94f4` — full sections collection, normalized metadata, progress repair and unreleased-activity guards.
2. `4d01fff` — material scheduling, supported scope/goal flags, source deduplication and 14 regression cases.
3. `25b18a6` — application skill/JSON contract and README.

Existing pi changes in materials/runner.py (CourseNavigator configuration and CourseItem argument) were preserved and included because the repaired materials path depends on them. No unrelated user edits were reverted.

## Verification

- Initial suite: 395 passing. Final suite: **409 passing**, 13.23 seconds, `uv run --extra dev python -m pytest -o addopts= -q --disable-warnings`.
- Fresh live scoped check: seven courses attempted, exact **18 source modules**, **17 incomplete**, completed math material 2847, zero errors, exit 0.
- Fresh Notion dry-run for the identical scope: **13 create, 4 update, 1 skip, 0 errors**; `dry_run=true`, `applied=false`, exit 0. Skip reason: lms_completed for material 2847.
- Fresh `progress --refresh --json`: all seven courses status ok, zero collection errors, all 18 baseline source modules present. Overall status success. Existing exit 1 is caused by 15 missed-past activities, not collection failure; documented without changing that policy.
- Fresh `materials --dry-run --week all --json`: 43 planned materials, no failures, baseline five material IDs present, exit 0. The existing dry-run DTO labels plans downloaded; this is not evidence of actual download/view completion (view_success=false).
- Git diff whitespace check passed. Codex, Hermes and pi skill junctions point to skills/kau-lxp. No Notion mutations, lecture watching, material viewing or downloads were performed.

## Scope and resume

This quick task is complete. Phase 17 remains pending at its existing context-gathered boundary; it is not marked complete by this fix. Actual scheduler application requires a separate approved `sync --apply` invocation with the same selectors. Live state can change, so future agents must collect fresh stdout rather than reuse this evidence.
