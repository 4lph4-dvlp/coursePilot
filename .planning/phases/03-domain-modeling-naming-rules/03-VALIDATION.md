---
phase: "03"
slug: "domain-modeling-naming-rules"
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-09-21"
---

# Phase 03 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.0+ |
| **Config file** | pyproject.toml (`[tool.pytest.ini_options]`) |
| **Quick run command** | `uv run pytest tests/test_domain_models.py tests/test_naming.py tests/test_priority.py tests/test_transformer.py -x` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~1 second |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_domain_models.py tests/test_naming.py tests/test_priority.py tests/test_transformer.py -x`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | DOMN-01 | — | Pydantic v2 domain model with KST timezone enforcement | unit | `uv run pytest tests/test_domain_models.py -x` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | DOMN-03 | — | Notion task title formatting and smart cleaning | unit | `uv run pytest tests/test_naming.py -x` | ❌ W0 | ⬜ pending |
| 03-01-03 | 01 | 1 | DOMN-02 | — | 24h urgency evaluation and Notion property mapping | unit | `uv run pytest tests/test_priority.py -x` | ❌ W0 | ⬜ pending |
| 03-01-04 | 01 | 1 | DOMN-01, DOMN-02, DOMN-03 | THREAT-PAYLOAD-OVERFLOW | Scraped item transformation, deadline rescue, 1500-char memo truncation | unit | `uv run pytest tests/test_transformer.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_domain_models.py` — unit tests for SyncTask, Course, and enums
- [ ] `tests/test_naming.py` — unit tests for naming conventions and smart cleanup
- [ ] `tests/test_priority.py` — unit tests for urgency ladder and property mappings
- [ ] `tests/test_transformer.py` — unit tests for DTO transformation, description deadline rescue, and memo truncation

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| None | — | — | All phase behaviors have automated verification. |

*If none: "All phase behaviors have automated verification."*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending 2026-09-21
