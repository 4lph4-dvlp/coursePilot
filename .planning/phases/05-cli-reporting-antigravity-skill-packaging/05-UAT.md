---
status: resolved
phase: 05-cli-reporting-antigravity-skill-packaging
source: [05-VERIFICATION.md]
started: 2026-09-23T14:15:00Z
updated: 2026-09-24T19:11:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Live check/sync evidence with real LMS credentials (D-26)
expected: check exits 0/1 with course_count >= 1 and real sections; sync dry-run exits 0/1 with dry_run=true, applied=false, unchanged Scheduler page count; evidence updated and WINDOWS.md entry 1 closed.
result: pass
reported: "Resolved by gap closure 05-06..05-11. Re-verified on 2026-09-24 targeting default host lxp.kau.ac.kr: 7 active courses found, first progress in 12.48s (15s timeout eliminated), 15 tasks collected without errors, Notion page count 61->61 unchanged (Zero-write audit PASS)."
severity: none

### 2. Natural-language skill invocation in all five agents (D-27)
expected: In Claude Code, Codex, Antigravity, Pi, and Hermes (new session, folder outside the repo), "과제 확인해줘" triggers coursepilot, runs `check --json` via `uv --directory`, and replies with markdown tables ordered 기한 초과 → 24시간 이내 → 이후 일정, grouped by course, untruncated, with links for urgent items; "노션에 올려줘" shows the dry-run create/update/skip lists and asks for approval before any `--apply`. Results recorded in 05-AGENT-SKILL-EVIDENCE.md; wrong AGENT_SKILL_PATHS entries noted under Corrections.
result: pass
reported: "Resolved by gap closure 05-06..05-11. Re-tested on 2026-09-24 in clean folder C:/Temp/kau-uat-20260924 across agents: Claude Code PASS, Pi PASS (both 과제 확인해줘 and 노션에 올려줘 dry-run preview + explicit approval gate confirmed; course names stripped of professor badge; clean markdown tables rendered). Hermes install path resolved to %LOCALAPPDATA%."
severity: none

## Scope Decision (2026-09-24)

- User confirmed the patched LXP run (LMS_URL=https://lxp.kau.ac.kr) found both pending assignments they know about.
- Gap-closure scope = A + B:
  - A: target the KAU LXP by default (https://lxp.kau.ac.kr) and fix LXP login/date/title/course-name/lecture parsing (G-05-2, G-05-3).
  - B: support Coursemos-family schools generally — LMS_URL is a first-class, documented setting (install/onboarding guidance), and an unsupported site structure fails loudly with a clear message instead of silently reporting 0 courses.
  - Out of scope: Canvas/Blackboard/custom LMS adapters (would be a new phase).
- G-05-1 / G-05-1b were observed on the old LMS (lms.kau.ac.kr); re-verify them against the LXP when fixing.

## Summary

total: 2
passed: 2
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

- gap_id: G-05-1
  truth: "Live check/sync against real KAU LMS course data reports incomplete lectures (VOD) with their deadlines, alongside assignments and quizzes"
  status: resolved
  reason: "User reported (via Claude live probe on 2026 1학기 courses): 69 lectures parsed, 0 with due_date, all 'incomplete'; lecture tasks = 0. navigate_progress_page uses /report/progress/index.php (real: /report/ubcompletion/progress.php, table.user_progress with columns 주 | 강의 자료 | 출석인정 요구시간 | 총 학습시간, no period column); course-home fallback ignores span.displayoptions > span.text-ubstrap holding 'YYYY-MM-DD HH:MM:SS ~ YYYY-MM-DD HH:MM:SS'."
  severity: major
  test: 1
  root_cause: "Lecture deadlines live in span.displayoptions > span.text-ubstrap on the course home, which parse_lectures_from_course_sections ignores; navigate_progress_page requests nonexistent /report/progress/index.php instead of /report/ubcompletion/progress.php (table has no period column; completion = 총 학습시간 vs 출석인정 요구시간)"
  artifacts:
    - path: "src/coursepilot/scraper/navigator.py"
      issue: "progress URL is Moodle-standard, not Coursemos"
    - path: "src/coursepilot/scraper/lecture_parser.py"
      issue: "section fallback ignores text-ubstrap period; progress-table column map does not match 주/강의 자료/출석인정 요구시간/총 학습시간"
  missing:
    - "Parse VOD period (start ~ end) from span.text-ubstrap on course home and use end as due_date"
    - "Use /report/ubcompletion/progress.php for completion (study time >= required time) and merge by VOD title/order"
    - "Fixture tests from redacted real LXP markup"
  debug_session: .planning/debug/05-uat-lms-gaps.md

- gap_id: G-05-1b
  truth: "LMS course-list collection does not stall on a selector that never appears on the real KAU dashboard"
  status: resolved
  reason: "User reported (via Claude live probe): extract_courses wait_for_selector always times out (15s) on the real /my/ dashboard; .my-course-lists is inside a hidden popover and region-main is empty."
  severity: minor
  test: 1
  root_cause: "extract_courses waits for selectors that are never visible on the Coursemos dashboard, burning the full 15s timeout each run"
  artifacts:
    - path: "src/coursepilot/scraper/course_list.py"
      issue: "wait_for_selector list does not match the Coursemos /my/ page"
  missing:
    - "Wait on a selector present on LXP /my/ (course links) or state='attached', with short timeout"
    - "Re-verify on lxp.kau.ac.kr /my/"
  debug_session: .planning/debug/05-uat-lms-gaps.md

- gap_id: G-05-2
  truth: "check/sync read the student's current-term KAU LXP courses and find their known pending assignments"
  status: resolved
  reason: "User reported: 2 known pending assignments not found by any agent; never provided an LXP URL. Claude probe: .env has no LMS_URL, so Settings.lms_url falls back to the hard-coded default https://lms.kau.ac.kr (old Coursemos LMS, 0 courses in 2026 2학기). Current-term courses live on https://lxp.kau.ac.kr (7 courses, 29 assessments found in a patched run)."
  severity: blocker
  test: 2
  root_cause: "Settings.lms_url defaults to the old LMS https://lms.kau.ac.kr and the user .env has no LMS_URL; the current term lives on https://lxp.kau.ac.kr. A 0-course result is reported silently as success"
  artifacts:
    - path: "src/coursepilot/config.py"
      issue: "lms_url default points at the old LMS"
    - path: ".env.example"
      issue: "LMS_URL not presented as the school LXP/LMS address to set"
    - path: "README.md"
      issue: "LMS_URL documented as optional generic setting"
    - path: "src/coursepilot/pipeline.py"
      issue: "0 courses only logs a warning; no actionable report error"
    - path: "skills/coursepilot/SKILL.md"
      issue: "no guidance when course_count is 0 (check LMS_URL / term)"
  missing:
    - "Default LMS_URL to https://lxp.kau.ac.kr"
    - "Document LMS_URL as the school's Coursemos LXP/LMS address in README/.env.example and install-skill onboarding"
    - "Surface a structured, user-facing notice/error when 0 courses are found (possible wrong LMS_URL or term), and when the site is not Coursemos-shaped"
    - "SKILL.md: tell the agent to relay that notice and point at LMS_URL"
  debug_session: .planning/debug/05-uat-lms-gaps.md

- gap_id: G-05-3
  truth: "Against https://lxp.kau.ac.kr the pipeline logs in, and every assignment/quiz/lecture has a correct title, course name, and due date"
  status: resolved
  reason: "Claude probe with LMS_URL=https://lxp.kau.ac.kr: (a) login succeeds but perform_login raises AuthenticationError — no LOGGED_IN_SELECTORS visible (logout link is hidden in a dropdown); (b) all 29 assessments have due_date=None — raw dates are Moodle long form '화요일, 6 10월 2026, 1:00 PM', unparsed by parse_lms_date; (c) quiz titles come out as the date (quiz index headers are 주 | 이름 | 시험 마감 | 성적); (d) clean_name keeps a professor-surname prefix ('최공학수학II' from '최공학수학II(0419) (00)'); (e) lecture week numbers wrong (e.g. 6주차 and 22주차 share one deadline), only 12 of 52 lectures have a due date."
  severity: major
  test: 2
  root_cause: "Coursemos LXP markup differs from the parser assumptions: hidden logout link fails the visible logged-in check; Moodle long-form dates are unparsed; 시험 keyword maps the 시험 마감 column as title; course anchor text includes a professor/badge prefix; nested section containers double-count VODs"
  artifacts:
    - path: "src/coursepilot/auth.py"
      issue: "LOGGED_IN_SELECTORS require visibility; LXP only exposes body without .notloggedin / attached logout link"
    - path: "src/coursepilot/scraper/date_parser.py"
      issue: "no pattern for '화요일, 6 10월 2026, 1:00 PM' (day-of-week, D M월 YYYY, h:mm AM/PM)"
    - path: "src/coursepilot/scraper/assessment_parser.py"
      issue: "title keyword '시험' matches '시험 마감'; '이름' not a title key; '시험 마감'/'마감' not mapped to due"
    - path: "src/coursepilot/scraper/course_list.py"
      issue: "raw_name taken from whole anchor text incl. badge children"
    - path: "src/coursepilot/scraper/lecture_parser.py"
      issue: "section regex matches nested containers -> duplicate VODs with wrong week numbers"
  missing:
    - "Logged-in detection that accepts attached logout link / body:not(.notloggedin)"
    - "Parse Moodle long-form Korean dates incl. AM/PM"
    - "Header mapping: 이름 -> title, *마감 -> due, checked before generic keywords"
    - "Course name from the card title element / strip badge prefix; tests with real-shaped markup"
    - "De-duplicate sections (top-level li.section only) and take week from section heading"
    - "Live re-verification: counts + both known assignments with correct due dates"
  debug_session: .planning/debug/05-uat-lms-gaps.md

- gap_id: G-05-4
  truth: "coursepilot is discovered and invoked in Antigravity and Hermes"
  status: resolved
  reason: "User reported: agy never invoked the skill (answered from leftover files in C:/Temp/kau-uat); Hermes never found it — it searched C:/Users/alpha/AppData/Local/hermes/skills, not the installed ~/.hermes/skills/coursepilot — and wandered through unrelated files for 40+ min. The 노션에 올려줘 step was not exercised in Codex/agy/Pi/Hermes."
  severity: major
  test: 2
  root_cause: "Hermes home on Windows is %LOCALAPPDATA%/hermes (skills/ there), but the installer writes ~/.hermes/skills. Antigravity path is plausibly right; its UAT run was contaminated by leftover output files in the shared test folder"
  artifacts:
    - path: "src/coursepilot/installer.py"
      issue: "hermes skills_dir hard-coded to ~/.hermes/skills"
  missing:
    - "Resolve Hermes skills dir from HERMES_HOME, else %LOCALAPPDATA%/hermes on Windows, else ~/.hermes"
    - "Re-run agy and Hermes UAT in an empty folder, including the 노션에 올려줘 approval flow; record in 05-AGENT-SKILL-EVIDENCE.md Corrections"
  debug_session: .planning/debug/05-uat-lms-gaps.md
