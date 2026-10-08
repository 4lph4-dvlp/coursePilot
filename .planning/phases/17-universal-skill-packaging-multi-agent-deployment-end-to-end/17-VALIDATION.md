---
phase: "17"
slug: "universal-skill-packaging-multi-agent-deployment-end-to-end"
status: complete
nyquist_compliant: true
wave_0_complete: true
created: "2026-10-04"
---

# Phase 17 — Validation Strategy

## Test Infrastructure

| Property | Value |
|---|---|
| Framework | pytest via `uv run` |
| Config file | `pyproject.toml` |
| Quick run command | `uv run pytest tests/test_contract_doc.py tests/test_installer.py -q` |
| Full suite command | `uv run pytest -q` |
| Estimated runtime | Measure during execution; no unverified estimate |

## Sampling Rate

- After each contract or installer task: run its targeted test module.
- After the offline implementation wave: run `uv run pytest -q` once.
- Before phase verification: rerun the full suite only if later changes touched code or tests.
- Live checks and agent session checks are separate evidence gates; a green pytest run does not replace them.

## Per-Task Verification Map

| Task | Requirement | Test type | Automated command | File exists | Status |
|---|---|---|---|---|---|
| Contract tracer and expansion | SKIL-04 | Contract and model validation | `uv run pytest tests/test_contract_doc.py -q` | Yes | passed in full suite |
| Installer batch and link guards | SKIL-04 | Fake-home unit/integration | `uv run pytest tests/test_installer.py -q` | Yes | passed in full suite |
| Existing integration regression | SKIL-04, VERIF-03 | Full suite | `uv run pytest -q` | Yes | 489 passed |
| Evidence ledger validator | SKIL-04, VERIF-03 | Automated evidence completeness | `uv run pytest tests/test_phase17_evidence.py -q` | Yes | passed in full suite |
| Agent routing gap probe | SKIL-04, VERIF-03 | Fake-event parser and bounded runtime diagnostics | `uv run pytest tests/test_phase17_agent_routes.py tests/test_phase17_evidence.py -q` | Yes | passed in full suite |
| Live LXP and agent routing | VERIF-03 | Live/manual observation plus deterministic ledger check | `uv run python scripts/verify_phase17_evidence.py --section live` and `--section agents` | Yes | passed, unmet=0 |

## Wave 0 Requirements

Existing pytest infrastructure covers the contract and installer requirements. Plan 04 creates `scripts/verify_phase17_evidence.py` and its fixture tests before the live evidence tasks run.

## Manual-Only Verifications

| Behavior | Requirement | Why manual | Test instructions |
|---|---|---|---|
| Five live agent routing sessions | SKIL-04 | Runtime availability and skill activation depend on installed agents | Plan 17-05 recorded all 15 separate fresh-session routes after the user confirmed Antigravity usage was available. Antigravity was exercised through its headless CLI; Codex used `danger-full-access` for read-only queries because Windows `workspace-write` setup failed. |
| All enrolled course read-only sweep | VERIF-03 | Live LXP content and enrollment vary | Run `check`, `progress`, `notices`, `qna` against every enrolled course and record per-course success/failure counts. |
| Material, VOD, and short watch | VERIF-03 | File creation and playback require live LXP | Preview, select one representative item of each kind, verify actual saved files, start/status/stop one watch, clean only smoke-created files. |
| Scheduler preview | VERIF-03 | Real Notion read path is environmental | Read through independent package, preview CoursePilot `sync` and watch-completion, confirm zero create/update calls. |

## Validation Sign-Off

- [x] Contract and installer targeted tests pass.
- [x] Full suite passes after offline implementation (489 tests).
- [x] All five agent paths and 15 available runtime routes are individually evidenced within their recorded execution surfaces.
- [x] Live LXP sweep covers the eight courses enrolled at the final gate.
- [x] Downloaded material and VOD files existed and matched reported results in the earlier Phase 17 smoke run.
- [x] Watch was stopped and Notion create/update count is zero.
- [x] `nyquist_compliant: true` after execution evidence is complete.

**Approval:** Phase execution evidence verified on 2026-10-08; runtime limits are scoped in the evidence ledger.
