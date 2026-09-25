# Requirements: KAU LXP Assistant & Notion Scheduler Sync Skill

**Defined:** 2026-09-21
**Core Value:** 학생이 수강 중인 모든 강의의 미완료 인강 및 과제 마감 기한을 빠짐없이 확인하고, 중복 없이 정형화된 이름 규칙으로 개인 노션 스케줄러에 동기화하여 학업 누락을 원천 방지하는 것.

## v1 Requirements

### Configuration & Session (CONF)

- [x] **CONF-01**: `.env` 및 설정 로더를 통해 LMS URL, 학번, 비밀번호, Notion API Key, Notion DB ID(`21d53280-64be-80ec-af4e-000b679f03bb`)를 안전하게 관리한다.
- [x] **CONF-02**: 과목명 축약 매핑(`course_mappings.json` / 설정)을 통해 과목별 축약 이름(예: `공학수학2` -> `공수2`, `자료구조` -> `자구`)을 정의하고 로드한다.
- [x] **CONF-03**: Playwright 브라우저 세션 스토리지(`session.json`)를 캐싱하여 불필요한 반복 로그인을 방지하고, 세션 만료 시 자동 재로그인을 수행한다.

### LMS Web Automation & Crawling (SCRP)

- [x] **SCRP-01**: Playwright 헤드리스 브라우저를 통해 대상 LMS에 자동 로그인하고 대시보드 정상 진입을 확인한다.
- [x] **SCRP-02**: 현재 학기 수강 중인 전체 강좌 목록(과목 ID, 과목명, 강좌 링크)을 추출한다.
- [x] **SCRP-03**: 각 과목의 주차별 온라인 동영상 강의 목록, 수강 진도율(출석/완료 여부), 수강 마감 일시를 추출한다.
- [x] **SCRP-04**: 각 과목의 과제 목록, 과제 제출 상태(제출완료/미제출), 과제 마감 일시를 추출한다.

### Domain Logic & Naming Rules (DOMN)

- [x] **DOMN-01**: 수집된 데이터를 바탕으로 미완료 강의 및 미제출 과제를 정확하게 판별한다.
- [x] **DOMN-02**: 마감 24시간 이내의 미완료 항목을 감지하여 긴급도(`🔴 긴급 (P1)`) 판정 및 경고 태그를 부여한다.
- [x] **DOMN-03**: 기존 노션 관례에 맞춘 통일된 이름 규칙(`[{과목약어}] {주차}주차 강의 시청`, `[{과목약어}] {과제명} 제출`)으로 작업명을 정규화한다.

### Notion Scheduler Integration & Deduplication (NOTN)

- [x] **NOTN-01**: Notion Scheduler DB(`21d53280-64be-80ec-af4e-000b679f03bb`)의 기존 페이지를 조회하여 작업명과 마감일(DueDate)을 확인한다.
- [x] **NOTN-02**: 중복 등록 방지: 기존에 등록된 항목은 건너뛰고(`Skip`), 신규 미완료 항목만 선별하여 등록한다.
- [x] **NOTN-03**: 대상 DB 스키마 속성(`선택`=루틴/이벤트, `구분`=학업, `DueDate`, `우선순위`=P1~P4, `상태`=시작 전, `메모`=URL)을 정확히 매핑하여 새 페이지를 생성한다.
- [x] **NOTN-04**: 노션에 실제 등록하기 전 파싱 결과와 등록 예정 목록을 미리 확인할 수 있는 드라이런(`--dry-run`) 모드를 지원한다.

### CLI & Universal Agent Skill Packaging (SKIL)

- [x] **SKIL-01**: 터미널 및 에이전트 대화창에 미완료 강의/과제 및 마감일을 직관적으로 보여주는 Rich 콘솔 브리핑 리포트를 출력한다.
- [x] **SKIL-02**: 상태 조회(`check`) 및 노션 동기화(`sync`)를 수행할 수 있는 CLI 명령어를 제공한다.
- [x] **SKIL-03**: 에이전트 중립 Agent Skill 형식(`SKILL.md`)으로 패키징하고 에이전트별 설치 명령을 제공하여 Claude Code, Codex, Antigravity, Pi, Hermes 등 모든 지원 에이전트가 자연어 요청으로 스킬을 호출할 수 있도록 한다.

### VOD Player Advanced Control (WATCH)

- [x] **WATCH-04**: 특정 주차의 N번째 영상만 핀포인트 지정하여 시청할 수 있는 `--video-index` 및 과목명 퍼지/유사어 매칭 기능을 지원한다.
- [x] **WATCH-05**: 백그라운드 재생 중 5초 간격으로 `watch_state.json`에 상태를 기록하고, `watch status`로 진행률 조회 및 `watch stop`으로 안전한 중단을 제공한다.
- [x] **WATCH-06**: 시청 완료된 내역을 `watch_history.json`에 보관하여, 사후 요청 시 `watch sync-notion`으로 Notion Scheduler 완료 상태를 소급 동기화한다.

### Learning Materials Auto-Completion & Downloader (RES)

- [x] **RES-01**: 미열람 상태의 `ubfile` 학습자료 페이지를 방문(열람)하여 LXP 진도율을 100% 완료 상태로 갱신한다.
- [x] **RES-02**: 첨부 파일(PDF, PPT, ZIP 등)을 `.env` 또는 요청된 기본 경로 하위 `<과목명>/W{주차}/` 폴더에 자동으로 다운로드 및 정리하고 CLI 및 JSON 인터페이스를 제공한다.

### Pure-Python VOD Stream Downloader Integration (VDL)

- [x] **VDL-01**: 시스템에 `ffmpeg` 설치가 없어도 동작하는 순수 파이썬 HLS/m3u8 세그먼트 파서 및 다운로더/병합기를 구현하고 AES-128 복호화 및 원자적 저장을 지원한다.
- [x] **VDL-02**: VOD 시청(`watch`) 시 네트워크 감시를 통해 미디어 스트림을 감지하여 다운로드를 병행하고, 단독 서브커맨드 `kau-assistant download-vod`를 제공한다.

### Course Announcements & Q&A Board Briefing (BRD)

- [x] **BRD-01**: 과목별 공지사항 게시판(`ubboard`)의 최근 공지글 목록(번호, 제목, 작성자, 작성일) 및 본문/첨부파일 메타데이터를 추출하고, 터미널 브리핑 및 단독 뷰어(`--view <id>`)를 제공한다.
- [x] **BRD-02**: 과목별 Q&A 게시판의 질문 목록, 답변 상태(답변완료/대기), 공식 답변 본문을 추출하고, 통합 CLI `board` 및 단독 편의 서브커맨드 `notices`, `qna`, 필터(`--unread-only`, `--unanswered`, `--my`), 로컬 읽음 상태 관리(`board_read_state.json`)를 지원한다.

### Comprehensive Activity Progress Dashboard (PROG)

- [ ] **PROG-01**: 각 과목별로 전체 학습활동(동영상, 과제, 퀴즈, 자료)의 종합 이수율을 계산하고, 오픈 기준 메인 지표/학기 전체 보조 지표 및 지난 주차 누적 이수율/결석 누락 지표를 산출한다.
- [ ] **PROG-02**: "전체 진도율", "지나온 주차 누적 이수율", "이번 주차 현황(완료/미완료 목록)"을 한눈에 볼 수 있는 3단 분할 `progress` 대시보드 및 표준 JSON 계약(`schema_version: 1`) 브리핑을 제공한다.

### Advanced Automation & Notifications

- **NOTF-01**: 마감 임박 항목에 대해 웹훅(Slack, Discord 등) 또는 OS 알림 전송
- **CAL-01**: Google Calendar / iCal 형식 내보내기 지원
- **MOBI-01**: 모바일 웹 뷰어 또는 모바일 브라우저 세션 연동

## Out of Scope

| Feature | Reason |
|---------|--------|
| 2차 인증(OTP/캡차) 자동 크랙/우회 | 보안 규정 준수 및 단순 ID/PW 기반 환경 우선 지원 (필요 시 세션 수동 저장 지원) |
| 다중 사용자 호스팅 SaaS 서버 구축 | 개인정보(학번/비밀번호) 보호를 위해 로컬 환경 전용 에이전트 스킬로 설계 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CONF-01 | Phase 1 | Complete |
| CONF-02 | Phase 1 | Complete |
| CONF-03 | Phase 1 | Complete |
| SCRP-01 | Phase 1 | Complete |
| SCRP-02 | Phase 2 | Complete |
| SCRP-03 | Phase 2 | Complete |
| SCRP-04 | Phase 2 | Complete |
| DOMN-01 | Phase 3 | Complete |
| DOMN-02 | Phase 3 | Complete |
| DOMN-03 | Phase 3 | Complete |
| NOTN-01 | Phase 4 | Complete |
| NOTN-02 | Phase 4 | Complete |
| NOTN-03 | Phase 4 | Complete |
| NOTN-04 | Phase 4 | Complete |
| SKIL-01 | Phase 5 | Complete |
| SKIL-02 | Phase 5 | Complete |
| SKIL-03 | Phase 5 | Complete |
| WATCH-04 | Phase 12 | Complete |
| WATCH-05 | Phase 12 | Complete |
| WATCH-06 | Phase 12 | Complete |
| RES-01 | Phase 13 | Complete |
| RES-02 | Phase 13 | Complete |
| VDL-01 | Phase 14 | Complete |
| VDL-02 | Phase 14 | Complete |
| BRD-01 | Phase 15 | Complete |
| BRD-02 | Phase 15 | Complete |
| PROG-01 | Phase 16 | Pending |
| PROG-02 | Phase 16 | Pending |
| NOTF-01 | Future | Backlog |
| CAL-01 | Future | Backlog |
| MOBI-01 | Future | Backlog |

**Coverage:**

- Requirements tracked: 31 total
- Mapped to phases: 28
- Backlog / Future: 3

---
*Requirements defined: 2026-09-21*
*Last updated: 2026-09-26 for Milestone 4 (Phase 15)*


