---
phase: 05-cli-reporting-antigravity-skill-packaging
plan: 07
status: completed
date: 2026-09-24
gap_ids: [G-05-3, G-05-1b, G-05-2]
---

# Plan 05-07 Summary: Clean Course Names, Attached Dashboard Wait & Unsupported LMS Detection

## Overview

Plan 05-07 resolved the course name corruption (professor surname badge prefix), eliminated the 15-second dashboard wait timeout, and enforced loud failure (`UnsupportedLmsError`, exit code 2) when targeting non-Coursemos sites.

## Key Changes

1. **Course Name Extraction (`src/coursepilot/scraper/course_list.py`)**:
   - Added `_derive_course_title(a: Tag) -> str` to strip badge/avatar/professor elements (such as `div.csms-avata`) and prioritize dedicated title elements (`.text-truncate`, `.course-title`, `.coursename`, `h3`-`h5`).
   - Prevents professor surname badges from prepending course names (e.g. `샘플과목II` instead of `홍샘플과목II`).
   - Preserves existing division, term, and bracket stripping via `clean_course_name`.

2. **Attached Dashboard Wait (`src/coursepilot/scraper/course_list.py`)**:
   - Replaced 15-second selector wait with a fast attached wait:
     `page.wait_for_selector("a[href*='/course/view.php?id=']", state="attached", timeout=5000)`.
   - Eliminates the 15-second stall when course elements are in hidden containers or load asynchronously.
   - Retained try/except fallback to parse whatever is in `page.content()` if the wait times out.

3. **Coursemos Structure Detection (`src/coursepilot/scraper/course_list.py`)**:
   - Added public `looks_like_coursemos(html: str) -> bool` checking for Moodle/Coursemos indicators (`M.cfg`, `/theme/`, `page-`, `pagelayout-`, `coursemos`, `moodle`, `ubion`).
   - If zero courses are discovered and the page does not look like Coursemos, `extract_courses` raises `UnsupportedLmsError`.
   - If zero courses are discovered on a valid Coursemos page, returns `[]` so that Plan 05-08's `no_courses_found` notice is issued.

4. **Fixtures & Tests (`tests/fixtures/lms_dashboard.html`, `tests/test_course_list.py`)**:
   - Created synthetic `lms_dashboard.html` fixture reproducing the probed LXP card structure with placeholder course titles and badge text.
   - Added unit and integration tests for clean name extraction, duplicate deduplication, attached selector waiting, Coursemos marker classification, empty list handling, and end-to-end fatal CLI check error response.

## Verification

- `uv run pytest -q tests/test_course_list.py tests/test_cli.py -x` passed (34 tests).
- Full test suite: `uv run pytest -v` (214 passed in 6.48s).
