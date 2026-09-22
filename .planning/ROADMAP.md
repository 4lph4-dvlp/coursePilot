# Roadmap: KAU LXP Assistant & Notion Scheduler Sync Skill

## Overview

본 로드맵은 대학 온라인 학습 사이트(한국항공대 LXP / 표준 Canvas·Moodle)에서 학생 계정으로 자동 로그인하여 강의 수강 현황 및 과제 마감일을 수집하고, 이를 사용자의 기존 Notion Scheduler 데이터베이스(`21d53280-64be-80ec-af4e-000b679f03bb`)에 중복 없이 정규화된 네이밍으로 동기화하는 범용 AI Agent Skill(Claude Code, Codex, Antigravity, Pi, Hermes 등 SKILL.md 지원 에이전트 공통)을 단계별로 구축합니다.

## Phases

- [x] **Phase 1: Foundation & Session Management** - 환경 설정 로더, 과목명 매핑 정의, Playwright 브라우저 셋업 및 LMS 자동 로그인/세션 캐시 구축 (completed 2026-09-21)
- [x] **Phase 2: LMS Scraper Core** - 수강 강좌 목록, 주차별 온라인 강의 진도율 및 마감일, 과제 목록 및 제출 여부 파싱 모듈 구현 (completed 2026-09-21)
- [x] **Phase 3: Domain Modeling & Naming Rules** - 데이터 모델 구조화, 노션 기존 관례를 반영한 과목명 약칭 및 통일 네이밍 엔진, 24시간 마감 임박 감지 로직 구현 (completed 2026-09-21)
- [x] **Phase 4: Notion Scheduler Integration & Deduplication** - Notion Scheduler DB 연동, 기존 등록 항목 조회 기반 중복 등록 방지, 스키마 속성 매핑 및 드라이런 모드 구현 (completed 2026-09-22)
- [ ] **Phase 5: CLI Reporting & Universal Agent Skill Packaging** - Rich 콘솔 브리핑 리포트 출력, CLI 인터페이스(`check`, `sync`, `install-skill`), 범용 Agent Skill(`SKILL.md`) 패키징 및 엔드투엔드 검증

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

**Plans**: 2 plans

Plans:

- [ ] 05-01: Rich 기반 콘솔 브리핑 리포터 및 통합 CLI 명령어 구현
- [ ] 05-02: 범용 `SKILL.md` 정의, `install-skill` 명령, 에이전트별 설치 안내 README 작성 및 전체 워크플로우 엔드투엔드 검증

---

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation & Session Management | 2/2 | Complete    | 2026-09-21 |
| 2. LMS Scraper Core | 2/2 | Complete    | 2026-09-21 |
| 3. Domain Modeling & Naming Rules | 1/1 | Complete    | 2026-09-21 |
| 4. Notion Scheduler Integration & Deduplication | 2/2 | Complete    | 2026-09-22 |
| 5. CLI Reporting & Universal Agent Skill Packaging | 0/2 | Not started | - |
