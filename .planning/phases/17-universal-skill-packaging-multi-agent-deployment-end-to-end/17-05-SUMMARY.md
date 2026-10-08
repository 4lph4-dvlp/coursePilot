---
phase: 17-universal-skill-packaging-multi-agent-deployment-end-to-end
plan: "05"
subsystem: agent-skill
tags: [agent-skill, routing, windows, evidence, progress-json]
requires: [{phase: "17-03", provides: five-agent linked deployment}]
provides: [bounded fresh-session route probe, exact command evidence, compact progress JSON, repaired short-prompt routing]
affects: [17-04]
plan_head_before: b3c513a95d3696e4830abf9383c065fcb54fc8b4
actuals: {tokens: 18000, tasks: 3, commits: 3}
tech-stack:
  added: []
  patterns: [privacy-limited route observations, explicit progress summary view]
key-files:
  created: [scripts/probe_phase17_agent_routes.py, tests/test_phase17_agent_routes.py]
  modified: [scripts/verify_phase17_evidence.py, skills/coursepilot/SKILL.md, src/coursepilot/cli.py, src/coursepilot/progress/models.py, .planning/phases/17-universal-skill-packaging-multi-agent-deployment-end-to-end/17-E2E-EVIDENCE.md]
key-decisions:
  - "Count a fresh agent route only after skill activation, exact command, valid CLI JSON, exit/result, and final response are observed."
  - "Use a compact progress JSON view for short prompts while preserving the existing full report."
  - "Record Codex danger-full-access and Antigravity headless CLI as the tested surfaces; retain their narrower scope in the evidence."
requirements-completed: [SKIL-04, VERIF-03]
coverage:
  - id: route-probe
    description: "Fresh-session probe distinguishes exact command and result while excluding private output"
    requirement: SKIL-04
    verification:
      - kind: unit
        ref: "uv run pytest -q tests/test_phase17_agent_routes.py tests/test_phase17_evidence.py"
        status: pass
    human_judgment: false
  - id: compact-progress
    description: "Compact progress JSON preserves course rates, counts, and overdue exit semantics"
    requirement: SKIL-04
    verification:
      - kind: unit
        ref: "tests/test_cli_progress.py#test_cli_progress_compact_json_keeps_counts_and_omits_activity_lists"
        status: pass
    human_judgment: false
  - id: agent-routes
    description: "All 15 exact bare prompts return the expected CoursePilot command and valid JSON in fresh sessions"
    requirement: VERIF-03
    verification:
      - kind: e2e
        ref: "17-E2E-EVIDENCE.md; uv run python scripts/verify_phase17_evidence.py --section agents"
        status: pass
    human_judgment: true
    rationale: "External agent execution was observed through configured runtime surfaces; the validator checks the recorded evidence but cannot replay every external session."
duration: 3d
completed: 2026-10-08
status: complete
---

# Phase 17 Plan 05: Agent Routing Gap Closure Summary

Fresh bare `진도율`, `공지`, and `Q&A` prompts reached the intended CoursePilot command and valid JSON across Claude Code, Codex, Antigravity CLI, Pi, and Hermes.

## Accomplishments

- Added bounded, privacy-limited fresh-session diagnostics and strict evidence validation; known wrong commands and missing CLI results cannot pass.
- Repaired Windows launcher argument handling in the probe, documented Codex's working diagnostic sandbox and Hermes's persistent skill discovery setting, and verified all 15 routes.
- Added `progress --json --compact` to keep the report inside agent tool output budgets while retaining per-course progress counts and rates.

## Task Commits

1. Routing probe and evidence validator: `66a2c40`
2. Launcher and browser diagnosis: `1f19b41`
3. Short-prompt routing, compact report, and refreshed evidence: `0f736d8`

## Checks Run

- `uv run pytest -q --basetemp .pytest_tmp_phase17_05_closure_full`: 489 passed.
- `uv run python scripts/verify_phase17_evidence.py --section deployment|live|agents`: each section passed with zero unmet checks (run separately).
- `git diff --check`: passed.
- Every claimed route was compared to a fresh skill, command, result, and final-response observation. The ledger stores counts and sanitized outcomes only.

## Decisions Made

- `progress` keeps its full JSON view; the skill uses the summary view for short progress prompts and can request details separately.
- Codex's `workspace-write` child setup error remains host-specific. Its recorded LMS passes used `danger-full-access` for read-only queries.
- Antigravity was tested via authenticated headless CLI after the user reported usage was available; its IDE UI was not observed.

## Deviations from Plan

- Added the compact progress contract and conditional setup guidance after agent tool output limits and unconditional `uv sync` disrupted fresh-session tests. Both changes were necessary to complete route verification.
- Used the now-available Antigravity headless CLI instead of leaving its rows unverified after the user lifted the earlier usage constraint.

## Issues Encountered

- Codex `workspace-write` child commands still fail before process start with `helper_unknown_error: setup refresh had errors`; the tested unrestricted child setting and exact limitation are recorded.
- Hermes required persistent `skills.auto_load`; the previous user config was backed up before the setting was added.

## User Setup Required

None for this verified machine. Hermes auto-load and the Antigravity CLI skill link are local user settings documented in the evidence.

## Next Phase Readiness

Plan 17-04 can run its final evidence gate. Phase 17 remains open until that plan passes and receives its own SUMMARY.

## Self-Check: PASSED

- All three task acceptance criteria and the plan-level verification passed; the three production commits above exist.
