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

---

## UAT Re-run — 2026-09-23 (after real LMS credentials were filled in)

Run during `/gsd-verify-work 05` Test 1, again from the OS temp scratch folder via `uv --directory "D:/dev/kau-lxp-assistant" run python -m kau_assistant ...`. `.env` was not opened. Only counts, exit codes, error scopes/codes and structural markers are recorded here. All captured HTML/JSON was deleted right after the counts were taken.

### Current term (2026 2학기): mechanics PASS, 0 active courses

| Item | Result |
|---|---|
| `check --json` exit / duration | 0 / 28s |
| `check` summary | course_count 0, total 0, overdue 0, within_24h 0, later 0, error_count 0 |
| `check` (Rich) | exit 0; all three section headings rendered (기한 초과 / 24시간 이내 / 이후 일정), each "없음" |
| `sync --json` exit / duration | 0 / 20s |
| `sync` flags | enabled=true, dry_run=true, applied=false, counts all 0 (create/update/skip/error) |
| Notion Scheduler page count before → after `sync` | 62 → 62 (read-only `query_existing_pages`) |
| `--apply` used | never |

Why course_count is 0: this is the real state, not a scraper miss. The LMS header popover shows "진행중인 강좌 (0)", and `/local/ubion/user/?year=2026&semester=20` shows "참여중인 강좌가 없습니다". The LMS defaults that page to 2026 1학기, which has 6 courses.

Minor: `extract_courses` waits for `.block_coursemos_my_courses, .course_list, #dashboard, .my-course-lists, [role='main']`. On the real dashboard none of these are visible (`.my-course-lists` is inside a hidden popover and the main region is empty), so every run spends the full 15s timeout before continuing.

### Real-data parse probe (2026 1학기 courses, read-only)

The real `collect_tasks` pipeline ran with only the course source swapped to the 2026 1학기 list (`/local/ubion/user/?year=2026&semester=10`). Everything else was unchanged.

| Item | Result |
|---|---|
| Courses extracted | 6 (`[i/N]` progress 1/6 … 6/6), errors 0 |
| Assessments parsed | 50 (assignments 30, quizzes 20). Status mix: submitted 20, not_attempted 30. 48 of 50 have a due date |
| Lectures parsed | 69 across 4 courses (2 courses have no VOD). **0 of 69 have a due date; all 69 are `incomplete`** |
| Tasks after transform | 30 (quiz 19, assignment 11, **lecture 0**) |
| Report classification (real now) | overdue 28, within_24h 0, later 2 |

**Defect found (G-05-1): lecture deadlines are never parsed on the KAU LMS.**
- `CourseNavigator.navigate_progress_page` requests `/report/progress/index.php?id=N`, which does not exist here, so every course falls back to the course-home parser. The real attendance/progress page linked from the course home is `/report/ubcompletion/progress.php?id=N` (`table.user_progress`). Its headers are `주 | 강의 자료 | 출석인정 요구시간 | 총 학습시간`, with the week cell row-spanned. It has no period/deadline column and no O/X column, so the current column map (`주차/차시/진도/출석/기간`) would not match it either.
- On the course home, each VOD activity is `li.activity.vod.modtype_vod`. Its period is in `span.displayoptions > span.text-ubstrap` (format `YYYY-MM-DD HH:MM:SS ~ YYYY-MM-DD HH:MM:SS`). `parse_lectures_from_course_sections` only reads `availabilityinfo|activity-dates`, so `raw_due_date` is always empty.
- Result: every lecture gets `due_date=None` and is excluded by D-11. Completion is never read from the real progress data either. **No lecture can appear in `check` or `sync`.**

### Verdict (UAT Test 1)

**ISSUE (major).** The D-26 mechanics are verified live: foreign cwd, exit codes, JSON contract, dry-run with no Notion write. Assignment/quiz parsing works on real data. The lecture half of "real course data" fails (G-05-1). WINDOWS entry 1 (empty credentials) is closed; entry 2 tracks G-05-1.

---

## Gap-closure re-verification (LXP default) — 2026-09-24

### Scope and Safeguards

- **Timestamp (KST):** 2026-09-24 14:48 (UTC 05:48)
- **Invocation mode:** Run from an OS temporary directory outside the repository using `uv --directory "D:/dev/kau-lxp-assistant" run python ...`
- **Secret handling:** No `.env` content was opened, printed, or copied.
- **Write guard:** Zero `--apply` invocations; read-only probes and dry-run sync only.
- **Capture cleanup:** Scratch captures cleaned up immediately; working directory clean.

### Live Markers

- **LMS host:** lxp.kau.ac.kr
- **LMS_URL set in .env:** false
- **check exit code:** 0
- **check schema_version:** 1
- **check course_count:** 7
- **Seconds to first progress line:** 12.48
- **sync exit code:** 0
- **sync dry_run:** true
- **sync applied:** false
- **Scheduler page count (before/after):** 61 / 61
- **Write audit:** PASS
- **Foreign-cwd invocation:** PASS
- **Lectures with due date (parse probe):** 0
- **Duplicate lecture (week, clip) pairs:** 0
- **Assessments with due date / total:** 27 / 29
- **Assessment titles that parse as dates:** 0

### Summary of Probe Results

- **Courses extracted:** 7 active courses found on `https://lxp.kau.ac.kr`.
- **First progress line:** 12.48s (15s timeout successfully eliminated; courses processed immediately).
- **check items summary:**
  - Overdue: 3 items (1 course group)
  - Due within 24h: 1 item (1 course group)
  - Later: 11 items (4 course groups)
  - Total tasks: 15 (11 assignments, 4 quizzes)
  - Date-like titles: 0 (all titles are real assignment/quiz names)
  - Null due dates in check items: 0
  - First title SHA-256 prefixes:
    - overdue: `2be194c285ad24f2`
    - due_within_24h: `f98844d2fb9954e9`
    - later: `315368047e441c93`
- **sync dry-run summary:**
  - Counts: total 15, create 15, update 0, skip 0, error 0
  - Notion write audit: 61 pages before, 61 pages after (PASS, zero writes)
- **Parse probe details:**
  - Total assessments: 29 (21 assignments, 8 quizzes)
  - Assessments with due date: 27 of 29
  - Assessment status breakdown: 4 graded, 10 submitted, 15 not_attempted
  - Total lectures: 15 VODs detected across the 7 courses
  - Duplicate (week, clip) lecture pairs: 0 (section nesting bug resolved)
  - Lectures with due date: 0 (the 15 VOD activities in the current semester's courses on LXP have no attendance window configured in Coursemos; fixture-tested in 05-09).

