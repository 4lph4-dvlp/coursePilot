---
phase: "04"
slug: "notion-scheduler-integration-deduplication"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: true
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
| 04-01-01 | 01 | 1 | NOTN-01, NOTN-04 | T-04-03, T-04-04 | Tracer performs target/schema/query reads in order and dry-run makes zero writes | integration-mock | `uv run pytest -q tests/test_notion_engine.py -x` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | NOTN-01 | T-04-01, T-04-02 | Credentials stay masked; explicit-ID/name configuration is unambiguous; missing configuration disables safely | unit | `uv run pytest -q tests/test_config.py -x` | ✅ existing | ⬜ pending |
| 04-01-03 | 01 | 1 | NOTN-01 | T-04-02, T-04-03, T-04-04 | Target ambiguity and schema drift fail closed; pagination/retries are bounded and do not expose secrets | unit/integration-mock | `uv run pytest -q tests/test_config.py tests/test_notion_client.py -x` | config ✅; client ❌ W0 | ⬜ pending |
| 04-02-01 | 02 | 2 | NOTN-01, NOTN-03 | T-04-03, T-04-06 | Client delegates raw schema/pages to the mapper-owned validator/parser; create payloads match the schema and updates allow only DueDate/우선순위/메모 while excluding 상태/Plan | unit/integration-mock | `uv run pytest -q tests/test_notion_client.py tests/test_notion_mapper.py -x` | ❌ W0 | ⬜ pending |
| 04-02-02 | 02 | 2 | NOTN-02, NOTN-03, NOTN-04 | T-04-06, T-04-07, T-04-08, T-04-09 | Title-only planning rejects conflicts, protects 상태/Plan, and branches before every dry-run write | unit/integration-mock | `uv run pytest -q tests/test_notion_deduplicator.py tests/test_notion_engine.py -x` | ❌ W0 | ⬜ pending |
| 04-02-03 | 02 | 2 | NOTN-01, NOTN-02, NOTN-03, NOTN-04 | T-04-06, T-04-07, T-04-08 | Full automated subset must pass before credentialed evidence; human approval remains blocked on real-read/zero-write proof | integration-mock + blocking human | `uv run pytest -q tests/test_config.py tests/test_domain_models.py tests/test_notion_client.py tests/test_notion_mapper.py tests/test_notion_deduplicator.py tests/test_notion_engine.py` | config/domain ✅; Notion tests ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

All six commands above are copied verbatim from the corresponding task `<verify><automated>` blocks. Each plan task also carries an explicit `<fails_when>` clause; the credentialed limitation is kept separate in Manual-Only Verifications and in the blocking 04-02-03 checkpoint.

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

- [x] All six tasks have `<automated>` verification; missing Notion test files are explicit Wave 0 outputs of those tasks
- [x] Sampling continuity: every task, including the human checkpoint, runs an automated command before completion
- [x] Wave 0 covers every missing Notion test file referenced by the six commands
- [x] No watch-mode flags
- [x] Expected focused-command feedback latency is < 30s; the credentialed live check is deliberately outside this automated latency target
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** Nyquist strategy approved for execution. `status` remains `draft` and `wave_0_complete` remains `false` until implementation creates and runs the missing test files; credentialed live Scheduler approval remains a blocking manual checkpoint and cannot be inferred from automated green status.
