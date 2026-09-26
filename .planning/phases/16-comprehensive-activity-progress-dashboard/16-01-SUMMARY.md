---
phase: 16-comprehensive-activity-progress-dashboard
plan: "01"
subsystem: progress
tags:
  - models
  - progress
  - calculator
  - week-detection
  - pydantic
requires: []
provides:
  - progress-domain-models
  - progress-calculation-engine
  - assessment-week-parser
  - hybrid-week-detection
affects:
  - "16-02"
tech-stack.added: []
patterns:
  - Dynamic column mapping for week numbers
  - Strict JSON contract with extra='forbid'
  - Hybrid week detection (date range -> .current -> fallback)
  - Multi-tier dual progress rates (open vs semester)
  - Strict past weeks missed activity accounting
key-files.created:
  - src/kau_assistant/progress/__init__.py
  - src/kau_assistant/progress/models.py
  - src/kau_assistant/progress/calculator.py
  - tests/test_progress_models.py
  - tests/test_progress_calculator.py
key-files.modified:
  - src/kau_assistant/scraper/models.py
  - src/kau_assistant/scraper/assessment_parser.py
  - tests/test_assessment_parser.py
key-decisions:
  - "D-16-01: Defined 4-tier activity breakdown (VOD, assignment, quiz, material) with counts and completion percentages."
  - "D-16-02: Implemented hybrid week detection combining date-range boundaries, LMS .current class, and minimum week fallback."
  - "D-16-03: Strict past weeks missed accounting treating uncompleted items from weeks 1 to current-1 as missed/absent."
  - "D-16-04: Separated current open progress rate (main metric) from semester overall rate (auxiliary metric) to prevent future week distortion."
  - "D-16-07: Prioritized this week To-Do activities by due date ascending with completed items trailing at bottom."
  - "D-16-12: Enforced schema_version: 1 and extra='forbid' on ProgressReport JSON contract."
  - "Pitfall 1: Handled Week 1 boundary safely with 0 past items, 100% past rate, and empty missed list."
requirements:
  - PROG-01
coverage:
  - deliverable: "AssessmentItem week_number extraction and table parser"
    human_judgment: false
    verification:
      kind: test
      ref: "tests/test_assessment_parser.py#test_parse_assessment_list"
      status: pass
  - deliverable: "Progress domain models and schema_version: 1 JSON contract"
    human_judgment: false
    verification:
      kind: test
      ref: "tests/test_progress_models.py#test_progress_report_json_contract"
      status: pass
  - deliverable: "Hybrid week detection engine"
    human_judgment: false
    verification:
      kind: test
      ref: "tests/test_progress_calculator.py#test_detect_current_week_by_date"
      status: pass
  - deliverable: "Multi-tier dual progress rates & Week 1 boundary safety"
    human_judgment: false
    verification:
      kind: test
      ref: "tests/test_progress_calculator.py#test_week_1_boundary_past_weeks_all_clear"
      status: pass
  - deliverable: "This Week To-Do prioritization and due date sorting"
    human_judgment: false
    verification:
      kind: test
      ref: "tests/test_progress_calculator.py#test_current_week_todo_sorting"
      status: pass
---

# Phase 16 Plan 01 Summary: Progress Models & Calculation Engine

## Key Achievements
1. **Enhanced Assessment Parser**: Added `week_number: int | None = None` to `AssessmentItem` and enabled `parse_assessment_list` to recognize table header columns matching "주차", "주", or "Week".
2. **Domain Models & DTOs**: Created `ActivityItem`, `ActivityBreakdown`, `CourseProgress`, `DashboardSummary`, and `ProgressReport` with `schema_version: 1` and `extra="forbid"`.
3. **Hybrid Week Detection**: Implemented `detect_current_week` using date-range verification against current KST time, LMS `.current` class detection, and positive week fallback.
4. **Multi-Tier Progress Metrics**:
   - `current_open_rate`: Main KPI measuring completion against currently available activities (weeks <= current).
   - `past_weeks_rate`: Cumulative completion across past weeks (weeks < current) with strict missed items accounting.
   - `semester_overall_rate`: Auxiliary KPI over all 16 weeks of the semester.
   - Week 1 boundary edge case handled safely with 100% past rate and 0 missed items.
5. **To-Do Prioritization**: Sorted current week activities to display incomplete items first by deadline ascending, followed by completed items.

## Verification
- `uv run pytest tests/test_progress_models.py tests/test_progress_calculator.py tests/test_assessment_parser.py`: 21 passed.
- Full project test suite: 376 passed.
