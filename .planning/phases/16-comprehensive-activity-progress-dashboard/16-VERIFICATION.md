---
phase: 16-comprehensive-activity-progress-dashboard
verified: 2026-09-26T01:42:00Z
status: passed
score: 6/6 must-haves verified
behavior_unverified: 0
overrides_applied: 0
human_verification: []
re_verification: null
---

# Phase 16: Comprehensive Activity Progress Dashboard Verification Report

**Phase Goal:** 학생이 수강 중인 모든 과목의 4대 핵심 학습 활동(동영상 강의, 과제, 퀴즈, 학습자료) 진척도를 종합 집계하여, 이번 주차 마감 중심의 3단 분할 Rich 대시보드와 `schema_version: 1` JSON 계약, 10분 TTL 원자적 캐시, 단일 CLI 진입점(`coursepilot progress`)을 제공
**Verified:** 2026-09-26T01:42:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | PROG-01, D-16-01, D-16-12: 4대 활동(VOD, 과제, 퀴즈, 학습자료) 통합 DTO(`ActivityItem`), 세부 달성률(`ActivityBreakdown`), 계층형 JSON 계약(`schema_version: 1`, `extra="forbid"`)이 엄격하게 검증된다 | ✓ VERIFIED | `src/coursepilot/progress/models.py` defines `ActivityItem`, `ActivityBreakdown`, `CourseProgress`, `DashboardSummary`, and `ProgressReport` with `SCHEMA_VERSION = 1` and `extra="forbid"`; `tests/test_progress_models.py` (4 tests) pass with round-trip JSON validation. |
| 2 | PROG-01, D-16-01: `AssessmentItem`에 `week_number` 메타데이터가 보존되고 `parse_assessment_list`가 테이블 헤더(주/주차/Week)를 감지하여 주차 번호를 추출한다 | ✓ VERIFIED | `src/coursepilot/scraper/models.py` adds `week_number: int | None = None`; `parse_assessment_list` parses week column with regex `(\d+)`; `tests/test_assessment_parser.py` asserts `items[0].week_number == 1` and `items[1].week_number == 2`. |
| 3 | PROG-01, D-16-02: 날짜 범위와 `.current` 클래스를 결합한 하이브리드 방식으로 오늘 날짜가 속한 이번 주차(Current Week)를 정확히 판별한다 | ✓ VERIFIED | `detect_current_week` in `calculator.py` matches `start_date <= now <= end_date`, falls back to `.current` boolean, then to minimum positive week; `tests/test_progress_calculator.py` verifies all 3 detection tiers. |
| 4 | PROG-01, D-16-03, D-16-04, Pitfall 1, Pitfall 2: 현재 주차 오픈 기준 메인 진도율과 학기 전체 보조 진도율을 분리 산출하고, 1~Current-1주차 미완료 건을 결석/미제출 누락으로 산출하며, 1주차 실행 시 누락 건수 0건/과거 이수율 100%로 안전하게 처리한다 | ✓ VERIFIED | `calculate_course_progress` in `calculator.py` separates `current_open_rate` (weeks <= current), `past_weeks_rate` (weeks < current), and `semester_overall_rate` (all 16 weeks); Week 1 boundary safe; `tests/test_progress_calculator.py` verifies all edge cases. |
| 5 | PROG-01, D-16-13, D-16-14, D-16-16: 과목 홈 HTML 1회 방문으로 동영상, 학습자료, 주차 메타데이터를 동시 추출하고, 10분 TTL 원자적 로컬 캐시(`progress_cache.json`) 및 과목별 독립 예외 격리를 보장한다 | ✓ VERIFIED | `runner.py` implements `extract_course_sections_meta`, `load_progress_cache`, `save_progress_cache` via `.tmp -> replace`, and per-course try-except error isolation returning `partial_success`; `tests/test_progress_runner.py` (6 tests) pass. |
| 6 | PROG-02, D-16-05, D-16-06, D-16-07, D-16-08, D-16-09, D-16-10, D-16-11, D-16-15: 3단 분할 대시보드([1] 요약 테이블, [2] To-Do 우선 점검, [3] 과거 누락 경고/올클리어 배지), 색상 코딩 프로그레스 스타일, 1~16주차 전 주차 로드맵 매트릭스(`--course`), 단일 CLI `coursepilot progress`, stderr 스피너 분리 및 stdout 순수 리포트/JSON 출력을 완비한다 | ✓ VERIFIED | `reporter.py` renders 3-tier layout, To-Do sorting with `[VOD]`, `[과제]`, `[퀴즈]`, `[자료]` tags, Alert vs All-Clear panels, and `render_course_matrix`; `cli.py` registers `progress` with stderr progress callback and stdout JSON contract; `tests/test_progress_reporter.py` and `tests/test_cli_progress.py` pass. |

**Score:** 6/6 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/coursepilot/scraper/models.py` | Enhanced AssessmentItem with backward-compatible week_number | ✓ VERIFIED | `week_number: int | None = None` added. |
| `src/coursepilot/scraper/assessment_parser.py` | parse_assessment_list with week column recognition | ✓ VERIFIED | Mapped week header ("주차", "주", "Week") and regex extraction. |
| `src/coursepilot/progress/__init__.py` | Package exports for progress models and calculation functions | ✓ VERIFIED | Exports all domain DTOs, calculation functions, and constants. |
| `src/coursepilot/progress/models.py` | Pydantic models for ActivityItem, ActivityBreakdown, CourseProgress, ProgressReport | ✓ VERIFIED | Strict `extra="forbid"` models with `SCHEMA_VERSION: Literal[1] = 1`. |
| `src/coursepilot/progress/calculator.py` | Pure calculation engine for hybrid week detection and multi-tier rates | ✓ VERIFIED | Implemented `detect_current_week`, `compute_breakdown`, `calculate_course_progress`, `aggregate_dashboard_summary`. |
| `src/coursepilot/progress/runner.py` | Collection pipeline with single-trip HTML parsing, 10m TTL cache, and error isolation | ✓ VERIFIED | Implemented `load_progress_cache`, `save_progress_cache`, `run_progress_pipeline`. |
| `src/coursepilot/progress/reporter.py` | Rich terminal 3-tier visualizer, color progress bars, To-Do highlighting, matrix roadmap | ✓ VERIFIED | Implemented `render_progress_dashboard`, `render_course_matrix`, `render_detailed_activities`. |
| `src/coursepilot/reporter.py` | Re-exports progress rendering functions for unified reporting interface | ✓ VERIFIED | Re-exports `render_progress_dashboard`, `render_course_matrix`, `render_detailed_activities`. |
| `src/coursepilot/cli.py` | Click CLI progress command with all options, stream separation, and exit codes | ✓ VERIFIED | Registered `coursepilot progress` command with `--course`, `--week`, `--detail`, `--cached`, `--refresh`, `--json`. |
| `tests/test_progress_models.py` | Unit tests for progress DTOs, validation, and JSON contract | ✓ VERIFIED | 4 tests passing. |
| `tests/test_progress_calculator.py` | Unit tests for week detection, dual rates, past missed items, and Week 1 edge cases | ✓ VERIFIED | 9 tests passing. |
| `tests/test_progress_runner.py` | Integration tests for progress pipeline runner, cache TTL, and error isolation | ✓ VERIFIED | 6 tests passing. |
| `tests/test_progress_reporter.py` | Unit tests for Rich terminal dashboard layouts, colors, To-Do ordering, and Alert panels | ✓ VERIFIED | 7 tests passing. |
| `tests/test_cli_progress.py` | CLI tests for progress command, options, stream separation, JSON contract, and exit codes | ✓ VERIFIED | 6 tests passing. |

### Test Summary

- Phase 16 targeted suite: 32 passed in 1.48s across 5 test modules (`tests/test_progress_*.py`, `tests/test_cli_progress.py`).
- Project regression suite: `uv run pytest` -> 395 passed in 13.77s (0 failed, 0 regressions).
