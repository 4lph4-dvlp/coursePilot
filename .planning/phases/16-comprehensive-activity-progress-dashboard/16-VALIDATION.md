---
phase: "16"
slug: "comprehensive-activity-progress-dashboard"
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-09-26"
---

# Phase 16 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (via uv) |
| **Config file** | pyproject.toml |
| **Quick run command** | `uv run pytest tests/test_progress_calculator.py tests/test_progress_models.py` |
| **Full suite command** | `uv run pytest tests/test_progress_*.py tests/test_cli_progress.py` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_progress_*.py`
- **After every plan wave:** Run `uv run pytest tests/test_progress_*.py tests/test_cli_progress.py`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 16-01-01 | 01 | 1 | PROG-01 | — | N/A | unit | `uv run pytest tests/test_progress_models.py tests/test_assessment_parser.py` | ❌ W0 | ⬜ pending |
| 16-01-02 | 01 | 1 | PROG-01 | — | N/A | unit | `uv run pytest tests/test_progress_calculator.py` | ❌ W0 | ⬜ pending |
| 16-02-01 | 02 | 2 | PROG-01, PROG-02 | — | Read-only LMS/Notion isolation, safe error handling | integration | `uv run pytest tests/test_progress_runner.py` | ❌ W0 | ⬜ pending |
| 16-02-02 | 02 | 2 | PROG-02 | — | No credential/cookie leakage in terminal output | unit | `uv run pytest tests/test_progress_reporter.py` | ❌ W0 | ⬜ pending |
| 16-02-03 | 02 | 2 | PROG-02 | — | Stream separation, clean JSON contract, exit codes | cli | `uv run pytest tests/test_cli_progress.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_progress_models.py` — DTOs, JSON schema_version: 1 contract, ActivityBreakdown verification
- [ ] `tests/test_progress_calculator.py` — Current week detection (date + .current), open/past/semester rates, missed item detection
- [ ] `tests/test_progress_runner.py` — Single-trip scraping, 10-minute cache management, per-course error isolation
- [ ] `tests/test_progress_reporter.py` — 3-section Rich rendering, ProgressBar colors, To-Do prioritization, Alert/All-Clear badge
- [ ] `tests/test_cli_progress.py` — CLI progress command, stderr spinner separation, exit codes

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live LXP Interactive Dashboard | PROG-02 | Requires live student session with real registered courses | Run `coursepilot progress` in terminal and visually check 3-section layout and color progress bars |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending 2026-09-26
