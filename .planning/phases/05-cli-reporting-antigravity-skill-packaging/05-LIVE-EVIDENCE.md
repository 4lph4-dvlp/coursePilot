# Phase 05-05 Live End-to-End Evidence

## Scope and Safeguards

- **Timestamp (UTC):** 2026-09-23T13:49-13:52Z (KST 22:49-22:52)
- **Automated baseline:** `uv run pytest` (full suite, before any live command)
- **Automated baseline result:** PASS — 178 tests
- **Invocation mode:** every live command below was run from an OS temp scratch folder outside the repository, via `uv --directory "D:/dev/kau-lxp-assistant" run python -m kau_assistant ...`
- **Secret handling:** No `.env` content was ever opened, printed, or copied. No student ID, password, Notion token, raw JSON payload, plain-text task title, or assignment text is recorded below — only counts, exit codes, error codes/scopes, and (where applicable) SHA-256 title-prefix hashes.
- **Write guard:** `sync` was run without `--apply` at every step; no `--apply` invocation occurred anywhere in this evidence.
- **Capture cleanup:** stdout/stderr captures and the standalone Notion read-count scripts were written only inside the OS temp scratch folder and deleted immediately after the values below were recorded; `git status --porcelain` after the run shows no new/untracked capture files in the repository.

## Result Summary

**The live run surfaced a genuine, previously-undetected precondition gap: `.env` exists (satisfying Task 1's file-existence-only precondition check) but its `LMS_USERNAME` and `LMS_PASSWORD` values are empty.** Both `check` and `sync` therefore exited `2` with a `ConfigError` before any browser session or course scrape began. This is not an LMS-structure mismatch (A-13) — it is a real, unmet environmental precondition that only the user can resolve by filling in their real LMS credentials in `.env`. Per this task's own instructions ("If `check` exits 2, record the error code, keep the markers truthful... and report the blocker"), this outcome is recorded exactly as observed rather than retried or fabricated. **The task's automated `<verify>` therefore fails as designed** (it requires `check exit code` 0 or 1) — see "Verify Outcome" below.

## `check --json` Result

- **check exit code:** 2
- **check duration:** ~1s (failed before any browser/session I/O — `validate_lms_settings` runs as the first statement of `collect_tasks`, per 05-02's D-18 guard)
- **check schema_version:** 1
- **command field:** `check`
- **Top-level keys:** `schema_version, command, generated_at, summary, items, errors` (matches `CheckReport`)
- **summary.course_count:** 0
- **summary.total_count:** 0
- **summary.overdue_count:** 0
- **summary.due_within_24h_count:** 0
- **summary.later_count:** 0
- **summary.error_count:** 1
- **Course-group / item counts per section:** overdue: 0 groups / 0 items; due_within_24h: 0 groups / 0 items; later: 0 groups / 0 items (all three sections empty — no non-empty section, so no title-hash prefix to record)
- **Errors — scope/code (messages omitted):** 1 error — scope `fatal`, code `ConfigError`
- **stderr `[i/N]` progress-line count:** 0 — equals `summary.course_count` (0), confirming per-course progress never started because the fatal-stage guard fired first (05-02 D-18 contract: nothing before `validate_lms_settings` touches a browser)

## `check` (non-JSON, Rich) Result

- **Section headings present:** yes — all three (기한 초과 / 24시간 이내 / 이후 일정) rendered, each showing "없음" (none) because the run never collected any courses; a "수집 오류" (collection error) table also rendered with the same `fatal` / `ConfigError` scope/code as the JSON run

## Notion Scheduler Read-Only Probe (independent of the CLI, D-26 write audit)

- **Scheduler target resolved:** yes (via `NotionClient(get_settings()).resolve_target()`, read-only)
- **Scheduler page count (before, `query_existing_pages`):** 62
- **Scheduler page count (after, `query_existing_pages`):** 62
- **Write audit:** PASS (page count unchanged: 62 / 62; zero create/update calls were made anywhere in this evidence — the CLI's own `sync` run never reached `NotionSyncEngine` at all, and the two `query_existing_pages` probes above are read-only by construction)

## `sync --json` Result

- **sync exit code:** 2
- **sync command field:** `sync`
- **sync.enabled / sync.dry_run / sync.applied / sync.counts:** not observable this run — the fatal `ConfigError` at the shared LMS-collection stage (`_collect_lms_tasks`) fired before `sync` ever reached the `else` branch that constructs `NotionSyncEngine(...).sync(tasks, dry_run=not apply)`; `cli.py`'s fatal-boundary path builds the report with `sync=None` (`build_sync_report([], None, course_count=0, errors=[fatal], now=now)`). This is the same shared-collection contract `check` and `sync` intentionally share (05-01/05-03 D-07/D-08) — Notion was never configured to be reached this run because the fatal stage is strictly upstream of it.
- **Notion error codes:** none — `sync.errors` never populated because the Notion stage was never entered
- **No `--apply` invocation appears in any command run in this evidence** (confirmed by direct inspection of the commands above)

## Foreign-Cwd Invocation

- **Foreign-cwd invocation:** PASS — both `check --json` and `sync --json` were invoked as `uv --directory "D:/dev/kau-lxp-assistant" run python -m kau_assistant ... --json` from the OS temp scratch folder (outside the repository) and both produced parseable, well-formed JSON on stdout (verified: `schema_version`, `command`, and the full top-level key set matched the contract in both cases, even on the fatal path)

## Verify Outcome

- The task's automated `<verify>` (`check exit code` must be 0 or 1, plus the five required marker substrings) **fails** on this run, because `check exit code` is genuinely `2`. This is the explicit, anticipated outcome for this scenario per the task's own action text ("the verify below then fails and halts the tracer, and report the blocker").
- Per the executor's instructions for this exact scenario, this run is **not retried** against the live LMS.

## Blocker — Action Required

`LMS_USERNAME` and `LMS_PASSWORD` in the repository's `.env` are empty. To obtain a clean D-26 live-evidence run with real course/assignment data:

1. Open `.env` (never share its contents in chat) and fill in the real KAU LXP student ID and password for `LMS_USERNAME` / `LMS_PASSWORD`.
2. Re-run `uv --directory "<repo root>" run python -m kau_assistant check --json` and `sync --json` from any folder outside the repository (as this evidence file did) and update this document, or ask for the equivalent verification step to be re-run.

This gap is also recorded in `.planning/WINDOWS.md` as an `unmet-truth` entry against D-26 so it stays visible at ship time.

## Verdict

**PARTIAL — real, redacted evidence recorded; D-26's full "working live check + dry-run sync against real course/assignment data" truth is unmet due to an empty `LMS_USERNAME`/`LMS_PASSWORD` in `.env`.** No secret, raw payload, or plain-text task/assignment title was recorded at any point. No Notion write occurred (62 pages before, 62 after). No `--apply` was ever invoked. This is a genuine environmental precondition gap, not a code defect — resolving it requires the user to fill in their real LMS credentials.
