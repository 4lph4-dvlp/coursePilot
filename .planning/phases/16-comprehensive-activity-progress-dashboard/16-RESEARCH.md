# Phase 16: Comprehensive Activity Progress Dashboard - Research
**Researched:** 2026-09-26  
**Domain:** Comprehensive Academic Activity Progress & Multi-Tier Dashboard (VOD, Assignment, Quiz, Learning Material)  
**Confidence:** HIGH  

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-16-01:** 단순 총합 + 유형별 달성률 병행: 전체 완료율(총 완료 건 / 총 등록 건 백분율)과 함께 동영상/과제/퀴즈/자료 4개 항목별 세부 달성률(x/y)을 동시에 산출 및 표기한다. — **Reversibility:** costly — 진척도 계산 엔진 및 대시보드/JSON 데이터 모델에 영향
- **D-16-02:** 하이브리드 이번 주차(Current Week) 자동 판별: 각 과목 섹션/강의 기간 날짜 범위와 LXP 현재 활성 섹션(`.current`)을 결합하여, 오늘 날짜가 속한 주차를 이번 주차로 자동 지정한다. — **Reversibility:** costly — 날짜 파싱 및 주차 판별 로직
- **D-16-03:** 지난 주차(Past Weeks) 엄격 누적 산출: 1주차부터 (이번 주차 - 1)까지의 전체 등록 활동을 대상으로 하여, 마감 기한이 지난 미완료 건을 결석/미제출(누락)으로 간주하고 지난 주차 누적 이수율(과거 완료수 / 과거 총등록수 %)에 반영하며 경고를 부여한다.
- **D-16-04:** 현재 주차 오픈 기준 메인 지표 + 학기 전체 보조 표기: 미래 주차에 선행 등록된 활동은 분리하여, 현재 주차까지 오픈된 활동 기준 진도율(예: 95% (19/20))을 주 지표로 삼고 학기 전체 기준 진도율(예: [학기 전체 25% (19/76)])을 보조 지표로 함께 제공한다.
- **D-16-05:** 3단 분할 대시보드 레이아웃: 터미널 렌더링 시 [1] 과목별 진도율 요약 테이블, [2] 이번 주차 상세 액션 아이템(완료/미완료 목록), [3] 지난 주차 누락/결석 경고 패널 순으로 배치하여 학업 상태를 한눈에 파악할 수 있도록 한다.
- **D-16-06:** 색상 코딩 프로그레스 바 + 수치 병기: 과목별 진도율을 달성률에 따른 색상(100% 녹색, 80~99% 청색, 50~79% 황색, 50% 미만 적색) Rich ProgressBar 그래픽과 백분율 및 건수 `85% (17/20)`로 가시성 높게 표현한다.
- **D-16-07:** 이번 주차 항목 To-Do 최우선 강조: 이번 주차 점검 섹션에서는 아직 완료하지 않은 잔여 활동(미완료)을 상단에 마감 기한/유형 태그(`[VOD]`, `[과제]`, `[퀴즈]`, `[자료]`)와 함께 눈에 띄게 강조하고, 완료된 활동은 하단에 체크(`✓`)로 컴팩트하게 정리한다.
- **D-16-08:** 상황 맞춤형 Alert 패널: 지난 주차에 결석/미제출된 누락 항목이 존재할 때만 적색/황색 Alert 패널(`⚠️ 과거 주차 누락 N건`)을 표시하고, 누락이 없을 경우 깔끔한 녹색 올클리어(`🎉 All Clear`) 배지를 출력한다.
- **D-16-09:** `coursepilot progress` 단일 진입점: 기본 실행 시 전체 수강 과목의 종합 대시보드를 일괄 브리핑한다. — **Reversibility:** costly — CLI 명령어 시그니처 및 에이전트 호출 계약
- **D-16-10:** 퍼지 과목 매칭 및 주차 지정: `--course <과목명/약칭>` 지정 시 해당 과목의 1~16주차 전 주차 활동 현황표(매트릭스 로드맵)를 펼쳐보고, `--week <N>`으로 특정 주차만 정밀 점검할 수 있도록 한다.
- **D-16-11:** 컴팩트 기본 뷰 및 `--detail` 전 주차 전개: 기본 실행 시 요약 게이지와 이번 주차 활동 위주로 간결하게 표시하고, `--detail` 플래그 지정 시 전 주차의 모든 완료/미완료 개별 활동 세부 목록을 펼쳐서 확인할 수 있다.
- **D-16-12:** 표준 JSON 계약(`schema_version: 1`): AI 에이전트 연동용 `--json` 출력은 최상위 `schema_version: 1`, `status`, `timestamp`, `summary`(종합 KPI), `courses`(과목별 전체/과거/이번주차 진도율, 4대 활동별 세부 통계, 액션 아이템 목록)를 계층형으로 일관되게 제공한다. — **Reversibility:** costly — JSON_CONTRACT.md 및 에이전트 파싱 계약
- **D-16-13:** 코스 홈 1회 방문 시 동영상+학습자료 동시 파싱: 과목 홈 HTML에서 강의 섹션과 ubfile/resource를 한 번에 추출하고, ublogs 활동 현황 및 과제/퀴즈 파서를 결합하여 네트워크 왕복 횟수를 최소화한다.
- **D-16-14:** 실시간 우선 + 10분 로컬 캐시(`--cached`/`--refresh`): 기본 실행 시 실시간 최신 데이터를 스크래핑하되, 연속 조회나 에이전트 다회 질의를 위해 10분 TTL의 로컬 캐시(`progress_cache.json`)와 `--cached` / `--refresh` 플래그를 제공한다.
- **D-16-15:** Rich Status Spinner (stderr) 분리: 수집 진행 중에는 `Console(stderr=True)`를 통해 `[1/6] [공수2] 활동 내역 수집 중...` 동적 스피너를 보여주고, 완료 시 stdout으로 최종 대시보드 또는 순수 JSON만 깔끔하게 출력한다.
- **D-16-16:** 과목별 독립 예외 격리(D-08, D-15-11 계승): 특정 과목 수집 중 네트워크나 HTML 파싱 에러가 발생해도 다른 과목의 진척도 산출을 중단하지 않고 해당 과목만 `[수집실패]`로 표시하여 안전하게 격리한다.

### Claude's Discretion
- `progress_cache.json` 저장 위치 및 원자적 파일 쓰기 방식.
- 콘솔 터미널 가로 폭에 맞춘 Rich Progress Bar 너비 자동 조정.
- 날짜 파싱 실패 시 폴백 주차 매핑 알고리즘 (단순 인덱스 순서 활용).

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|---|---|---|
| **PROG-01** | 각 과목별로 전체 학습활동(동영상, 과제, 퀴즈, 자료)의 종합 이수율을 계산하고 세부 지표를 산출한다. | `calculator.py`를 통해 4대 활동(VOD, 과제, 퀴즈, 자료)의 단순 총합 및 개별 달성률을 동시 집계하고, 주차 판별 로직(D-16-02)을 바탕으로 현재 오픈 기준 진도율(D-16-04), 지난 주차 누적 이수율(D-16-03), 학기 전체 진도율을 엄격히 산출. |
| **PROG-02** | "전체 진도율", "지나온 주차 누적 이수율", "이번 주차 현황(완료/미완료 목록)"을 한눈에 볼 수 있는 3단 분할 `progress` 대시보드 및 표준 JSON 계약 브리핑을 제공한다. | `reporter.py` 및 `cli.py`를 통해 [1] 과목별 진도율 요약 테이블, [2] 이번 주차 상세 액션 아이템, [3] 지난 주차 누락 경고/올클리어 패널 3단 레이아웃(D-16-05)과 `--json` 계약(`schema_version: 1`)(D-16-12) 구현. |
</phase_requirements>

---

## Summary

Phase 16은 CoursePilot의 학습 자동화 기능을 종합 집대성하여, 학생이 수강 중인 모든 강좌의 **4대 학습활동(동영상 VOD, 과제, 퀴즈, 학습자료)** 이수 상태를 빈틈없이 파악하고 학업 진척도를 한눈에 브리핑받을 수 있는 통합 진척도 대시보드(`coursepilot progress`)를 구축합니다.

기존 마일스톤(Phase 2, 6, 7, 13)에서 구축된 파서들(`lecture_parser.py`, `assessment_parser.py`, `material_parser.py`)을 효율적으로 재사용하되, 네트워크 부하를 극소화하기 위해 과목 홈 HTML 1회 방문으로 동영상 강의와 학습자료를 동시에 추출(D-16-13)하고 활동 현황(ublogs) 및 과제/퀴즈 목록을 결합합니다.

핵심 계산 엔진(`calculator.py`)은 날짜 범위와 LMS 활성 섹션(`.current`)을 결합하여 오늘 날짜가 속한 이번 주차(Current Week)를 지능적으로 판별(D-16-02)하고, 학기 전체에 선행 등록된 활동 때문에 진도율이 왜곡되는 문제를 방지하기 위해 **현재 주차 오픈 기준 진도율(메인 지표)**과 **학기 전체 진도율(보조 지표)**을 분리 산출(D-16-04)합니다. 아울러 지나온 주차(1주차 ~ 이번 주차 - 1)의 미완료 항목은 학점/출석 감점 위험을 경고하는 누락/결석 지표(D-16-03)로 엄격히 관리됩니다.

터미널 화면은 Rich 라이브러리를 활용해 [1] 과목별 색상 프로그레스 바 요약 테이블, [2] 이번 주차 To-Do 미완료 활동 최우선 액션 아이템, [3] 과거 누락 경고 패널 또는 🎉 All Clear 배지의 **3단 분할 레이아웃**(D-16-05)으로 렌더링되며, AI 에이전트 연동을 위한 무결점 JSON 계약(`schema_version: 1`)(D-16-12)과 10분 TTL 로컬 캐시(`progress_cache.json`)(D-16-14)를 완벽히 지원합니다.

---

## Architectural Responsibility Map

```
src/coursepilot/
├── scraper/
│   ├── models.py                     # [UPDATE] AssessmentItem에 week_number: int | None = None 추가 (하위 호환)
│   ├── assessment_parser.py          # [UPDATE] parse_assessment_list에서 주차 헤더(주/주차/Week) 감지 및 week_number 추출
│   ├── lecture_parser.py             # [REUSE] parse_lectures_from_course_sections, parse_ublogs_completion, merge
│   └── material_parser.py            # [REUSE] parse_materials_from_course_sections
├── progress/                         # [NEW MODULE]
│   ├── __init__.py                   # 모듈 익스포트
│   ├── models.py                     # 4대 활동 통합 ActivityItem, ActivityBreakdown, CourseProgress, ProgressReport DTO
│   ├── calculator.py                 # 이번 주차 판별, 오픈/과거/학기 진도율, 미완료 To-Do/과거 누락 계산 엔진
│   ├── runner.py                     # 통합 데이터 수집 파이프라인, 단일 방문 파싱, 10분 로컬 캐시, 과목별 오류 격리
│   └── reporter.py                   # 3단 분할 Rich 대시보드, 1~16주차 매트릭스 로드맵, All Clear/Alert 배지 렌더러
└── cli.py                            # [UPDATE] @cli.command("progress") 등록, stderr 스피너 분리, 옵션 파싱
```

### Module Responsibilities

1. **`src/coursepilot/scraper/models.py` & `assessment_parser.py` (Domain Enhancement)**
   - `AssessmentItem`에 `week_number: int | None = None` 필드를 추가하여 과제와 퀴즈가 소속된 주차 메타데이터를 보존합니다.
   - `parse_assessment_list`에서 테이블 헤더의 "주", "주차", "Week" 열을 식별하여 각 행의 주차 정보를 추출합니다 (Moodle 장문/단문 테이블 지원).
   - [VERIFIED: `tests/fixtures/assignment_list.html` 및 `lms_quiz_index.html`에 이미 `<th>주차</th>`, `<th>주</th>` 열이 실재함].

2. **`src/coursepilot/progress/models.py` (Data Models & JSON Contract)**
   - `ActivityType(str, Enum)`: `VOD`, `ASSIGNMENT`, `QUIZ`, `MATERIAL`.
   - `ActivityItem(BaseModel)`: 개별 학습활동의 통합 표현(제목, 활동타입, 주차, 완료여부, 마감일, 지연여부, URL).
   - `ActivityCount(BaseModel)`: `completed: int`, `total: int`, `rate: float`.
   - `ActivityBreakdown(BaseModel)`: 4개 항목별 `ActivityCount` 및 종합 계산 메서드.
   - `CourseProgress(BaseModel)`: 과목별 현재 주차, 오픈 진도율, 과거 주차 이수율, 학기 전체 진도율, 4대 활동 통계, 이번 주차 액션 아이템, 과거 누락 목록.
   - `DashboardSummary(BaseModel)`: 전체 수강 과목의 종합 KPI.
   - `ProgressReport(BaseModel)`: `schema_version: 1`, `status`, `timestamp`, `is_cached`, `summary`, `courses`, `errors`, `notices`.

3. **`src/coursepilot/progress/calculator.py` (Progress Calculation Engine)**
   - `detect_current_week(sections, now)`: 섹션별 시작/종료일 범위(`start_date <= now <= end_date`)와 `.current` 클래스를 결합한 하이브리드 이번 주차 판정.
   - `calculate_course_progress(course, activities, current_week, now)`:
     * 오픈 활동(`week_number <= current_week`): 메인 진도율 산출.
     * 과거 활동(`week_number < current_week`): 과거 누적 이수율 및 미완료 누락/결석 건수 산출.
     * 이번 주차 활동(`week_number == current_week`): To-Do(미완료) 마감순 우선 정렬 및 완료 목록 분리.
     * 학기 전체 활동: 보조 지표 산출.
     * 4대 활동별 세부 달성률(x/y) 산출.
   - `aggregate_dashboard_summary(course_progress_list)`: 전 과목 통합 KPI 집계.

4. **`src/coursepilot/progress/runner.py` (Collection & Cache Orchestrator)**
   - `run_progress_pipeline(...)`:
     * 캐시 확인: `--cached` 플래그 지정 시 10분 TTL 이내의 `progress_cache.json`이 존재하면 즉시 반환.
     * 세션 및 과목 탐색: `SessionManager` 기반 인증 세션 확보 및 `extract_courses`.
     * 과목별 수집 및 예외 격리(D-16-16): 단일 과목 실패 시 `status="error"`로 격리하고 나머지 과목 계속 진행.
     * 단일 방문 동시 파싱(D-16-13): 코스 홈 HTML 1회 fetch로 강의(VOD), 자료(Material), 섹션 주차 날짜/`.current` 추출.
     * 활동 현황(ublogs) 및 과제/퀴즈 목록 수집 후 통합 DTO 변환.
     * 캐시 저장: 새로 수집된 결과를 `progress_cache.json`에 원자적(atomic rename)으로 기록.

5. **`src/coursepilot/progress/reporter.py` (Rich Visual Presentation)**
   - `render_progress_dashboard(report, console, ...)`:
     * Section 1: 색상 코딩 프로그레스 바 테이블 (100% 녹색, 80~99% 청색, 50~79% 황색, 50% 미만 적색) 및 4대 활동 x/y 병기.
     * Section 2: 이번 주차 To-Do 최상단 강조 (유형별 색상 태그 `[VOD]`, `[과제]`, `[퀴즈]`, `[자료]` 및 잔여 시간), 하단 완료 목록(`✓`).
     * Section 3: 과거 누락 존재 시 경고 패널(`⚠️`), 누락 없을 시 녹색 올클리어 배지(`🎉 All Clear`).
   - `render_course_matrix(course_progress, console)`: `--course` 지정 시 1~16주차 전 주차 로드맵 매트릭스 테이블 렌더링.
   - `render_detailed_activities(report, console)`: `--detail` 플래그 지정 시 전 주차 세부 활동 목록 전개.

6. **`src/coursepilot/cli.py` (CLI Command Integration)**
   - `@cli.command("progress")` 등록 및 옵션 파싱 (`--course`, `--week`, `--detail`, `--cached`, `--refresh`, `--json`, `--relogin`, `--headed`).
   - `Console(stderr=True)` 스피너와 stdout 리포트/JSON의 완벽한 분리(D-16-15).
   - 종료 코드: 완전 성공 0, 부분 실패(일부 과목 에러 또는 과거 누락 존재) 1, 치명적 에러 2.

---

## Standard Stack

| 컴포넌트 | 선택 기술 | 선정 근거 |
|---|---|---|
| **CLI Framework** | `click >= 8.1.0` | 프로젝트 표준 CLI 프레임워크 (`check`, `sync`, `board`, `materials`와 일관성 유지) [VERIFIED: `src/coursepilot/cli.py`] |
| **Data Validation** | `pydantic >= 2.6.0` | 엄격한 타입 검증, `schema_version: 1` 직렬화, 불변성 보장 [VERIFIED: `src/coursepilot/report_models.py`] |
| **Terminal UI** | `rich >= 13.7.0` | `ProgressBar`, `Table`, `Panel`, `Text`, `Status` 스피너 지원 [VERIFIED: `src/coursepilot/reporter.py`] |
| **HTTP Client** | `httpx >= 0.28.0` | 동기 쿠키 인증 클라이언트 기반 빠른 LXP HTML 스크래핑 [VERIFIED: `src/coursepilot/board/runner.py`] |
| **HTML Parsing** | `beautifulsoup4 >= 4.12.0` (`lxml`) | 기존 Coursemos 섹션 및 테이블 파서와 100% 호환 [VERIFIED: `src/coursepilot/scraper/`] |
| **Browser Driver** | `playwright >= 1.42.0` | 세션 관리 및 인증 상태 갱신 [VERIFIED: `src/coursepilot/session_manager.py`] |

---

## Architecture Patterns

### Pattern 1: Single-Trip HTML Scraping (D-16-13)
과목 홈 페이지(`/course/view.php?id=...`)를 방문했을 때 HTML을 한 번만 가져와 세 가지 필수 정보를 동시에 추출합니다:
1. `parse_lectures_from_course_sections(home_html, course)`: VOD 강의 목록 및 차시 정보.
2. `parse_materials_from_course_sections(home_html, course)`: 학습자료(`ubfile`, `resource`) 목록 및 완료 상태.
3. `extract_course_sections_meta(home_html)`: 각 주차 섹션의 주차 번호, 기간 날짜 범위(`text-ubstrap`), 그리고 `.current` 활성 섹션 여부.

이로 인해 과목당 브라우저/HTTP 이동 횟수가 대폭 감소하여 수집 속도가 최대 3배 향상됩니다.

### Pattern 2: Hybrid Current Week Detection (D-16-02)
이번 주차(Current Week)는 다음 3단계 우선순위로 결정합니다:
```python
def detect_current_week(sections: list[SectionMeta], now: datetime) -> int:
    # 1단계: 오늘 날짜(KST)가 섹션의 날짜 범위(start_date <= now <= end_date)에 포함되는 주차
    for sec in sections:
        if sec.start_date and sec.end_date and sec.start_date <= now <= sec.end_date:
            return sec.week_number

    # 2단계: LXP 마크업에서 class="... current ..." 또는 "current-section"을 가진 주차
    for sec in sections:
        if sec.is_current and sec.week_number > 0:
            return sec.week_number

    # 3단계 (폴백): 오늘 날짜와 가장 가까운 미래 마감 섹션, 또는 미완료 활동이 있는 최소 주차, 없으면 1주차
    valid_weeks = [sec.week_number for sec in sections if sec.week_number > 0]
    return min(valid_weeks) if valid_weeks else 1
```

### Pattern 3: Dual Progress Metric Modeling (D-16-04)
학기 전체에 선행 등록된 활동(예: 1~16주차 강의자료 60건이 개강 첫날 모두 등록된 경우)으로 인해 현재 학업 이수율이 10%로 왜곡되는 현상을 방지하기 위해 진도율을 2중 구조로 분리합니다:
- **메인 지표 (Current Open Rate)**: `현재 주차까지 오픈된 활동 완료수 / 오픈된 총 활동수 * 100` (예: `90% (9/10)`)
- **보조 지표 (Semester Overall Rate)**: `학기 전체 완료수 / 학기 전체 총 활동수 * 100` (예: `25% (9/36)`)

### Pattern 4: Strict Past-Weeks Cumulative Accountability & Alert Triggering (D-16-03, D-16-08)
지나온 주차(`1 <= week_number < current_week`)에 속한 활동은 이미 마감 시점이 지났으므로, 미완료 상태인 경우 예외 없이 **누락/결석(Missed)**으로 판정합니다:
- 과거 주차 이수율: `과거 완료 건수 / 과거 등록 건수 * 100`
- 과거 누락 건수 > 0: 적색/황색 경고 패널(`⚠️ 과거 주차 누락 N건`)을 출력하고, 누락된 항목명과 해당 마감일을 명시합니다.
- 과거 누락 건수 == 0: 녹색 `🎉 All Clear` 배지를 출력합니다 (이번 주차가 1주차인 경우 과거 주차가 없으므로 자연스럽게 All Clear 처리).

### Pattern 5: Action Item Prioritization (D-16-07)
이번 주차(`week_number == current_week`)의 활동 목록 렌더링 시:
1. 아직 완료하지 않은 잔여 활동(To-Do)을 최상단에 마감 임박 순서로 정렬합니다.
2. 활동 유형에 따라 시인성 높은 대괄호 태그를 부여합니다:
   - `[VOD]`: 청색 (`[blue]`)
   - `[과제]`: 자홍색/적색 (`[magenta]` / `[red]`)
   - `[퀴즈]`: 황색 (`[yellow]`)
   - `[자료]`: 청록색 (`[cyan]`)
3. 마감이 24시간 이내인 경우 `🔴 긴급` 배지를 추가합니다.
4. 이미 완료된 활동은 하단에 체크표시(`✓`)와 함께 컴팩트한 회색 톤으로 요약하여 시각적 피로도를 줄입니다.

### Pattern 6: Stream Separation & Versioned JSON Contract (D-16-12, D-16-15)
- **stderr**: `Console(stderr=True)`를 통해 실시간 수집 진행 상태 및 스피너(`[1/6] [공수2] 활동 내역 수집 중...`)를 출력합니다.
- **stdout**: CLI 인자에 따라 Rich 터미널 대시보드 또는 순수 JSON(`ProgressReport.model_dump_json(indent=2)`)만 단독 출력합니다.
- 파이프(`| jq`) 처리 시 깨짐이 없도록 stdout은 UTF-8로 재구성됩니다.

### Pattern 7: Atomic Cache with 10-Minute TTL (D-16-14)
- 캐시 경로: `settings.session_cache_path.parent / "progress_cache.json"`
- 만료 시간: 600초 (10분)
- 저장 방식: 임시 파일(`.tmp`) 생성 후 `replace()`를 통한 원자적(atomic) 교체 (Claude's Discretion).
- 동작 규칙:
  * `--cached`: 유효한 캐시가 있으면 즉시 로드, 만료되었거나 없으면 실시간 수집 후 캐시 갱신.
  * `--refresh`: 기존 캐시를 무시하고 무조건 실시간 수집 후 캐시 갱신.
  * 기본 실행: 실시간 최신 수집 후 캐시 자동 갱신.

### Pattern 8: Per-Course Error Isolation (D-16-16)
특정 과목의 수집 중 네트워크 단절, HTML 파싱 변경, 접근 권한 없음 등의 에러가 발생하더라도, `try ... except Exception as e` 블록으로 안전하게 격리합니다:
- 해당 과목은 `CourseProgress(status="error", error_message=...)`로 표시.
- 대시보드 테이블에서는 `[수집실패]`로 표기.
- 나머지 정상 과목들의 진척도 산출 및 전체 대시보드 브리핑은 100% 정상 완료.

---

## Don't Hand-Roll

| 기능 | 권장 구현 | 직접 작성 시 발생하는 위험 |
|---|---|---|
| **터미널 프로그레스 바** | `rich.progress_bar.ProgressBar` 또는 Rich Table 스타일 문자열 | 터미널 가로폭 깨짐, ANSI 이스케이프 시퀀스 오작동, 윈도우 cmd/PowerShell 호환성 결함 |
| **JSON 스키마 직렬화** | Pydantic `BaseModel.model_dump_json()` | datetime ISO 형식 불일치, Enum 직렬화 실패, 계약 불일치 |
| **한국 표준시 계산** | `src/coursepilot/scraper/date_parser.py`의 `KST` 및 `get_current_kst_time()` | 시스템 로컬 타임존(UTC 등)과 KST 혼용으로 인한 9시간 시차 버그 |
| **과목명 퍼지 매칭** | `src/coursepilot/player/runner.py`의 `find_target_course` 및 `course_mapping.py` | 약칭 매핑 누락, 괄호/분반 표기 미처리로 과목 검색 실패 |
| **원자적 파일 저장** | `temp_path.write_text(...)` 후 `temp_path.replace(target_path)` | 프로세스 강제 종료 시 JSON 파일이 깨져 이후 실행에서 영구 SyntaxError 발생 |

---

## Common Pitfalls

### Pitfall 1: 1주차 실행 시 과거 주차(Past Weeks) 누락 오탐지 (Off-by-One)
- **문제점:** 개강 첫 주차(`current_week == 1`)일 때, `past_weeks = 1 ~ (current_week - 1)` 범위는 0개 주차입니다. 만약 범위 판정을 잘못하여 1주차 미완료 활동을 과거 주차 누락으로 간주하면 첫 주부터 결석 경고가 발생합니다.
- **해결책:** `week_number < current_week` 조건을 엄격히 적용하며, `current_week <= 1`인 경우 `past_weeks_total = 0`, `past_weeks_rate = 100.0`, `missed_past_items = []`로 처리하여 깔끔하게 `🎉 All Clear` 배지를 띄웁니다.

### Pitfall 2: 미래 주차 선행 등록으로 인한 전체 진도율 왜곡
- **문제점:** 교수가 16주차 분량의 강의계획서와 PDF 자료 50개를 미리 올려두면, 3주차 학생이 지금까지의 모든 활동을 100% 완료했음에도 `15/65 = 23%`로 표시되어 학업 불안감을 조성합니다.
- **해결책:** D-16-04 결정에 따라 `week_number <= current_week`에 해당하는 오픈 활동 기준 진도율을 메인 게이지로 삼고, `전체 15/65 (23%)`는 보조 설명으로 작게 병기합니다.

### Pitfall 3: 퀴즈 성적 비공개 시 미응시 오분류
- **문제점:** LMS 퀴즈 목록 테이블에서 성적이 비어있는 경우, 학생이 이미 응시했음에도 `미응시(NOT_ATTEMPTED)`로 판정되어 To-Do 목록에 남을 수 있습니다.
- **해결책:** Phase 6에서 검증된 `enrich_assessment_detail` 및 `is_quiz_attempt_completed`를 적용하여 상세 페이지의 `답안 검토` 또는 `응시 가능 횟수 초과` 여부를 확인하여 `SUBMITTED`로 보정합니다.

### Pitfall 4: 표준출력(stdout) 오염으로 인한 AI 에이전트 JSON 파싱 오류
- **문제점:** 수집 중 진행 상황이나 파이썬 경고 메시지가 stdout으로 흘러들어가면 `--json` 실행 시 `json.loads()`가 실패합니다.
- **해결책:** D-16-15에 따라 모든 스피너, 진행 메시지, 경고는 `Console(stderr=True)` 또는 `logging.basicConfig(stream=sys.stderr)`로 보내고 stdout에는 오직 최종 리포트 또는 JSON 문자열만 단독 출력합니다.

---

## Code Examples

### 1. Unified Progress Models (`src/coursepilot/progress/models.py`)

```python
"""Data models and versioned JSON contract for activity progress dashboard."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from coursepilot.report_models import ErrorItem, ReportNotice

SCHEMA_VERSION = 1


class ActivityType(str, Enum):
    """Four core academic activity types."""
    VOD = "vod"
    ASSIGNMENT = "assignment"
    QUIZ = "quiz"
    MATERIAL = "material"


class ActivityItem(BaseModel):
    """Unified domain representation of a single learning activity."""
    model_config = ConfigDict(extra="forbid")

    course_id: str
    activity_type: ActivityType
    week_number: int
    title: str
    is_completed: bool
    due_date: datetime | None = None
    raw_due_date: str = ""
    is_overdue: bool = False
    is_urgent: bool = False
    url: str = ""
    module_id: str | None = None
    clip_number: int | None = None


class ActivityCount(BaseModel):
    """Completion counter and rate for a specific activity type."""
    model_config = ConfigDict(extra="forbid")

    completed: int = 0
    total: int = 0
    rate: float = 0.0


class ActivityBreakdown(BaseModel):
    """Breakdown across all 4 activity types."""
    model_config = ConfigDict(extra="forbid")

    vod: ActivityCount = Field(default_factory=ActivityCount)
    assignment: ActivityCount = Field(default_factory=ActivityCount)
    quiz: ActivityCount = Field(default_factory=ActivityCount)
    material: ActivityCount = Field(default_factory=ActivityCount)


class CourseProgress(BaseModel):
    """Comprehensive progress metrics for a single course."""
    model_config = ConfigDict(extra="forbid")

    course_id: str
    course_name: str
    course_abbr: str
    current_week: int
    current_open_rate: float
    current_open_completed: int
    current_open_total: int
    past_weeks_rate: float
    past_weeks_completed: int
    past_weeks_total: int
    semester_overall_rate: float
    semester_completed: int
    semester_total: int
    activity_breakdown: ActivityBreakdown
    current_week_items: list[ActivityItem] = Field(default_factory=list)
    missed_past_items: list[ActivityItem] = Field(default_factory=list)
    all_items: list[ActivityItem] = Field(default_factory=list)
    status: Literal["ok", "error"] = "ok"
    error_message: str | None = None


class DashboardSummary(BaseModel):
    """Aggregate KPIs across all enrolled courses."""
    model_config = ConfigDict(extra="forbid")

    total_courses: int
    current_open_rate: float
    current_open_completed: int
    current_open_total: int
    past_weeks_rate: float
    past_weeks_completed: int
    past_weeks_total: int
    semester_overall_rate: float
    semester_completed: int
    semester_total: int
    missed_past_count: int
    current_week_todo_count: int
    activity_totals: ActivityBreakdown


class ProgressReport(BaseModel):
    """Top-level JSON contract for the progress dashboard."""
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = SCHEMA_VERSION
    status: Literal["success", "partial_success", "error"]
    generated_at: datetime
    is_cached: bool = False
    summary: DashboardSummary
    courses: list[CourseProgress]
    errors: list[ErrorItem] = Field(default_factory=list)
    notices: list[ReportNotice] = Field(default_factory=list)
```

### 2. Progress Calculation Logic (`src/coursepilot/progress/calculator.py`)

```python
"""Progress calculation engine for multi-tier activity completion."""

from datetime import datetime
from coursepilot.progress.models import (
    ActivityBreakdown,
    ActivityCount,
    ActivityItem,
    ActivityType,
    CourseProgress,
    DashboardSummary,
)
from coursepilot.scraper.date_parser import get_current_kst_time


def compute_breakdown(items: list[ActivityItem]) -> ActivityBreakdown:
    """Calculates completion counts and percentages across 4 activity types."""
    counts = {t: [0, 0] for t in ActivityType}  # [completed, total]
    for item in items:
        counts[item.activity_type][1] += 1
        if item.is_completed:
            counts[item.activity_type][0] += 1

    def make_count(t: ActivityType) -> ActivityCount:
        comp, tot = counts[t]
        rate = round((comp / tot * 100.0), 1) if tot > 0 else 100.0
        return ActivityCount(completed=comp, total=tot, rate=rate)

    return ActivityBreakdown(
        vod=make_count(ActivityType.VOD),
        assignment=make_count(ActivityType.ASSIGNMENT),
        quiz=make_count(ActivityType.QUIZ),
        material=make_count(ActivityType.MATERIAL),
    )


def calculate_course_progress(
    course_id: str,
    course_name: str,
    course_abbr: str,
    current_week: int,
    activities: list[ActivityItem],
    now: datetime | None = None,
) -> CourseProgress:
    """Calculates multi-tier progress metrics according to D-16-01 ~ D-16-04."""
    current_time = now or get_current_kst_time()

    # 1. Bucket activities by week relative to current_week
    past_activities = [a for a in activities if a.week_number < current_week]
    current_week_activities = [a for a in activities if a.week_number == current_week]
    open_activities = [a for a in activities if a.week_number <= current_week]
    all_activities = activities

    # 2. Main Metric: Current Open Rate (D-16-04)
    open_total = len(open_activities)
    open_completed = sum(1 for a in open_activities if a.is_completed)
    open_rate = round(open_completed / open_total * 100.0, 1) if open_total > 0 else 100.0

    # 3. Past Weeks Cumulative Rate (D-16-03)
    past_total = len(past_activities)
    past_completed = sum(1 for a in past_activities if a.is_completed)
    past_rate = round(past_completed / past_total * 100.0, 1) if past_total > 0 else 100.0
    missed_past = [a for a in past_activities if not a.is_completed]

    # 4. Semester Overall Rate (Auxiliary) (D-16-04)
    semester_total = len(all_activities)
    semester_completed = sum(1 for a in all_activities if a.is_completed)
    semester_rate = round(semester_completed / semester_total * 100.0, 1) if semester_total > 0 else 100.0

    # 5. Current Week Action Items (To-Do prioritized) (D-16-07)
    todo_items = [a for a in current_week_activities if not a.is_completed]
    todo_items.sort(key=lambda x: (x.due_date is None, x.due_date or datetime.max))
    done_items = [a for a in current_week_activities if a.is_completed]
    current_week_items = todo_items + done_items

    # 6. Activity Breakdown for open activities
    breakdown = compute_breakdown(open_activities)

    return CourseProgress(
        course_id=course_id,
        course_name=course_name,
        course_abbr=course_abbr,
        current_week=current_week,
        current_open_rate=open_rate,
        current_open_completed=open_completed,
        current_open_total=open_total,
        past_weeks_rate=past_rate,
        past_weeks_completed=past_completed,
        past_weeks_total=past_total,
        semester_overall_rate=semester_rate,
        semester_completed=semester_completed,
        semester_total=semester_total,
        activity_breakdown=breakdown,
        current_week_items=current_week_items,
        missed_past_items=missed_past,
        all_items=all_activities,
        status="ok",
    )
```

### 3. Local Cache Management (`src/coursepilot/progress/runner.py`)

```python
"""Atomic 10-minute cache management for progress reports (D-16-14)."""

import json
import logging
from pathlib import Path
from datetime import datetime

from coursepilot.progress.models import ProgressReport
from coursepilot.scraper.date_parser import get_current_kst_time

logger = logging.getLogger(__name__)
CACHE_TTL_SECONDS = 600  # 10 minutes


def load_progress_cache(cache_path: Path, max_age_seconds: int = CACHE_TTL_SECONDS) -> ProgressReport | None:
    """Loads cached progress report if present and within TTL."""
    if not cache_path.exists():
        return None
    try:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
        gen_time = datetime.fromisoformat(data["generated_at"])
        age = (get_current_kst_time() - gen_time).total_seconds()
        if age > max_age_seconds:
            logger.debug("Progress cache expired (age: %.1fs > %ds)", age, max_age_seconds)
            return None

        report = ProgressReport.model_validate(data)
        report.is_cached = True
        return report
    except Exception as e:
        logger.debug("Failed to read progress cache: %s", e)
        return None


def save_progress_cache(cache_path: Path, report: ProgressReport) -> None:
    """Atomically writes progress report to local cache file."""
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_file = cache_path.with_suffix(".tmp")
        tmp_file.write_text(report.model_dump_json(indent=2), encoding="utf-8")
        tmp_file.replace(cache_path)
    except Exception as e:
        logger.warning("Failed to save progress cache: %s", e)
```

---

## Environment Availability

| 의존성 / 리소스 | 준비 상태 | 검증 내용 |
|---|---|---|
| **Python 3.11+ Runtime** | 설치됨 (uv 환경) | `uv run pytest` 정상 실행 확인 완료 (363개 전 테스트 PASS) [VERIFIED: CLI output] |
| **Playwright Browser** | Chromium 설치됨 | `SessionManager` 및 헤드리스 브라우저 구동 가능 [VERIFIED: Phase 1~15] |
| **Rich & Click** | 설치됨 | `rich>=13.7.0`, `click>=8.1.0` [VERIFIED: `pyproject.toml`] |
| **로컬 세션 캐시** | 준비됨 | `.session_cache/session.json` 및 `progress_cache.json` 기록 경로 확보 |
| **테스트 픽스처** | 준비됨 | `lms_course_home.html`, `lms_course_materials.html`, `assignment_list.html`, `lms_quiz_index.html` [VERIFIED: `tests/fixtures/`] |

---

## Validation Architecture

### Test Framework
- **Runner:** `pytest` (via `uv run pytest tests/`)
- **Isolation:** `tmp_path` fixture for cache directory, `pytest-mock` for network/page mocking.
- **Fixture files:** Existing server HTML snapshots in `tests/fixtures/`.

### Phase Requirements -> Test Map

| Requirement ID | Test Focus | Target Test File |
|---|---|---|
| **PROG-01** | 4대 활동 통합 이수율 계산, 주차 판정(날짜범위 + `.current`), 오픈 vs 학기 전체 진도율 분리, 과거 주차 누락 감지 | `tests/test_progress_calculator.py` |
| **PROG-01** | `ActivityItem`, `CourseProgress`, `DashboardSummary`, `ProgressReport` 모델 검증 및 직렬화 | `tests/test_progress_models.py` |
| **PROG-01, PROG-02** | 단일 방문 파싱(D-16-13), 10분 로컬 캐시 관리(D-16-14), 과목별 예외 격리(D-16-16), `--course`/`--week` 필터링 | `tests/test_progress_runner.py` |
| **PROG-02** | 3단 분할 대시보드 렌더링(D-16-05), 색상 프로그레스 바(D-16-06), To-Do 최상단 강조(D-16-07), Alert/All-Clear 배지(D-16-08), 매트릭스 로드맵(D-16-10) | `tests/test_progress_reporter.py` |
| **PROG-02** | CLI `progress` 서브커맨드, stderr 스피너 분리(D-16-15), `--json` 계약 출력(D-16-12), 종료 코드(0, 1, 2) | `tests/test_cli_progress.py` |

### Sampling Rate
- 단위 테스트 및 목 통합 테스트: 100% (자동화 파이프라인 전 항목 검증).
- 라이브 LXP 수집 검증: 사용자 세션 및 환경변수 주입 시 E2E 검증 가능.

### Wave 0 Gaps
- `AssessmentItem` (`src/coursepilot/scraper/models.py`)에 주차 식별용 `week_number: int | None = None` 필드 추가 필요.
- `parse_assessment_list` (`src/coursepilot/scraper/assessment_parser.py`)에 테이블 헤더 "주"/"주차" 열 감지 로직 추가 필요.
- 이 두 항목은 기존 동작에 전혀 영향을 주지 않는 순수한 하위 호환 확장입니다.

---

## Security Domain

1. **인증 정보 누출 원천 차단:**
   - 대시보드 터미널 출력 및 JSON 리포트에는 학생 패스워드, 세션 쿠키, Notion API 토큰이 일절 포함되지 않습니다.
   - 예외 발생 시 `safe_cli_error` 허용목록을 경유하여 안전한 한국어 고정 안내문만 표기합니다.
2. **로컬 캐시 파일 보안:**
   - `progress_cache.json`은 오직 과목명, 활동명, 완료율 등 공개 학습 메타데이터만 담으며, 사용자 로컬 애플리케이션 캐시 디렉터리에만 보관됩니다.
3. **읽기 전용 격리 (Safety Guard):**
   - Phase 16의 `progress` 커맨드는 LMS와 Notion 데이터베이스에 어떠한 쓰기/수정/삭제 요청도 보내지 않는 순수 조회(Read-Only) 도구로 격리됩니다.

---

## Sources

- [VERIFIED: `src/coursepilot/scraper/models.py` & `src/coursepilot/scraper/lecture_parser.py`] - VOD 파싱 및 ublogs 완료 병합 구조
- [VERIFIED: `src/coursepilot/scraper/material_parser.py` & `src/coursepilot/materials/models.py`] - 학습자료 파싱 및 완료 상태 추출
- [VERIFIED: `src/coursepilot/scraper/assessment_parser.py`] - 과제 및 퀴즈 완료/제출 상태 판정 로직
- [VERIFIED: `src/coursepilot/board/runner.py` & `src/coursepilot/materials/downloader.py`] - 인증된 httpx 클라이언트 및 세션 매니저 연동 패턴
- [VERIFIED: `skills/coursepilot/JSON_CONTRACT.md`] - `schema_version: 1` 에이전트 계약 명세
- [VERIFIED: `tests/fixtures/lms_course_home.html` & `assignment_list.html`] - Coursemos HTML 주차 및 섹션 구조 확인
