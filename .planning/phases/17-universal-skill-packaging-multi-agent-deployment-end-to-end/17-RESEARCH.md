# Phase 17 Research: CoursePilot skill packaging and live verification

**Researched:** 2026-10-04  
**Domain:** Agent skill contract, five-agent deployment, Coursemos LXP smoke testing  
**Confidence:** HIGH for repository behavior; live agent and LXP availability must be checked during execution.

## User Constraints

The following implementation decisions and discretion areas are copied from `17-CONTEXT.md`:

## Implementation Decisions

### Natural-language routing and user briefing

- **D-17-01:** For broad requests such as “이번 주 학업 현황 알려줘”, route to `progress` first. Use `check` when the user explicitly asks about deadlines, assignments, or tasks due.
- **D-17-02:** Route notice requests to `notices`, question or answer requests to `qna`, and broad board requests to `board`. Preserve the board and dashboard presentation decisions from Phases 15 and 16.
- **D-17-03:** After an explicitly requested material or VOD download, report each item's actual outcome and saved path. Distinguish file download success, `viewed_only`, and failure; a planned path is not proof of a file.
- **D-17-04:** If collection failed for any course or an empty result cannot establish completion, warn before the valid briefing. Never describe an unverified zero-item result as “all complete”.

### JSON contract documentation

- **D-17-05:** Give each newly documented command its own section containing invocation, result fields, status interpretation, and examples. Follow the implemented Pydantic models and existing version rules rather than inventing a new envelope. — **Reversibility:** costly — agents and contract tests will depend on the published field meanings.
- **D-17-06:** Include a normal JSON example and relevant caution examples for each command, including cases where an exit code, a partial collection failure, or a planned/view-only download could be misread. Examples must reflect real model validation and status semantics.
- **D-17-07:** Keep general personal Scheduler task fields in the independent `notion-scheduler` contract. The CoursePilot contract explains its academic `sync` and watch-completion results and refers to the independent contract at the responsibility boundary.
- **D-17-08:** Write explanations primarily in Korean while keeping JSON keys, types, and commands verbatim.

### Five-agent CoursePilot skill deployment

- **D-17-09:** A batch deployment continues after an individual agent fails and reports each target's success, skip, or failure with its reason and target path. Do not treat partial success as all-five success.
- **D-17-10:** Deploy the CoursePilot skill as links to its source directory. Replace a verified prior CoursePilot copy with a link, but leave any foreign skill at the target untouched. — **Reversibility:** costly — installed agent directories and source-location assumptions depend on the link strategy.
- **D-17-11:** If an agent's home/skill directory does not yet exist, skip that agent and explain why. Do not create a home preemptively. The roadmap's five-agent success criterion stays open until all five can be verified.
- **D-17-12:** Verify target links and access to `SKILL.md` and `JSON_CONTRACT.md`. For each available agent runtime, test “진도율”, “공지”, and “Q&A” as separate natural-language requests in fresh sessions. Record unavailable runtime checks as unverified.
- **D-17-13:** Keep an agent-by-agent evidence table with the prompt, whether the skill triggered, selected CLI command, result, and failure reason. Do not retain full personal course data or full conversation transcripts.
- **D-17-14:** Diagnose a broken source link after a repository move and explain how to relink it from the current checkout. Do not search for and silently switch to another checkout.
- **D-17-15:** Check the separately installed `notion-scheduler` skill as an optional status item. If absent, recommend it without failing CoursePilot deployment. CoursePilot academic commands must remain usable through the Phase 16.1 package dependency without that separate Agent Skill.
- **D-17-16:** Before the independent repository has a GitHub location, mention the separate skill's name and role in CoursePilot guidance without publishing a machine-specific local path or unfinished installation instructions. Add public installation guidance when the separate repository is published.

### Live LXP and Scheduler verification

- **D-17-17:** Run read-only `check`, `progress`, `notices`, and `qna` against every course enrolled at test time. Record per-course success and failure counts; do not assume the historical count of seven still applies.
- **D-17-18:** Actually download one representative material and one representative VOD, confirm the reported status and saved files, and remove only local files created for this smoke test. A material visit may change its LXP viewed state.
- **D-17-19:** For `watch`, first inspect a dry-run target list, then briefly start one real video, observe `watch status`, and stop it with `watch stop`. Partial LXP playback progress may remain; do not run the video to completion for this smoke test.
- **D-17-20:** Read the real Scheduler through the independent package and run academic `sync` and watch-completion previews only. Confirm zero Notion create/update calls; do not apply a live write.

### The agent's Discretion

- Choose exact representative material/VOD items and safe local smoke-test paths after inspecting the live course data.
- Choose the batch command's internal structure, documentation tables, and test fixture design while preserving the behaviors above.
- Choose how to capture concise deployment and E2E evidence without personal data.

### Deferred Ideas (out of scope)

- Prepare the independent `notion-scheduler` project for publication as a new GitHub repository and add its public installation guidance afterward. Its repository is already outside CoursePilot; GitHub publication is a separate capability from Phase 17's CoursePilot skill deployment.

## Project Constraints (from AGENTS.md)

- GSD owns lifecycle and state. Read the active workflow gates, verify plans, and commit through its documented gate.
- Delegate only when authorized. Preserve other work in the shared checkout.
- Keep searches and tool output bounded; run targeted checks during implementation and the full suite at the final gate.
- On a usage or quota failure, preserve work and record the resume boundary instead of marking incomplete work complete.

## Phase Requirements

| ID | Execution meaning | Source |
|---|---|---|
| SKIL-04 | Document all newer CLI commands and the independent Scheduler boundary, then deploy the source-linked CoursePilot skill to all five agents with per-agent evidence. | ROADMAP.md Phase 17; CONTEXT.md D-17-01 to D-17-16 |
| VERIF-03 | Run the live, privacy-limited LXP and Scheduler smoke sequence and record actual outcomes, including incomplete or unavailable checks. | ROADMAP.md Phase 17; CONTEXT.md D-17-17 to D-17-20 |

`SKIL-04` and `VERIF-03` were named in ROADMAP.md but missing from REQUIREMENTS.md at research start. Their definitions and traceability rows were added during planning so the requirement coverage gate has source text. [VERIFIED: `.planning/ROADMAP.md:456-468`; `.planning/REQUIREMENTS.md:39,78,114,132`]

## Summary

Build one production-quality tracer through the documented `progress` JSON and a fake-home linked install, then expand to board and download commands, five-agent deployment, and live E2E evidence. Keep the live actions in an explicit final execution plan after offline contract and installer checks pass. A skipped agent or live probe remains unverified in the evidence table. [VERIFIED: `17-CONTEXT.md` D-17-09, D-17-11, D-17-13, D-17-17 to D-17-20]

## Standard Stack

| Concern | Use | Evidence |
|---|---|---|
| CLI and output | Existing Click commands and `--json` output; no new CLI framework | [VERIFIED: `src/coursepilot/cli.py:184-221,667-756,821-874,984-1025`] |
| JSON contract | Existing Pydantic report models and `schema_version: 1` where present | [VERIFIED: `src/coursepilot/progress/models.py:111-124`; `src/coursepilot/board/models.py:102-112`; `src/coursepilot/report_models.py`] |
| Install links | Existing `AGENT_SKILL_PATHS`, `resolve_agent_home`, and `install_skill` as the base; add batch coordination and safe inspection around them | [VERIFIED: `src/coursepilot/installer.py:38-94,286-347`] |
| Automated checks | Existing pytest fixtures, `CliRunner`, fake homes, and Pydantic example validation | [VERIFIED: `tests/test_installer.py:1-140`; `tests/test_contract_doc.py:1-95`] |
| General Scheduler tasks | Independent `notion-scheduler` package and skill; CoursePilot remains academic sync/watch policy | [VERIFIED: `.planning/phases/16.1-independent-notion-scheduler-module-and-agent-skill/16.1-04-SUMMARY.md`; `skills/coursepilot/SKILL.md:54-65`] |

## Architecture Patterns

1. **Source of truth flows into docs.** Read `cli.py` options and the Pydantic models before writing each JSON section. `ProgressReport` has `status` values `"success"`, `"partial_success"`, `"error"`; `BoardReport.command` has `"board"`, `"notices"`, `"qna"`. The download result types are distinct from those report envelopes. Quote and validate examples against the actual model for each command. [VERIFIED: `src/coursepilot/progress/models.py:111-124`; `src/coursepilot/board/models.py:102-112`; `src/coursepilot/materials/models.py:8-73`; `src/coursepilot/stream/models.py:57-96`]
2. **A batch wraps the single-agent installer.** Resolve each candidate home first; skip absent homes without creating them. Process all five independently; catch each `InstallError`, report `success`/`skip`/`failure`, reason, and target. Keep the foreign-target guard in `_prepare_replace`. Verify the final link/junction resolves to the current `skill_source_dir()` and both docs can be read. A broken link must be diagnosed and explicitly relinked from this checkout. [VERIFIED: `src/coursepilot/installer.py:38-94,179-259,286-347`; `17-CONTEXT.md` D-17-09 to D-17-15]
3. **Evidence is an outcome ledger.** Record per-agent path checks and three fresh-session prompts separately from LXP command results. Record per-course counts, not full payloads or conversations. Preserve `unknown`/`unverified` where a runtime or enrolled course cannot be reached. [VERIFIED: `17-CONTEXT.md` D-17-12, D-17-13, D-17-17]
4. **Preview before state-changing probes.** Use `materials --dry-run` and `download-vod --dry-run` to select one item each; save to an isolated smoke directory, inspect actual files and statuses, and delete only files created by the smoke run. For `watch`, inspect a dry-run target list, start one video briefly, then `watch status` and `watch stop`. For Scheduler, use independent package read plus CoursePilot `sync --json` and `watch sync-notion --dry-run --json`; no apply/write. [VERIFIED: `src/coursepilot/cli.py:141-183,562-666,667-756,821-874`; `17-CONTEXT.md` D-17-18 to D-17-20]

## Don't Hand-Roll

- Do not create a second JSON envelope. Document each existing result model, including commands whose top-level shape differs from `CheckReport`/`SyncReport`.
- Do not implement a second single-agent installer or bypass its foreign-skill guard. Extend the existing safe path.
- Do not include personal Scheduler field definitions in the CoursePilot contract; refer to the independent contract by skill name until the separate repository is published.
- Do not infer a file exists from `saved_path` in a dry run, or infer all courses are complete from empty arrays after a failed collection.

## Common Pitfalls

- `progress` may return exit code 1 with `status: "success"` because past-week missed items exist. Treat collection failure according to `status`, `errors`, and each course `status`, not the process code alone. [VERIFIED: `skills/coursepilot/JSON_CONTRACT.md:38`; `src/coursepilot/progress/models.py:111-124`]
- The existing `install_skill()` currently creates the skill directory even when `agent_home_found` is false. The batch path must check home existence before calling it. [VERIFIED: `src/coursepilot/installer.py:320-330`]
- The current contract test only validates `check` and `sync` JSON examples. Extend it to `progress`, `board`/`notices`/`qna`, materials, and VOD downloads, with any status and error examples chosen from real models. [VERIFIED: `tests/test_contract_doc.py:55-81`]
- Link/junction replacement can be destructive if a target is foreign. Keep the existing name check and inspect broken links before removal; never recursively remove an unknown target. [VERIFIED: `src/coursepilot/installer.py:199-238`]
- Installed agent skill discovery and live Coursemos state are environmental; record observed behavior and failures separately. Do not claim five-agent success from five target paths alone. [VERIFIED: `17-CONTEXT.md` D-17-12 to D-17-13]

## Code Examples

These existing call shapes should guide task actions, without inventing new field names:

```text
coursepilot progress --refresh --json
coursepilot notices --json
coursepilot qna --json
coursepilot materials --course <course> --week <n> --dry-run --json
coursepilot download-vod --course <course> --week <n> --video-index <n> --dry-run --json
coursepilot watch sync-notion --course <course> --dry-run --json
```

The `materials` status values are `"downloaded"`, `"skipped"`, `"viewed_only"`, `"failed"`, `"planned"`; VOD download status values are `"downloaded"`, `"skipped"`, `"failed"`. [VERIFIED: `src/coursepilot/materials/models.py:8-15`; `src/coursepilot/stream/models.py:57-60`]

## Validation Architecture

| Layer | Proof | Command or procedure |
|---|---|---|
| Contract | Every documented JSON block parses and validates against its command model; routing and warnings are present in the skill text. | `uv run pytest tests/test_contract_doc.py tests/test_installer.py -q` |
| Installer | Fake homes cover all five agents, absent homes, foreign target protection, broken source links, and partial batch results. | `uv run pytest tests/test_installer.py -q` |
| Offline integration | Existing command and Scheduler tests remain green. | `uv run pytest -q` |
| Live LXP | Run `check`, `progress`, `notices`, `qna` for every currently enrolled course; capture per-course counts/errors without payloads. | Manual live CLI evidence; network and session required. |
| Live actions | One material and one VOD downloaded to isolated paths, with actual files checked; short watch start/status/stop; Scheduler reads/previews with zero Notion writes. | Manual evidence with exact status and cleanup ledger. |
| Agent routing | Each available runtime receives separate fresh-session prompts `진도율`, `공지`, `Q&A`. | Agent-by-agent evidence table; unavailable means unverified. |

Validation must not mark the phase passed if any required live or agent check is unverified. The full suite runs at the final implementation gate; targeted tests run after relevant tasks. [VERIFIED: `17-CONTEXT.md` D-17-11 to D-17-20; user AGENTS.md]

## Execution-time Observations

- Which of the five agent homes and interactive runtimes exist at execution time? Discover and report; do not create absent homes.
- Which courses are enrolled and which representative downloadable material/VOD are safe to sample? Select after a live read-only preview.
- The checkout already has unrelated edits in `src/coursepilot/installer.py` and `src/coursepilot/player/runner.py`; preserve them and inspect current state before changing either file.

