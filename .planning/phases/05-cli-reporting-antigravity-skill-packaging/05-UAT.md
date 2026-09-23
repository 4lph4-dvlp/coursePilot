---
status: testing
phase: 05-cli-reporting-antigravity-skill-packaging
source: [05-VERIFICATION.md]
started: 2026-09-23T14:15:00Z
updated: 2026-09-23T14:15:00Z
---

## Current Test

number: 1
name: Live check/sync evidence with real LMS credentials (D-26)
expected: |
  After filling real LMS_USERNAME/LMS_PASSWORD into .env, `uv --directory <repo> run python -m kau_assistant check --json`
  run from a folder outside the repository exits 0 or 1 with summary.course_count >= 1 and the three urgency sections
  populated with real course data; `sync --json` exits 0/1 with sync.dry_run=true, sync.applied=false, and an unchanged
  Notion Scheduler page count before/after. 05-LIVE-EVIDENCE.md is updated with the real counts and WINDOWS.md entry 1 is closed.
awaiting: user response

## Tests

### 1. Live check/sync evidence with real LMS credentials (D-26)
expected: check exits 0/1 with course_count >= 1 and real sections; sync dry-run exits 0/1 with dry_run=true, applied=false, unchanged Scheduler page count; evidence updated and WINDOWS.md entry 1 closed.
result: [pending]

### 2. Natural-language skill invocation in all five agents (D-27)
expected: In Claude Code, Codex, Antigravity, Pi, and Hermes (new session, folder outside the repo), "과제 확인해줘" triggers kau-lxp, runs `check --json` via `uv --directory`, and replies with markdown tables ordered 기한 초과 → 24시간 이내 → 이후 일정, grouped by course, untruncated, with links for urgent items; "노션에 올려줘" shows the dry-run create/update/skip lists and asks for approval before any `--apply`. Results recorded in 05-AGENT-SKILL-EVIDENCE.md; wrong AGENT_SKILL_PATHS entries noted under Corrections.
result: [pending]

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps
