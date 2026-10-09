---
phase: "18"
slug: "selected-materials-contract-and-attachment-manifest"
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-09"
---

# Phase 18 — Validation Strategy

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest through `uv run --offline python -m pytest` |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run --offline python -m pytest tests/test_material_models.py tests/test_material_parser.py tests/test_material_downloader.py tests/test_materials_runner.py tests/test_cli_materials.py -q` |
| **Full suite command** | `uv run --offline python -m pytest -q` |
| **Estimated runtime** | Measure during execution; use a unique `--basetemp` on Windows if shared temp cleanup fails |

## Sampling Rate

- **After every task commit:** Run focused new tests and affected existing material tests.
- **After every plan wave:** Run the materials parser, downloader, runner, models, and CLI compatibility suites.
- **Before `$gsd-verify-work`:** Run full pytest suite, published CLI help/JSON contract check, and installed runtime canary.
- **Max feedback latency:** Measure at Wave 0; keep focused tests bounded.

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------------|-----------|-------------------|-------------|--------|
| Assigned by planner | TBD | TBD | MCON-01 | Coarse listing avoids detail-page view effects; inspected layouts prove complete or say unknown. | parser/CLI fixture | `uv run --offline python -m pytest tests/test_material_parser.py tests/test_cli_materials.py -q` | Existing suites; new fixtures W0 | ⬜ pending |
| Assigned by planner | TBD | TBD | MCON-02 | Exact module/file selection rejects changed full manifest before download and never runs a sibling. | runner fixture | `uv run --offline python -m pytest tests/test_materials_runner.py tests/test_material_downloader.py -q` | Existing suites; new fixtures W0 | ⬜ pending |
| Assigned by planner | TBD | TBD | MCON-03 | Versioned per-file result, partial/fatal/error mapping, and legacy compatibility are independently checked. | CLI/contract fixture | `uv run --offline python -m pytest tests/test_cli_materials.py tests/test_material_models.py -q` | Existing suites; new fixtures W0 | ⬜ pending |

*Task IDs, waves and any new test filenames will be updated after PLAN.md is finalized. Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky.*

## Wave 0 Requirements

- [ ] Add sanitized reviewed one-file, two-file, and indeterminate detail-page fixtures. The current course-page fixture does not prove attachment completeness.
- [ ] Add negative fixtures for sibling module, changed/added file, stale digest, duplicate link, unknown enumeration, and attempted whole-batch fallback.
- [ ] Add selected-mode contract snapshots, legacy `materials`/`files` compatibility tests, and an offline installed-package canary.

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Actual Coursemos detail-page completeness | MCON-01 | Current repo has no reviewed representative page for all supported layouts | Under separately approved account scope, obtain sanitized representative HTML, then prove the exact closed-enumeration predicate or keep the layout `unknown`. |
| Live selected file save | MCON-02, MCON-03 | Requires approved LMS visit and download effects | Inspect and approve one bounded module/file, execute once, and check the returned source identity and local file bytes. |

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies.
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify.
- [ ] Wave 0 covers all missing references.
- [ ] No watch-mode flags.
- [ ] Feedback latency measured and bounded.
- [ ] `nyquist_compliant: true` set only after validation.

**Approval:** pending
