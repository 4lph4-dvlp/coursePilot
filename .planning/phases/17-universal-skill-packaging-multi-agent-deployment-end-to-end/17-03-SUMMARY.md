---
phase: 17-universal-skill-packaging-multi-agent-deployment-end-to-end
plan: "03"
subsystem: installer
tags: [agent-skill, links, windows, batch]
requires: [{phase: "17-01", provides: linked source documentation}]
provides: [five-agent linked deployment, per-target outcomes, optional Scheduler visibility]
affects: [17-04]
actuals: {tokens: 4700, tasks: 2, commits: 2}
tech-stack: {added: [], patterns: [independent per-target install attempts]}
key-files:
  created: []
  modified: [src/coursepilot/installer.py, src/coursepilot/cli.py, tests/test_installer.py, README.md]
key-decisions:
  - "Batch mode skips absent agent homes and preserves foreign targets."
  - "A successful link must resolve to this checkout and expose both skill docs."
requirements-completed: [SKIL-04]
coverage:
  - id: batch-install
    description: "Five-agent batch with skip, failure, and success outcomes"
    requirement: SKIL-04
    verification: [{kind: integration, ref: "tests/test_installer.py#test_batch_mixed_results_preserve_foreign_and_repair_links", status: pass}]
    human_judgment: false
  - id: optional-scheduler
    description: "Optional Scheduler skill is reported separately"
    requirement: SKIL-04
    verification: [{kind: integration, ref: "tests/test_installer.py#test_batch_five_successes_and_optional_scheduler", status: pass}]
    human_judgment: false
duration: 14min
completed: 2026-10-04
status: complete
---

# Phase 17 Plan 03: Five-Agent Link Deployment Summary

The installer now links the current CoursePilot source to every existing agent home and reports each outcome independently.

## Accomplishments
- Added `install-skill --all` with five target rows, summary, and partial exit status.
- Preserved foreign content, replaced prior CoursePilot copies, and repaired broken links.
- Verified both linked documents and reported optional notion-scheduler skill readability.

## Task Commits
1. Batch installer and CLI: `23c63a5`
2. Outcome tests and README: `ab40960`

## Verification
- `uv run pytest tests/test_installer.py tests/test_contract_doc.py -q --basetemp .pytest_tmp_phase17`: 44 passed.

## Deviations from Plan
- Incorporated an existing uncommitted installer junction-order fix because broken-link repair depends on it. The unrelated player change remains untouched.

## Self-Check: PASSED
- Fake-home success, skip, foreign target, broken-link, and CLI tests passed.
