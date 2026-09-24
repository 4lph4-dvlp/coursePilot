---
phase: 06-quiz-submission-enrichment
plan: 01
status: completed
date: 2026-09-24
---

# Plan 06-01 Summary: Hidden-Grade Quiz Attempt Status Enrichment

## Overview

Plan 06-01 resolved the issue where quizzes with hidden grades (such as 기초전자실험 W01, W02, W03) were incorrectly flagged as `NOT_ATTEMPTED` and `OVERDUE`. It implemented quiz attempt inspection via the quiz view page (`/mod/quiz/view.php?id=...`), detecting submission completion markers such as `"답안 검토"`, `"응시 가능 횟수를 초과하여 더 이상 응시할 수 없습니다."`, and attempt status `"완료됨"`.

## Key Accomplishments

1. **Quiz Attempt Inspection Function (`src/kau_assistant/scraper/assessment_parser.py`)**:
   - Implemented pure function `is_quiz_attempt_completed(html: str) -> bool`.
   - Inspects review buttons/links (`답안 검토`, `Review attempt`), attempt exhaustion banners (`응시 가능 횟수를 초과하여 더 이상 응시할 수 없습니다`), and Moodle attempt summary table rows (`완료됨`, `Finished`, `Submitted`).
   - Integrated into `enrich_assessment_detail`: for quizzes with status `NOT_ATTEMPTED` or `DRAFT`, if attempt completion is detected on the view page, updates status to `SubmissionStatus.SUBMITTED` and sets `is_overdue = False`.

2. **Unit Tests & Fixture Coverage (`tests/test_assessment_parser.py`)**:
   - Added unit tests for `is_quiz_attempt_completed` verifying review buttons, attempt notices, attempt table rows, and unattempted quiz pages.
   - Added integration test `test_enrich_assessment_detail_marks_hidden_grade_quiz_as_submitted`.
   - Full test suite: 239 passed in 9.27s.

3. **Live LXP Verification**:
   - Executed live `check --json` against `lxp.kau.ac.kr`.
   - Verified `overdue` count dropped from 3 to 0.
   - Already-completed quizzes (기초전자실험 W01, W02, W03) are now correctly recognized as submitted and excluded from overdue tasks.
   - Pending future quiz (기초전자실험 W04, due 10/02) correctly remains in `later`.

## Verification

- `uv run pytest tests/test_assessment_parser.py` (8 passed)
- Full regression suite `uv run pytest` (239 passed)
- Live LXP verification confirmed zero false overdue quizzes.
