---
phase: 05-cli-reporting-antigravity-skill-packaging
plan: 09
status: completed
date: 2026-09-24
gap_ids: [G-05-1, G-05-3]
---

# Plan 05-09 Summary: LXP Course Home VOD Deadlines, Deduplication & Ubcompletion Progress Merging

## Overview

Plan 05-09 closed gaps G-05-1 and G-05-3 (item e). It resolved VOD period deadline extraction on Coursemos LXP sites (`span.displayoptions > span.text-ubstrap`), eliminated nested section duplication and invented week numbers, and implemented lecture completion scraping and merging from `/report/ubcompletion/progress.php` (`table.user_progress`).

## Key Changes

1. **Course Section Parser Rewrite (`src/coursepilot/scraper/lecture_parser.py`)**:
   - Filtered candidate sections to top-level `li` containers only (dropping nested containers that caused 49-fold duplication).
   - Extracted week numbers primarily from section headings (`.sectionname`, `.section-title`, `h3`-`h5`), falling back to section ID numbers or ordinals.
   - Deduped VOD activities by module ID (`module-<N>` or `id=` parameter).
   - Removed `.accesshide` elements (e.g. trailing " 동영상" labels) from lecture titles.
   - Extracted period dates from `span.displayoptions span.text-ubstrap` and passed them to `parse_lms_date` so the range end becomes the `due_date`.
   - Numbered clips 1..n per week across the page.

2. **Coursemos Progress Parser & Merge (`src/coursepilot/scraper/lecture_parser.py`)**:
   - Added `LectureProgress` model with week, title, module ID, required/studied seconds, and completion flag.
   - Implemented `_parse_duration_seconds` supporting `HH:MM:SS`, `MM:SS`, and Korean `N시간 N분 N초` formats.
   - Implemented `parse_ubcompletion_progress` for `table.user_progress` handling row-spanned week cells across multiple clips.
   - Implemented `merge_lecture_progress` matching by module ID, then normalized title within the same week, then per-week ordinal fallback.
   - Lectures completed in progress reports (`studied >= required > 0`) are set to `COMPLETED` and excluded from tasks by `transformer`.

3. **Navigator & Pipeline Wiring (`src/coursepilot/scraper/navigator.py`, `src/coursepilot/pipeline.py`)**:
   - Updated `CourseNavigator.navigate_progress_page` to target `/report/ubcompletion/progress.php?id=<course_id>` and accept `table.user_progress`.
   - Updated `scrape_course` in `pipeline.py` to parse course-section lectures first, then merge ubcompletion progress, and fall back to legacy `progress_report.html` only when both are absent.

4. **Fixtures & Tests (`tests/fixtures/lms_course_home.html`, `tests/fixtures/lms_ubcompletion_progress.html`, `tests/test_lecture_parser.py`, `tests/test_navigator.py`, `tests/test_pipeline.py`)**:
   - Created synthetic `lms_course_home.html` fixture with nested sections and `text-ubstrap` periods.
   - Created synthetic `lms_ubcompletion_progress.html` fixture with row-spanned week cells and duration columns.
   - Added comprehensive tests for section deduping, deadline extraction, accesshide removal, rowspan parsing, duration formatting, progress merging, and end-to-end task generation.

## Verification

- `uv run pytest -q tests/test_navigator.py tests/test_pipeline.py tests/test_lecture_parser.py -x` passed (34 tests).
- Full test suite: `uv run pytest -v` (225 passed in 6.81s).
