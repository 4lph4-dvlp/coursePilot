---
phase: 05-cli-reporting-antigravity-skill-packaging
plan: 06
status: completed
date: 2026-09-24
gap_ids: [G-05-3]
---

# Plan 05-06 Summary: LXP Login Recognition, Markup Shape Probe, Date Parsing & Assessment Header Mapping

## Overview

Plan 05-06 closed the LXP login recognition, date parsing, and assessment title mapping defects identified in UAT gap G-05-3 (items a, b, c). It also executed a read-only live markup shape probe on `https://lxp.kau.ac.kr` and documented the real redacted shapes in `.planning/debug/05-uat-lms-gaps.md`.

## Key Changes

1. **Authentication (`src/coursepilot/auth.py`, `src/coursepilot/session_manager.py`)**:
   - Implemented public `is_logged_in(page, timeout=5000) -> bool` helper.
   - Recognizes authentication if any `LOGGED_IN_SELECTORS` element is visible, or if an attached `a[href*='logout']` element is present in the DOM while `body.notloggedin` is absent.
   - Updated `perform_login` and `SessionManager._check_authenticated` to delegate to `is_logged_in`.

2. **Live Shape Probe (`.planning/debug/05-uat-lms-gaps.md`)**:
   - Performed read-only probe using session authentication on `https://lxp.kau.ac.kr`.
   - Recorded strictly redacted markup shapes (Login, /my/ dashboard, Course home VOD sections, Progress page, Assessment index pages) with all IDs, dates, durations, and text masked.
   - Confirmed 7 distinct courses, verified wait selector states, discovered avatar/text-truncate structure, VOD section hierarchy, and table headers.

3. **Date Parser (`src/coursepilot/scraper/date_parser.py`)**:
   - Added `_adjust_12_hour` helper for AM/PM and 오전/오후 12-hour conversion.
   - Updated Korean date pattern to handle optional weekday tokens and 오전/오후 markers.
   - Added Moodle long-form pattern (`화요일, 6 10월 2026, 1:00 PM` and English variants `Tuesday, 6 October 2026, 1:00 PM`) supporting 12-hour and 24-hour clocks.

4. **Assessment Parser (`src/coursepilot/scraper/assessment_parser.py`)**:
   - Implemented deadline-first header column mapping (due -> submission -> grade -> title).
   - Prevents `시험 마감` from being captured as title; correctly maps `이름` to title and `시험 마감` to due date.
   - Header roles missing from the header default to None when headers are detected.
   - Added numeric grade check so that rows with numeric score cells (e.g. `8.00`) are marked as `SubmissionStatus.GRADED`.

5. **Fixtures & Tests (`tests/fixtures/lms_quiz_index.html`, `tests/test_auth.py`, `tests/test_session_manager.py`, `tests/test_date_parser.py`, `tests/test_assessment_parser.py`)**:
   - Added synthetic LXP quiz index fixture.
   - Added unit tests for LXP attached logout detection, 12-hour/Moodle long-form date parsing, and deadline-first quiz index parsing reaching check reports.

## Verification

- `uv run pytest -q tests/test_auth.py tests/test_session_manager.py tests/test_date_parser.py tests/test_assessment_parser.py -x` passed (38 tests).
- Automated debug leak test passed (`section True id_leak False`).
- Full test suite passed (197 tests passed).
