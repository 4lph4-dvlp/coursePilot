---
phase: "02"
slug: "lms-scraper-core"
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-09-21"
---

# Phase 02 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-mock + beautifulsoup4 |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `uv run pytest tests/test_course_list.py tests/test_date_parser.py -q` |
| **Full suite command** | `uv run pytest tests/ -v` |
| **Estimated runtime** | ~6 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick test suite (`uv run pytest tests/test_course_list.py tests/test_date_parser.py -q`)
- **After every plan wave:** Run full test suite (`uv run pytest tests/ -v`)
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | SCRP-02 | — | Pydantic scraper data models validation | unit | `uv run pytest tests/test_scraper_models.py` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | SCRP-02 | T-02-01 | Dashboard course list extraction & term filtering | unit | `uv run pytest tests/test_course_list.py` | ❌ W0 | ⬜ pending |
| 02-01-03 | 01 | 1 | SCRP-02 | T-02-02 | Smart wait, sequential navigation & debug dump on failure | unit | `uv run pytest tests/test_navigator.py tests/test_debug_dump.py` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 2 | SCRP-03 | — | Flexible date parser with Sunday fallback | unit | `uv run pytest tests/test_date_parser.py` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 2 | SCRP-03 | — | Lecture clips split & hybrid attendance/progress parsing | unit | `uv run pytest tests/test_lecture_parser.py` | ❌ W0 | ⬜ pending |
| 02-02-03 | 02 | 2 | SCRP-04 | T-02-03 | Assessment item list, deep detail & submission status parsing | unit | `uv run pytest tests/test_assessment_parser.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/fixtures/dashboard_coursemos.html` — mock Coursemos dashboard HTML
- [ ] `tests/fixtures/progress_report.html` — mock lecture attendance & progress table
- [ ] `tests/fixtures/assignment_list.html` — mock assignment/quiz table
- [ ] `tests/fixtures/assignment_detail.html` — mock assignment detail description and attachments
- [ ] `tests/test_scraper_models.py` — unit tests for models
- [ ] `tests/test_course_list.py` — unit tests for SCRP-02 course extractor
- [ ] `tests/test_navigator.py` — unit tests for page navigation & error course skipping
- [ ] `tests/test_date_parser.py` — unit tests for date parsing & fallback
- [ ] `tests/test_lecture_parser.py` — unit tests for SCRP-03 lecture extractor
- [ ] `tests/test_assessment_parser.py` — unit tests for SCRP-04 assessment extractor
- [ ] Framework install: `uv add beautifulsoup4 lxml`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real LMS Live Crawling | SCRP-02, SCRP-03, SCRP-04 | Requires live active student enrollment on KAU LMS | Run integration script with live session and inspect extracted JSON items |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
