---
phase: "13"
slug: "learning-materials-ubfile-auto-completion-file-downloader"
status: ready
nyquist_compliant: true
wave_0_complete: false
created: "2026-09-25"
---

# Phase 13 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/test_material_parser.py tests/test_filename_utils.py tests/test_material_downloader.py tests/test_materials_runner.py tests/test_cli_materials.py -q` |
| **Full suite command** | `uv run pytest -ra -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_material_parser.py tests/test_filename_utils.py tests/test_material_downloader.py tests/test_materials_runner.py tests/test_cli_materials.py -q`
- **After every plan wave:** Run `uv run pytest -ra -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 13-01-01 | 01 | 1 | RES-01, RES-02 | — | Validates data schemas and serialization | unit | `uv run pytest tests/test_material_models.py` | ❌ W0 | ⬜ pending |
| 13-01-02 | 01 | 1 | RES-01 | — | HTML DOM parsing extracts material items and status | unit | `uv run pytest tests/test_material_parser.py` | ❌ W0 | ⬜ pending |
| 13-01-03 | 01 | 1 | RES-02 | — | RFC 5987 / 6266 filename resolution and path sanitization | unit | `uv run pytest tests/test_filename_utils.py` | ❌ W0 | ⬜ pending |
| 13-01-04 | 01 | 2 | RES-01, RES-02 | — | Session-authenticated streaming download, size-skip, atomic rename | integration | `uv run pytest tests/test_material_downloader.py` | ❌ W0 | ⬜ pending |
| 13-01-05 | 01 | 2 | RES-01, RES-02 | — | MaterialsRunner orchestration, filters, dry-run, no-download | integration | `uv run pytest tests/test_materials_runner.py` | ❌ W0 | ⬜ pending |
| 13-01-06 | 01 | 3 | RES-01, RES-02 | — | Click CLI options, JSON output, console formatting | cli | `uv run pytest tests/test_cli_materials.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_material_models.py` — Stubs for MaterialItem, MaterialDownloadResult, MaterialsRunResult DTOs
- [ ] `tests/test_material_parser.py` — Stubs and HTML mock fixtures for `mod/ubfile/view.php` and course home
- [ ] `tests/test_filename_utils.py` — Stubs for RFC 5987/6266 parsing and filesystem sanitization
- [ ] `tests/test_material_downloader.py` — Stubs and mock responses for streaming downloader
- [ ] `tests/test_materials_runner.py` — Stubs for course/week filtering and runner orchestration
- [ ] `tests/test_cli_materials.py` — Stubs for `coursepilot materials` / `files` CLI invocation

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real LMS `ubfile` view completion | RES-01 | Requires active student LMS credentials and unpublished/unviewed material | Run `python -m coursepilot materials --course <과목> --no-download`, verify 100% completion in LXP web UI |
| Real LMS binary file download | RES-02 | Requires live LMS network access and active course attachments | Run `python -m coursepilot materials --course <과목> --week current`, verify files saved in `downloads/<과목>/W{주차}/` |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved
