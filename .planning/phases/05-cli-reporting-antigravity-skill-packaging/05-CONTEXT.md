# Phase 5: CLI Reporting & Universal Agent Skill Packaging - Context

**Gathered:** 2026-09-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 5 delivers the user-facing layer on top of the Phase 1–4 engine:

1. A single end-to-end pipeline (LMS login → course scrape → normalize to `SyncTask` → briefing / Notion sync) callable from the CLI.
2. A Rich console briefing report plus an equivalent, versioned `--json` output.
3. `python -m kau_assistant check` / `sync` / `install-skill` commands.
4. An **agent-neutral** skill package (`SKILL.md` + support docs) usable by any agent that supports the common Agent Skills format — explicitly NOT Antigravity-only.
5. Per-agent install guidance (README) and an install command for Claude Code, Codex, Antigravity, and Pi/Hermes.
6. End-to-end verification: fixture-based automated tests, live `check` + dry-run `sync`, and manual skill-invocation checks in every supported agent.

**Scope correction made during discussion:** the user stated the system must work in all agents, not only Antigravity. The phase name, SKIL-03, and PROJECT.md wording must be changed from "Antigravity Skill" to "universal Agent Skill (SKILL.md)" as part of this phase.

</domain>

<decisions>
## Implementation Decisions

### 1. Briefing layout (브리핑 구성)
- **D-01:** Top-level grouping is by urgency: **기한 초과 → 24시간 이내 → 이후 일정**. Inside each section, items are grouped by course.
- **D-02:** Two-level detail. Tables show course, task name, due date, and time remaining. Only urgent items (overdue + within 24h) and errors get an extra detail block with description and LMS link.
- **D-03:** A summary header shows the total course count and the counts for overdue / within 24h / later.
- **D-04:** Never truncate. Both the terminal and the agent chat show every incomplete item.
- **D-05:** The "기한 초과" section includes every item the LMS still reports as incomplete, however old. No N-day cutoff.

### 2. Command safety (명령 안전성)
- **D-06:** `sync` is a dry-run by default. It writes to Notion only when `--apply` is passed. This reuses the Phase 4 real-read / blocked-write dry-run path. — **Reversibility:** costly — agents and users will build habits and SKILL.md instructions on this default
- **D-07:** `check` runs LMS login, scraping, normalization, and the briefing. It never touches Notion.
- **D-08:** Configuration or login failures abort immediately. Failures for a single course or item do not stop the run: processing continues, the errors are collected and shown, and the command exits non-zero.
- **D-09:** Human output uses Rich by default. `--json` emits the same result for agents and automation.

### 3. CLI options, progress, exit codes, and JSON contract
- **D-10:** Options stay minimal. Shared: `--json`, `--headed` (shows the browser; `SessionManager` already accepts `headful`), `--relogin` (ignores the cached `session.json`). `sync` only: `--apply`. No course filter or other convenience flags.
- **D-11:** Progress is shown per course (for example `[3/7] 자료구조 수집 중`) with a Rich spinner or status line. **All progress and log output goes to stderr**, so stdout carries only the report or pure JSON.
- **D-12:** Exit codes: `0` = full success, `1` = partial failure (some courses or items failed; results are still printed), `2` = fatal (missing config or login failure; aborted). — **Reversibility:** costly — SKILL.md and agent flows branch on these codes
- **D-13:** The JSON contract is versioned and documented, and is not a raw model dump. Top-level shape: `{schema_version, command, generated_at, summary, items | sync, errors}`. It is documented in the skill's support docs. Any breaking change bumps `schema_version`. — **Reversibility:** one-way — once agents parse `schema_version` 1, changing the shape breaks installed skills
- **D-14:** No output (Rich, JSON, or error text) may contain the student ID, password, Notion token, or session cookies. Item LMS links and Notion page URLs are included. Apply the existing `_safe_error` masking approach (`notion/engine.py`) to CLI error output as well.

### 4. Skill invocation experience (스킬 호출 경험)
- **D-15:** The skill folder lives at `skills/kau-lxp/` in the repo (`SKILL.md` + support docs such as the JSON schema reference).
- **D-16:** For requests like "노션에 올려줘", the agent runs `sync` (dry-run) first, shows the create / update / skip lists, and runs `sync --apply` only after the user approves in the conversation.
- **D-17:** In chat, the agent parses `--json` and rebuilds the briefing as markdown tables that follow D-01–D-04. It does not paste the Rich/ANSI output.
- **D-18:** On first run, the agent diagnoses the environment. It installs dependencies itself (`uv sync`, `playwright install chromium`). For secrets (student ID, password, Notion token), it only tells the user to put them in `.env` themselves. **The agent never asks for secrets in conversation.**

### 5. Universal agent skill packaging (범용 에이전트 스킬)
- **D-19:** `SKILL.md` uses only the fields common to the Agent Skills format (`name`, `description`) plus agent-neutral body instructions: run the CLI, read `--json`, follow D-16/D-17/D-18. No agent-specific tool names or frontmatter extensions. — **Reversibility:** costly — every installed copy across agents depends on the format
- **D-20:** README includes per-agent install guidance (a table of skill paths and steps) for Claude Code, Codex, Antigravity, and Pi/Hermes.
- **D-21:** The install command is a CLI subcommand: `python -m kau_assistant install-skill --agent {claude|codex|antigravity|pi|hermes}`. It is one Python implementation for every OS and is testable.
- **D-22:** Supported install targets from day one: Claude Code, Codex, Antigravity, Pi, Hermes. Agent → skill-path mappings are kept as **data** (a table or dict) so adding an agent is a data change. Exact paths (user-level vs project-level, Pi/Hermes locations) must be confirmed in research.
- **D-23:** Install copies the folder by default. `--link` creates a symlink or junction for development so repo edits show up immediately. The installed SKILL.md must resolve the repo / CLI location so it works from any agent's working directory (for example, the installer writes the repo path into the installed copy).
- **D-24:** Update ROADMAP.md (Phase 5 name and goal), REQUIREMENTS.md (SKIL-03), and PROJECT.md (Active item, Context) to say "universal Agent Skill (SKILL.md)" instead of "Antigravity Skill".

### 6. Verification (E2E 검증)
- **D-25:** Automated tests cover CLI commands, the reporter (sections, grouping, no truncation), JSON contract, exit codes, secret redaction, and install-skill path generation, using fixtures and mocks.
- **D-26:** Live evidence: one real `check` run and one real dry-run `sync` against the user's LMS and Notion, recorded as evidence the same way as Phase 4 (`04-02-LIVE-DRY-RUN-EVIDENCE.md`). Live `sync --apply` happens only with the user's explicit approval and is not a mandatory verification step.
- **D-27:** Manual skill-invocation check in **every** supported agent (Claude Code, Codex, Antigravity, Pi, Hermes): install with `install-skill`, then ask something like "과제 확인해줘". Confirm the skill triggers and follows D-16/D-17. This was previously deferred in the Codex session and is now in scope by the user's choice.

### Claude's Discretion
- CLI framework wiring (`click` is already a dependency), module layout (`cli.py`, `reporter.py`, `pipeline.py`, etc.).
- Exact Rich styling (colors, borders), time-remaining format ("3시간 12분" vs "D-1").
- Exact JSON field names below the top level, as long as they are documented and versioned.
- Whether `install-skill` also supports a project-level target in addition to user-level.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project scope
- `.planning/ROADMAP.md` — Phase 5 goal and success criteria (wording to be updated per D-24)
- `.planning/REQUIREMENTS.md` — SKIL-01, SKIL-02, SKIL-03
- `.planning/PROJECT.md` — core value, constraints (secrets in `.env`), out-of-scope items

### Prior phase contracts
- `.planning/phases/04-notion-scheduler-integration-deduplication/04-CONTEXT.md` — D-04/D-05 (dry-run semantics, `SyncResult` DTO for the reporter), D-09 (standalone fallback without Notion)
- `.planning/phases/04-notion-scheduler-integration-deduplication/04-02-LIVE-DRY-RUN-EVIDENCE.md` — format precedent for live evidence (D-26)
- `.planning/phases/04-notion-scheduler-integration-deduplication/04-VERIFICATION.md` — verified engine behavior

### External formats (research must confirm)
- Agent Skills `SKILL.md` format — common frontmatter fields and discovery paths for Claude Code, Codex, Antigravity, Pi, Hermes (no in-repo spec; researcher must fetch current docs)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/kau_assistant/notion/engine.py` `NotionSyncEngine` + `_safe_error`: sync execution with dry-run, and a secret-masking error pattern to reuse for CLI errors (D-14).
- `src/kau_assistant/notion/models.py` `SyncResult` / `CreateAction` / `UpdateAction` (with `FieldDiff`) / `SkipAction` / `ErrorAction` / `SyncStats`: input for the sync report and JSON `sync` section.
- `src/kau_assistant/domain/transformer.py` `transform_to_sync_tasks`, `domain/priority.py` `calculate_priority`: normalized tasks and the 24h / overdue classification behind D-01.
- `src/kau_assistant/domain/models.py` `SyncTask`, `Course`: briefing item model.
- `src/kau_assistant/session_manager.py` `SessionManager(headful=...)`: backs `--headed` and session caching (`--relogin`).
- `src/kau_assistant/scraper/` (`course_list`, `navigator`, `lecture_parser`, `assessment_parser`): the scraping steps.
- `src/kau_assistant/exceptions.py`: `ConfigError` / `AuthenticationError` map to exit code 2; per-course errors (`NavigationTimeoutError`, `CourseAccessDeniedError`, Notion item errors) map to exit code 1.
- `rich` and `click` are already declared in `pyproject.toml`.

### Established Patterns
- Pydantic models for all DTOs, so the JSON contract should be explicit Pydantic output models, not raw dumps.
- Pure domain layer with I/O at the edges; the reporter should be a pure function of results, so it can be tested without a browser.
- Graceful degradation when Notion config is missing (Phase 4 D-09).

### Integration Points
- **No end-to-end orchestrator exists yet.** There is no `__main__.py` or `cli.py`, and nothing chains login → course list → per-course parse → `transform_to_sync_tasks`. Phase 5 must add this pipeline with per-course error collection (D-08).
- New: `src/kau_assistant/__main__.py` / `cli.py`, reporter module, JSON output models, `install-skill` command, `skills/kau-lxp/`.

</code_context>

<specifics>
## Specific Ideas

- The user explicitly rejected the Antigravity-only framing: "이 시스템은 모든 에이전트에서 사용 가능하도록 만들어야 하는데".
- Example chat request to verify: "과제 확인해줘" → check briefing; "노션에 올려줘" → dry-run, then approval, then `--apply`.

</specifics>

<deferred>
## Deferred Ideas

- None remaining. Per-agent install adapters and compatibility checks were deferred in the earlier Codex session and are now in scope (D-21, D-22, D-27).

</deferred>

---

*Phase: 05-cli-reporting-antigravity-skill-packaging*
*Context gathered: 2026-09-23*
