---
phase: 05-cli-reporting-antigravity-skill-packaging
plan: 08
status: completed
date: 2026-09-24
gap_ids: [G-05-2]
---

# Plan 05-08 Summary: Default LMS_URL to LXP, Add Notices Contract & UnsupportedLmsError

## Overview

Plan 05-08 closed the reporting and configuration half of gap G-05-2. It changed the default target to `https://lxp.kau.ac.kr`, introduced structured `notices` into the JSON v1 contract with the `no_courses_found` notice for empty course discoveries, added `UnsupportedLmsError` with a safe static message for non-Coursemos sites, and rendered user-facing notices in Rich reports.

## Key Changes

1. **Configuration (`src/kau_assistant/config.py`)**:
   - Defined `DEFAULT_LMS_URL = "https://lxp.kau.ac.kr"`.
   - Updated `Settings.lms_url` default from `https://lms.kau.ac.kr` to `DEFAULT_LMS_URL`.

2. **Error Handling (`src/kau_assistant/exceptions.py`, `src/kau_assistant/errors.py`)**:
   - Added `UnsupportedLmsError` exception subclassing `KauAssistantError`.
   - Added static safe CLI error conversion for `UnsupportedLmsError` with code `"UnsupportedLmsError"`, exit code 2 (fatal), and instructions to check `LMS_URL`.
   - Enhanced `_AUTH_MESSAGE` to remind users to verify that `LMS_URL` matches the institution's Coursemos LXP/LMS address.

3. **Report Models (`src/kau_assistant/report_models.py`)**:
   - Created `ReportNotice(BaseModel)` with `code: str` and `message: str` (`extra="forbid"`).
   - Added `notices: list[ReportNotice] = Field(default_factory=list)` to `CheckReport` and `SyncReport` (v1 additive non-breaking field).

4. **Reporter (`src/kau_assistant/reporter.py`)**:
   - Added `NO_COURSES_NOTICE_CODE = "no_courses_found"` and a static Korean notice message instructing the user to check `LMS_URL` and term enrollment.
   - Built helper to attach `no_courses_found` notice to check and sync reports when `course_count == 0` and no fatal error occurred.
   - Updated `render_check_report` and `render_sync_report` to print a bold yellow "안내" notice section right after the summary panel.

5. **JSON Contract (`skills/kau-lxp/JSON_CONTRACT.md`)**:
   - Documented `notices` field on `CheckReport` and `SyncReport`.
   - Added `ReportNotice` model documentation and `no_courses_found` notice code specification.
   - Documented `UnsupportedLmsError` under the error reference.
   - Updated JSON contract schema examples to include `"notices": []`.

6. **Tests (`tests/test_config.py`, `tests/test_errors.py`, `tests/test_cli.py`, `tests/test_reporter.py`)**:
   - Verified default URL fallback.
   - Verified `UnsupportedLmsError` mapping to exit code 2 and safe message.
   - Verified structured `no_courses_found` notice in `check --json` and `sync --json` when course count is zero.
   - Verified that fatal errors suppress the `no_courses_found` notice.
   - Verified Rich notice rendering in check and sync console outputs.

## Verification

- Automated test run: `uv run pytest -v` (208 passed in 6.20s).
- Contract documentation check: `uv run pytest tests/test_contract_doc.py` passed.
