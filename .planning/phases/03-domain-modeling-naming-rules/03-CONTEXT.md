# Phase 3: Domain Modeling & Naming Rules - Context

**Gathered:** 2026-09-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 3는 수집된 원시 데이터(`CourseItem`, `LectureItem`, `AssessmentItem`)를 비즈니스 도메인 모델(`SyncTask` 등)로 정규화 및 변환하고, 사용자 노션 관례에 맞춘 통일 네이밍 규칙 및 24시간 마감 임박/우선순위 판정 엔진을 구축합니다:
1. 도메인 엔티티 정의 (`SyncTask`, `Course`, `TaskType`, `TaskPriority` 등)
2. 노션 관례 기반 통일된 작업명 네이밍 포매터 (`naming.py`)
3. 잔여 마감 기한 및 활동 유형 기반 우선순위/노션 속성 매핑 엔진 (`priority.py`)
4. 태스크 수명주기 모델링 및 과거 지연/설명란 기한 과제 선별 로직
5. 노션 메모 페이로드 구성 및 텍스트 안전 절삭 모듈 (`transformer.py`)

*노션 API 실제 호출, 노션 DB 페이지 생성/조회, 중복 방지 쿼리는 Phase 4의 영역이며, CLI 인터페이스 및 리포터는 Phase 5의 영역입니다.*

</domain>

<decisions>
## Implementation Decisions

### 1. 작업명 네이밍 세부 규칙 (Task Naming Formats)
- **D-01:** 온라인 동영상 강의는 고정 차시 표기형 `[{과목약어}] {N}주차 {M}차시 강의 시청` 포맷을 적용 (예: `[공수2] 3주차 1차시 강의 시청`). 기존 노션 스케줄러 관례와 완전히 일치하도록 구성. — **Reversibility:** costly — 노션 DB에 동기화된 기존 제목 및 Phase 4 중복 검사 로직에 직접 영향
- **D-02:** 과제 및 평가 활동은 유형별 동사 분기형 포맷을 적용:
  - 일반 과제: `[{과목약어}] {N}주차 {과제명} 제출`
  - 퀴즈/시험: `[{과목약어}] {N}주차 [퀴즈] {이름} 응시`
  - 토론: `[{과목약어}] {N}주차 [토론] {이름} 참여`
  — **Reversibility:** costly — 작업명 규칙 변경 시 노션 기등록 제목 매칭에 영향
- **D-03:** 과제/퀴즈 중 특정 주차에 속하지 않거나 주차 정보가 없는 공통/전체 과제는 주차 표기를 유연하게 생략하여 `[{과목약어}] {과제명} 제출`로 조건부 폴백. — **Reversibility:** reversible
- **D-04:** LMS 과제명 및 강의명은 스마트 정제를 적용하여 HTML 엔티티(`&amp;` -> `&` 등) 디코딩, 다중 공백 단일화, 교수자가 제목 앞단에 중복 기재한 `[과제]` 등의 태그를 자동 정리하여 깔끔한 작업명을 생성. — **Reversibility:** reversible

### 2. 우선순위 및 속성 매핑 (Priority & Notion Properties)
- **D-05:** 노션의 `선택` 속성은 활동 성격에 따라 자동 매핑: 동영상 강의 시청은 `루틴`, 과제/퀴즈/시험/토론은 `이벤트`로 분류. — **Reversibility:** reversible
- **D-06:** 노션의 `우선순위`(P1~P4)는 활동 유형 + 긴급도 결합형 규칙을 적용:
  - 마감 24시간 이내 미완료 항목: 무조건 `P1` (🔴 긴급) 승격
  - 평상시 과제/시험/토론: `P2` (🟠 보통/높음)
  - 평상시 동영상 강의 시청: `P3` (🟡 보통)
  - 마감 기한이 이미 지난 항목(지연): `P4` (⚪ 낮음)
  — **Reversibility:** reversible
- **D-07:** 노션 `DueDate` 필드에는 한국 표준시(KST) 기준 정확한 시:분:초를 포함한 ISO 8601 포맷(`YYYY-MM-DDTHH:MM:SS+09:00`)으로 기록하여 정확한 타임라인 알림 지원. — **Reversibility:** reversible
- **D-08:** 노션 `Plan`(계획일) 필드는 학생이 개인 스케줄에 맞춰 직접 배치할 수 있도록 초기값을 비워두고(`None`), `구분` 속성은 `["학업"]`으로 자동 설정. — **Reversibility:** reversible

### 3. 태스크 상태 모델링 및 과거 지연 처리 (Status Lifecycle & Filtering)
- **D-09:** 동기화 기본 대상은 미완료 항목만 선별하여 반환하되, 도메인 모델(`SyncTask`) 자체는 `is_completed` 필드를 포함하여 향후 완료 상태 조회 및 리포팅 확장을 지원. — **Reversibility:** reversible
- **D-10:** 출석 인정/제출 기한이 지난 과거 미완료 항목은 노션 상태(`상태`)를 `시작 전`으로 유지. 노션 DB의 `D-Day` 수식 속성에서 오늘 날짜와 `DueDate`를 기반으로 자동으로 지연을 계산·표시하므로 작업명에 별도의 `[지연]` 태그를 붙이지 않고 깨끗한 표준 제목 유지. — **Reversibility:** costly — 제목에 태그 부착 여부는 Phase 4 중복 방지 엔진의 키 생성 방식에 영향
- **D-11:** 마감일이 없는 단순 상시 열람/OT 영상은 스케줄러 동기화 대상에서 제외. 단, LMS 정규 기한 설정이 없더라도 과제 설명란에 기한과 제출 방법(개인 메시지, 이메일 제출 등)이 적혀 있는 과제는 본문 텍스트 분석을 통해 유효 마감일을 추정/보완하여 스케줄러에 포함. — **Reversibility:** reversible

### 4. 노션 메모 페이로드 및 코드 아키텍처 (Memo Payload & Architecture)
- **D-12:** 동영상 강의의 노션 `메모` 필드는 `LMS 바로가기: {link}` 형태로 단독/간결하게 구성하여 원클릭 학습 이동 지원. — **Reversibility:** reversible
- **D-13:** 과제/평가 항목의 노션 `메모` 필드는 단락을 나누어 구조화: LMS 바로가기 링크, 지각 제출 마감일(있을 시), 첨부파일 목록, 교수자 과제 설명/제출 안내 요약을 단락별로 구분하여 기록. — **Reversibility:** reversible
- **D-14:** 교수자 과제 설명문이 긴 경우 노션 API의 단일 텍스트 2000자 제한을 고려하여 1500자 초과 시 안전하게 절삭하고 말줄임표 및 `... [이하 생략 - 전체 내용은 LMS 페이지 참조]` 안내 문구를 자동 추가. — **Reversibility:** reversible
- **D-15:** Phase 3 코드는 `src/kau_assistant/domain/` 서브패키지로 모듈화하여 `models.py`(도메인 엔티티), `naming.py`(작업명 규칙 포매터), `priority.py`(긴급도/우선순위/속성 매핑), `transformer.py`(원시 DTO -> SyncTask 변환기)로 명확히 역할 분리. — **Reversibility:** costly — 패키지 구조 및 임포트 경로 의존

### the agent's Discretion
- 세부적인 과제 설명문 정규식 패턴 및 불필요한 HTML 태그 제거 로직
- 도메인 모델 유효성 검증용 Pydantic v2 필드 제약 조건 구성

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project & Roadmap Specs
- `.planning/PROJECT.md` — 프로젝트 개요, 노션 DB 스키마 속성(`선택`, `구분`, `DueDate`, `Plan`, `우선순위`, `상태`, `메모`), 기존 네이밍 관례
- `.planning/REQUIREMENTS.md` — DOMN-01 (미완료 판별), DOMN-02 (24시간 마감 임박/P1 지정), DOMN-03 (통일된 작업명 규칙)
- `.planning/ROADMAP.md` — Phase 3 목표, 성공 기준 및 계획 지침
- `.planning/phases/01-foundation-session-management/01-CONTEXT.md` — Phase 1 결정사항 (D-05, D-06: 과목명 약칭 매핑 로직)
- `.planning/phases/02-lms-scraper-core/02-CONTEXT.md` — Phase 2 결정사항 (D-06: 과거 지연 강의 보존, D-07: 차시 분할, D-10: 미제출 판정, D-12: 지각 마감 보존)

### Source Code References
- `src/kau_assistant/scraper/models.py` — 원시 추출 DTO (`CourseItem`, `LectureItem`, `AssessmentItem`, `AttendanceStatus`, `SubmissionStatus`, `AssessmentType`)
- `src/kau_assistant/course_mapping.py` — 과목 약칭 매핑 로더 (`get_abbreviation`, `load_course_mappings`)
- `src/kau_assistant/scraper/date_parser.py` — KST 기준 일시 파싱, `is_past_deadline`, `get_current_kst_time`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/kau_assistant/course_mapping.py`: 과목명 약칭 변환 함수(`get_abbreviation`)를 네이밍 포매터(`naming.py`)에서 직접 호출하여 과목 접두사(`[{과목약어}]`) 생성.
- `src/kau_assistant/scraper/date_parser.py`: KST 시간대(`KST`), 현재 KST 시간 반환(`get_current_kst_time`), 마감 여부 판별(`is_past_deadline`), 날짜 파서(`parse_lms_date`)를 우선순위 판정 및 본문 설명 마감일 추출에 재사용.
- `src/kau_assistant/scraper/models.py`: 입력 DTO로 활용되며, 이를 기반으로 Phase 3의 `transformer.py`가 `SyncTask`로 변환.

### Established Patterns
- Pydantic BaseModel 기반 엄격한 타입 정의
- KST (`Asia/Seoul`, UTC+9) 고정 타임존 처리
- 불완전 데이터 발생 시 안전한 폴백(Fallback) 보장

### Integration Points
- `src/kau_assistant/domain/`: 이번 단계에서 구축되는 비즈니스 로직 계층.
- Phase 4 노션 동기화 엔진(`NotionSyncEngine`)이 `SyncTask` 컬렉션을 입력받아 노션 API와 비교/생성하게 됨.

</code_context>

<specifics>
## Specific Ideas

- **노션 수식 필드 존중**: 사용자의 Notion Scheduler DB에 이미 `D-Day` 수식 열이 있으므로 작업명에 지저분하게 `[지연]`을 붙이지 않고 깔끔하게 유지할 것.
- **설명란 마감일 과제 구출**: LMS 자체 DueDate가 없더라도 과제 설명 텍스트에 "개인 이메일 제출", "X월 X일까지" 등의 제출 안내가 있으면 파싱하여 누락 없이 스케줄러에 등록할 것.
- **1500자 안전 절삭**: 노션 API rich_text 속성 2000자 초과 시 발생하는 400 Bad Request를 사전에 원천 차단할 것.

</specifics>

<deferred>
## Deferred Ideas

- None — 모든 논의가 Phase 3 Domain Modeling & Naming Rules 범위 내에서 집중적으로 완료됨.

</deferred>

---

*Phase: 3-Domain Modeling & Naming Rules*
*Context gathered: 2026-09-21*
