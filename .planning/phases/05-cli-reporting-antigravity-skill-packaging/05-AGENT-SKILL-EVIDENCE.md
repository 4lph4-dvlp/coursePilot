# Phase 05-05 Agent Skill Install + Invocation Evidence (D-27)

Automated part (install + smoke) run by the executor. The two invocation columns require an actual human to open each agent in a new session outside this repository and ask a natural-language question — they cannot be driven from this repository, so they start as "pending (human)" per this plan's `human_verify_mode = end-of-phase` design.

## Foreign-cwd Smoke Check

- **Command:** `uv --directory "D:/dev/kau-lxp-assistant" run python -m kau_assistant --help`, run from an OS temp scratch folder outside the repository
- **Exit code:** 0
- **Result:** the group help text listed all three subcommands (`check`, `sync`, `install-skill`) correctly, confirming the CLI resolves and runs from a foreign working directory (D-23)

## Per-Agent Install + Smoke Table

| Agent | Installed path | Path evidence (from `AGENT_SKILL_PATHS` comment) | install exit | smoke | "과제 확인해줘" result | "노션에 올려줘" preview + approval gate | Notes |
|-------|-----------------|---------------------------------------------------|---------------|-------|--------------------------|------------------------------------------|-------|
| Claude Code | `C:\Users\alpha\.claude\skills\kau-lxp` | MEDIUM confidence — official docs + this repo's own `.claude/skills/` | 0 | PASS | PASS (headless `claude -p`, cwd outside repo, 2026-09-23): `kau-lxp` triggered via Skill tool, ran `uv --directory "D:\dev\kau-lxp-assistant" run python -m kau_assistant check --json`, gave the one-line summary (0 courses / 0 / 0 / 0 / 0 errors) and relayed the no-courses warning; no secret requested. Section-table ordering not observable (0 items this term) | PASS: ran `sync --json` (dry-run) only, reported create/update/skip all 0, no `--apply` attempted (also denied by permission rule); Notion Scheduler 62 → 62. Approval prompt not reached because there was nothing to apply | Installed `SKILL.md` shows no `{{KAU_LXP_REPO}}` placeholder and contains the absolute repo root; `JSON_CONTRACT.md` present alongside; `repo-root.txt` holds the repo root. The `kau-lxp` skill is now listed as an available skill in this very session, which is corroborating (non-human) evidence the install is discoverable by Claude Code. |
| Codex | `C:\Users\alpha\.codex\skills\kau-lxp` | LOW confidence — WebSearch snippets only (A1); this repo's own `.codex/skills/` is Codex-managed (`.system`), not proof of the user-level path | 0 | PASS | pending (human) | pending (human) | Same placeholder/contract/repo-root.txt checks as above, all PASS. Path confidence is LOW — confirm or correct via the human check below. |
| Antigravity | `C:\Users\alpha\.gemini\antigravity\skills\kau-lxp` | LOW confidence — WebSearch only (A2); no `skills/` dir was observed in this repo before this install | 0 | PASS | pending (human) | pending (human) | Same checks PASS. Path confidence is LOW — confirm or correct via the human check below. |
| Pi | `C:\Users\alpha\.pi\agent\skills\kau-lxp` | LOW confidence — WebSearch only (A3); no `skills/` dir was observed in this repo before this install | 0 | PASS | pending (human) | pending (human) | Same checks PASS. Path confidence is LOW — confirm or correct via the human check below. |
| Hermes | `C:\Users\alpha\.hermes\skills\kau-lxp` | LOW confidence — WebSearch only (A4); no in-repo evidence was available | 0 | PASS | pending (human) | pending (human) | Same checks PASS. Path confidence is LOW — confirm or correct via the human check below. |

**Smoke PASS criteria (all five):** installed `SKILL.md` exists, contains no `{{KAU_LXP_REPO}}` placeholder, contains the absolute repo root (`D:\dev\kau-lxp-assistant`), `JSON_CONTRACT.md` is present beside it, and `repo-root.txt` holds the repo root. Verified via `python -c "..."` inspection of all five `resolve_install_target(agent)` directories immediately after each install; also confirmed by the task's own automated `<verify>` (`bad: []`, exit 0).

All five installs were run in **copy mode** (never `--link`), from the repository, per this task's instructions.

## How to Verify (human steps)

1. **Live-evidence cross-check:** open `05-LIVE-EVIDENCE.md` and compare the course count and the overdue / within-24h / later counts with what the LMS actually shows. *(Note: as of this plan's execution, `05-LIVE-EVIDENCE.md` records a `ConfigError` blocker — `.env`'s `LMS_USERNAME`/`LMS_PASSWORD` are empty — so this cross-check cannot be meaningfully performed until real credentials are filled in and the live run is repeated. See that file's "Blocker — Action Required" section.)*
2. **Per-agent invocation, for each of Claude Code, Codex, Antigravity, Pi, and Hermes:**
   - Start a new session in any folder **outside** this repository.
   - Ask: "과제 확인해줘"
   - Then ask: "노션에 올려줘" and **decline** when asked to apply (approve only if you genuinely want a live write).
   - Record both results in the table above, replacing "pending (human)" with the observed outcome.

**Expected results:**
- (a) Counts match the LMS; no item is missing.
- (b) In every agent, the `kau-lxp` skill triggers, runs `check --json` through `uv --directory`, and answers with markdown tables in the order 기한 초과 → 24시간 이내 → 이후 일정, grouped by course, listing every item with detail/LMS links for urgent ones (no pasted terminal/ANSI output, no truncation), without asking for any secret; for "노션에 올려줘" it shows the dry-run create/update/skip lists and asks for approval before any `--apply`.

**Why human:** skill discovery and natural-language triggering happen inside five separate agent runtimes that cannot be driven from this repository, and only the student can compare the briefing with their own LMS view.

## Corrections

None recorded yet. If the human check above finds an installed path is wrong for an agent, record here: **Agent**, **Observed working location**, then fix `AGENT_SKILL_PATHS` in `src/kau_assistant/installer.py` as a one-line data-only change through `/gsd-plan-phase 5 --gaps` (per A-10 in the plan's flagged assumptions).

| Agent | Observed working location | Status |
|-------|----------------------------|--------|
| — | — | No corrections reported yet |
