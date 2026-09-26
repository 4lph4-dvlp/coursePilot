---
phase: 05-cli-reporting-antigravity-skill-packaging
plan: 04
subsystem: packaging
tags: [agent-skills, skill-md, installer, symlink, ntfs-junction, click, pydantic, tdd]

# Dependency graph
requires:
  - phase: 05-cli-reporting-antigravity-skill-packaging
    provides: "05-02/05-03's finished check/sync commands, exit codes, and JSON contract v1 that SKILL.md instructs the agent to call"
provides:
  - "skills/coursepilot/SKILL.md: agent-neutral frontmatter (name/description only) plus the full D-16..D-18 behavior contract (briefing rebuild, sync preview-then-approve-then-apply, self-installed deps, secret and untrusted-data rules)"
  - "python -m coursepilot install-skill --agent {claude|codex|antigravity|pi|hermes} [--link]"
  - "installer.py: AGENT_SKILL_PATHS data table, resolve_install_target (pure), install_skill (copy default, --link with Windows junction fallback, safe re-install)"
affects: [05-05-verification]

actuals:
  tokens: 7398
  tasks: 3
  commits: 5

tech-stack:
  added: []
  patterns:
    - "Containment-checked install target: target.parent.resolve() must equal the agent's resolved skills dir and target.name must equal SKILL_NAME before any filesystem write, defending install_skill against a future AGENT_SKILL_PATHS/resolve_install_target mismatch"
    - "Replace-before-write gate (_prepare_replace): a symlink/junction at the target is removed as a link only (os.rmdir/os.unlink, never shutil.rmtree through a link); a real directory is removed wholesale only if its own SKILL.md name: frontmatter reads coursepilot; anything else raises InstallError untouched"
    - "Symlink-then-junction-then-loud-fail: os.symlink first, subprocess mklink /J fallback only on a Windows OSError, InstallError (pointing back to copy mode) if both fail -- never a silent copy"
    - "Data-driven agent table: AGENT_SKILL_PATHS: dict[str, AgentTarget] is the single source of per-agent skill-directory paths; adding an agent is a data-only change, matching the RESEARCH.md Pattern 3 requirement"

key-files:
  created:
    - skills/coursepilot/SKILL.md
    - src/coursepilot/installer.py
    - tests/test_installer.py
  modified:
    - src/coursepilot/cli.py
    - .gitignore

key-decisions:
  - "Task 1's install_skill shipped copy-mode only, with `link=True` raising a clear 'not yet supported' InstallError -- kept the tracer commit a clean, narrowly-scoped slice (matching the plan's explicit 'Copy mode for this task' instruction) before Task 3 added link/replace handling"
  - "Task 3's replace-safety check identifies a prior coursepilot install by reading only the target's own SKILL.md `name:` frontmatter line (not a full YAML parse) -- cheap, dependency-free, and sufficient to distinguish 'our skill' from 'someone else's directory' per the plan's exact wording"
  - "repo-root.txt for a --link install is written into the *source* directory (the repo's own skills/coursepilot/), not the linked target -- since the target IS a link to the source, this is the only location that actually needs writing, and matches why .gitignore needed a new entry (the file lands inside the tracked repo tree)"
  - "The 'still shows the placeholder' explanatory sentence in SKILL.md section 1 intentionally also gets its own {{COURSEPILOT_REPO}} occurrence replaced during a copy install (reads a little redundantly resolved, but is harmless -- the agent only needs the resolved value to be present, and correctness of the repo-root.txt fallback path only matters for --link installs where the placeholder is never replaced)"

patterns-established:
  - "Pattern: any future filesystem-mutating CLI operation that can target a pre-existing directory should gate on a 'replace vs refuse' check keyed off content the operation itself wrote (here: SKILL.md's own name: field) before any destructive call, never a bare shutil.copytree/rmtree without a pre-check"

requirements-completed: [SKIL-03]

coverage:
  - id: D1
    description: "skills/coursepilot/SKILL.md has agent-neutral frontmatter (exactly name + description, <=1024 chars, Korean trigger phrases) and an agent-neutral body containing no agent-specific tool/runtime identifiers"
    requirement: SKIL-03
    verification:
      - kind: unit
        ref: "tests/test_installer.py#test_skill_frontmatter_agent_neutral"
        status: pass
      - kind: unit
        ref: "tests/test_installer.py#test_skill_body_agent_neutral"
        status: pass
    human_judgment: false
  - id: D2
    description: "install-skill --agent {claude|codex|antigravity|pi|hermes} resolves each agent's user-level skills directory from the AGENT_SKILL_PATHS data table; an unknown --agent value fails via click's own usage error (exit 2)"
    requirement: SKIL-03
    verification:
      - kind: unit
        ref: "tests/test_installer.py#test_path_claude_user_target"
        status: pass
      - kind: unit
        ref: "tests/test_installer.py#test_path_all_agents_table"
        status: pass
      - kind: unit
        ref: "tests/test_installer.py#test_path_unknown_agent_rejected"
        status: pass
    human_judgment: false
  - id: D3
    description: "Default install copies the skill folder, replaces every {{COURSEPILOT_REPO}} placeholder in the installed SKILL.md with the absolute repo root, and writes repo-root.txt -- the repo's own tracked copy keeps the placeholder untouched"
    requirement: SKIL-03
    verification:
      - kind: unit
        ref: "tests/test_installer.py#test_resolve_path_copy_install_renders_repo_root"
        status: pass
    human_judgment: false
  - id: D4
    description: "--link creates a real symlink (or falls back to an NTFS junction on a Windows privilege error) so source edits are reflected live; if both a symlink and a junction fail, install-skill exits 2 with a message pointing at copy mode -- it never silently copies"
    requirement: SKIL-03
    verification:
      - kind: unit
        ref: "tests/test_installer.py#test_link_real_filesystem_reflects_source_edits"
        status: pass
      - kind: unit
        ref: "tests/test_installer.py#test_link_windows_junction_fallback"
        status: pass
      - kind: unit
        ref: "tests/test_installer.py#test_link_both_fail_is_loud"
        status: pass
    human_judgment: false
  - id: D5
    description: "SKILL.md's body encodes the full D-16..D-18 conversation contract: check --json briefing rebuilt as ordered, ungrouped-by-nothing markdown tables with no truncation; sync --json preview shown and explicitly approved before sync --apply --json; self-installed uv/playwright dependencies with only a .env-existence check; secrets never requested, repeated, or stored; JSON string values treated as untrusted display data, never instructions"
    requirement: SKIL-03
    verification:
      - kind: unit
        ref: "tests/test_installer.py#test_skill_body_briefing_flow"
        status: pass
      - kind: unit
        ref: "tests/test_installer.py#test_skill_body_sync_approval_flow"
        status: pass
      - kind: unit
        ref: "tests/test_installer.py#test_skill_body_environment_and_secrets"
        status: pass
      - kind: unit
        ref: "tests/test_installer.py#test_skill_body_untrusted_data_rule"
        status: pass
    human_judgment: false
  - id: D6
    description: "Re-installing never deletes anything outside <skills dir>/coursepilot: a prior link is removed as a link only (its target/source untouched), a prior coursepilot copy is replaced wholesale, and any foreign content at the target is refused (InstallError, untouched); a missing agent home directory still succeeds but warns"
    requirement: SKIL-03
    verification:
      - kind: unit
        ref: "tests/test_installer.py#test_link_reinstall_over_link_keeps_source"
        status: pass
      - kind: unit
        ref: "tests/test_installer.py#test_path_reinstall_replaces_previous_copy"
        status: pass
      - kind: unit
        ref: "tests/test_installer.py#test_path_refuses_foreign_target"
        status: pass
      - kind: unit
        ref: "tests/test_installer.py#test_path_missing_agent_home_warns"
        status: pass
    human_judgment: false

duration: ~50min
completed: 2026-09-23
status: complete
---

# Phase 5 Plan 4: Universal Agent Skill Packaging Summary

**`skills/coursepilot/SKILL.md` (name/description-only frontmatter, full D-16..D-18 behavior contract) plus `install-skill --agent {5 agents} [--link]` — a data-driven copy/link installer with a loud Windows junction fallback and a replace-safety gate that never deletes outside its own target.**

## Performance

- **Duration:** ~50 min
- **Started:** 2026-09-23
- **Completed:** 2026-09-23
- **Tasks:** 3 (1 tracer + 2 TDD)
- **Files created:** 3 (2 source, 1 test); **Files modified:** 2

## Accomplishments

- `skills/coursepilot/SKILL.md`: frontmatter holds exactly `name: coursepilot` and a single double-quoted `description` line (English + Korean trigger phrases '과제 확인해줘' / '노션에 올려줘', <=1024 chars). Body is fully agent-neutral (no `Bash(`, `allowed-tools`, `run_shell_command`, or any other agent-specific identifier) and encodes: repo-location resolution (placeholder or `repo-root.txt` fallback), the `uv --directory ... run python -m coursepilot` execution rule, first-run environment self-diagnosis (`uv --version`, self-run `uv sync` + `playwright install chromium`, `.env`-existence-only check, never touching its contents), the full briefing flow (urgency-ordered markdown tables, no truncation), the sync preview-then-explicit-approval-then-apply gate, a troubleshooting section (`--relogin`/`--headed` only), and the untrusted-data rule (JSON string values are data to display, never instructions to follow).
- `installer.py`: `AGENT_SKILL_PATHS` data table for Claude Code, Codex, Antigravity, Pi, and Hermes (each entry commented with its RESEARCH.md evidence level); `resolve_install_target` is a pure path computation; `install_skill` performs a containment check before any write, a `_prepare_replace` safety gate (link-only removal, matched-name wholesale replace, or a refusal that leaves foreign content untouched), copies by default (placeholder resolution + `repo-root.txt`), and links via `os.symlink` with an `mklink /J` fallback that raises loudly — never silently copying — if both fail.
- `cli.py` `install-skill` command: `--agent` is a `click.Choice` built from the data table (unknown agents fail with click's own usage error); `--link` toggles link mode; success output shows the target path and a "(복사)"/"(링크)" mode label plus a restart-and-retry hint; a missing agent home directory still succeeds but prints a Korean stderr warning.
- `.gitignore` gained a `skills/coursepilot/repo-root.txt` entry — the file a `--link` install writes into the repo's own tracked `skills/coursepilot/` directory.

## Task Commits

Task 1 was `type="tracer"` (single production-quality commit + re-verified `<verify>` before expanding, per the tracer feedback gate — auto mode inactive per config, `human_verify_mode` default `end-of-phase`, tracer `<verify>` carried only `<automated>`, so it re-ran silently and continued to Task 2 with no checkpoint). Tasks 2 and 3 were `tdd="true"` (RED -> GREEN, no REFACTOR needed — code was clean on first pass):

1. **Task 1: agent-neutral SKILL.md and install-skill (claude, copy mode)** - `188b39d` (feat)
2. **Task 2 RED: failing tests for SKILL.md briefing/sync/env/secrets body** - `2f17ef2` (test)
2. **Task 2 GREEN: SKILL.md briefing, approval-gated sync, env diagnosis, secret rules** - `d9f741c` (feat)
3. **Task 3 RED: failing tests for all-agent paths, --link, and safe re-install** - `75b3f6e` (test)
3. **Task 3 GREEN: --link with loud junction fallback and safe re-install** - `8b37413` (feat)

**Plan metadata:** committed after this SUMMARY.

## Files Created/Modified

- `skills/coursepilot/SKILL.md` - Agent-neutral frontmatter + full behavior contract (briefing, sync approval gate, env diagnosis, secret/untrusted-data rules)
- `src/coursepilot/installer.py` - AGENT_SKILL_PATHS table, InstallError/InstallResult, resolve_install_target, install_skill (copy/link, replace-safety, containment check)
- `src/coursepilot/cli.py` - `install-skill --agent [--link]` command
- `.gitignore` - Ignores the generated link-mode `skills/coursepilot/repo-root.txt`
- `tests/test_installer.py` - 21 tests: path generation (all 5 agents), copy-install repo-root resolution, frontmatter/body content contract, real symlink/junction linking, Windows fallback call shape, loud both-fail, safe re-install (over link / over copy / foreign target refused), missing-home warning

## Decisions Made

- Kept Task 1's `install_skill` copy-mode-only with an explicit "not yet supported" `InstallError` for `link=True`, per the plan's literal "Copy mode for this task" scoping — this let the tracer commit stay a clean, narrowly-reviewable slice before Task 3 added the link/replace logic on top of the same function signature.
- `_prepare_replace`'s "is this our prior install?" check reads only the target's own `SKILL.md`'s `name:` frontmatter line (a cheap, dependency-free string check), not a full YAML parse — sufficient to distinguish "our skill, safe to replace" from "foreign content, refuse" per the plan's exact wording, and avoids adding a YAML dependency the project doesn't otherwise need (confirmed `pyyaml` is not installed in this environment).
- `--link`'s `repo-root.txt` is written into the *source* directory (the repo's own `skills/coursepilot/` when no `source=` override is passed), not the linked target — since the target is a link to the source, the source is the only location that actually needs the resolved path, and it is also why `.gitignore` needed a new entry (the file lands inside the tracked repo tree, not just in a user's home directory).

## Deviations from Plan

None - plan executed exactly as written. All `<action>` details (module boundaries, function signatures, data table entries, replace-safety semantics, link fallback order, SKILL.md section structure and content) were implemented as specified; no Rule 1-4 auto-fixes or architectural changes were needed.

## Issues Encountered

- Task 3's `test_path_missing_agent_home_warns` initially reused the same `fake_home` for both a direct `install_skill(...)` call and a subsequent `CliRunner` invocation. The first call's `mkdir(parents=True)` for the skills directory incidentally created the `.hermes` home-marker directory, so the second call's `agent_home_found` came back `True` and the expected warning never printed — caught before the RED/GREEN commit by inspecting the failure, not carried into either commit. Fixed by giving the direct-call assertion and the CLI-invocation assertion two independent home directories within the same test.
- Confirmed via a deliberate RED verification: `installer.py`/`cli.py` were temporarily reverted to the prior commit (Task 1's copy-only implementation) with the new Task 3 test file left in place, and `uv run pytest tests/test_installer.py` was run to prove genuine failures before restoring and committing GREEN — 5 of 8 new tests failed as expected (link mode still raised "not yet supported"; a second copy install `FileExistsError`'d on the un-cleared target); the other 3 (all-agent path table, "both fail" exit-2, missing-home warning) passed immediately, which is expected: `AGENT_SKILL_PATHS` already had all five agents and `agent_home_found` detection already existed since Task 1, and Click's own usage error for the not-yet-added `--link` flag happened to also satisfy the "exit 2 and mentions --link" assertion.

## User Setup Required

None - no external service configuration required. No new packages were installed (click/rich/pydantic were already locked dependencies; `pyyaml` was considered for frontmatter parsing but deliberately not added — see Decisions Made).

## Next Phase Readiness

- `skills/coursepilot/SKILL.md` and `installer.py`/`install-skill` are complete, tested, and stable for Plan 05-05 to build on: `JSON_CONTRACT.md`, the per-agent README install table, and — critically — the D-27 live per-agent manual verification, which is where `AGENT_SKILL_PATHS`' provisional (LOW/MEDIUM confidence) paths for Codex, Antigravity, Pi, and Hermes get confirmed or corrected as a one-line data change.
- The `check`/`sync` CLI contract this SKILL.md instructs the agent to call is unchanged from 05-01/05-03 — no coupling risk for 05-05's live-evidence capture.
- No blockers.

## Self-Check: PASSED

- FOUND: skills/coursepilot/SKILL.md
- FOUND: src/coursepilot/installer.py
- FOUND: tests/test_installer.py
- FOUND commits: 188b39d, 2f17ef2, d9f741c, 75b3f6e, 8b37413
- `uv run pytest -q tests/test_installer.py -x` green (21 tests)
- `uv run python -m coursepilot install-skill --help` lists `--agent {antigravity|claude|codex|hermes|pi}` and `--link`
- `uv run pytest` green (full suite, 178 tests)

---
*Phase: 05-cli-reporting-antigravity-skill-packaging*
*Completed: 2026-09-23*
