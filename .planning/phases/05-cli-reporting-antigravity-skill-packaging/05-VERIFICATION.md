---
phase: 05-cli-reporting-antigravity-skill-packaging
verified: 2026-09-23T14:10:00Z
status: human_needed
score: 16/18 must-haves verified
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Fill real LMS_USERNAME/LMS_PASSWORD into .env, then re-run `uv --directory <repo> run python -m coursepilot check --json` and `sync --json` from a folder outside the repository (D-26)."
    expected: "check exits 0 or 1 with summary.course_count >= 1 and the three urgency sections populated with real course data; sync exits 0/1 with sync.dry_run=true, sync.applied=false, and an unchanged Notion Scheduler page count before/after. Update 05-LIVE-EVIDENCE.md with the real counts and close the open `unmet-truth` entry (id 1) in .planning/WINDOWS.md."
    why_human: "Requires the student's real LMS credentials, which this verifier is explicitly forbidden from reading or supplying, and a live network round-trip to the LMS/Notion that must not be run during automated verification."
  - test: "For each of Claude Code, Codex, Antigravity, Pi, and Hermes: start a new session in a folder outside the repository, ask '과제 확인해줘', then ask '노션에 올려줘' and decline the apply prompt."
    expected: "In every agent the coursepilot skill triggers on the natural-language request, runs `check --json`/`sync --json` via `uv --directory`, and replies with markdown tables in the order 기한 초과 → 24시간 이내 → 이후 일정, grouped by course, with detail/LMS links for urgent items and no truncation; for the Notion request it shows the dry-run create/update/skip lists and asks for explicit approval before any `--apply`. Record each result in 05-AGENT-SKILL-EVIDENCE.md, replacing 'pending (human)', and correct any wrong `AGENT_SKILL_PATHS` entry via the Corrections section."
    why_human: "Skill discovery and natural-language triggering happen inside five separate agent runtimes that cannot be driven from this repository or this verification session."
re_verification: null
---

# Phase 5: CLI Reporting & Universal Agent Skill Packaging Verification Report

**Phase Goal:** 직관적인 Rich 콘솔 브리핑 리포트, 통합 CLI 진입점 제공, 에이전트 중립 `SKILL.md` 패키징·에이전트별 설치 지원 및 최종 검증
**Verified:** 2026-09-23T14:10:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `check` chains SessionManager → course list → per-course scrape → `transform_to_sync_tasks` → briefing, Rich by default / JSON with `--json`, never imports Notion (D-07) | ✓ VERIFIED | `src/coursepilot/pipeline.py::collect_tasks`, `src/coursepilot/cli.py::check`; `grep -c "coursepilot.notion" src/coursepilot/cli.py` context shows only the `sync`-scoped import at line 13, guarded by `test_check_no_notion_engine_constructed` (passing); independently ran `uv --directory <repo> run python -m coursepilot check --json` from a foreign cwd — produced well-formed JSON, exit 2 on the real `.env` state (see truth 17) |
| 2 | `--json` stdout is exactly one v1 `CheckReport` (`schema_version`, `command`, `generated_at`, `summary`, `items`, `errors`), Korean unescaped, never a raw `SyncTask` dump | ✓ VERIFIED | `src/coursepilot/report_models.py` (`SCHEMA_VERSION = 1`, 6 `BaseModel` classes); `reporter.to_json` uses `model_dump_json`; `tests/test_cli.py::test_json_contract_check_envelope`, `tests/test_reporter.py::test_json_contract_korean_unescaped` pass; independently confirmed the exact key set via a live `check --json` run |
| 3 | Items split overdue → due_within_24h → later from existing `is_overdue`/`is_urgent` flags, grouped by course, no N-day cutoff | ✓ VERIFIED | `reporter.py::_classify_by_urgency`, `_group_by_course`; `tests/test_reporter.py::test_grouping_sections_by_urgency_then_course`, `test_grouping_includes_very_old_overdue`, `test_grouping_summary_counts` pass |
| 4 | Rich report: summary header, 4-column table per section (과목/작업/마감일/남은 시간), detail blocks only for overdue/within-24h/errors, no truncation/ellipsis | ✓ VERIFIED | `reporter.py::render_check_report`, `_render_section_table` (`overflow="fold"`, no width cap); `tests/test_reporter.py::test_detail_only_for_urgent_and_overdue`, `test_no_truncation_sixty_items_json_and_rich`, `test_no_truncation_narrow_console_no_ellipsis`, `test_detail_bracketed_titles_render_literally` pass |
| 5 | CLI accepts only `--json`/`--headed`/`--relogin`; progress/logging stderr-only; UTF-8 stdout survives a cp949 parent pipe | ✓ VERIFIED | `cli.py::check`, `_configure_streams`; `tests/test_cli.py::test_check_rejects_unknown_option`, `test_stderr_only_progress`, `test_main_utf8_stdout_under_cp949` pass |
| 6 | Exit codes 0 (success) / 1 (course or Notion errors) / 2 (fatal) hold on every `check`/`sync` path | ✓ VERIFIED | `errors.py::exit_code_for`; `tests/test_cli.py` exit-code tests (zero/one/two, config, validation, sync-notion-error, sync-fatal) all pass; independently reproduced exit 2 on a real `check --json` invocation |
| 7 | No secret (LMS username/password, Notion token, cookies) ever reaches stdout/stderr; every error routed through the typed allowlist | ✓ VERIFIED | `errors.py::safe_cli_error`; `tests/test_errors.py`/`tests/test_cli.py` redaction tests pass; the live `check --json` run's `errors[0].message` names only key names ("LMS_USERNAME, LMS_PASSWORD 값이 비어 있습니다…"), no values |
| 8 | A failing course is isolated (per-course try/except → `ErrorItem(scope="course")`), the rest of the briefing stays intact, and `check` exits 1; config/login/course-list failures are fatal (exit 2); zero courses is a warning, not an error | ✓ VERIFIED | `pipeline.py::collect_tasks`, `validate_lms_settings`; `tests/test_pipeline.py` (`test_course_failure_is_isolated`, `test_exit_code_one_end_to_end_course_failure`, `test_exit_code_config_error_before_browser`, `test_exit_code_login_failure_propagates`, `test_exit_code_course_list_failure_propagates`, `test_zero_courses_warns_not_errors`) all pass |
| 9 | Real per-course scraping (progress-table path + course-home fallback) exercised over fixture HTML and mechanically proven read-only | ✓ VERIFIED | `tests/test_pipeline.py::test_scrape_course_uses_progress_report`, `test_scrape_course_falls_back_to_course_sections`, `test_scrape_course_is_read_only` pass; `page.method_calls` assertion is a subset of `{goto, content, wait_for_selector, wait_for_timeout, screenshot}` |
| 10 | `sync` is a dry-run by default (zero `create_page`/`update_page` calls through the real `NotionSyncEngine`); only `--apply` writes | ✓ VERIFIED | `cli.py::sync` (`dry_run=not apply_changes`); `tests/test_cli.py::test_sync_dry_run_default_never_writes`, `test_sync_apply_writes_planned_actions` pass |
| 11 | Sync JSON contract (`SyncReport`, `sync` section keys exactly `{enabled, dry_run, applied, target_title, notice, create, update, skip, counts}`) carries D-16 approval-flow data (create/update-with-diffs/skip-with-reason) | ✓ VERIFIED | `report_models.py` (7 sync `BaseModel` classes); `reporter.py::build_sync_report`, `_build_sync_section`; `tests/test_reporter.py::test_json_contract_sync_envelope_keys`, `test_detail_sync_render_sections` pass |
| 12 | `check` never constructs `NotionSyncEngine`; sync exit codes hold (0/1/2), unconfigured Notion still reports the LMS summary with `enabled=false` + a key-names-only notice | ✓ VERIFIED | `tests/test_cli.py::test_check_no_notion_engine_constructed`, `test_sync_no_notion_configured_notice`, `test_exit_code_sync_notion_error_is_partial`, `test_exit_code_sync_fatal_skips_notion` pass |
| 13 | Rich sync report: shared summary header, mode banner (미리보기/적용 완료/notice), untruncated create/update/skip tables, shared errors section | ✓ VERIFIED | `reporter.py::render_sync_report`, `_sync_mode_banner`, `_render_sync_*_table`; `tests/test_reporter.py::test_detail_sync_render_sections`, `test_detail_sync_no_truncation` pass |
| 14 | `skills/coursepilot/SKILL.md` has agent-neutral frontmatter (exactly `name`/`description`, Korean triggers) and an agent-neutral body encoding D-16..D-19 (briefing rebuild, approval-gated sync, self-installed deps, secret/untrusted-data rules) | ✓ VERIFIED | Read `skills/coursepilot/SKILL.md` directly — frontmatter is exactly `name: coursepilot` + one `description` line containing '과제 확인해줘'/'노션에 올려줘'; body sections 1-7 cover repo resolution, execution rule, env diagnosis, briefing, sync approval gate, troubleshooting, untrusted-data rule; no agent-specific tokens found; `tests/test_installer.py` skill-body/frontmatter tests pass |
| 15 | `install-skill --agent {claude\|codex\|antigravity\|pi\|hermes} [--link]` resolves each agent's skills dir from a data table, copy mode rewrites `{{COURSEPILOT_REPO}}` and writes `repo-root.txt`, `--link` creates a symlink/junction with a loud (never-silent-copy) failure path, and re-install never deletes outside the target | ✓ VERIFIED | `src/coursepilot/installer.py` (`AGENT_SKILL_PATHS`, `install_skill`, `_prepare_replace`); `tests/test_installer.py` (21 tests: path table, copy repo-root resolution, real symlink, junction fallback call shape, both-fail loud exit 2, safe re-install over link/copy, foreign-target refusal, missing-home warning) all pass; independently inspected `~/.claude`, `~/.codex`, `~/.gemini/antigravity`, `~/.pi/agent`, `~/.hermes` skills folders — all five contain `SKILL.md` (no `{{COURSEPILOT_REPO}}` placeholder, absolute repo path present), `JSON_CONTRACT.md`, and `repo-root.txt` |
| 16 | `skills/coursepilot/JSON_CONTRACT.md` documents every `CheckReport`/`SyncReport` field with validating examples; `README.md` has setup + per-agent install table; `.planning/PROJECT.md` carries universal-skill wording; full automated suite green with nothing skipped | ✓ VERIFIED | `tests/test_contract_doc.py` (4 tests) pass; `uv run pytest` → 182 passed, 0 failed, 0 skipped (`-rs` shows no skip markers); `grep -c "범용 Agent Skill" .planning/PROJECT.md` = 2, `grep -c "Universal Agent Skill Packaging" .planning/ROADMAP.md` = 3, `grep -c "에이전트 중립" .planning/REQUIREMENTS.md` = 1; read `README.md` directly — setup, commands/exit-code tables, Notion safety, 5-agent install table, `--link` note all present |
| 17 | D-26: a real `check --json` and dry-run `sync --json` ran against the user's live LMS/Notion, invoked with `uv --directory <repo>` from outside the repo, recording exit codes/schema_version/counts/error codes/sync dry_run/applied and an unchanged Scheduler page count | ✗ NOT MET (routed to human) | `05-LIVE-EVIDENCE.md` and `.planning/WINDOWS.md` (open `unmet-truth` id 1): both `check` and `sync` genuinely exited `2` with `ConfigError` because `.env`'s `LMS_USERNAME`/`LMS_PASSWORD` are empty — no real course/assignment data was ever collected, so `summary.course_count`, section counts, and `sync.dry_run`/`sync.applied` were never observed. Notion write audit (62/62 pages, zero writes) did pass. Independently reproduced this exact exit-2/ConfigError behavior in a fresh `check --json` run during this verification. Resolving this requires a human to fill real LMS credentials into `.env` (this verifier is explicitly forbidden from reading `.env` or running further live LMS commands) — see human_verification |
| 18 | D-27: the skill triggers on natural-language requests ('과제 확인해줘', '노션에 올려줘') in all five installed agents and follows the D-16/D-17 briefing/approval-gate contract | ⚠️ INSTALL VERIFIED / INVOCATION NOT YET DONE | Install mechanics independently confirmed (see truth 15). `05-AGENT-SKILL-EVIDENCE.md` stages one row per agent with install exit 0 / smoke PASS, but both natural-language invocation columns are still "pending (human)" — no evidence yet that any agent runtime actually discovers and triggers the skill conversationally. See human_verification |

**Score:** 16/18 truths verified (2 routed to human verification — both are external-precondition/live-runtime items, not code defects)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/coursepilot/report_models.py` | JSON contract v1 (check + sync) | ✓ VERIFIED | 172 lines, `SCHEMA_VERSION = 1`, 13 `BaseModel` classes, `extra="forbid"` |
| `src/coursepilot/reporter.py` | Pure builder + Rich renderers | ✓ VERIFIED | 471 lines, `build_check_report`/`build_sync_report`/`render_check_report`/`render_sync_report`/`format_remaining`/`to_json`/`notion_page_url` all present and exercised by tests |
| `src/coursepilot/pipeline.py` | LMS orchestrator with resilience | ✓ VERIFIED | 146 lines, `collect_tasks`/`scrape_course`/`validate_lms_settings`/`PipelineResult` |
| `src/coursepilot/cli.py` | `check`/`sync`/`install-skill` commands | ✓ VERIFIED | 204 lines; `python -m coursepilot --help` lists all three commands, exit 0 |
| `src/coursepilot/errors.py` | Typed-allowlist redaction + exit mapping | ✓ VERIFIED | 99 lines, `safe_cli_error`/`exit_code_for`/`EXIT_OK`/`EXIT_PARTIAL`/`EXIT_FATAL` |
| `src/coursepilot/installer.py` | Data-driven 5-agent installer | ✓ VERIFIED | 284 lines, `AGENT_SKILL_PATHS` (5 entries), `install_skill`, `resolve_install_target`, `_prepare_replace` |
| `skills/coursepilot/SKILL.md` | Agent-neutral skill instructions | ✓ VERIFIED | 64 lines, `name: coursepilot` + one `description`, 7-section agent-neutral body |
| `skills/coursepilot/JSON_CONTRACT.md` | Contract v1 reference | ✓ VERIFIED | 327 lines, field tables for all 13 models + validating example payloads |
| `README.md` | User + per-agent install guide | ✓ VERIFIED | 89 lines, setup/commands/exit-codes/5-agent table/`--link` note |
| `.planning/phases/.../05-LIVE-EVIDENCE.md` | Redacted live evidence (D-26) | ⚠️ PARTIAL | Exists, correctly redacted, but records a `ConfigError` blocker rather than real course data — the truth it documents is unmet |
| `.planning/phases/.../05-AGENT-SKILL-EVIDENCE.md` | Per-agent install/invocation record (D-27) | ⚠️ PARTIAL | Install/smoke rows complete and independently reconfirmed; invocation columns are all "pending (human)" |
| Tests (`test_cli.py`, `test_reporter.py`, `test_errors.py`, `test_pipeline.py`, `test_installer.py`, `test_contract_doc.py`) | Full automated coverage | ✓ VERIFIED | 182 tests total, all pass, none skipped |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `cli.py::check` | `pipeline.py::collect_tasks` | `_collect_lms_tasks` shared helper | ✓ WIRED | Confirmed in source and by a live `check --json` run |
| `cli.py::check` | `reporter.py` | `build_check_report`/`render_check_report`/`to_json` | ✓ WIRED | Confirmed in source and live run |
| `reporter.py` | `report_models.py` | `CheckReport(...)`/`SyncReport(...)` construction | ✓ WIRED | Confirmed in source |
| `cli.py::check`/`sync` | `errors.py` | `safe_cli_error(...)`, `exit_code_for(...)` | ✓ WIRED | Confirmed in source and live run (exit 2, redacted message) |
| `pipeline.py` | `domain/transformer.py` | `transform_to_sync_tasks(...)` | ✓ WIRED | Confirmed in source |
| `cli.py::sync` | `notion/engine.py` | `NotionSyncEngine(settings=settings).sync(tasks, dry_run=not apply_changes)` | ✓ WIRED | Confirmed in source; never reached on the live run because the fatal LMS-stage guard fired first (expected per D-08) |
| `cli.py::install_skill_command` | `installer.py` | `install_skill(agent, link=link)` | ✓ WIRED | Confirmed in source and by inspecting all 5 real installed skill folders |
| `installer.py` (copy mode) | `skills/coursepilot/SKILL.md` | `REPO_PLACEHOLDER` replacement | ✓ WIRED | Confirmed: repo's own `skills/coursepilot/SKILL.md` still holds `{{COURSEPILOT_REPO}}` (2 occurrences); all 5 installed copies hold the resolved absolute path and no placeholder |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `check --json` produces the v1 envelope and exit code contract from a foreign cwd | `uv --directory "<repository root>" run python -m coursepilot check --json` (run from an OS-temp scratch folder) | Exit 2; well-formed JSON with `schema_version:1`, `errors[0]` = `{scope: fatal, code: ConfigError, message: "LMS_USERNAME, LMS_PASSWORD 값이 비어 있습니다..."}`, no secret values present | ✓ PASS |
| `python -m coursepilot --help` lists all three commands | `uv run python -m coursepilot --help` | Exit 0; lists `check`, `sync`, `install-skill` | ✓ PASS |
| `install-skill --help` lists `--agent` choices and `--link` | `uv run python -m coursepilot install-skill --help` | Exit 0; `[antigravity|claude|codex|hermes|pi]` and `--link` present | ✓ PASS |
| All 5 real agent skill folders contain a resolved, placeholder-free `SKILL.md` + `JSON_CONTRACT.md` + `repo-root.txt` | Directly inspected `~/.claude`, `~/.codex`, `~/.gemini/antigravity`, `~/.pi/agent`, `~/.hermes` skills dirs | All 5 present; `grep -c "{{COURSEPILOT_REPO}}"` = 0 in the Claude copy, absolute repo path present | ✓ PASS |
| Full automated suite | `uv run pytest` | `182 passed` in 4.24s, 0 failed, 0 skipped | ✓ PASS |
| Debt-marker scan on all phase-5 source files | `grep -nE "TBD\|FIXME\|XXX\|TODO\|HACK\|PLACEHOLDER" ...` | Only the intentional `REPO_PLACEHOLDER = "{{COURSEPILOT_REPO}}"` constant and its two legitimate uses matched — no debt markers | ✓ PASS |
| Live `sync --apply` / real LMS network round-trip | — | Not run | ? SKIP (explicitly out of scope for this verification per orchestrator instruction) |

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|-----------------|--------------|--------|----------|
| SKIL-01 | 05-01, 05-02, 05-03, 05-05 | Rich console briefing of incomplete lectures/assignments/deadlines | ✓ SATISFIED (code/tests); real-data proof pending | Truths 1-4, 13, 16; live real-data proof is truth 17 (human) |
| SKIL-02 | 05-01, 05-02, 05-03, 05-05 | `check`/`sync` CLI commands | ✓ SATISFIED (code/tests); real-data proof pending | Truths 1, 5-12, 16; live real-data proof is truth 17 (human) |
| SKIL-03 | 05-04, 05-05 | Agent-neutral `SKILL.md` + per-agent install for all 5 agents | ✓ SATISFIED (install mechanics); conversational proof pending | Truths 14-16; invocation proof is truth 18 (human) |

No orphaned requirements: REQUIREMENTS.md's Phase 5 traceability row lists exactly SKIL-01/02/03, matching every plan's `requirements:` frontmatter field. **Note:** REQUIREMENTS.md currently marks SKIL-01/02/03 as "Complete" outright. Given the codebase/test evidence, the underlying mechanics genuinely are complete and stable — but the requirements' own language ("직관적으로 보여주는", "모든 지원 에이전트가 자연어 요청으로 스킬을 호출할 수 있도록") implies demonstrated behavior against real data and real agent runtimes, which is exactly what truths 17-18 have not yet shown. This is not a code gap; it is a documentation/status precision note tied to the same two human-verification items already flagged.

### Anti-Patterns Found

None. No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` debt markers in any phase-5 source file (the only matches are the intentional `REPO_PLACEHOLDER` template-substitution constant, which is documented, tested, and by design). No empty stub implementations, no hardcoded-empty data flowing to rendered output, no markup-injection risk (all user-authored text passed through `rich.text.Text`).

### Human Verification Required

### 1. D-26 live evidence re-run with real LMS credentials

**Test:** Fill real `LMS_USERNAME`/`LMS_PASSWORD` into `.env`, then re-run `check --json` and `sync --json` (dry-run, no `--apply`) from outside the repository.
**Expected:** `check` exits 0 or 1 with `summary.course_count >= 1` and populated urgency sections; `sync` shows `dry_run=true`/`applied=false` and an unchanged Notion Scheduler page count. Update `05-LIVE-EVIDENCE.md` and close the open `unmet-truth` entry in `.planning/WINDOWS.md`.
**Why human:** Requires the student's real secret credentials (this verifier cannot read `.env` or supply them) and a live network round-trip to the LMS that must not be triggered during automated verification.

### 2. D-27 five-agent natural-language invocation

**Test:** In a new session, outside the repository, for each of Claude Code, Codex, Antigravity, Pi, and Hermes: ask "과제 확인해줘", then ask "노션에 올려줘" and decline the apply prompt.
**Expected:** The `coursepilot` skill triggers in every agent, runs `check --json`/`sync --json` via `uv --directory`, and replies with correctly-ordered, ungrouped-by-nothing markdown tables and a Notion preview-then-approval flow, per `05-AGENT-SKILL-EVIDENCE.md`'s "How to Verify" section.
**Why human:** Skill discovery and natural-language triggering happen inside five separate agent runtimes that cannot be driven from this repository or verification session.

### Gaps Summary

No code-level gaps were found: all 182 automated tests pass, every artifact this phase's plans committed to exists and is substantive and wired (independently re-confirmed for the CLI JSON contract, exit-code/redaction behavior, and all 5 real agent skill installs), and no anti-patterns or debt markers were found. The phase's mechanics — Rich briefing, CLI contract, Notion dry-run/apply gate, and the universal skill packaging/installer — are all genuinely built and tested, not stubbed.

Two items remain open and are exactly the two the phase's own plans (05-05) and `.planning/WINDOWS.md` already flag as unresolved: (1) D-26's live evidence run never observed real course/assignment data because `.env`'s LMS credentials are empty — a human must supply real credentials and re-run; (2) D-27's actual natural-language skill invocation in all five agents has not happened yet — a human must run it in each agent's own runtime. Both are external-precondition/live-runtime items outside what a codebase verifier can resolve or fabricate, so the phase is `human_needed` rather than `passed` or `gaps_found`.

---

*Verified: 2026-09-23T14:10:00Z*
*Verifier: Claude (gsd-verifier)*
