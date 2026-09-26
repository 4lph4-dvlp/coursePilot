---
phase: "05"
slug: "cli-reporting-antigravity-skill-packaging"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-09-23"
---

# Phase 05 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=8.0.0 + pytest-mock, pytest-asyncio |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (`testpaths = ["tests"]`, `pythonpath = ["src"]`) |
| **Quick run command** | `uv run pytest -q tests/test_cli.py tests/test_reporter.py tests/test_pipeline.py tests/test_installer.py -x` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest -q tests/test_<touched_module>.py -x`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd-verify-work`:** Full suite must be green, plus D-26 live-evidence checkpoint and D-27 per-agent manual skill-invocation checkpoint
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 05-01-xx | 01 | 1 | SKIL-01 | — | Report groups 기한 초과/24h/이후, no truncation, detail block only for urgent+errors | unit | `uv run pytest tests/test_reporter.py -k "grouping or truncat or detail" -x` | ❌ W0 | ⬜ pending |
| 05-01-xx | 01 | 1 | SKIL-01 | — | JSON contract is versioned Pydantic output; Korean not escaped | unit | `uv run pytest tests/test_reporter.py -k "json_contract" -x` | ❌ W0 | ⬜ pending |
| 05-01-xx | 01 | 1 | SKIL-02 | — | `check` never calls Notion; `sync` dry-run by default, writes only with `--apply` | behavioral | `uv run pytest tests/test_cli.py -k "dry_run or apply or no_notion" -x` | ❌ W0 | ⬜ pending |
| 05-01-xx | 01 | 1 | SKIL-02 | — | Config/login failure exit 2; per-course failure continues, exit 1 | behavioral | `uv run pytest tests/test_cli.py -k "exit_code" -x` | ❌ W0 | ⬜ pending |
| 05-01-xx | 01 | 1 | SKIL-02 | — | Progress/logs on stderr only; stdout carries report/JSON | behavioral | `uv run pytest tests/test_cli.py -k "stderr" -x` | ❌ W0 | ⬜ pending |
| 05-01-xx | 01 | 1 | SKIL-02 | T-05 | No LMS password / Notion token / session cookie in any output | unit | `uv run pytest tests/test_cli.py -k "redaction" -x` | ❌ W0 | ⬜ pending |
| 05-01-xx | 01 | 1 | SKIL-02 | — | Pipeline isolates per-course errors | unit | `uv run pytest tests/test_pipeline.py -x` | ❌ W0 | ⬜ pending |
| 05-02-xx | 02 | 2 | SKIL-03 | — | `install-skill --agent X` resolves correct path per data table | unit | `uv run pytest tests/test_installer.py -k "path" -x` | ❌ W0 | ⬜ pending |
| 05-02-xx | 02 | 2 | SKIL-03 | — | `--link` produces link/junction; falls back loudly if unsupported | unit (mocked FS) | `uv run pytest tests/test_installer.py -k "link" -x` | ❌ W0 | ⬜ pending |
| 05-02-xx | 02 | 2 | SKIL-03 | — | Installed SKILL.md resolves repo/CLI location from any cwd | unit | `uv run pytest tests/test_installer.py -k "resolve_path" -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_reporter.py` — stubs for SKIL-01
- [ ] `tests/test_cli.py` — stubs for SKIL-02 (CliRunner + mocked pipeline)
- [ ] `tests/test_pipeline.py` — per-course error isolation (D-08)
- [ ] `tests/test_installer.py` — stubs for SKIL-03 (tmp_path-based FS)

*No framework install needed — pytest, pytest-mock, pytest-asyncio already present.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real `check` and dry-run `sync` against live LMS/Notion | SKIL-01, SKIL-02 | Needs real credentials and live services (D-26) | Run `python -m coursepilot check` and `python -m coursepilot sync`; record evidence file |
| Skill install + natural-language invocation per agent | SKIL-03 | Needs each agent runtime installed (D-27) | For Claude Code, Codex, Antigravity, Pi, Hermes: `install-skill --agent X`, restart agent, ask in natural language, record result |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
