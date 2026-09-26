# Phase 2: LMS Scraper Core - Context

**Gathered:** 2026-09-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 2는 한국항공대 LXP(Coursemos/Canvas 기반 LMS)의 학업 데이터를 스크래핑하는 핵심 모듈을 구현합니다:
1. 현재 학기 수강 강좌 목록 추출 (강좌명, 과목 ID, 링크 URL, 분반/연도 정제) (SCRP-02)
2. 각 과목별 주차 강의 동영상 수강 상태, 출석 완료 여부, 시청 마감일 파싱 (SCRP-03)
3. 각 과목별 과제/퀴즈/토론 등 모든 평가 항목 목록, 제출 완료 상태, 마감일 및 본문 상세 정보 추출 (SCRP-04)
4. LMS 페이지 탐색 최적화(학습현황 요약 페이지 우선 활용, 스마트 대기, 딜레이를 통한 WAF 차단 방지)
5. 실패 시 디버깅 스냅샷(`.cache/debug/` 스크린샷 및 HTML) 덤프 기능

*노션 DB 연동(Phase 4) 및 작업명 최종 정규화/긴급도 판정(Phase 3)은 본 Phase의 범위에 포함되지 않으며, 순수 스크래퍼 추출 계층에 집중합니다.*

</domain>

<decisions>
## Implementation Decisions

### 1. 수강 과목 대상 및 필터링 기준 (Course Scope & Filtering)
- **D-01:** LMS 대시보드의 '진행 중' 필터 및 현재 학기(연도-학기) 텍스트를 기준으로 정규 수강 과목을 자동 판별하고 지난 학기나 만료 강좌는 제외. — **Reversibility:** reversible
- **D-02:** 과목명 문자열에서 정규식을 적용하여 순수 과목명(분반 번호, 연도, 학기 표기 제거), 원본 전체 텍스트, 강좌 ID를 모두 분리하여 데이터 모델에 저장. — **Reversibility:** reversible
- **D-03:** 강좌 진입 시 '접근 권한 없음' 또는 '비공개 강좌'(403/리다이렉트) 발생 시 경고 로그를 남기고 해당 과목만 스킵 후 나머지 과목 수집을 계속 진행. — **Reversibility:** reversible
- **D-04:** 항상 실시간으로 대시보드를 탐색하여 최신 수강 상태를 반영하되, 디버깅 및 테스트를 위해 캐시된 과목 목록 주입/로드를 지원. — **Reversibility:** reversible

### 2. 동영상 강의 출석 및 진도율 완료 판정 (Lecture Progress & Completion)
- **D-05:** 동영상 강의 완료 여부는 출석 인정 마크('O' 또는 완료 체크박스)를 최우선 기준으로 판정하며, 마크가 없는 경우 진도율 100% 도달 여부를 보조로 확인하는 하이브리드 판정 적용. — **Reversibility:** reversible
- **D-06:** 출석 인정 마감 기한이 이미 지난 과거 주차의 미수강 강의도 누락하지 않고 추출하며, 노션 스케줄러 동기화 시 '지연' 상태로 전달될 수 있도록 마감 만료 플래그를 정확히 부여. — **Reversibility:** costly — 도메인 모델(Phase 3) 및 노션 상태 매핑(Phase 4) 전반에 영향
- **D-07:** 한 주차 내에 여러 개의 동영상 클립(1차시, 2차시 등)이 포함된 경우 개별 영상(차시) 단위로 정밀하게 각각 분할 추출 (예: `[공수2] 3주차 1차시 시청`). — **Reversibility:** reversible
- **D-08:** LMS 마감 시간 표기(다양한 한국어/표준 패턴) 파싱을 위해 다중 정규식 기반 유연한 파서를 적용하고, 파싱 실패 시 원본 문자열을 보존하면서 해당 주차 일요일 23:59로 안전하게 폴백. — **Reversibility:** reversible

### 3. 과제 및 평가 항목 수집 범위 (Assignment & Assessment Scope)
- **D-09:** 일반 과제(Assignment)뿐만 아니라 마감일이 지정된 모든 평가 활동(주차별 퀴즈, 온라인 시험, 토론 게시글 제출 등)을 포괄적으로 수집. — **Reversibility:** costly — LMS 셀렉터 및 파서 확장 필요
- **D-10:** 평가 항목 제출 상태는 '미제출(No attempt)' 및 '임시저장(Draft)'을 미완료 태스크로 판정하고, '제출 완료' 및 '채점 완료'는 완료 처리. — **Reversibility:** reversible
- **D-11:** 과제/평가 항목은 요약 목록 수집에 그치지 않고 모든 과제의 상세 페이지에 진입하여 교수자 안내문 및 첨부파일 메타데이터까지 전수 추출. — **Reversibility:** costly — 상세 페이지 네비게이션 및 세부 DOM 파싱 구조 종속
- **D-12:** 정규 마감일 이후 '지각 제출'이 허용된 과제의 경우 정규 마감일(Due Date)을 주 DueDate로 설정하고, 지각 제출 마감일(Cut-off)이 존재하면 메모/부가정보에 병기. — **Reversibility:** reversible

### 4. LMS 페이지 탐색 및 데이터 수집 경로 (Navigation Strategy & Scraping Flow)
- **D-13:** 과목별 데이터 수집 시 '학습현황(진도표/출석부)' 및 '과제/퀴즈 모아보기' 전용 페이지를 우선 활용하고, 해당 뷰가 없는 과목은 메인 홈(주차별 섹션)으로 안전하게 폴백. — **Reversibility:** reversible
- **D-14:** 동적 렌더링 대기 시 주요 컨테이너 셀렉터(`.generaltable`, `.user_progress` 등) 출현 대기와 `domcontentloaded`를 결합한 스마트 명시적 대기(최대 15초) 적용. — **Reversibility:** reversible
- **D-15:** LMS 서버 과부하 및 대학 웹방화벽(WAF)/IP 차단 방지를 위해 단일 페이지 순차 탐색 + 요청 간 미세 딜레이(0.2~0.5초)를 적용. — **Reversibility:** reversible
- **D-16:** 파싱 실패나 타임아웃 발생 시 원인 분석을 위해 `.cache/debug/` 디렉터리에 실패 화면 스크린샷과 HTML 스냅샷을 자동 저장 (.gitignore 격리). — **Reversibility:** reversible

### the agent's Discretion
- 세부적인 Coursemos 테이블 파싱 DOM 셀렉터 구성
- 네트워크 재시도 횟수 및 백오프 딜레이 미세 조정

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project & Roadmap Specs
- `.planning/PROJECT.md` — 프로젝트 개요, 핵심 가치, 시스템 제약 사항
- `.planning/REQUIREMENTS.md` — SCRP-02, SCRP-03, SCRP-04 상세 요구사항
- `.planning/ROADMAP.md` — Phase 2 성공 기준 및 단계별 목표
- `.planning/phases/01-foundation-session-management/01-CONTEXT.md` — Phase 1 결정사항

### Source Code References
- `src/coursepilot/auth.py` — LMS 셀렉터 및 로그인/대시보드 판별 기준
- `src/coursepilot/session_manager.py` — 브라우저 컨텍스트 수명주기 및 세션 캐싱 인프라
- `src/coursepilot/course_mapping.py` — 과목명 정규화 매핑 로직

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `SessionManager`: 세션 쿠키가 보존된 인증 브라우저 페이지 제공
- `LOGGED_IN_SELECTORS`: 대시보드 진입 확인
- `course_mapping.py`: 과목명 축약 매핑 및 정규화 기반

### Established Patterns
- Multi-selector fallback (`find_first_visible`): Coursemos와 Canvas 변형 구조에 유연하게 대응
- `.cache/` 디렉터리 격리: 민감 정보 및 디버깅 데이터 격리 보존

### Integration Points
- `src/coursepilot/scraper/`: 이번 단계에서 신규 구축할 스크래퍼 모듈 패키지
- Phase 3 도메인 모델 생성기로 전달할 원시 추출 데이터 구조

</code_context>

<specifics>
## Specific Ideas

- **지연된 과거 강의도 동기화**: 출석 마감이 지난 과거 미완료 강의도 누락하지 않고 노션에 '지연' 상태로 반영.
- **과제 상세 본문 추출**: 과제 요약표에 그치지 않고 과제 상세 페이지를 방문해 과제 본문 설명 및 첨부파일 메타데이터까지 파싱.
- **개별 차시 단위 작업화**: 한 주차에 여러 강의 영상이 있을 경우 `3주차 1차시`, `3주차 2차시`로 개별 태스크화.

</specifics>

<deferred>
## Deferred Ideas

- None — 모든 논의가 Phase 2 LMS Scraper Core 범위 내에서 진행됨.

</deferred>

---

*Phase: 02-LMS Scraper Core*
*Context gathered: 2026-09-21*
