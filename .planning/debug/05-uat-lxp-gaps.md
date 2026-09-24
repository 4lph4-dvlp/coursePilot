# Debug: Phase 05 UAT gaps (LXP target, parsing, agent discovery)

**Goal:** find_root_cause_only (fixes via /gsd-plan-phase 05 --gaps)
**Discovered:** /gsd-verify-work 05, 2026-09-23/24
**Method:** live read-only probes against lms.kau.ac.kr and lxp.kau.ac.kr (counts and structure only; captured HTML deleted after use), plus code reading. `.env` was never opened.

## G-05-2 (blocker): wrong LMS target

- `src/kau_assistant/config.py:18`: `lms_url` defaults to `https://lms.kau.ac.kr`. `"lms_url" in get_settings().model_fields_set` is False, so the user's `.env` has no `LMS_URL` and the default is used.
- lms.kau.ac.kr is the old Coursemos LMS. For 2026 2학기, `/local/ubion/user/?year=2026&semester=20` says "참여중인 강좌가 없습니다". Only 1학기 courses exist there.
- https://lxp.kau.ac.kr ("한국항공대LXP", also Coursemos/Moodle; login form `input#input-username`, `input#input-password`, `button[name=loginbutton][type=submit]`) holds the current term. `/my/` lists 7 courses and `extract_courses_from_html` finds all 7. With the URL overridden, the user confirmed their 2 known pending assignments were found.
- `/local/ubion/user/` returns 403 on the LXP, so course discovery must stay on `/my/`.
- README/.env.example treat `LMS_URL` as optional, and nothing warns when a Coursemos site returns 0 courses because it is the wrong site or term.

## G-05-3 (major): LXP parsing defects

a. **Login check:** `auth.py` `LOGGED_IN_SELECTORS` has no match *visible* on the LXP home page after a successful login (`a[href*='logout']` exists but sits in a hidden dropdown). `perform_login` raises `AuthenticationError("로그인 후 대시보드 인증 요소를 확인할 수 없습니다.")`, final page `/`, title `홈 | 한국항공대LXP`. Login actually succeeded. The logged-in state is visible on `body` (no `notloggedin` class), and the logout link is present in the DOM.
b. **Dates:** LXP renders Moodle long-form dates, e.g. `화요일, 6 10월 2026, 1:00 PM` and `월요일, 14 9월 2026, 3:20 PM`. `date_parser.parse_lms_date` only knows `YYYY-MM-DD HH:MM`, `YYYY년 M월 D일 HH:MM`, `M월 D일 HH:MM`, and `M/D HH:MM`, so all 29 assessments get `due_date=None`. Reports and Notion then show no deadlines.
c. **Quiz title = date:** the LXP quiz index header is `주 | 이름 | 시험 마감 | 성적`. In `assessment_parser.py:44` the title keywords include `시험`, so `시험 마감` is mapped as the title column. `이름` is not a title keyword and `시험 마감` never maps to due, so the title comes from the date cell.
d. **Course name prefix:** the anchor text is `최공학수학II(0419) (00)`, i.e. professor-surname/badge text concatenated by `a.get_text(strip=True)` in `course_list.py`. `clean_course_name` removes `(0419)`/`(00)` but keeps the leading `최`. Needs the dedicated title element of the course card (or removal of badge children) instead of the whole anchor text.
e. **Lectures:** in the one LXP course with VODs, 52 lectures were parsed but only 12 have due dates, and week numbers are wrong (e.g. 6주차 and 22주차 share one deadline). Likely cause: the `parse_lectures_from_course_sections` selector (`section\s*main|course-section`) matches nested section containers, so VODs are counted twice under different `sec_idx`. The period sits in `span.displayoptions > span.text-ubstrap` (seen on the old LMS, same theme family), which the parser ignores. The progress URL `/report/progress/index.php` does not exist on Coursemos. The real page is `/report/ubcompletion/progress.php?id=N` (table `user_progress`, headers `주 | 강의 자료 | 출석인정 요구시간 | 총 학습시간`, no period column; completion must compare 총 학습시간 against 출석인정 요구시간, or use the O/X attendance page `/local/ubattendance/my_status.php?id=N`).
f. **G-05-1b** (old LMS): `extract_courses` waits 15s for `.block_coursemos_my_courses, .course_list, #dashboard, .my-course-lists, [role='main']`, which never becomes visible on the old LMS dashboard. Re-check on the LXP `/my/` ("강의 현황").

## G-05-4 (major): agent discovery

- **Hermes:** the installer target is `~/.hermes/skills` (`installer.py:80-81`). On this Windows machine Hermes' home is `%LOCALAPPDATA%\hermes` (config.yaml, skills/, state.db), and its `skills/` holds the user's other skills. Hermes searched there and never found kau-lxp. Fix: resolve `HERMES_HOME`, else `%LOCALAPPDATA%\hermes` on Windows, else `~/.hermes`.
- **Antigravity (agy):** the path `~/.gemini/antigravity/skills` is plausibly correct (agy's `settings.json` references `~/.gemini/antigravity/skills/gsd-*`). The agent skipped the skill because the shared test folder already contained `check.stdout.json` from the Codex run, so this was test contamination. Needs a retest in an empty folder.
- The "노션에 올려줘" flow was only exercised in Claude Code.

## Scope (user decision 2026-09-24): A + B

A: default to the KAU LXP and fix a–e. B: Coursemos-family schools via a documented `LMS_URL`, with a loud "unsupported structure / 0 courses — check LMS_URL and term" diagnostic instead of a silent empty report. Canvas and other platforms are out of scope.

## LXP markup shapes (redacted probe, 2026-09-24)

### Login
- Landing URL: `https://lxp.kau.ac.kr/`
- Site title: `홈 | 한국항공대LXP`
- Attached logout link present: True
- body.notloggedin count: 0

### /my/ dashboard
- Distinct course links found: 7
- Moodle markers: M.cfg: True, /theme/: True, page-my-index: False, pagelayout-: True, coursemos: True, ubion: True
- Wait selectors status:
  - `.block_coursemos_my_courses`: attached=False, visible=False, count=0
  - `.course_list`: attached=False, visible=False, count=0
  - `#dashboard`: attached=False, visible=False, count=0
  - `.my-course-lists`: attached=False, visible=False, count=0
  - `[role='main']`: attached=True, visible=True, count=1
  - `a[href*='/course/view.php?id=']`: attached=True, visible=False, count=7
- First course link text starts with single Hangul syllable: False
- Course card container skeleton:
```xml
<li.dropdown-item-course>
  <a.dropdown-item.dropdown-item-icon>
    <div.csms-avata.csms-avata-NN.csms-avata-picture.csms-avata-Nxsm>
«text:1»
    </div>
    <div.text-truncate>
«text:17»
    </div>
  </a>
</li>
```

### Course home (VOD sections)
- Course [id=NNNN]:
  - VOD activity li count: 0, distinct module IDs: 0
  - span.displayoptions span.text-ubstrap count: 0
  - Current regex matched count: 1, top-level li.section count: 0
  - Section headings (sample up to 4): []
  - span.instancename has .accesshide child: False
- Course [id=NNNN]:
  - VOD activity li count: 15, distinct module IDs: 15
  - span.displayoptions span.text-ubstrap count: 0
  - Current regex matched count: 49, top-level li.section count: 15
  - Section headings (sample up to 4): ['강의 개요', 'N주차', 'N주차', 'N주차']
  - span.instancename has .accesshide child: False
- Course [id=NNNN]:
  - VOD activity li count: 0, distinct module IDs: 0
  - span.displayoptions span.text-ubstrap count: 0
  - Current regex matched count: 1, top-level li.section count: 0
  - Section headings (sample up to 4): []
  - span.instancename has .accesshide child: False
- First VOD ancestor chain: ul.section -> div.course-section-content.course-content-item-content -> div.section-item -> li.section.course-section.main.clearfix -> ul.ubsweeks.weeks.ubformat
- First VOD li skeleton:
```xml
<li#module-NNNN.activity.activity-wrapper.vod.modtype_vod.hasinfo.activity-incomplete>
  <div.activity-item.focus-control>
    <div.activity-flex>
      <a.activity-container.activity-container-link>
        <div.activity-icon-area.has-extend-info>
          <div.bulkselect.d-none.form-check>

          </div>
          <div.activity-icon.activityiconcontainer.other.courseicon>

          </div>
        </div>
        <div.activity-name-area>
          <div.activitytitle.modtype_vod.position-relative>

          </div>
          <div.activity-extend-info>

          </div>
        </div>
      </a>
    </div>
  </div>
</li>
```

### Progress page
- HTTP status: 404
- table.user_progress exists: False

### Assessment index pages
- Quiz index (`table.generaltable`):
  - Headers: ['주', '이름', '시험 마감', '성적']
  - First row cells (masked): ['N주차', '«title:len»', '월요일, NN N월 NNNN, N:NN PM', 'NN.NN/NN.NN']
- Assign index (`table.generaltable`):
  - Headers: ['주', '과제물들', '종료 일시', '제출물', '성적']
  - First row cells (masked): ['', '«title:len»', '-', '제출 완료', '-']
