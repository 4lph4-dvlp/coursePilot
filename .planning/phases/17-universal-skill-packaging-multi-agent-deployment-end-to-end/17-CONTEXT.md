# Phase 17: Universal Skill Packaging, Multi-Agent Deployment & End-to-End Verification - Context

**Gathered:** 2026-10-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Update the CoursePilot Agent Skill and JSON contract for the features delivered through Phase 16.1, deploy the updated CoursePilot skill to Claude Code, Codex, Antigravity, Pi, and Hermes, and verify the new commands against the live Coursemos LXP. The CoursePilot skill must describe its boundary with the independent `notion-scheduler` package and skill. Phase 17 does not publish that separate repository.

The phase's roadmap success criteria remain: complete documentation of new commands, working deployment to all five agents, live LXP end-to-end verification, and accurate Scheduler integration guidance. A skipped or untestable agent must be reported as incomplete evidence rather than counted as a passing deployment.

</domain>

<decisions>
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

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project scope and prior decisions
- `.planning/ROADMAP.md` § Phase 17 — phase goal and four success criteria.
- `.planning/REQUIREMENTS.md` — project requirements; the roadmap names `SKIL-04` and `VERIF-03`, but these IDs are currently absent here and must be reconciled during planning.
- `.planning/PROJECT.md` — product boundary, supported LMS family, Scheduler separation, and user data protections.
- `.planning/STATE.md` — current phase and later quick-task decisions affecting CoursePilot naming and Scheduler approval.
- `.planning/phases/15-course-announcements-q-a-board-briefing/15-CONTEXT.md` — board command, default scope, and presentation decisions.
- `.planning/phases/16-comprehensive-activity-progress-dashboard/16-CONTEXT.md` — progress dashboard and JSON decisions.
- `.planning/phases/16.1-independent-notion-scheduler-module-and-agent-skill/16.1-CONTEXT.md` — independent Scheduler responsibility and API boundary.

### CoursePilot skill, contract, and implementation
- `skills/coursepilot/SKILL.md` — current natural-language guidance, safety rules, and command use.
- `skills/coursepilot/JSON_CONTRACT.md` — existing schema version and check/sync/watch contract.
- `README.md` — current agent installation guidance.
- `src/coursepilot/installer.py` — five-agent target map, safe replacement, link/copy handling, and home resolution.
- `src/coursepilot/cli.py` — command names, options, and install-skill entry point.
- `src/coursepilot/report_models.py` — check/sync report models.
- `src/coursepilot/progress/models.py` — progress JSON models.
- `src/coursepilot/board/models.py` — board JSON models.
- `src/coursepilot/materials/models.py` — materials JSON models.
- `src/coursepilot/stream/downloader.py` — VOD download result models.
- `src/coursepilot/player/runner.py` — watch result and completion behavior.
- `tests/test_installer.py` — existing installer and skill checks.
- `tests/test_contract_doc.py` — current field-list and example-validation checks.

### Independent Scheduler repository
- `../notion-scheduler/README.md` — independent package and distribution status.
- `../notion-scheduler/skills/notion-scheduler/SKILL.md` — separate general Scheduler skill.
- `../notion-scheduler/skills/notion-scheduler/JSON_CONTRACT.md` — general task JSON contract.

### Historical deployment and live verification
- `.planning/phases/08-end-to-end-verification-agent-redeployment/08-01-SUMMARY.md` — previous live verification.
- `.planning/phases/11-background-subagent-packaging/11-01-SUMMARY.md` — background watch and agent packaging precedent.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `AGENT_SKILL_PATHS` contains all five agent targets; `install_skill()` handles one agent at a time and protects non-CoursePilot content.
- `tests/test_contract_doc.py` already collects nested Pydantic fields and validates check/sync example blocks.
- `tests/test_installer.py` isolates fake homes so installation tests do not touch user directories.

### Established Patterns
- `SKILL.md` already distinguishes explicit downloads and watch playback from read-only checks; its progress/materials guidance exists but board and VOD-download routing need consolidation.
- `JSON_CONTRACT.md` establishes `schema_version: 1`, stdout JSON vs stderr progress, and status/exit-code interpretation, but complete command sections and examples for the newer reports are missing.
- Phase 16.1 puts general Scheduler work in a separate package and skill; CoursePilot keeps academic LMS interpretation and sync.

### Integration Points
- The `install-skill` Click option currently accepts one agent from `AGENT_SKILL_PATHS`; planning can add a batch route with per-agent results.
- New skill guidance should map to the existing `progress`, `board`/`notices`/`qna`, `materials`, `download-vod`, and watch CLI commands.
- The existing report model classes and CLI JSON output are the sources for contract tables and executable examples.
- No `.planning/codebase/*.md` maps exist; this phase's code scout used the files listed above.

</code_context>

<specifics>
## Specific Ideas

- “이번 주 학업 현황 알려줘” → `progress` first; “공지” → `notices`; “질문·답변” → `qna`; broad “게시판” → `board`.
- The independent repository already lives at `D:/dev/notion-scheduler`, outside CoursePilot. On 2026-10-04 its Git worktree was clean and it had no remote. This is background for the deferred publication task, not a deployment path to embed in the portable CoursePilot skill.
- Agent evidence uses the separate read-only prompts “진도율”, “공지”, and “Q&A”.
- Live verification uses the courses actually enrolled when it runs, one real material and one real VOD download, short watch start/status/stop, and Notion reads/previews with zero writes.

</specifics>

<deferred>
## Deferred Ideas

- Prepare the independent `notion-scheduler` project for publication as a new GitHub repository and add its public installation guidance afterward. Its repository is already outside CoursePilot; GitHub publication is a separate capability from Phase 17's CoursePilot skill deployment.

</deferred>

---

*Phase: 17-universal-skill-packaging-multi-agent-deployment-end-to-end*
*Context gathered: 2026-10-04*
