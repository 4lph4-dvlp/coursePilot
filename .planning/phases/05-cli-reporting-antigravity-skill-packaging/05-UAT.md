---
status: complete
phase: 05-cli-reporting-antigravity-skill-packaging
source: [05-VERIFICATION.md]
started: 2026-09-23T14:15:00Z
updated: 2026-09-23T15:33:49Z
---

## Current Test

[testing complete]

## Tests

### 1. Live check/sync evidence with real LMS credentials (D-26)
expected: check exits 0/1 with course_count >= 1 and real sections; sync dry-run exits 0/1 with dry_run=true, applied=false, unchanged Scheduler page count; evidence updated and WINDOWS.md entry 1 closed.
result: issue
reported: "1 (user chose: probe real parsing on 2026 1학기 courses, then pass if OK). Probe by Claude found: current term has 0 active courses (real state; check/sync exit 0, dry_run=true, applied=false, Notion 62→62). On 1학기 data, assignments/quizzes parse correctly (50 items), but 0 of 69 lectures get a due date, so no lecture ever reaches check/sync. Also: dashboard selector wait always times out (15s per run)."
severity: major

### 2. Natural-language skill invocation in all five agents (D-27)
expected: In Claude Code, Codex, Antigravity, Pi, and Hermes (new session, folder outside the repo), "과제 확인해줘" triggers kau-lxp, runs `check --json` via `uv --directory`, and replies with markdown tables ordered 기한 초과 → 24시간 이내 → 이후 일정, grouped by course, untruncated, with links for urgent items; "노션에 올려줘" shows the dry-run create/update/skip lists and asks for approval before any `--apply`. Results recorded in 05-AGENT-SKILL-EVIDENCE.md; wrong AGENT_SKILL_PATHS entries noted under Corrections.
result: issue
reported: "Claude Code / Codex / Pi triggered kau-lxp and ran check --json correctly. agy answered fastest but only read leftover check.stdout.json files in the shared folder (skill not invoked). Hermes never found the skill, searched unrelated files for 40+ min, interrupted. All agents failed to find the 2 assignments I know I have. I never gave my school's LXP address — where is it looking? Would it work for other schools with a different site structure?"
severity: blocker

## Scope Decision (2026-09-24)

- User confirmed the patched LXP run (LMS_URL=https://lxp.kau.ac.kr) found both pending assignments they know about.
- Gap-closure scope = A + B:
  - A: target the KAU LXP by default (https://lxp.kau.ac.kr) and fix LXP login/date/title/course-name/lecture parsing (G-05-2, G-05-3).
  - B: support Coursemos-family schools generally — LMS_URL is a first-class, documented setting (install/onboarding guidance), and an unsupported site structure fails loudly with a clear message instead of silently reporting 0 courses.
  - Out of scope: Canvas/Blackboard/custom LMS adapters (would be a new phase).
- G-05-1 / G-05-1b were observed on the old LMS (lms.kau.ac.kr); re-verify them against the LXP when fixing.

## Summary

total: 2
passed: 0
issues: 2
pending: 0
skipped: 0
blocked: 0

## Gaps

- gap_id: G-05-1
  truth: "Live check/sync against real KAU LMS course data reports incomplete lectures (VOD) with their deadlines, alongside assignments and quizzes"
  status: failed
  reason: "User reported (via Claude live probe on 2026 1학기 courses): 69 lectures parsed, 0 with due_date, all 'incomplete'; lecture tasks = 0. navigate_progress_page uses /report/progress/index.php (real: /report/ubcompletion/progress.php, table.user_progress with columns 주 | 강의 자료 | 출석인정 요구시간 | 총 학습시간, no period column); course-home fallback ignores span.displayoptions > span.text-ubstrap holding 'YYYY-MM-DD HH:MM:SS ~ YYYY-MM-DD HH:MM:SS'."
  severity: major
  test: 1
  artifacts: []  # Filled by diagnosis
  missing: []    # Filled by diagnosis

- gap_id: G-05-1b
  truth: "LMS course-list collection does not stall on a selector that never appears on the real KAU dashboard"
  status: failed
  reason: "User reported (via Claude live probe): extract_courses wait_for_selector always times out (15s) on the real /my/ dashboard; .my-course-lists is inside a hidden popover and region-main is empty."
  severity: minor
  test: 1
  artifacts: []  # Filled by diagnosis
  missing: []    # Filled by diagnosis

- gap_id: G-05-2
  truth: "check/sync read the student's current-term KAU LXP courses and find their known pending assignments"
  status: failed
  reason: "User reported: 2 known pending assignments not found by any agent; never provided an LXP URL. Claude probe: .env has no LMS_URL, so Settings.lms_url falls back to the hard-coded default https://lms.kau.ac.kr (old Coursemos LMS, 0 courses in 2026 2학기). Current-term courses live on https://lxp.kau.ac.kr (7 courses, 29 assessments found in a patched run)."
  severity: blocker
  test: 2
  artifacts: []  # Filled by diagnosis
  missing: []    # Filled by diagnosis

- gap_id: G-05-3
  truth: "Against https://lxp.kau.ac.kr the pipeline logs in, and every assignment/quiz/lecture has a correct title, course name, and due date"
  status: failed
  reason: "Claude probe with LMS_URL=https://lxp.kau.ac.kr: (a) login succeeds but perform_login raises AuthenticationError — no LOGGED_IN_SELECTORS visible (logout link is hidden in a dropdown); (b) all 29 assessments have due_date=None — raw dates are Moodle long form '화요일, 6 10월 2026, 1:00 PM', unparsed by parse_lms_date; (c) quiz titles come out as the date (quiz index headers are 주 | 이름 | 시험 마감 | 성적); (d) clean_name keeps a professor-surname prefix ('최공학수학II' from '최공학수학II(0419) (00)'); (e) lecture week numbers wrong (e.g. 6주차 and 22주차 share one deadline), only 12 of 52 lectures have a due date."
  severity: major
  test: 2
  artifacts: []  # Filled by diagnosis
  missing: []    # Filled by diagnosis

- gap_id: G-05-4
  truth: "kau-lxp is discovered and invoked in Antigravity and Hermes"
  status: failed
  reason: "User reported: agy never invoked the skill (answered from leftover files in C:/Temp/kau-uat); Hermes never found it — it searched C:/Users/alpha/AppData/Local/hermes/skills, not the installed ~/.hermes/skills/kau-lxp — and wandered through unrelated files for 40+ min. The 노션에 올려줘 step was not exercised in Codex/agy/Pi/Hermes."
  severity: major
  test: 2
  artifacts: []  # Filled by diagnosis
  missing: []    # Filled by diagnosis
