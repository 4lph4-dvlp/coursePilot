---
phase: 04-notion-scheduler-integration-deduplication
plan: 01
subsystem: api
tags: [notion, pydantic, dry-run, pagination, retry]
requires:
  - phase: 03-domain-modeling-naming-rules
    provides: normalized SyncTask models and exact Scheduler titles
provides:
  - stable Notion synchronization DTOs and result hierarchy
  - safe credential and target configuration gate
  - exact Notion target resolution, schema preflight, and paginated D-03 reads
  - real-read and zero-write dry-run orchestration
affects: [04-02-smart-upsert, phase-05-cli-reporting]
actuals:
  tokens: 10646
  tasks: 3
  commits: 6
tech-stack:
  added: []
  patterns:
    - injected synchronous Notion SDK boundary
    - exact-title identity with post-read write gating
    - SDK-owned 429 retry plus bounded read-only 529 retry
key-files:
  created:
    - src/kau_assistant/notion/models.py
    - src/kau_assistant/notion/client.py
    - src/kau_assistant/notion/engine.py
    - tests/test_notion_client.py
    - tests/test_notion_engine.py
  modified:
    - src/kau_assistant/config.py
    - src/kau_assistant/exceptions.py
    - tests/test_config.py
    - tests/conftest.py
    - .env.example
key-decisions:
  - "Explicit database ID takes priority; name discovery accepts one complete exact-title match only."
  - "The SDK alone handles bounded 429 retry; the wrapper retries only read-only 529 failures."
  - "Dry-run branches only after target resolution, schema validation, query, and title-only planning."
patterns-established:
  - "Real-read/write-gate: dry-run uses the production read and planning path and suppresses only creates and updates."
  - "Fail-closed target selection: ambiguous database children or search matches never select index zero."
requirements-completed: [NOTN-01, NOTN-04]
coverage:
  - id: D1
    description: "Configured users can resolve and validate one Scheduler data source and paginate the locked D-03 read set."
    requirement: NOTN-01
    verification:
      - kind: integration
        ref: "tests/test_notion_client.py#target schema query and pagination suite"
        status: pass
    human_judgment: false
  - id: D2
    description: "Dry-run performs target, schema, query, and planning reads while issuing zero writes."
    requirement: NOTN-04
    verification:
      - kind: integration
        ref: "tests/test_notion_engine.py#test_configured_dry_run_reads_before_planning_and_never_writes"
        status: pass
    human_judgment: false
  - id: D3
    description: "Notion configuration supports preferred and legacy credentials without exposing secrets and safely disables when incomplete."
    requirement: NOTN-01
    verification:
      - kind: unit
        ref: "tests/test_config.py#Notion configuration tests"
        status: pass
    human_judgment: false
duration: 11 min
completed: 2026-09-22
status: complete
---

# Phase 04 Plan 01: Notion Read Path and Dry-Run Tracer Summary

**Exact Scheduler resolution, read-only schema/query preflight, and a production dry-run path that plans by title while mechanically suppressing all Notion writes**

## Performance

- **Duration:** 11 min
- **Started:** 2026-09-21T23:19:10Z
- **Completed:** 2026-09-21T23:30:53Z
- **Tasks:** 3
- **Files modified:** 10

## Accomplishments

- Added stable Pydantic target, page, action, diff, error, statistics, and result contracts for Phase 4 and the Phase 5 reporter.
- Added explicit-ID and paginated exact-name Scheduler resolution, complete read-only schema validation, D-03 pagination/filtering, throttling, and safe typed transport errors.
- Added a real-read dry-run tracer that uses title-only identity, reports planned actions, and proves both write methods remain uncalled.

## Task Commits

Each TDD task was committed as a failing test followed by its implementation:

1. **Task 1: Prove one configured real-read dry-run path end to end** - `e628fed` (test), `8d4f9f1` (feat)
2. **Task 2: Make Notion configuration explicit, masked, and safely disableable** - `d901ef9` (test), `78dd515` (feat)
3. **Task 3: Harden target resolution, schema validation, pagination, and transport policy** - `5dc946f` (test), `fcaf22d` (feat)

## Files Created/Modified

- `src/kau_assistant/notion/models.py` - Stable public synchronization DTOs.
- `src/kau_assistant/notion/client.py` - Guarded SDK transport, target resolution, schema preflight, and paginated reads.
- `src/kau_assistant/notion/engine.py` - Configuration gate, title-only planning, and dry-run write suppression.
- `src/kau_assistant/config.py` - Preferred/legacy token handling and explicit target configuration state.
- `src/kau_assistant/exceptions.py` - Typed safe Notion integration errors.
- `tests/test_notion_client.py` - Transport, ambiguity, schema, pagination, timing, retry, and secret-safety evidence.
- `tests/test_notion_engine.py` - End-to-end dry-run tracer and safe-disabled evidence.
- `tests/test_config.py`, `tests/conftest.py`, `.env.example` - Configuration contract and documentation.

## Decisions Made

- Kept database-container IDs distinct from child data-source IDs; all data operations use the latter.
- Kept 429 retry inside `notion-client` with `RetryOptions(max_retries=3)` and restricted wrapper retries to bounded, read-only 529 failures.
- Placed the dry-run branch after all real reads and action planning so preview and live behavior share one decision path.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- `origin/HEAD` was unresolved, so the GSD isolation gate safely downgraded execution to sequential main-worktree mode. No implementation behavior changed.

## User Setup Required

Set `NOTION_TOKEN` plus either `NOTION_DATABASE_ID` or `NOTION_DATABASE_NAME` as documented in `.env.example` before live use. No setup is required for disabled/local-only operation.

## Next Phase Readiness

- The read boundary and result contracts are ready for Plan 04-02 mapper, deduplicator, and smart-upsert expansion.
- Live verification still belongs to Plan 04-02's blocking-human dry-run checkpoint.

---
*Phase: 04-notion-scheduler-integration-deduplication*
*Completed: 2026-09-22*
