# Phase 16: Comprehensive Activity Progress Dashboard - Context

**Gathered:** 2026-09-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 16은 전체 학습활동(동영상 + 과제 + 퀴즈 + 학습자료)의 종합 진척도를 체계적으로 계산하고 터미널 및 에이전트 대화창에 한눈에 브리핑하는 종합 대시보드(`coursepilot progress`)를 구축합니다:
1. 각 과목별 4대 학습활동(동영상, 과제, 퀴즈, 자료)의 종합 이수율 계산 및 유형별 세부 달성률 산출.
2. 3단 분할 대시보드 뷰([1] 과목별 진도율 요약 테이블, [2] 이번 주차 상세 액션 아이템, [3] 지난 주차 누락/결석 경고 패널).
3. 지나온 주차(1주차 ~ Current Week - 1) 누적 이수율 엄격 산출 및 결석/미제출 경고 연계.
4. 미래 주차 선행 등록 활동 분리(현재 주차 오픈 기준 메인 지표 vs 학기 전체 기준 보조 지표).
5. CLI 인터페이스 `coursepilot progress` 및 필터 옵션(`--course`, `--week`, `--detail`, `--cached`, `--refresh`, `--json`).
6. 표준 JSON 계약(`schema_version: 1`) 기반 에이전트 브리핑 연동.
7. LXP 네트워크 효율 최적화(코스 홈 1회 방문 시 동영상과 자료 동시 추출) 및 과목별 독립 예외 격리(D-08 계승).
8. Notion Scheduler DB에는 직접 쓰지 않으며(D-13-07, D-15-13 원칙 준수), 순수 상태 조회/브리핑 도구로 격리.

</domain>

<decisions>
## Implementation Decisions

### 1. 진척도 산출 공식 및 주차 판정 기준
- **D-16-01:** 단순 총합 + 유형별 달성률 병행: 전체 완료율(총 완료 건 / 총 등록 건 백분율)과 함께 동영상/과제/퀴즈/자료 4개 항목별 세부 달성률(x/y)을 동시에 산출 및 표기한다. — **Reversibility:** costly — 진척도 계산 엔진 및 대시보드/JSON 데이터 모델에 영향
- **D-16-02:** 하이브리드 이번 주차(Current Week) 자동 판별: 각 과목 섹션/강의 기간 날짜 범위와 LXP 현재 활성 섹션(`.current`)을 결합하여, 오늘 날짜가 속한 주차를 이번 주차로 자동 지정한다. — **Reversibility:** costly — 날짜 파싱 및 주차 판별 로직
- **D-16-03:** 지난 주차(Past Weeks) 엄격 누적 산출: 1주차부터 (이번 주차 - 1)까지의 전체 등록 활동을 대상으로 하여, 마감 기한이 지난 미완료 건을 결석/미제출(누락)으로 간주하고 지난 주차 누적 이수율(과거 완료수 / 과거 총등록수 %)에 반영하며 경고를 부여한다.
- **D-16-04:** 현재 주차 오픈 기준 메인 지표 + 학기 전체 보조 표기: 미래 주차에 선행 등록된 활동은 분리하여, 현재 주차까지 오픈된 활동 기준 진도율(예: 95% (19/20))을 주 지표로 삼고 학기 전체 기준 진도율(예: [학기 전체 25% (19/76)])을 보조 지표로 함께 제공한다.

### 2. 대시보드 시각화 및 터미널 레이아웃
- **D-16-05:** 3단 분할 대시보드 레이아웃: 터미널 렌더링 시 [1] 과목별 진도율 요약 테이블, [2] 이번 주차 상세 액션 아이템(완료/미완료 목록), [3] 지난 주차 누락/결석 경고 패널 순으로 배치하여 학업 상태를 한눈에 파악할 수 있도록 한다.
- **D-16-06:** 색상 코딩 프로그레스 바 + 수치 병기: 과목별 진도율을 달성률에 따른 색상(100% 녹색, 80~99% 청색, 50~79% 황색, 50% 미만 적색) Rich ProgressBar 그래픽과 백분율 및 건수 `85% (17/20)`로 가시성 높게 표현한다.
- **D-16-07:** 이번 주차 항목 To-Do 최우선 강조: 이번 주차 점검 섹션에서는 아직 완료하지 않은 잔여 활동(미완료)을 상단에 마감 기한/유형 태그(`[VOD]`, `[과제]`, `[퀴즈]`, `[자료]`)와 함께 눈에 띄게 강조하고, 완료된 활동은 하단에 체크(`✓`)로 컴팩트하게 정리한다.
- **D-16-08:** 상황 맞춤형 Alert 패널: 지난 주차에 결석/미제출된 누락 항목이 존재할 때만 적색/황색 Alert 패널(`⚠️ 과거 주차 누락 N건`)을 표시하고, 누락이 없을 경우 깔끔한 녹색 올클리어(`🎉 All Clear`) 배지를 출력한다.

### 3. CLI 인터페이스 및 조회 스코프
- **D-16-09:** `coursepilot progress` 단일 진입점: 기본 실행 시 전체 수강 과목의 종합 대시보드를 일괄 브리핑한다. — **Reversibility:** costly — CLI 명령어 시그니처 및 에이전트 호출 계약
- **D-16-10:** 퍼지 과목 매칭 및 주차 지정: `--course <과목명/약칭>` 지정 시 해당 과목의 1~16주차 전 주차 활동 현황표(매트릭스 로드맵)를 펼쳐보고, `--week <N>`으로 특정 주차만 정밀 점검할 수 있도록 한다.
- **D-16-11:** 컴팩트 기본 뷰 및 `--detail` 전 주차 전개: 기본 실행 시 요약 게이지와 이번 주차 활동 위주로 간결하게 표시하고, `--detail` 플래그 지정 시 전 주차의 모든 완료/미완료 개별 활동 세부 목록을 펼쳐서 확인할 수 있다.
- **D-16-12:** 표준 JSON 계약(`schema_version: 1`): AI 에이전트 연동용 `--json` 출력은 최상위 `schema_version: 1`, `status`, `timestamp`, `summary`(종합 KPI), `courses`(과목별 전체/과거/이번주차 진도율, 4대 활동별 세부 통계, 액션 아이템 목록)를 계층형으로 일관되게 제공한다. — **Reversibility:** costly — JSON_CONTRACT.md 및 에이전트 파싱 계약

### 4. 데이터 수집 성능 및 캐싱 전략
- **D-16-13:** 코스 홈 1회 방문 시 동영상+학습자료 동시 파싱: 과목 홈 HTML에서 강의 섹션과 ubfile/resource를 한 번에 추출하고, ublogs 활동 현황 및 과제/퀴즈 파서를 결합하여 네트워크 왕복 횟수를 최소화한다.
- **D-16-14:** 실시간 우선 + 10분 로컬 캐시(`--cached`/`--refresh`): 기본 실행 시 실시간 최신 데이터를 스크래핑하되, 연속 조회나 에이전트 다회 질의를 위해 10분 TTL의 로컬 캐시(`progress_cache.json`)와 `--cached` / `--refresh` 플래그를 제공한다.
- **D-16-15:** Rich Status Spinner (stderr) 분리: 수집 진행 중에는 `Console(stderr=True)`를 통해 `[1/6] [공수2] 활동 내역 수집 중...` 동적 스피너를 보여주고, 완료 시 stdout으로 최종 대시보드 또는 순수 JSON만 깔끔하게 출력한다.
- **D-16-16:** 과목별 독립 예외 격리(D-08, D-15-11 계승): 특정 과목 수집 중 네트워크나 HTML 파싱 에러가 발생해도 다른 과목의 진척도 산출을 중단하지 않고 해당 과목만 `[수집실패]`로 표시하여 안전하게 격리한다.

### the agent's Discretion
- `progress_cache.json` 저장 위치 및 원자적 파일 쓰기 방식.
- 콘솔 터미널 가로 폭에 맞춘 Rich Progress Bar 너비 자동 조정.
- 날짜 파싱 실패 시 폴백 주차 매핑 알고리즘 (단순 인덱스 순서 활용).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Roadmap & Requirements
- `.planning/ROADMAP.md` § Phase 16 — Comprehensive Activity Progress Dashboard
- `.planning/REQUIREMENTS.md` § PROG-01, PROG-02 — Progress dashboard requirements

### Domain & Scraper Models
- `src/coursepilot/scraper/models.py` — LectureItem, AssessmentItem, CourseItem, AttendanceStatus, SubmissionStatus
- `src/coursepilot/materials/models.py` — MaterialItem definition and completion flag
- `src/coursepilot/domain/models.py` — Course, SyncTask domain representation

### Scraping & Extraction Engines
- `src/coursepilot/scraper/lecture_parser.py` — parse_lectures_from_course_sections, parse_ublogs_completion
- `src/coursepilot/scraper/assessment_parser.py` — scrape_course_assessments, quiz submission checking
- `src/coursepilot/scraper/material_parser.py` — parse_materials_from_course_sections (ubfile/resource)
- `src/coursepilot/scraper/course_list.py` — extract_courses, CourseItem extraction
- `src/coursepilot/scraper/date_parser.py` — Korean date string and range parsing
- `src/coursepilot/pipeline.py` — scrape_course orchestration and validation patterns

### CLI & Reporting Framework
- `src/coursepilot/cli.py` — Click CLI command structure and options
- `src/coursepilot/reporter.py` — Rich table formatting and console stream separation (stderr vs stdout)
- `src/coursepilot/report_models.py` — JSON contract structures and ErrorItem

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `CourseNavigator`: 과목 홈 및 세부 페이지 탐색 제어.
- `SessionManager`: 세션 캐싱 및 인증 브라우저 컨텍스트 제공.
- `extract_courses` / `find_target_course`: 수강 과목 목록 추출 및 약칭/퍼지 매칭.
- `parse_lectures_from_course_sections` & `parse_materials_from_course_sections`: 단일 course home HTML에서 동영상과 학습자료 동시 파싱 가능.
- `scrape_course_assessments`: 과제 및 퀴즈 제출 상태 일괄 파싱.
- `parse_date`: 다양한 한국어 날짜/시간 포맷 정규화.

### Established Patterns
- Click 서브커맨드 패턴 (`coursepilot <command>`).
- `Console(stderr=True)`로 실시간 진행 상태/스피너 출력, stdout은 최종 결과 리포트 또는 JSON만 단독 출력.
- 과목별 try-except 격리: 단일 과목 실패 시 전체 파이프라인 중단 방지.
- Pydantic BaseModel 기반 엄격한 데이터 검증 및 JSON 직렬화.

### Integration Points
- `src/coursepilot/progress/` (신규 모듈):
  * `models.py`: `CourseProgress`, `ActivityBreakdown`, `DashboardSummary`, `WeekProgress` 등 대시보드 DTO.
  * `calculator.py`: 4대 활동 통합 진도율, 이번 주차 판정, 지난 주차 누적 이수율 계산 엔진.
  * `runner.py`: 통합 스크래핑 파이프라인 및 10분 로컬 캐시 관리자.
  * `reporter.py`: 3단 분할 Rich 대시보드 렌더러.
- `src/coursepilot/cli.py`: `@cli.command("progress")` 서브커맨드 등록.

</code_context>

<specifics>
## Specific Ideas

- 사용자가 `coursepilot progress` 실행 시:
  "전체 수강 과목의 [종합 진도율 게이지 테이블], [이번 주차 To-Do 및 완료 목록], [지난 주차 결석/미제출 경고 Alert]가 3단 뷰로 시원하게 터미널에 렌더링."
- 사용자가 `coursepilot progress --course 공수2` 실행 시:
  "공학수학2의 1주차부터 16주차까지 전 주차 활동 달성 매트릭스 로드맵이 상세하게 출력."
- 사용자가 `coursepilot progress --detail` 실행 시:
  "모든 과목의 전 주차 완료/미완료 개별 활동 세부 목록 전개."
- 사용자가 `coursepilot progress --json` 실행 시:
  "에이전트가 완벽히 파싱할 수 있는 `schema_version: 1` 규격의 종합 진척도 JSON 출력."

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope.

</deferred>

---

*Phase: 16-comprehensive-activity-progress-dashboard*
*Context gathered: 2026-09-26*
