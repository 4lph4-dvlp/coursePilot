# Roadmap: KAU LXP Assistant & Notion Scheduler Sync Skill

## Overview

본 로드맵은 대학 온라인 학습 사이트(한국항공대 LXP / 표준 Canvas·Moodle)에서 학생 계정으로 자동 로그인하여 강의 수강 현황 및 과제 마감일을 수집하고, 이를 사용자의 기존 Notion Scheduler 데이터베이스(`21d53280-64be-80ec-af4e-000b679f03bb`)에 중복 없이 정규화된 네이밍으로 동기화하는 범용 AI Agent Skill(Claude Code, Codex, Antigravity, Pi, Hermes 등 SKILL.md 지원 에이전트 공통)을 단계별로 구축합니다.

## Milestone 1: Core Foundation & Sync Skill (v1.0 - Completed)

- [x] **Phase 1: Foundation & Session Management** - 환경 설정 로더, 과목명 매핑 정의, Playwright 브라우저 셋업 및 LMS 자동 로그인/세션 캐시 구축 (completed 2026-09-21)
- [x] **Phase 2: LMS Scraper Core** - 수강 강좌 목록, 주차별 온라인 강의 진도율 및 마감일, 과제 목록 및 제출 여부 파싱 모듈 구현 (completed 2026-09-21)
- [x] **Phase 3: Domain Modeling & Naming Rules** - 데이터 모델 구조화, 노션 기존 관례를 반영한 과목명 약칭 및 통일 네이밍 엔진, 24시간 마감 임박 감지 로직 구현 (completed 2026-09-21)
- [x] **Phase 4: Notion Scheduler Integration & Deduplication** - Notion Scheduler DB 연동, 기존 등록 항목 조회 기반 중복 등록 방지, 스키마 속성 매핑 및 드라이런 모드 구현 (completed 2026-09-22)
- [x] **Phase 5: CLI Reporting & Universal Agent Skill Packaging** - Rich 콘솔 브리핑 리포트 출력, CLI 인터페이스(`check`, `sync`, `install-skill`), 범용 Agent Skill(`SKILL.md`) 패키징 및 엔드투엔드 검증 (completed 2026-09-24)

## Milestone 2: LXP Quiz Submission Verification & VOD Completion Enhancement (v1.1)

- [x] **Phase 6: Quiz Submission Status Enrichment** - 성적 비공개 퀴즈의 상세 페이지(view.php) 응시 내역(답안 검토, 응시 횟수 초과) 파싱 및 완료 상태 판정 (completed 2026-09-24)
- [x] **Phase 7: VOD Activity & Attendance Completion Tracking** - LXP 실제 활동 현황(/report/ublogs/completion.php) 연동 및 개별 VOD 시청 완료/미완료 상태 및 미지정 마감일 보존 (completed 2026-09-24)
- [x] **Phase 8: End-to-End Verification & Agent Re-deployment** - 실사이트 LXP 대상 E2E 검증 및 5개 에이전트 스킬 일괄 재배포 (completed 2026-09-24)

## Milestone 3: Automated VOD Attendance Player & Notion Completion Sync (v1.2)

- [x] **Phase 9: VOD Playback Engine & Heartbeat Automation** - Video.js 플레이어 자동 재생, 음소거, 이어보기 모달 처리, 진도 하트비트 세션 유지 엔진 구축 (completed 2026-09-25)
- [x] **Phase 10: Watch Pipeline, CLI Runner & Notion Completion Mode** - 과목/주차 필터링 기반 순차 VOD 시청 파이프라인, `watch` CLI 명령어 및 Notion `완료` 상태 동기화 모드 (completed 2026-09-25)
- [x] **Phase 11: Background Sub-agent Automation & Multi-Agent Skill Packaging** - 비동기 백그라운드/서브에이전트 시청 실행 가이드, 범용 `SKILL.md` 업데이트 및 5개 에이전트 재배포 (completed 2026-09-25)

## Phase Details

### Phase 1: Foundation & Session Management

**Goal**: 안전한 환경변수 로딩, 과목명 축약 매핑 로드, Playwright 기반 LMS 자동 로그인 및 세션 캐싱 인프라 구축
**Depends on**: Nothing (first phase)
**Requirements**: CONF-01, CONF-02, CONF-03, SCRP-01
**Success Criteria** (what must be TRUE):

  1. `.env` 파일과 `course_mappings.json`에서 접속 정보와 약칭 매핑을 정상 로드할 수 있다.
  2. Playwright 헤드리스 브라우저가 LMS 로그인 페이지에 접속하여 로그인에 성공하고 대시보드 진입을 확인한다.
  3. 로그인 후 세션 쿠키/스토리지 상태가 `session.json`에 저장되어 재실행 시 로그인 과정을 건너뛸 수 있다.

**Plans**: 2/2 plans executed

Plans:

- [x] 01-01-PLAN.md
- [x] 01-02-PLAN.md

**Wave 1**

- [x] 01-01: 프로젝트 기본 디렉터리 구조, 의존성(`pyproject.toml` 또는 `requirements.txt`), `.env.example`, `config.py` 구현

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 01-02: Playwright 브라우저 관리자 및 세션 캐싱/자동 로그인 모듈(`session_manager.py`, `auth.py`) 구현 및 로그인 테스트

---

### Phase 2: LMS Scraper Core

**Goal**: 수강 강좌 목록 수집 및 각 과목별 주차 강의 수강 상태, 과제 제출 여부, 마감일 파싱 구현
**Depends on**: Phase 1
**Requirements**: SCRP-02, SCRP-03, SCRP-04
**Success Criteria** (what must be TRUE):

  1. 학생이 수강 중인 모든 강좌의 이름, ID, 과목 홈 URL 목록을 정확하게 추출한다.
  2. 각 강좌의 주차별 동영상 강의 항목, 수강 진도(완료/미완료), 시청 마감 일시를 파싱한다.
  3. 각 강좌의 과제 목록, 제출 완료 여부, 제출 마감 일시를 파싱한다.

**Plans**: 2/2 plans executed

Plans:

- [x] 02-01-PLAN.md
- [x] 02-02-PLAN.md

**Wave 1**

- [x] 02-01: 강좌 목록 추출 및 과목별 메인/주차별 페이지 탐색기 구현

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 02-02: 동영상 강의 진도율/마감일 파서 및 과제 목록/제출 상태 파서 구현

---

### Phase 3: Domain Modeling & Naming Rules

**Goal**: 수집 데이터의 정규화, 통일된 작업 이름 규칙 생성, 24시간 마감 임박 판정 로직 구현
**Depends on**: Phase 2
**Requirements**: DOMN-01, DOMN-02, DOMN-03
**Success Criteria** (what must be TRUE):

  1. 수집된 강의/과제 데이터를 표준 `Course`, `LectureItem`, `AssignmentItem`, `SyncTask` 데이터클래스로 변환한다.
  2. 과목명 매핑 규칙에 따라 `[공수2] 3주차 강의 시청`, `[자구] 1차 과제 제출` 형태로 작업명이 정규화된다.
  3. 마감 일시가 현재 시간 기준 24시간 이내인 미완료 항목에 `🔴 긴급 (P1)` 우선순위가 자동 지정된다.

**Plans**: 1/1 plans executed

Plans:

- [x] 03-01-PLAN.md

**Wave 1**

- [x] 03-01: 도메인 데이터 모델(`SyncTask`, `Course`), 네이밍 포맷팅 엔진(`naming.py`), 24시간 긴급도/우선순위 분석기(`priority.py`) 및 DTO 변환기(`transformer.py`) 구현

---

### Phase 4: Notion Scheduler Integration & Deduplication

**Goal**: 사용자의 기존 Notion Scheduler DB 연동, 기등록 항목 조회를 통한 중복 등록 방지, 스키마 매핑 및 동기화 구현
**Depends on**: Phase 3
**Requirements**: NOTN-01, NOTN-02, NOTN-03, NOTN-04
**Success Criteria** (what must be TRUE):

  1. Notion Scheduler DB(`21d53280-64be-80ec-af4e-000b679f03bb`)의 기존 페이지를 조회하여 기등록 작업명 목록을 추출할 수 있다.
  2. 이미 등록된 강의/과제는 건너뛰고 신규 미완료 항목만 노션 페이지로 생성한다.
  3. `선택`('루틴'/'이벤트'), `구분`(['학업']), `DueDate`, `우선순위`, `상태`('시작 전'), `메모` 속성이 정확하게 입력된다.
  4. `--dry-run` 옵션 실행 시 실제 노션 페이지 생성 없이 등록 대상 및 스킵 목록을 확인할 수 있다.

**Plans**: 2/2 plans executed

Plans:

- [x] 04-01-PLAN.md
- [x] 04-02-PLAN.md

**Wave 1**

- [x] 04-01: Notion API/MCP 클라이언트 래퍼 및 기등록 항목 중복 검사 엔진 구현

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 04-02: 노션 스키마 속성 매핑, 페이지 생성 로직 및 드라이런 모드 구현

---

### Phase 5: CLI Reporting & Universal Agent Skill Packaging

**Goal**: 직관적인 Rich 콘솔 브리핑 리포트, 통합 CLI 진입점 제공, 에이전트 중립 `SKILL.md` 패키징·에이전트별 설치 지원 및 최종 검증
**Depends on**: Phase 4
**Requirements**: SKIL-01, SKIL-02, SKIL-03
**Success Criteria** (what must be TRUE):

  1. 터미널 및 대화창에 과목별 미완료 강의, 미제출 과제, 마감 임박 목록이 표(Table) 형태로 깔끔하게 브리핑된다.
  2. `python -m kau_assistant check` 및 `python -m kau_assistant sync` CLI 명령어가 안정적으로 동작한다.
  3. 범용 Agent Skill 폴더(`skills/kau-lxp/SKILL.md`, 지침 및 메타데이터)가 완성되어 Claude Code, Codex, Antigravity, Pi, Hermes에서 설치 후 자연어 요청으로 스킬을 구동할 수 있다.

**Plans**: 11/11 plans executed (05-06..05-11: UAT gap closure completed, 2026-09-24)

Plans:

- [x] 05-01-PLAN.md — `check` 명령 end-to-end: 수집 파이프라인, 버전드 JSON 계약(schema_version 1), Rich 브리핑, 종료 코드 0/1/2, 비밀 마스킹
- [x] 05-02-PLAN.md — 파이프라인 복원력: 과목별 오류 격리, LMS 설정 검증, 진행 표시, `--relogin`/`--headed`, 읽기 전용 스크래핑 검증
- [x] 05-03-PLAN.md — `sync` 명령: 기본 드라이런, `--apply` 쓰기 게이트, 동기화 리포트(Rich/JSON)
- [x] 05-04-PLAN.md — 범용 `SKILL.md`와 `install-skill` (5개 에이전트 경로 데이터 테이블, 복사/링크 설치)
- [x] 05-05-PLAN.md — JSON 계약·README 설치 안내·PROJECT.md 문구, 라이브 E2E 증거, 5개 에이전트 설치 및 호출 검증
- [x] 05-06-PLAN.md — (gap G-05-3) LXP 로그인 인식, 읽기 전용 마크업 구조 조사, Moodle 장문 날짜·퀴즈 헤더(이름/시험 마감) 파싱
- [x] 05-07-PLAN.md — (gap G-05-3, G-05-1b, G-05-2) LXP 과목명 배지 제거, 대시보드 대기 단축, 비-Coursemos 사이트 UnsupportedLmsError
- [x] 05-08-PLAN.md — (gap G-05-2) LMS_URL 기본값 https://lxp.kau.ac.kr, 0과목 `notices`(no_courses_found), UnsupportedLmsError 안전 메시지
- [x] 05-09-PLAN.md — (gap G-05-1, G-05-3) VOD 기간(text-ubstrap) 마감일, 섹션 중복 제거·주차, /report/ubcompletion 진도 병합
- [x] 05-10-PLAN.md — (gap G-05-4, G-05-2) Hermes 스킬 경로(HERMES_HOME/%LOCALAPPDATA%), LMS_URL 문서·온보딩·SKILL.md 안내
- [x] 05-11-PLAN.md — (gap 전체) 읽기 전용 LXP 라이브 재검증, 5개 에이전트 재설치, 빈 폴더 agy/Hermes 재테스트

**Wave 1**

- [x] 05-01: `check` end-to-end (파이프라인·JSON 계약·Rich 브리핑·실패 계약)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 05-02: 파이프라인 복원력
- [x] 05-03: `sync` 명령

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 05-04: 범용 `SKILL.md` 및 `install-skill`

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 05-05: 계약·설치 문서, 라이브 증거, 에이전트별 검증

**Gap closure — Wave 1**

- [x] 05-06: LXP 로그인·구조 조사·날짜·평가 헤더
- [x] 05-08: LXP 기본 대상·0과목 안내·UnsupportedLmsError

**Gap closure — Wave 2** *(blocked on gap Wave 1)*

- [x] 05-07: 과목명·대시보드 대기·비-Coursemos 실패
- [x] 05-09: 강의(VOD) 마감일·중복 제거·진도 병합
- [x] 05-10: Hermes 경로·LMS_URL 문서/온보딩/SKILL.md

**Gap closure — Wave 3** *(blocked on gap Wave 2)*

- [x] 05-11: 라이브 재검증·에이전트 재테스트

---

### Phase 6: Quiz Submission Status Enrichment

**Goal**: 성적이 비공개된 퀴즈에 대해 상세 페이지(`/mod/quiz/view.php`)를 확인하여 이미 응시한 퀴즈를 `SUBMITTED`로 정확히 판정함으로써 기한 초과 오분류 방지
**Depends on**: Phase 5
**Requirements**: QUIZ-01, QUIZ-02
**Success Criteria** (what must be TRUE):

  1. 퀴즈 목록 테이블에서 성적 열이 비어있는(`''`) 퀴즈에 대해 상세 페이지(`/mod/quiz/view.php?id=...`)를 조회한다.
  2. 상세 페이지에 `답안 검토` 버튼 또는 `"응시 가능 횟수를 초과하여 더 이상 응시할 수 없습니다."` 등의 완료 지표가 존재할 경우 `SUBMITTED`로 판정한다.
  3. 기초전자실험 W01~W03 퀴즈가 완료 처리되어 `check` 및 `sync`의 기한 초과(Overdue) 목록에서 올바르게 제외된다.

**Plans**: 1/1 plans executed

- [x] 06-01-PLAN.md — 퀴즈 상세 페이지(view.php) 응시 내역(답안 검토, 응시 횟수 초과) 파싱 및 완료 상태 판정

---

### Phase 7: VOD Activity & Attendance Completion Tracking

**Goal**: KAU LXP의 활동 현황 페이지(`/report/ublogs/completion.php`)를 연동하여 주차별 개별 VOD 강의의 수강 완료/미완료 상태를 정확히 추출하고, 마감일 처리 규칙 정립
**Depends on**: Phase 6
**Requirements**: VOD-01, VOD-02, VOD-03
**Success Criteria** (what must be TRUE):

  1. 각 과목의 `/report/ublogs/completion.php?id={course_id}` 활동 현황 테이블에서 학습활동별 `완료`/`미완료` 상태를 파싱한다.
  2. 코스 홈의 VOD 활동과 활동 현황의 완료 여부를 매핑하여 `LectureItem.status`에 반영한다.
  3. VOD 마감일(출석 인정 기간 또는 과목 기본 일정)을 적절히 산출하여 미완료 강의가 `check` 및 `sync`에 정상적으로 포함되도록 한다.

**Plans**: 1/1 plans executed

- [x] 07-01-PLAN.md — LXP 실제 활동 현황(/report/ublogs/completion.php) 연동 및 개별 VOD 시청 완료/미완료 상태 및 미지정 마감일 보존

---

### Phase 8: End-to-End Verification & Agent Re-deployment

**Goal**: 실사이트(LXP) 대상 E2E 검증 수행 및 5개 에이전트에 최신 스킬 배포
**Depends on**: Phase 7
**Requirements**: VERIF-01, VERIF-02
**Success Criteria** (what must be TRUE):

  1. 실사이트 읽기 전용 검증에서 퀴즈와 VOD 모두 사용자 실제 학업 현황과 일치함을 확인한다.
  2. 5개 에이전트(Claude Code, Codex, Antigravity, Pi, Hermes)에 최신 스킬을 재배포하고 UAT를 통과한다.

**Plans**: 1/1 plans executed

- [x] 08-01-PLAN.md — 실사이트 LXP 대상 E2E 검증 및 5개 에이전트 스킬 일괄 재배포

---

### Phase 9: VOD Playback Engine & Heartbeat Automation

**Goal**: Playwright 기반으로 Coursemos Video.js VOD 플레이어를 자동 제어하고, 음소거, 이어보기 대화상자 자동 승인, 정상 재생 및 주기적 진도 하트비트 세션을 유지하는 플레이어 엔진 구축
**Depends on**: Phase 8
**Requirements**: PLAY-01, PLAY-02, PLAY-03
**Success Criteria** (what must be TRUE):

  1. `/mod/vod/view.php`의 Video.js `<video>` 요소를 감지하고 음소거(`muted=True`) 상태에서 안정적으로 자동 재생을 개시한다.
  2. 브라우저의 "이어보기" 또는 "새로시작" confirm/alert 모달을 자동 감지하고 승인(`dialog.accept()`)한다.
  3. 재생 중 영상의 전체 길이(`duration`)와 현재 재생 시간(`currentTime`)을 추적하며, 정지 없이 Coursemos 출석 인정 하트비트 주기를 유지한다.
  4. 재생 완료(`ended` 이벤트 또는 `currentTime >= duration - 1`)를 정확히 감지하고 브라우저 자원을 정상 반환한다.

**Plans**: 1/1 plans executed

- [x] 09-01-PLAN.md — Video.js 플레이어 자동 재생, 음소거, 이어보기 모달 처리, 진도 하트비트 세션 유지 엔진 구축

---

### Phase 10: Watch Pipeline, CLI Runner & Notion Completion Mode

**Goal**: 지정된 과목 및 주차의 미완료 VOD를 선별하여 순차 재생하고, 시청 완료 시 선택적으로 Notion Scheduler의 해당 작업 상태를 '완료'로 변경하는 CLI 파이프라인 구축
**Depends on**: Phase 9
**Requirements**: WATCH-01, WATCH-02, WATCH-03
**Success Criteria** (what must be TRUE):

  1. `--course` 및 `--week` 인자를 해석하여 미수강(`AttendanceStatus.INCOMPLETE`) VOD만 선별하고, 이미 완료된 강의는 자동 건너뛴다.
  2. 선별된 미완료 VOD들을 순서대로 Phase 9 플레이어 엔진에 전달하여 순차 시청 작업을 수행하고 실시간 진행 상황을 콘솔에 출력한다.
  3. `--update-notion` 플래그 활성화 시, 시청이 완료된 강의의 Notion Scheduler DB 상태(`상태`)를 `완료`로 업데이트한다 (기본값은 보호).
  4. `kau-assistant watch` CLI 서브커맨드를 추가하고 에러 및 타임아웃 상황을 격리한다.

**Plans**: 1/1 plans executed

- [x] 10-01-PLAN.md — 과목/주차 필터링 기반 순차 VOD 시청 파이프라인, `watch` CLI 명령어 및 Notion `완료` 상태 동기화 모드

---

### Phase 11: Background Sub-agent Automation & Multi-Agent Skill Packaging

**Goal**: AI 에이전트(Claude Code, Pi, Antigravity 등)가 백그라운드 태스크나 서브에이전트로 VOD 시청 작업을 독립 실행할 수 있도록 지원하고, 5개 에이전트에 통합 배포
**Depends on**: Phase 10
**Requirements**: SKIL-03, AGNT-01, AGNT-02
**Success Criteria** (what must be TRUE):

  1. `skills/kau-lxp/SKILL.md`에 VOD 시청 요청 자연어 트리거(예: "기초전자실험 이번주 영상 시청해줘") 및 백그라운드 실행 지침을 추가한다.
  2. 에이전트가 영상 시청 요청을 받았을 때 백그라운드 프로세스로 `watch`를 구동하고, 메인 세션에서는 즉시 사용자에게 작업 시작을 알리며 다른 요청을 처리할 수 있는 패턴을 확립한다.
  3. 5개 지원 AI 에이전트(Claude Code, Codex, Antigravity, Pi, Hermes)에 업데이트된 스킬을 일괄 재배포하고 E2E UAT를 완료한다.

**Plans**: 1/1 plans executed
- [x] 11-01-PLAN.md — 비동기 백그라운드/서브에이전트 시청 실행 가이드, 범용 `SKILL.md` 업데이트 및 5개 에이전트 재배포

---

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation & Session Management | 2/2 | Complete    | 2026-09-21 |
| 2. LMS Scraper Core | 2/2 | Complete    | 2026-09-21 |
| 3. Domain Modeling & Naming Rules | 1/1 | Complete    | 2026-09-21 |
| 4. Notion Scheduler Integration & Deduplication | 2/2 | Complete    | 2026-09-22 |
| 5. CLI Reporting & Universal Agent Skill Packaging | 11/11 | Complete| 2026-09-24 |
| 6. Quiz Submission Status Enrichment | 1/1 | Complete    | 2026-09-24 |
| 7. VOD Activity & Attendance Completion Tracking | 1/1 | Complete    | 2026-09-24 |
| 8. End-to-End Verification & Agent Re-deployment | 1/1 | Complete    | 2026-09-24 |
| 9. VOD Playback Engine & Heartbeat Automation | 1/1 | Complete    | 2026-09-25 |
| 10. Watch Pipeline, CLI Runner & Notion Completion Mode | 1/1 | Complete    | 2026-09-25 |
| 11. Background Sub-agent Automation & Multi-Agent Skill Packaging | 1/1 | Complete | 2026-09-25 |




