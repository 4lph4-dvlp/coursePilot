---
phase: 05-cli-reporting-antigravity-skill-packaging
plan: 05
subsystem: packaging
tags: [json-contract, docs, live-evidence, install-skill, agent-skills, pydantic]

# Dependency graph
requires:
  - phase: 05-cli-reporting-antigravity-skill-packaging
    provides: "05-01..05-04's check/sync commands, report_models.py contract v1, installer.py AGENT_SKILL_PATHS/install_skill, skills/coursepilot/SKILL.md"
provides:
  - "05-LIVE-EVIDENCE.md: real, redacted check/sync run from a foreign cwd, with a documented ConfigError blocker (D-26 partially unmet — see Deviations)"
  - "skills/coursepilot/JSON_CONTRACT.md: full field/enum/versioning reference for CheckReport/SyncReport v1, validated example payloads (D-13)"
  - "README.md: Korean setup guide, commands/exit-code tables, and per-agent install table for all 5 AGENT_SKILL_PATHS agents (D-20)"
  - "PROJECT.md 동작 방식 rewritten to the universal-skill flow (D-24)"
  - "tests/test_contract_doc.py: 4 tests keeping JSON_CONTRACT.md/README.md/SKILL.md honest against report_models.py and installer.py"
  - "coursepilot skill installed (copy mode) into all five real agent home folders on this machine; 05-AGENT-SKILL-EVIDENCE.md staged for the end-of-phase human invocation check (D-27)"
affects: [phase-verification, gsd-ship]

actuals:
  tokens: 11057
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Recursive Pydantic field-name collection (typing.get_args unwrap + model_fields walk) to mechanically keep a hand-written Markdown contract doc honest against the live Pydantic models, rather than hand-maintaining a field list that can silently drift"
    - "Live-run precondition gap handling: when a task's own <verify> requires real external success (course_count >= 1) and the real environment returns a genuine ConfigError, record truthfully and stop rather than retry or fabricate — matches the plan's own explicit 'record the error code, keep the markers truthful... and report the blocker' instruction for this exact scenario"

key-files:
  created:
    - .planning/phases/05-cli-reporting-antigravity-skill-packaging/05-LIVE-EVIDENCE.md
    - .planning/phases/05-cli-reporting-antigravity-skill-packaging/05-AGENT-SKILL-EVIDENCE.md
    - skills/coursepilot/JSON_CONTRACT.md
    - tests/test_contract_doc.py
    - .planning/WINDOWS.md
  modified:
    - skills/coursepilot/SKILL.md
    - README.md
    - .planning/PROJECT.md

key-decisions:
  - "Task 1's live check/sync run genuinely hit a ConfigError (.env's LMS_USERNAME/LMS_PASSWORD are empty) rather than a fabricated or retried result -- recorded truthfully in 05-LIVE-EVIDENCE.md exactly as the task's own action text anticipates for a check-exits-2 outcome ('keep the markers truthful... report the blocker'), and not retried against the live LMS per this execution's explicit instruction"
  - "Proceeded to Task 2 and Task 3 after Task 1's real-world precondition gap, rather than halting the whole plan -- Task 2 (contract doc/README/PROJECT.md/tests) and Task 3 (install-skill across 5 agents) do not build on Task 1's live-run output at all; they depend only on already-tested 05-01..05-04 code, so there is no 'broken foundation' for them to layer onto"
  - "Recorded the D-26 gap as an open 'unmet-truth' entry in .planning/WINDOWS.md (not silently dropped) so it stays visible through phase verification and /gsd-ship until the user fills real LMS credentials and the live run is repeated"
  - "JSON_CONTRACT.md's field-completeness test walks report_models.py's Pydantic models recursively (typing.get_args + model_fields) instead of hand-listing field names in the test, so the test catches future field additions to CheckReport/SyncReport automatically"

patterns-established:
  - "Pattern: any future hand-written doc that must stay in sync with a Pydantic model's fields should be checked by a recursive model_fields walk in a test, not a hand-maintained field list"

requirements-completed: [SKIL-01, SKIL-02, SKIL-03]

coverage:
  - id: D1
    description: "Real check --json and dry-run sync --json were run against the live LMS/Notion from a foreign cwd via uv --directory; both surfaced a genuine ConfigError (empty LMS_USERNAME/LMS_PASSWORD in .env) rather than collecting real course data, recorded truthfully with no secrets/raw payloads/task titles"
    requirement: SKIL-01
    verification:
      - kind: manual_procedural
        ref: ".planning/phases/05-cli-reporting-antigravity-skill-packaging/05-LIVE-EVIDENCE.md"
        status: fail
    human_judgment: true
    rationale: "The task's own automated <verify> requires check exit code 0 or 1 and summary.course_count >= 1; the real run genuinely returned exit 2 / course_count 0 due to an unfilled .env precondition outside code's control. A human must fill real LMS credentials and re-run before this truth can be proven; this is not a code defect to auto-fix."
  - id: D2
    description: "The Notion Scheduler write audit (independent read-only page-count probe) shows 62 pages before and 62 after the live run, with zero create/update calls and no --apply invocation anywhere in this evidence"
    requirement: SKIL-02
    verification:
      - kind: manual_procedural
        ref: ".planning/phases/05-cli-reporting-antigravity-skill-packaging/05-LIVE-EVIDENCE.md#write-audit"
        status: pass
    human_judgment: false
  - id: D3
    description: "skills/coursepilot/JSON_CONTRACT.md documents every field of CheckReport/SyncReport v1 (13 models), exit codes, versioning rule, enum values, and datetime format; SKILL.md points to it; example payloads validate via model_validate"
    requirement: SKIL-01
    verification:
      - kind: unit
        ref: "tests/test_contract_doc.py#test_json_contract_doc_lists_every_field"
        status: pass
      - kind: unit
        ref: "tests/test_contract_doc.py#test_json_contract_doc_examples_validate"
        status: pass
      - kind: unit
        ref: "tests/test_contract_doc.py#test_json_contract_skill_md_points_to_contract"
        status: pass
    human_judgment: false
  - id: D4
    description: "README.md documents setup (uv, playwright, .env keys named not shown), commands/exit codes, Notion dry-run safety, and a per-agent install table for all 5 AGENT_SKILL_PATHS agents with install command, install path, and status"
    requirement: SKIL-03
    verification:
      - kind: unit
        ref: "tests/test_contract_doc.py#test_json_contract_readme_lists_every_agent"
        status: pass
    human_judgment: false
  - id: D5
    description: "PROJECT.md Active/Context sections describe a universal Agent Skill for all supported agents; ROADMAP.md/REQUIREMENTS.md already carried the universal wording from an earlier commit"
    requirement: SKIL-03
    verification:
      - kind: other
        ref: "grep -c '범용 Agent Skill' .planning/PROJECT.md (2), grep -c 'Universal Agent Skill Packaging' .planning/ROADMAP.md (3), grep -c '에이전트 중립' .planning/REQUIREMENTS.md (1)"
        status: pass
    human_judgment: false
  - id: D6
    description: "install-skill ran for all five agents in copy mode; each installed SKILL.md is present with the repo path resolved (no {{COURSEPILOT_REPO}} placeholder) and JSON_CONTRACT.md alongside; 05-AGENT-SKILL-EVIDENCE.md has one row per agent with install exit 0 and smoke PASS, staged for the human invocation results"
    requirement: SKIL-03
    verification:
      - kind: other
        ref: "task 3 automated <verify>: bad=[], exit 0; manual smoke inspection of all 5 resolve_install_target(agent) directories"
        status: pass
    human_judgment: false
  - id: D7
    description: "Every supported agent triggers the coursepilot skill on natural-language requests ('과제 확인해줘', '노션에 올려줘') and follows the D-16/D-17 briefing/approval-gate contract"
    requirement: SKIL-03
    verification: []
    human_judgment: true
    rationale: "Skill discovery and natural-language triggering happen inside five separate agent runtimes that cannot be driven from this repository; only the student can compare the briefing with their own LMS view. Staged in 05-AGENT-SKILL-EVIDENCE.md as 'pending (human)' per workflow.human_verify_mode=end-of-phase."

duration: ~16min
completed: 2026-09-23
status: complete
---

# Phase 5 Plan 5: End-to-End Phase Closure — Live Evidence, JSON Contract, README, and Five-Agent Install Summary

**Ran the real `check`/`sync` CLI against the live LMS and Notion (surfacing a genuine, previously-undetected `.env` credentials gap rather than a code defect), documented the full JSON contract v1 and per-agent README install guide, updated PROJECT.md's universal-skill wording, and installed `coursepilot` into all five real agent home folders on this machine.**

## Performance

- **Duration:** ~16 min
- **Started:** 2026-09-23T04:44Z (session start, immediately after 05-04)
- **Completed:** 2026-09-23T04:58:52Z
- **Tasks:** 3 (1 tracer + 2 auto)
- **Files created:** 5; **Files modified:** 3

## Accomplishments

- **Live evidence (Task 1, tracer):** Ran `uv run pytest` (178 baseline passed) then real `check --json` and `sync --json` from an OS-temp scratch folder outside the repo via `uv --directory "<repo>" run python -m coursepilot ...`. Both genuinely exited `2` with `ConfigError` — `.env`'s `LMS_USERNAME`/`LMS_PASSWORD` are empty (the file exists, satisfying the task's file-existence-only precondition, but its LMS credential values were never filled in). Recorded this truthfully in `05-LIVE-EVIDENCE.md` exactly as the task's action text anticipates for this scenario ("keep the markers truthful... report the blocker"), including: schema_version/exit codes/summary counts/error scopes-codes from the real JSON, all three section headings confirmed present in the non-JSON Rich render, an independent read-only Notion page-count write-audit (62 before / 62 after, zero writes, no `--apply` anywhere), and the foreign-cwd invocation confirmation. The task's own automated `<verify>` fails as designed for this scenario (requires exit 0/1) — not retried against the live LMS. The D-26 gap is recorded as an open `unmet-truth` entry in the new `.planning/WINDOWS.md`.
- **JSON contract v1 doc (Task 2):** `skills/coursepilot/JSON_CONTRACT.md` documents the versioning rule, invocation/stream rules, exit codes, one field table per all 13 `report_models.py` models (types, nullability, meaning from class docstrings), enum values (`ErrorItem.scope`/codes including `duplicate_incoming_title`/`duplicate_existing_title`/`malformed_existing_page`, `SyncSkipItem.reason`), ISO-8601+KST datetime format, and one validated example payload each for `check`/`sync`. `SKILL.md`'s 실행 규칙 section now points to it.
- **README.md (Task 2):** Full Korean rewrite — overview, requirements (Python 3.11+, uv), setup (`uv sync`, `playwright install chromium`, `.env` keys named but never shown), commands + exit-code tables, Notion dry-run safety, a per-agent install table for all five `AGENT_SKILL_PATHS` agents (install command, example path, status), the restart/new-session note, and a `--link` dev-mode note covering the Windows junction fallback and its loud both-fail behavior.
- **PROJECT.md (Task 2):** Context's 동작 방식 line rewritten to describe the universal `SKILL.md`/`install-skill`/`--json` flow across all five agents (D-24); confirmed `ROADMAP.md`'s Phase 5 heading and `REQUIREMENTS.md`'s SKIL-03 already carried the universal wording from an earlier commit (no edit needed).
- **tests/test_contract_doc.py (Task 2):** 4 new tests — a recursive `model_fields` walk over `CheckReport`/`SyncReport` confirms every field name (including nested models) is backtick-documented in the contract doc; both example JSON payloads in the doc validate via `model_validate`; README lists every `AGENT_SKILL_PATHS` agent id and its `skills_dir` path; SKILL.md mentions `JSON_CONTRACT.md`.
- **Five-agent install (Task 3):** `install-skill --agent {claude,codex,antigravity,pi,hermes}` ran in copy mode (never `--link`) from the repository against this machine's real agent home folders — all five exited 0. Verified for each: no `{{COURSEPILOT_REPO}}` placeholder remains, the absolute repo root is resolved into the installed `SKILL.md`, `JSON_CONTRACT.md` is present alongside, and `repo-root.txt` holds the repo root (task's automated `<verify>`: `bad=[]`, exit 0). Confirmed the foreign-cwd smoke check (`--help` from the scratch folder, exit 0). `05-AGENT-SKILL-EVIDENCE.md` records path-evidence confidence levels per agent, install exit, smoke PASS, and "pending (human)" invocation columns, plus "How to verify" and "Corrections" sections, staged for the end-of-phase UAT per `workflow.human_verify_mode = end-of-phase`.

## Task Commits

Task 1 was `type="tracer"` (single commit; its own `<verify>` fails on this run because the real LMS environment returned a genuine `ConfigError` — documented truthfully per the plan's explicit instructions for this scenario, not retried). Tasks 2 and 3 were `type="auto"`:

1. **Task 1: Live check/sync evidence (ConfigError blocker documented)** - `197dc38` (docs)
2. **Task 2: JSON contract doc, SKILL.md pointer, README, PROJECT.md wording, contract tests** - `fb53989` (feat)
3. **Task 3: Five-agent install + D-27 invocation evidence staging** - `72984f9` (docs)

**Plan metadata:** committed after this SUMMARY.

## Files Created/Modified

- `.planning/phases/05-cli-reporting-antigravity-skill-packaging/05-LIVE-EVIDENCE.md` - Real check/sync evidence with a documented ConfigError blocker
- `.planning/phases/05-cli-reporting-antigravity-skill-packaging/05-AGENT-SKILL-EVIDENCE.md` - Per-agent install/smoke table, staged D-27 human-check
- `.planning/WINDOWS.md` - New cross-phase defect ledger; opened with the D-26 unmet-truth entry
- `skills/coursepilot/JSON_CONTRACT.md` - Full JSON contract v1 field/enum/versioning reference
- `skills/coursepilot/SKILL.md` - Added a pointer line to JSON_CONTRACT.md
- `README.md` - Full Korean rewrite: setup, commands, exit codes, Notion safety, per-agent install table
- `.planning/PROJECT.md` - 동작 방식 line rewritten to the universal-skill flow
- `tests/test_contract_doc.py` - 4 tests keeping the doc/README/SKILL.md honest against the models/installer

## Decisions Made

- Task 1's live run genuinely hit a `ConfigError` (empty `LMS_USERNAME`/`LMS_PASSWORD` in `.env`) rather than a fabricated pass — recorded truthfully, not retried against the live LMS, exactly matching the plan's own explicit instructions for a `check exit code 2` outcome.
- Proceeded to Tasks 2 and 3 after Task 1's real-world precondition gap rather than halting the whole plan, since neither task builds on Task 1's live-run output — both depend only on already-tested 05-01..05-04 code paths.
- Recorded the D-26 gap as an open `unmet-truth` entry in the new `.planning/WINDOWS.md` so it stays visible through phase verification and `/gsd-ship` rather than being silently dropped.
- `JSON_CONTRACT.md`'s field-completeness test walks `report_models.py`'s Pydantic models recursively instead of hand-listing field names, so it automatically catches future field additions.

## Deviations from Plan

### Auto-fixed Issues

None — no Rule 1-3 auto-fixes were needed; all code touched in this plan (`report_models.py`, `installer.py`, `cli.py`) is from prior plans and was not modified here.

### Documented Blocker (not a Rule 1-4 deviation — an unmet external precondition)

**1. D-26 live evidence: `check`/`sync` exit 2 (`ConfigError`) instead of collecting real course data**
- **Found during:** Task 1 (live end-to-end run)
- **Issue:** `.env` exists (the task's precondition check is file-existence-only) but its `LMS_USERNAME`/`LMS_PASSWORD` values are empty, so the real LMS session never starts
- **Handling:** Recorded truthfully in `05-LIVE-EVIDENCE.md` per the plan's own explicit instructions for this exact scenario; not retried against the live LMS; task's own `<verify>` fails as designed; gap tracked as an open entry in `.planning/WINDOWS.md`
- **Files:** `.planning/phases/05-cli-reporting-antigravity-skill-packaging/05-LIVE-EVIDENCE.md`
- **Resolution required:** the user must fill real LMS credentials into `.env` and the live check/sync run must be repeated to close D-26

---

**Total deviations:** 0 auto-fixed. **1 documented, unresolved external precondition gap** (D-26, tracked in WINDOWS.md, requires user action outside this executor's control).
**Impact on plan:** Tasks 2 and 3 fully completed independent of the gap. D-26's "real course-count >= 1" truth remains unproven until real LMS credentials are supplied.

## Issues Encountered

None beyond the documented D-26 blocker above.

## User Setup Required

**`.env`'s `LMS_USERNAME` and `LMS_PASSWORD` need to be filled in with the real KAU LXP student ID and password before a clean D-26 live-evidence run can be captured.** No other external service configuration is required — Notion was already configured and reachable (the read-only Scheduler page-count probe succeeded: 62 pages, unchanged).

## Next Phase Readiness

- All Phase 5 artifacts required by the ROADMAP success criteria are in place: `check`/`sync`/`install-skill` CLI, versioned JSON contract v1 + doc, Rich briefing, README per-agent guide, and the skill installed into all five real agent home folders on this machine.
- **Blocker for full D-26 closure:** real LMS credentials must be filled into `.env`, after which `check --json`/`sync --json` should be re-run from a foreign cwd and `05-LIVE-EVIDENCE.md` updated (or a follow-up verification step run) to replace the `ConfigError` result with real course/assignment data.
- **Pending human action for D-27:** the five per-agent natural-language invocation checks in `05-AGENT-SKILL-EVIDENCE.md` are staged but unanswered — a human must run them in a new session per agent, outside this repository, and record the results (or path corrections) before phase verification can close SKIL-03 end to end.
- `.planning/WINDOWS.md` (new) currently has one open entry (D-26 unmet-truth); it should be resolved or explicitly waived before `/gsd-ship`.

## Self-Check: PASSED

- FOUND: .planning/phases/05-cli-reporting-antigravity-skill-packaging/05-LIVE-EVIDENCE.md
- FOUND: .planning/phases/05-cli-reporting-antigravity-skill-packaging/05-AGENT-SKILL-EVIDENCE.md
- FOUND: skills/coursepilot/JSON_CONTRACT.md
- FOUND: tests/test_contract_doc.py
- FOUND: .planning/WINDOWS.md
- FOUND commits: 197dc38, fb53989, 72984f9
- `uv run pytest -q tests/test_contract_doc.py -x` green (4 tests)
- `uv run pytest` green (full suite, 182 tests)
- Task 1's own automated `<verify>` FAILS (exit 2, real ConfigError) — documented as an intentional, plan-anticipated outcome, not a self-check failure

---
*Phase: 05-cli-reporting-antigravity-skill-packaging*
*Completed: 2026-09-23*
