---
phase: "04"
slug: "notion-scheduler-integration-deduplication"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-09-22"
---

# Phase 04 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 + pytest-mock 3.15.1 |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest -q tests/test_notion_client.py tests/test_notion_mapper.py tests/test_notion_deduplicator.py tests/test_notion_engine.py` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run the task-owned Notion/config test file listed below
- **After every plan wave:** Run `uv run pytest -q tests/test_config.py tests/test_domain_models.py tests/test_notion_client.py tests/test_notion_mapper.py tests/test_notion_deduplicator.py tests/test_notion_engine.py`
- **Before `$gsd-verify-work`:** `uv run pytest` must be green, followed by the credentialed dry-run manual check
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | NOTN-01 | — | Token is never emitted; target discovery fails closed on ambiguity | unit/integration-mock | `uv run pytest -q tests/test_config.py tests/test_notion_client.py -x` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | NOTN-01, NOTN-03 | — | Live schema is read-only validated before payload construction | unit | `uv run pytest -q tests/test_notion_mapper.py -x` | ❌ W0 | ⬜ pending |
| 04-02-01 | 02 | 2 | NOTN-02 | — | Title-only matching detects duplicate conflicts and never mutates protected fields | unit | `uv run pytest -q tests/test_notion_deduplicator.py -x` | ❌ W0 | ⬜ pending |
| 04-02-02 | 02 | 2 | NOTN-02, NOTN-03, NOTN-04 | — | Dry-run performs live reads but calls neither create nor update | integration-mock | `uv run pytest -q tests/test_notion_engine.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_notion_client.py` — explicit-ID/name target resolution, database→data-source resolution, pagination, throttling/retry, safe error translation
- [ ] `tests/test_notion_mapper.py` — schema validation, existing-page parsing, exact create payload, three-field-only update diff
- [ ] `tests/test_notion_deduplicator.py` — title-only action planning, unchanged/new/deadline-change paths, duplicate conflicts
- [ ] `tests/test_notion_engine.py` — unconfigured fallback, real-read/mocked-write dry-run, live write dispatch, partial error aggregation
- [ ] Extend `tests/test_config.py` and `tests/conftest.py` — `NOTION_TOKEN`, legacy alias, empty ID, `NOTION_DATABASE_NAME`, shared fixtures

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Resolve and validate the user's live Scheduler data source | NOTN-01, NOTN-03 | No Notion token/shared live database is available to automated tests | Share Scheduler with the connection, configure token plus ID or exact name, run a credentialed read-only dry-run, and confirm the resolved data source and all eight property names/types/options |
| Prove credentialed dry-run performs zero writes | NOTN-04 | Requires observing the real user-owned Scheduler while preventing mutation | Record the page count or `last_edited_time`, run `dry_run=True`, confirm the planned create/update/skip lists, then confirm no page count/property/timestamp changed |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
