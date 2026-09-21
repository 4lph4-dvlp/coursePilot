---
phase: "03"
plan: "01"
subsystem: "domain"
tags:
  - pydantic
  - domain-modeling
  - notion-sync
  - naming-rules
  - priority-ladder
  - date-rescue

# Dependency graph
requires:
  - phase: 01-foundation-session-management
    provides: Course name mapping engine (get_abbreviation, load_course_mappings)
  - phase: 02-lms-scraper-core
    provides: Scraper DTOs (CourseItem, LectureItem, AssessmentItem, enums) and date parser (KST, parse_lms_date)
provides:
  - Pure domain entities (SyncTask, Course, TaskType, TaskPriority, TaskSelect, TaskStatus)
  - Task naming engine with Korean week/activity rules and smart title cleaning (naming.py)
  - 24-hour urgency analyzer and Notion selection/priority decision ladder (priority.py)
  - DTO to SyncTask transformer with description deadline rescue and 1500/1950 char memo truncation (transformer.py)
  - Domain package public facade (kau_assistant.domain)
affects:
  - 04-notion-sdk-database-sync
  - 05-cli-reporter-session-persistence

actuals:
  tokens: 4200
  tasks: 4
  commits: 4

tech-stack:
  added: []
  patterns:
    - Pure domain layer isolation (zero network/IO imports)
    - KST timezone enforcement via Pydantic field_validator
    - Defensive text truncation against Notion API 2000-char limits
    - Goal-backward priority decision ladder (completed -> overdue -> <=24h -> normal)

key-files:
  created:
    - src/kau_assistant/domain/__init__.py
    - src/kau_assistant/domain/models.py
    - src/kau_assistant/domain/naming.py
    - src/kau_assistant/domain/priority.py
    - src/kau_assistant/domain/transformer.py
    - tests/test_domain_models.py
    - tests/test_naming.py
    - tests/test_priority.py
    - tests/test_transformer.py
  modified: []

key-decisions:
  - "D-01: Online video lectures formatted as '[{과목약어}] {N}주차 {M}차시 강의 시청'"
  - "D-02: Assignments/quizzes/forums formatted with activity verbs ('제출', '[퀴즈] {이름} 응시', '[토론] {이름} 참여')"
  - "D-03: Activities without week information fall back gracefully without week prefix"
  - "D-04: Smart title cleaning decodes HTML entities and strips redundant bracket tags ([과제], [HW], etc.)"
  - "D-05: Notion '선택' property mapped to '루틴' for lectures, '이벤트' for assignments/quizzes/forums"
  - "D-06: Notion priority P1~P4: <=24h is P1, normal assignment is P2, normal lecture is P3, overdue/completed is P4"
  - "D-07: DueDate forced to Asia/Seoul (KST) timezone via Pydantic validator"
  - "D-08: Plan date defaults to None for user scheduling; category defaults to ['학업']"
  - "D-09: transform_to_sync_tasks filters completed items by default (include_completed=False)"
  - "D-10: Overdue items maintain '시작 전' status without appending '[지연]' to title"
  - "D-11: Open/OT lectures without deadline excluded; assignment description scanned for rescued deadline"
  - "D-12: Lecture memo concise format ('LMS 바로가기: {link}')"
  - "D-13: Assessment memo structured into LMS link, cutoff date, attachments, and description"
  - "D-14: Description safe truncation at 1500 chars with ellipsis notice; overall memo hard capped at 1950 chars"
  - "D-15: Modular domain subpackage architecture (models, naming, priority, transformer, facade)"

patterns-established:
  - "Pure Domain Isolation: Domain modules never import playwright, httpx, or network libraries"
  - "Trailing Verb Deduplication: Strips trailing '제출'/'응시'/'참여' before template combination to prevent duplicate verbs"
  - "Minute-Precision Dedup Key: dedup_key property formatted as '{title}|{YYYY-MM-DD HH:MM}' or '{title}|no_due'"

requirements-completed:
  - DOMN-01
  - DOMN-02
  - DOMN-03

coverage:
  - id: D1
    description: "Pure domain models (SyncTask, Course, Enums) with KST timezone enforcement and dedup key"
    requirement: DOMN-01
    verification:
      - kind: unit
        ref: "tests/test_domain_models.py#test_sync_task_creation_and_defaults"
        status: pass
      - kind: unit
        ref: "tests/test_domain_models.py#test_sync_task_kst_enforcement"
        status: pass
    human_judgment: false
  - id: D2
    description: "24-hour urgency evaluation and priority decision ladder (P1~P4)"
    requirement: DOMN-02
    verification:
      - kind: unit
        ref: "tests/test_priority.py#test_urgent_24h_boundary"
        status: pass
      - kind: unit
        ref: "tests/test_priority.py#test_overdue_and_completed_priorities"
        status: pass
    human_judgment: false
  - id: D3
    description: "Standardized task title formatting with Korean week/activity conventions and smart HTML cleaning"
    requirement: DOMN-03
    verification:
      - kind: unit
        ref: "tests/test_naming.py#test_lecture_naming_convention"
        status: pass
      - kind: unit
        ref: "tests/test_naming.py#test_assignment_naming_conventions"
        status: pass
      - kind: unit
        ref: "tests/test_naming.py#test_smart_title_cleaning"
        status: pass
      - kind: unit
        ref: "tests/test_naming.py#test_double_verb_prevention"
        status: pass
    human_judgment: false
  - id: D4
    description: "DTO to SyncTask transformation, description deadline rescue, and Notion 1500/1950-char memo truncation"
    requirement: DOMN-01
    verification:
      - kind: unit
        ref: "tests/test_transformer.py#test_transform_to_sync_tasks_filtering_and_sorting"
        status: pass
      - kind: unit
        ref: "tests/test_transformer.py#test_deadline_rescue_from_description"
        status: pass
      - kind: unit
        ref: "tests/test_transformer.py#test_format_memo_structure_and_truncation"
        status: pass
    human_judgment: false

duration: 15 min
completed: 2026-09-21
status: complete
---

# Phase 03 Plan 01: Domain Modeling, Task Naming Engine, Priority Analyzer & DTO Transformer Summary

**Pure Domain Layer delivering Notion-aligned Pydantic models (SyncTask, Course), smart task naming with Korean activity rules, 24-hour urgency P1~P4 priority ladder, and DTO transformer with deadline rescue and 1500/1950-char memo truncation.**

## Performance

- **Duration:** 15 min
- **Started:** 2026-09-21T11:22:45Z
- **Completed:** 2026-09-21T11:26:15Z
- **Tasks:** 4
- **Files created:** 9 (5 implementation, 4 test suites)
- **Unit test coverage:** 22 new tests added, 81/81 passed across entire repository

## Accomplishments

- Implemented pure domain entities (`SyncTask`, `Course`, `TaskType`, `TaskPriority`, `TaskSelect`, `TaskStatus`) with automatic KST (`Asia/Seoul`) timezone attachment and minute-precision `dedup_key` (DOMN-01).
- Built task naming engine (`naming.py`) supporting fixed lecture format `[{과목약어}] {N}주차 {M}차시 강의 시청` (D-01), verb-branched assignment format `[{과목약어}] {N}주차 {과제명} 제출` (D-02), non-week fallback (D-03), smart HTML unescaping/tag stripping (D-04), and double-verb deduplication (DOMN-03).
- Implemented 24-hour urgency analyzer and priority ladder (`priority.py`) strictly enforcing P1 promotion for <=24h deadlines, P4 for overdue/completed items, and routine/event mapping for Notion '선택' (DOMN-02).
- Built DTO transformer (`transformer.py`) converting scraper models to `SyncTask`, filtering OT/open lectures without deadlines (D-11), rescuing deadlines from assignment descriptions (D-11), and applying 1500/1950-char safety caps to Notion memos (D-12 ~ D-14).
- Exported unified package facade (`kau_assistant.domain`) for downstream Phase 4 Notion SDK and Phase 5 CLI reporter integration.

## Task Commits

Each task was committed atomically:

1. **Task 03-01-01: Domain Entities, Notion Enums & KST Validation (DOMN-01)** - `08718d5` (feat)
2. **Task 03-01-02: Task Naming Rules & Smart Title Cleaning Engine (DOMN-03)** - `dd5e1f0` (feat)
3. **Task 03-01-03: 24-Hour Urgency & Priority Decision Ladder (DOMN-02)** - `3629edc` (feat)
4. **Task 03-01-04: DTO Transformer, Deadline Rescue, Memo Formatter & Package Facade (DOMN-01, DOMN-02, DOMN-03)** - `ae42a2b` (feat)

## Files Created/Modified

- `src/kau_assistant/domain/__init__.py` - Package facade exporting all public domain models, enums, and functions
- `src/kau_assistant/domain/models.py` - Core Pydantic domain models (`SyncTask`, `Course`) and Notion property enums
- `src/kau_assistant/domain/naming.py` - Task title normalizer, HTML cleaner, and week/activity formatter
- `src/kau_assistant/domain/priority.py` - 24-hour urgency calculator, P1~P4 priority ladder, and selection mapper
- `src/kau_assistant/domain/transformer.py` - Scraper DTO to SyncTask converter, deadline rescuer, and memo builder
- `tests/test_domain_models.py` - 4 unit tests validating models, enums, KST enforcement, and dedup key
- `tests/test_naming.py` - 7 unit tests validating naming formats, smart cleaning, and double-verb prevention
- `tests/test_priority.py` - 4 unit tests validating 24h boundary conditions, overdue/completed priorities, and selection mapping
- `tests/test_transformer.py` - 7 unit tests validating DTO transformation, deadline rescue, memo truncation, and filtering/sorting

## Decisions Made

- Followed D-01 through D-15 as specified in CONTEXT.md and PLAN.md without deviation.
- All domain modules maintain strict pure-domain isolation: zero network or external I/O imports.
- Reused `KST` and `parse_lms_date` from `kau_assistant.scraper.date_parser` for consistency.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all tests passed on the first run.

## User Setup Required

None - no external service configuration required for domain layer.

## Next Phase Readiness

- Pure domain models (`SyncTask`, `Course`) and transformation pipelines are 100% complete and verified.
- Ready for Phase 4: Notion SDK Integration & Database Sync (`04-notion-sdk-database-sync`), where `SyncTask` objects will be matched against Notion Database properties and upserted via official `@notionhq/client` or Notion HTTP API.

---
*Phase: 03-domain-modeling-naming-rules*
*Completed: 2026-09-21*
