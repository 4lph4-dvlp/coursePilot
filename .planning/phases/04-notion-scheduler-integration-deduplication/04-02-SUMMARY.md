---
phase: 04-notion-scheduler-integration-deduplication
plan: 02
subsystem: api
tags: [notion, deduplication, dry-run, schema-mapping, smart-upsert]
requires:
  - phase: 04-notion-scheduler-integration-deduplication
    provides: guarded Notion read boundary, target resolution, and synchronization DTOs from Plan 04-01
  - phase: 03-domain-modeling-naming-rules
    provides: normalized SyncTask titles, dates, priorities, and capped memo values
provides:
  - exact-title deterministic create/update/skip/error planning
  - allowlisted Scheduler create and partial-update property mapping
  - stable Notion synchronization facade and per-action result aggregation
  - credentialed live Scheduler dry-run proof with zero writes
affects: [phase-05-cli-reporting, notion-sync, scheduler]
actuals:
  tokens: 14200
  tasks: 3
  commits: 11
tech-stack:
  added: []
  patterns:
    - pure mapper and planner before side-effect dispatch
    - exact-title identity with duplicate conflicts failing closed
    - decorated Notion labels translated only at the API boundary
key-files:
  created:
    - src/coursepilot/notion/mapper.py
    - src/coursepilot/notion/deduplicator.py
    - tests/test_notion_mapper.py
    - tests/test_notion_deduplicator.py
    - .planning/phases/04-notion-scheduler-integration-deduplication/04-02-LIVE-DRY-RUN-EVIDENCE.md
  modified:
    - src/coursepilot/notion/__init__.py
    - src/coursepilot/notion/client.py
    - src/coursepilot/notion/engine.py
    - tests/test_notion_client.py
    - tests/test_notion_engine.py
key-decisions:
  - "SyncTask.title is the sole identity key; duplicate incoming or existing titles fail closed rather than selecting an arbitrary page."
  - "Only DueDate, 우선순위, and 메모 may be updated; 상태 and Plan remain user-owned."
  - "Domain priorities stay P1-P4 and map to the existing decorated Scheduler labels only at the Notion boundary."
patterns-established:
  - "Plan then execute: all reads and pure action planning finish before dry-run returns or live writes begin."
  - "Allowlisted partial updates: property payloads are constructed explicitly rather than dumping domain models."
requirements-completed: [NOTN-02, NOTN-03, NOTN-04]
coverage:
  - id: D1
    description: "Exact-title smart upsert updates changed existing tasks once, creates only new titles, and fails closed on duplicate identities."
    requirement: NOTN-02
    verification:
      - kind: unit
        ref: "tests/test_notion_deduplicator.py#exact-title planning and duplicate-conflict suite"
        status: pass
    human_judgment: false
  - id: D2
    description: "Scheduler creates use the declared property types while updates are restricted to DueDate, 우선순위, and 메모."
    requirement: NOTN-03
    verification:
      - kind: unit
        ref: "tests/test_notion_mapper.py#schema, create, and allowlisted-update suite"
        status: pass
    human_judgment: false
  - id: D3
    description: "Configured dry-run performs real live discovery, schema, pagination, and planning reads while issuing zero writes."
    requirement: NOTN-04
    verification:
      - kind: integration
        ref: "tests/test_notion_engine.py#dry-run and result aggregation suite"
        status: pass
      - kind: manual_procedural
        ref: ".planning/phases/04-notion-scheduler-integration-deduplication/04-02-LIVE-DRY-RUN-EVIDENCE.md#Verdict"
        status: pass
    human_judgment: false
duration: 5h 35m
completed: 2026-09-22
status: complete
---

# Phase 04 Plan 02: Scheduler Smart Upsert and Live Dry-Run Summary

**Exact-title smart upsert with protected Scheduler fields, stable per-action results, and user-approved live real-read/zero-write evidence**

## Performance

- **Duration:** 5h 35m, including the external-configuration and human-review pause
- **Started:** 2026-09-22T08:37:34+09:00
- **Completed:** 2026-09-22T14:12:24+09:00
- **Tasks:** 3
- **Files modified:** 11

## Accomplishments

- Centralized all Scheduler schema validation, page parsing, create serialization, and protected partial-update behavior in one pure mapper.
- Added deterministic exact-title planning and a live dispatcher that aggregates stable create, update, skip, and error results while continuing independent actions.
- Proved against the credentialed live Scheduler that exact-name discovery, eight-property schema validation, D-03 pagination, and action planning perform zero create/update calls and leave all page evidence unchanged.

## Task Commits

1. **Task 1: Canonicalize and wire the Scheduler schema and property payloads** - `c6bd1a1` (test), `d6df06f` (feat)
2. **Task 2: Plan title-only actions, execute allowed writes, and aggregate stable results** - `f4f5192` (test), `6b43f55` (feat)
3. **Task 3: Verify the credentialed read-only dry-run against the live Scheduler** - `68bc402`, `1f583e2`, `8d7a146` (evidence/checkpoint)
4. **Live compatibility fixes discovered during Task 3** - `cddf558`, `407e18c` (priority labels), `9b2a562`, `17f1986` (date normalization)

## Files Created/Modified

- `src/coursepilot/notion/mapper.py` - Canonical Scheduler schema, parsing, create payload, and allowlisted update transformations.
- `src/coursepilot/notion/deduplicator.py` - Pure exact-title action planner and duplicate conflict handling.
- `src/coursepilot/notion/client.py` - Mapper-delegated schema and page parsing while retaining the guarded transport boundary.
- `src/coursepilot/notion/engine.py` - Configuration gate, read-plan-write orchestration, dry-run suppression, and action failure aggregation.
- `src/coursepilot/notion/__init__.py` - Stable Phase 5-facing synchronization facade.
- `tests/test_notion_mapper.py`, `tests/test_notion_deduplicator.py`, `tests/test_notion_client.py`, `tests/test_notion_engine.py` - Schema, mapping, identity, orchestration, and regression coverage.
- `.planning/phases/04-notion-scheduler-integration-deduplication/04-02-LIVE-DRY-RUN-EVIDENCE.md` - Redacted credentialed verification and human approval record.

## Decisions Made

- Preserved `P1`-`P4` inside the domain model and translated to the Scheduler's decorated labels only in the mapper, so no Notion-side option migration is required.
- Normalized Notion date-only values to KST before comparison, matching the domain's KST date contract and preventing false updates.
- Kept exact normalized title as the only persistent identity value; deadline changes therefore update one existing page instead of creating another.

## Deviations from Plan

### Auto-fixed Issues

**1. Live Scheduler priority labels differ from internal enum values**
- **Found during:** Task 3 live schema preflight
- **Issue:** The live select options use decorated Korean labels rather than literal `P1`-`P4` strings.
- **Fix:** Added bidirectional API-boundary mapping while leaving domain values unchanged.
- **Files modified:** `src/coursepilot/notion/mapper.py`, `tests/test_notion_mapper.py`
- **Verification:** Mapper tests and live eight-property schema validation pass.
- **Committed in:** `407e18c`

**2. Date-only values caused a false DueDate update**
- **Found during:** Task 3 guarded live probe
- **Issue:** A Notion date-only value was interpreted without the project KST timezone, producing a false comparison difference.
- **Fix:** Attached or converted KST during Notion date parsing before action planning.
- **Files modified:** `src/coursepilot/notion/mapper.py`, `tests/test_notion_mapper.py`
- **Verification:** Regression test passes and the final live plan reports one unchanged skip with zero updates.
- **Committed in:** `17f1986`

---

**Total deviations:** 2 auto-fixed correctness issues.
**Impact on plan:** Both fixes preserve the locked identity and ownership contracts without expanding scope or requiring a Notion migration.

## Issues Encountered

- The initially configured identifier was a data-source ID rather than a database-container ID. Exact-name discovery resolved the unique `Scheduler` target and retained both IDs safely.
- Execution remained sequential on the main worktree because `origin/HEAD` was unresolved; this did not alter implementation or verification behavior.

## User Setup Required

None. The Scheduler is already shared with the configured Notion connection, and the existing decorated priority options are handled by code-side mapping.

## Next Phase Readiness

- Phase 5 can consume the stable facade and hierarchical `SyncResult` without importing SDK or mapper internals.
- The live target and schema are verified, and no Notion-side changes remain.

## Self-Check: PASSED

- All declared implementation, test, summary, and evidence files exist.
- The relevant 36-test command passed before the live checkpoint.
- Credentialed before/after page count, edit time, and state digest are identical.
- The user approved the blocking live dry-run evidence.

---
*Phase: 04-notion-scheduler-integration-deduplication*
*Completed: 2026-09-22*
