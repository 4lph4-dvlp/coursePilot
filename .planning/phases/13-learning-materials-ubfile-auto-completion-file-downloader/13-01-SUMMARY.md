---
phase: 13-learning-materials-ubfile-auto-completion-file-downloader
plan: "01"
status: completed
date: 2026-09-25
---

# Plan 13-01 Summary: Learning Materials (ubfile) Auto-Completion & File Downloader

## Overview

Plan 13-01 delivered automated Coursemos LXP activity completion for unviewed `ubfile` and Moodle `resource` learning materials, alongside a cookie-authenticated hierarchical local file downloader:
1. Automated LXP completion marking (100% progress rate) for unviewed materials upon visiting their `view.php` endpoint via session-authenticated GET requests (RES-01).
2. Clean local hierarchical storage under `downloads/<과목명>/W{주차}/` (or `--output-dir` / `DOWNLOAD_DIR`) with atomic `.tmp` writes, duplicate size matching skips (D-13-02), and embedded HTML viewer resolution (RES-02, D-13-01).
3. Robust filename resolution with RFC 5987 / 6266 UTF-8 percent-decoding, MIME type fallbacks (e.g. HWP/HWPX/PDF/ZIP), and cross-platform OS sanitization neutralizing illegal characters and Windows reserved stems.
4. Flexible orchestration supporting fuzzy course matching, week queries (`current`, `all`, or numeric), `--no-download` view-only completion (D-13-03), and zero-write `--dry-run` inspection (D-13-08).
5. User-friendly Rich terminal table reporting and Click CLI registration of `kau-assistant materials` and its convenient alias `kau-assistant files` with full JSON output contracts (D-13-05..D-13-08).

## Key Accomplishments

1. **Domain Models & Settings (`src/kau_assistant/materials/models.py`, `src/kau_assistant/config.py`)**:
   - Added `download_dir: Path` (`DOWNLOAD_DIR` in `.env`, default `downloads`) to `Settings`.
   - Defined `MaterialStatus` enum (`DOWNLOADED`, `SKIPPED`, `VIEWED_ONLY`, `FAILED`).
   - Defined `MaterialItem`, `MaterialDownloadResult`, `CourseMaterialsResult`, and `MaterialsRunResult` with full Pydantic JSON serialization contracts.

2. **DOM Parser & Link Extractor (`src/kau_assistant/scraper/material_parser.py`)**:
   - Implemented `parse_materials_from_course_sections` scanning course sections for `ubfile` and `resource` activities, parsing week headings, removing Moodle `span.accesshide` noise, and extracting completion state.
   - Implemented `extract_pluginfile_url` to detect underlying documents inside embedded viewer pages (`<a>`, `<object>`, `<iframe>`, `<embed>`).

3. **Filename Resolution & Sanitization (`src/kau_assistant/materials/filename_utils.py`)**:
   - Implemented `resolve_filename` prioritizing RFC 5987 / 6266 `filename*=UTF-8''` headers, standard quoted filenames, URL basename fallbacks, and MIME type extension inference.
   - Implemented `sanitize_filename` neutralizing illegal characters (`[<>:"/\\|?*\x00-\x1f]`), whitespace collapsing, trailing dot/space stripping, Windows reserved stem guards (`_CON.pdf`, `_aux.hwp`), and length truncation preserving extensions.

4. **Cookie Downloader & View Engine (`src/kau_assistant/materials/downloader.py`)**:
   - Implemented `get_authenticated_httpx_client` reusing session cache cookies (`MoodleSession`).
   - Implemented `mark_material_viewed` achieving server-side LXP completion without headless browser overhead (RES-01).
   - Implemented `download_material_file` with atomic temporary streaming write (`.tmp`), size verification, duplicate skip detection (D-13-02), and recursive pluginfile handling.

5. **Multi-Course / Week Runner (`src/kau_assistant/materials/runner.py`)**:
   - Implemented `resolve_candidate_materials` resolving earliest uncompleted weeks for "current" or full rosters for "all".
   - Implemented `process_course_materials` with smart visit policies (D-13-04), `--no-download` mode (D-13-03), `--dry-run` inspection (D-13-08), and per-item error isolation.
   - Implemented `run_materials_pipeline` integrating browser session navigation, fuzzy course selection, and run summary aggregation.

6. **CLI & Rich Reporter (`src/kau_assistant/materials/reporter.py`, `src/kau_assistant/cli.py`)**:
   - Implemented `render_materials_report` displaying formatted status tables, color-coded badges, human-readable file sizes, and summary metrics.
   - Registered `kau-assistant materials` and alias `kau-assistant files` supporting all standard flags (`--course`, `--week`, `--output-dir`, `--no-download`, `--dry-run`, `--json`, `--relogin`, `--headed`).

## Verification & Validation

- Automated unit & integration tests:
  - `tests/test_material_models.py` (5 passed)
  - `tests/test_material_parser.py` (2 passed)
  - `tests/test_filename_utils.py` (11 passed)
  - `tests/test_material_downloader.py` (8 passed)
  - `tests/test_materials_runner.py` (10 passed)
  - `tests/test_cli_materials.py` (5 passed)
  - Phase 13 suite: 41 passed
- Full project test suite: 307 passed with 0 failures or regressions.
