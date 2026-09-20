---
phase: "01"
slug: "foundation-session-management"
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-09-21"
---

# Phase 01 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-mock |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `uv run pytest tests/test_config.py tests/test_course_mapping.py -q` |
| **Full suite command** | `uv run pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_config.py tests/test_course_mapping.py -q`
- **After every plan wave:** Run `uv run pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | CONF-01 | T-01-01 | .env secrets not logged or committed | unit | `uv run pytest tests/test_config.py -k "test_env_loading"` | ❌ W0 | ⬜ pending |
| 01-01-02 | 01 | 1 | CONF-02 | — | Course name fallback without crashing | unit | `uv run pytest tests/test_course_mapping.py` | ❌ W0 | ⬜ pending |
| 01-02-01 | 02 | 2 | SCRP-01 | T-01-02 | Credentials isolated from git, secure login | unit | `uv run pytest tests/test_auth.py` | ❌ W0 | ⬜ pending |
| 01-02-02 | 02 | 2 | CONF-03 | T-01-03 | Cache invalidation on expired session | unit | `uv run pytest tests/test_session_manager.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/conftest.py` — shared fixtures for mock Page, mock Context, temp directories
- [ ] `tests/test_config.py` — stubs for CONF-01
- [ ] `tests/test_course_mapping.py` — stubs for CONF-02
- [ ] `tests/test_auth.py` — stubs for SCRP-01
- [ ] `tests/test_session_manager.py` — stubs for CONF-03
- [ ] Framework install: `uv add --dev pytest pytest-mock pytest-asyncio`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real LMS Login with live credentials | SCRP-01 | Requires active student KAU LMS credentials not stored in test repo | Run `uv run python -m kau_lxp.cli login --headful` and verify browser navigates to dashboard |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
