---
phase: 07-vod-attendance-completion
plan: 01
status: completed
date: 2026-09-24
---

# Plan 07-01 Summary: VOD Activity & Attendance Completion Tracking

## Overview

Plan 07-01 resolved the issue where VOD video lectures lacked completion tracking and were omitted from task lists. It hooked up the real KAU LXP activity completion page (`/report/ublogs/completion.php?id={course_id}`), parsed the `table-learning-student-activity` records into per-activity completion statuses (`완료` -> `COMPLETED`, `미완료` -> `INCOMPLETE`), merged them with course-home VODs, and allowed undated regular lectures to reach task tracking with priority P3 in the `later` section while excluding introductory/OT videos without deadlines.

## Key Accomplishments

1. **Ublogs Completion Navigation (`src/coursepilot/scraper/navigator.py`)**:
   - Updated `CourseNavigator.navigate_progress_page` to try `/report/ublogs/completion.php?id={course.course_id}` first with detection of `table-learning-student-activity`, `학습활동`, or `완료 상태`.
   - Kept fallback to `/report/ubcompletion/progress.php?id={course.course_id}` for environments using the alternative Coursemos completion plugin.

2. **Ublogs Activity Completion Parser & Merger (`src/coursepilot/scraper/lecture_parser.py`)**:
   - Implemented `UblogsActivityStatus` Pydantic model.
   - Implemented `parse_ublogs_completion(html: str) -> list[UblogsActivityStatus]` to parse multi-column activity completion tables.
   - Implemented `merge_ublogs_completion(lectures, ublogs_records, now)` with multi-tier matching (exact/normalized title within same week, across weeks, and order fallback). Completed activities become `AttendanceStatus.COMPLETED` (100% progress), while incomplete activities remain `INCOMPLETE` (0% progress).

3. **Pipeline Integration (`src/coursepilot/pipeline.py`)**:
   - Connected `scrape_course` to detect ublogs activity completion tables and merge records into course lectures.

4. **Transformer Handling for Undated Lectures (`src/coursepilot/domain/transformer.py`)**:
   - Retained regular incomplete lectures without explicit deadlines (`week_number >= 1`) as `SyncTask` items with `due_date=None` and Priority `P3`, allowing them to appear in the `later` section.
   - Correctly excluded undated OT/introductory lectures (`week_number == 0` or matching orientation/overview keywords) per rule D-11.
   - Excluded completed undated lectures by default.

5. **Unit & Integration Test Coverage**:
   - Updated `tests/test_navigator.py` to verify ublogs primary navigation and ubcompletion fallback.
   - Added `test_parse_ublogs_completion` and `test_merge_ublogs_completion` in `tests/test_lecture_parser.py`.
   - Added `test_transform_undated_incomplete_lecture_becomes_p3_task` and `test_transform_undated_completed_lecture_is_excluded` in `tests/test_transformer.py`.
   - Full test suite: 244 passed in 12.18s.

## Verification

- `uv run pytest tests/test_lecture_parser.py tests/test_transformer.py tests/test_navigator.py` (all passed)
- Full regression suite `uv run pytest` (244 passed)
