---
phase: 08-end-to-end-verification-agent-redeployment
plan: 01
status: completed
date: 2026-09-24
---

# Plan 08-01 Summary: End-to-End Verification & Agent Re-deployment

## Overview

Plan 08-01 successfully validated Milestone 2 enhancements against the live KAU LXP system (`https://lxp.kau.ac.kr`) and re-deployed the unified `coursepilot` skill to all 5 supported AI coding agents (Claude Code, Codex, Antigravity, Pi, Hermes).

## Key Accomplishments

1. **Relative Assessment Link Normalization Fix (`src/coursepilot/scraper/assessment_parser.py`)**:
   - Identified root cause where relative quiz URLs (`view.php?id=...`) were joined against `course.url` (`/course/view.php`), generating `/course/view.php?id=...` instead of `/mod/quiz/view.php?id=...`.
   - Fixed `parse_assessment_list` to prefix `/mod/quiz/` or `/mod/assign/` for relative view links, and passed module-specific index URLs from `scrape_course_assessments`.

2. **Live LXP Read-Only Verification**:
   - Executed live `check --json` across all 7 enrolled courses:
     - 공학수학II (1125)
     - 디지털시스템설계 (1113)
     - 자료구조및실습 (1129)
     - 전자컴퓨터세미나 (1102)
     - 확률및랜덤변수 (1114)
     - 기초전자실험 (1103)
     - 항공우주산업개론 (1478)
   - **Quiz status**: Overdue count dropped to 0 (`overdue_count: 0`, `overdue: []`). 기초전자실험 W01, W02, W03 quizzes are now recognized as completed (`SUBMITTED`) and excluded from overdue.
   - **VOD status**: VOD lectures (including 디지털시스템설계 4~10주차 lectures) are accurately tracked and presented in the `later` section.
   - **Urgent task**: `[기초전자실험] W03 결과보고서 제출함 제출` (due 2026-09-25 09:00:00 KST, 13 hours remaining) accurately classified into `due_within_24h`.
   - **Zero Notion Writes**: Verified pure read-only inspection; Notion database was untouched.

3. **Re-deployment Across All 5 Agents**:
   - **Claude Code**: `C:\Users\alpha\.claude\skills\coursepilot` (link mode)
   - **Codex**: `C:\Users\alpha\.codex\skills\coursepilot` (link mode)
   - **Antigravity**: `C:\Users\alpha\.gemini\antigravity\skills\coursepilot` (link mode)
   - **Pi**: `C:\Users\alpha\.pi\agent\skills\coursepilot` (link mode)
   - **Hermes**: `C:\Users\alpha\AppData\Local\hermes\skills\coursepilot` (link mode)

## Verification

- `uv run pytest` (244 passed in 9.36s)
- Live LMS `check --json` output: `overdue_count: 0`, `due_within_24h_count: 1`, `later_count: 27`, `error_count: 0`.
- All 5 agent skill links verified.
