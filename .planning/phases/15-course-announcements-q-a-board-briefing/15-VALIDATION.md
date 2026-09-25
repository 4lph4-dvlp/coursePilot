---
phase: "15"
slug: "course-announcements-q-a-board-briefing"
status: ready
nyquist_compliant: true
wave_0_complete: false
created: "2026-09-26"
---

# Phase 15 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-mock |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/test_board_*.py tests/test_cli_board.py` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_board_*.py tests/test_cli_board.py`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 15-01-01 | 01 | 1 | BRD-01, BRD-02 | — | Pydantic schema validation & strict models | unit | `uv run pytest tests/test_board_parser.py` | ❌ W0 | ⬜ pending |
| 15-01-02 | 01 | 1 | BRD-01 | T-15-01 | Safe text cleaning & CP949 encoding safety | unit | `uv run pytest tests/test_board_text_converter.py` | ❌ W0 | ⬜ pending |
| 15-01-03 | 01 | 1 | BRD-02 | T-15-02 | Atomic replace & LRU 200 entry capping | unit | `uv run pytest tests/test_board_read_state.py` | ❌ W0 | ⬜ pending |
| 15-02-01 | 02 | 2 | BRD-01, BRD-02 | — | Course error isolation & mock session runner | integration | `uv run pytest tests/test_board_runner.py` | ❌ W0 | ⬜ pending |
| 15-02-02 | 02 | 2 | BRD-01, BRD-02 | T-15-03 | Safe attachment downloads & Rich console rendering | integration | `uv run pytest tests/test_board_runner.py tests/test_cli_board.py` | ❌ W0 | ⬜ pending |
| 15-02-03 | 02 | 2 | BRD-01, BRD-02 | — | CLI exit codes (0/1/2) & schema_version: 1 JSON contract | integration | `uv run pytest tests/test_cli_board.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_board_parser.py` — stubs for BRD-01, BRD-02 board discovery, table parsing, and article detail parsing
- [ ] `tests/test_board_text_converter.py` — stubs for BRD-01 HTML-to-Markdown conversion and summary previews
- [ ] `tests/test_board_read_state.py` — stubs for BRD-02 local read state manager and LRU 200 capping
- [ ] `tests/test_board_runner.py` — stubs for BRD-01, BRD-02 collection pipeline, filtering, and single article viewer
- [ ] `tests/test_cli_board.py` — stubs for BRD-01, BRD-02 CLI subcommands (`board`, `notices`, `qna`) and `--json` contract

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real LMS live board inspection & Rich briefing | BRD-01, BRD-02 | Requires real student credentials and active course enrolments | Run `kau-assistant board` and verify announcements and Q&A from enrolled courses render cleanly in terminal without CP949 errors. Test `kau-assistant notices --unread-only` and `kau-assistant qna --my`. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending 2026-09-26
