---
quick_id: 260928-np1
status: complete
completed: 2026-09-28
execution: inline-codex-adapter
---

# Propose Notion completion after watching

Code commit: `074b2cd`.

- Agent watch runs never use `--update-notion`. After playback, the skill reads a `watch sync-notion --dry-run` preview and proposes exact Scheduler titles. A separate approval is required before applying only those titles with repeated `--task-title` options. The explicit direct CLI `watch --update-notion` override remains available.
- Preview does not update Notion or local watch history. Already complete, absent, and ambiguous Scheduler titles are reported separately. Both completion paths now index the actual list returned by the Notion client and exclude duplicate titles.
- Storage documentation distinguishes source checkout root from installed wheel fallback `Path.home() / ".coursepilot"`; relative configured paths are anchored there. Windows was verified, while macOS and Linux paths rely on the portable `pathlib` implementation and were not run live.
- The full 428 test suite passed. A live read-only Scheduler preview succeeded with two planned titles, seven already complete, zero unmatched or ambiguous titles, and zero writes. No Notion apply was performed.

The pre-existing player edit and untracked root output files were preserved. Phase 17 remains pending.
