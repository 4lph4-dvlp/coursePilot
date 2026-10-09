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
| 18-01-01/02 | 01 | 1 | MCON-01..03 | Exact public proposal is reviewed before one-way publication. | proposal/checkpoint | `python -c "from pathlib import Path; assert Path('.planning/phases/18-selected-materials-contract-and-attachment-manifest/18-CONTRACT-PROPOSAL.md').is_file()"` | ❌ W0 | ⬜ pending |
| 18-02-01/02 | 02 | 2 | MCON-01 | Coarse listing avoids detail-page view effects and preserves legacy output. | runner/CLI fixture | `uv run --offline python -m pytest tests/test_cli_materials.py tests/test_materials_runner.py -q` | Existing suites; new cases W0 | ⬜ pending |
| 18-03-01/02 | 03 | 3 | MCON-01, MCON-02 | Approved inspect returns a proven complete full attachment list and digest, or unknown with reason. | parser/CLI fixture | `uv run --offline python -m pytest tests/test_material_parser.py tests/test_materials_runner.py tests/test_cli_materials.py -q` | Existing suites; new cases W0 | ⬜ pending |
| 18-04-01/02 | 04 | 4 | MCON-02, MCON-03 | Exact module/file selection rejects changed full manifest before download and never runs a sibling. | runner/downloader fixture | `uv run --offline python -m pytest tests/test_materials_runner.py tests/test_material_downloader.py -q` | Existing suites; new cases W0 | ⬜ pending |
| 18-05-01/02 | 05 | 5 | MCON-01..03 | Published docs and installed runtime canary agree with approved JSON and preserve legacy compatibility. | contract/package fixture | `uv run --offline python -m pytest tests/test_contract_doc.py tests/test_materials_install_canary.py -q` | Canary suite ❌ W0 | ⬜ pending |

*Task IDs and waves reflect the draft plans; update the inspect row if revision changes its focused test command. Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky.*

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
