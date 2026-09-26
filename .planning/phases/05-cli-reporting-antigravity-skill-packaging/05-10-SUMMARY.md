---
phase: 05-cli-reporting-antigravity-skill-packaging
plan: 10
status: completed
date: 2026-09-24
gap_ids: [G-05-4, G-05-2]
---

# Plan 05-10 Summary: Hermes Install Path Fix, LMS_URL Onboarding & SKILL.md Guidance

## Overview

Plan 05-10 closed gaps G-05-4 (Hermes skill installation path) and G-05-2 (LMS_URL onboarding, documentation, and agent guidance). It implemented dynamic per-agent home directory resolution for Hermes (`HERMES_HOME`, Windows `%LOCALAPPDATA%\hermes`, and `~/.hermes`), added LMS_URL onboarding hints to CLI installation, updated `SKILL.md` to relay notices/errors and enforce the fresh-run rule, updated `.env.example` with explicit Coursemos LXP guidance, and updated `README.md`.

## Key Changes

1. **Installer Dynamic Home Resolution (`src/coursepilot/installer.py`)**:
   - Added `home_env_var` and `windows_localappdata_home` fields to `AgentTarget`.
   - Configured `hermes` to check `HERMES_HOME` first, then `%LOCALAPPDATA%\hermes` on Windows, falling back to `~/.hermes`.
   - Added pure helpers `resolve_agent_home` and `resolve_skills_dir` supporting keyword-only `env` and `platform` overrides.
   - Forwarded `env` and `platform` through `resolve_install_target` and `install_skill`.

2. **CLI Skill Installation Hint (`src/coursepilot/cli.py`)**:
   - Added a static guidance message to `install_skill_command` displaying `DEFAULT_LMS_URL` (`https://lxp.kau.ac.kr`) and explaining how students of other Coursemos-based institutions can set `LMS_URL` in `.env`.

3. **SKILL.md Guidance (`skills/coursepilot/SKILL.md`)**:
   - Updated description to document Coursemos/Moodle support and the default KAU LXP address while keeping trigger phrases and length restrictions.
   - Enforced rule in Section 2 to always execute a fresh CLI run and answer only from stdout JSON, never reusing stale result files.
   - Documented LMS_URL in Section 3, noting Coursemos compatibility and that Canvas/Blackboard are unsupported.
   - Instructed agents in Section 4 (before the one-line summary) to relay every `notices` item verbatim, with special instructions for `no_courses_found`.
   - Added `notices` relay instruction to Section 5 (Notion sync).
   - Documented `UnsupportedLmsError` and `AuthenticationError` in Section 6.

4. **Documentation & Environment Template (`README.md`, `.env.example`)**:
   - Updated `README.md` with an "LMS 주소 (LMS_URL)" section, a "문제 해결 (Troubleshooting)" section, and updated agent status columns.
   - Replaced `.env.example` with a clean, fully commented template setting `LMS_URL=https://lxp.kau.ac.kr` with Coursemos guidance and empty secret fields (approved by user).

5. **Tests (`tests/test_installer.py`, `tests/test_config.py`)**:
   - Added autouse isolation fixture in `test_installer.py` preventing writes to real agent directories.
   - Added unit tests for Hermes environment precedence (`HERMES_HOME` vs `LOCALAPPDATA` vs fallback), CLI hints, and SKILL.md body rules.
   - Added tests in `test_config.py` verifying that `.env.example` sets `LMS_URL == DEFAULT_LMS_URL` with empty secrets and loads cleanly into `Settings`.

## Verification

- `uv run pytest -q tests/test_installer.py tests/test_contract_doc.py tests/test_config.py -x` passed (45 tests).
- Full test suite: `uv run pytest -v` (237 passed in 8.13s).
- Verified `git diff --stat` touches `.env.example` but touches no real `.env` file.
