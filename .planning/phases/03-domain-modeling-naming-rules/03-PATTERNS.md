# Phase 3: Domain Modeling & Naming Rules - Pattern Mapping

**Generated:** 2026-09-21  
**Phase:** 03-domain-modeling-naming-rules  
**Status:** Complete  

---

## 1. Codebase Status & Architectural Context

Phase 1에서 구축한 기반 시스템(`SessionManager`, `auth.py`, `course_mapping.py`, `config.py`)과 Phase 2에서 구축한 데이터 수집 엔진(`src/coursepilot/scraper/`)을 토대로, Phase 3는 수집된 원시 데이터(`CourseItem`, `LectureItem`, `AssessmentItem`)를 비즈니스 도메인 모델(`SyncTask`)로 정규화 및 변환하고, 사용자 노션 관례에 맞춘 통일 네이밍 규칙 및 24시간 마감 임박/우선순위 판정 엔진을 구축하는 **순수 도메인 계층(Pure Domain Layer)**입니다.

- **완전 격리된 순수 도메인 로직:** 외부 I/O(Playwright 브라우저 제어, Notion HTTP API 호출, 파일 시스템 영속화)를 일절 배제하여 100% 빠르고 결정론적인(deterministic) 단위 테스트가 가능합니다.
- **기존 노션 스케줄러 DB 관례 준수:** Notion Scheduler DB(`21d53280-64be-80ec-af4e-000b679f03bb`)의 기존 속성(`선택`: 루틴/이벤트, `구분`: ["학업"], `우선순위`: P1~P4, `상태`: 시작 전, `DueDate`: KST)과 네이밍 관례를 엄격히 계승합니다.
- **방어적 데이터 처리:** HTML 엔티티 정제, 1500자/1950자 텍스트 절삭(Notion API 2000자 한계 방어), 설명란 마감일 구출, KST 타임존 자동 강제.

---

## 2. File Pattern Mapping

The following table maps every file to be created in Phase 3 to its role, data flow, closest existing analog in the codebase, and primary responsibilities.

| Target File | Role | Data Flow | Closest Existing Analog | Primary Responsibilities & Locked Decisions |
|-------------|------|-----------|-------------------------|----------------------------------------------|
| `src/coursepilot/domain/__init__.py` | Package Root / Public Facade | Downstream consumers import directly from `coursepilot.domain` | `src/coursepilot/scraper/__init__.py` | 도메인 계층 공개 API 일괄 export (`SyncTask`, `Course`, `TaskType`, `TaskPriority`, `TaskSelect`, `TaskStatus`, `clean_task_title`, `format_task_title`, `calculate_priority`, `get_task_selection`, `transform_to_sync_tasks` 등) |
| `src/coursepilot/domain/models.py` | Model / Domain Entities | Produced by `transformer.py`; consumed by Phase 4 `NotionSyncEngine` and Phase 5 CLI reporter | `src/coursepilot/scraper/models.py` | Pydantic v2 기반 도메인 모델 정의 (`SyncTask`, `Course`, `TaskType`, `TaskPriority`, `TaskSelect`, `TaskStatus`). KST 타임존 검증기(`field_validator`), 중복 방지 키(`dedup_key`), 기본값 주입 (D-05, D-06, D-08, D-10, D-15) |
| `src/coursepilot/domain/naming.py` | Utility / String Formatter | Ingests course/activity metadata and mappings; outputs canonical Notion task title for `transformer.py` | `src/coursepilot/course_mapping.py` & `src/coursepilot/scraper/lecture_parser.py` | 과목 약칭 접두사 결합, 주차/차시 표준 표기, 활동 유형별 동사(`시청`/`제출`/`응시`/`참여`) 분기, HTML 엔티티 정제, 중복 태그 및 접미사 동사 제거 (D-01 ~ D-04) |
| `src/coursepilot/domain/priority.py` | Business Logic / Rules Engine | Ingests task metadata, `due_date`, and reference `now`; calculates priority and Notion properties for `transformer.py` | `src/coursepilot/scraper/date_parser.py` (`is_past_deadline`, `get_current_kst_time`) | KST 기준 잔여 시간 계산, 24시간 마감 임박(`P1`) 판정 (DOMN-02), 과거 지연(`P4`), 기본 우선순위(`P2`/`P3`), 노션 속성(`선택`: 루틴/이벤트, `상태`: "시작 전") 매핑 (D-05, D-06, D-10) |
| `src/coursepilot/domain/transformer.py` | Domain Service / DTO Transformer | Ingests Phase 2 DTOs (`CourseItem`, `LectureItem`, `AssessmentItem`); produces filtered and sorted `list[SyncTask]` | `src/coursepilot/scraper/assessment_parser.py` & `src/coursepilot/scraper/lecture_parser.py` | Scraper DTO -> `SyncTask` 변환, 상시 열람 영상 필터링, 과제 설명란 텍스트 정규식 분석을 통한 마감일 구출 (D-11), 1500자 안전 절삭 및 단락 구조화 노션 메모 생성 (D-12 ~ D-14), 미완료 항목 필터링 (D-09) |
| `tests/test_domain_models.py` | Model Unit Tests | Validates `domain/models.py` schema, defaults, KST enforcement, and dedup key generation | `tests/test_scraper_models.py` | `SyncTask`, `Course`, Enums 유효성 검증, KST 타임존 자동 부착 validator 검증, `dedup_key` 일관성 테스트 |
| `tests/test_naming.py` | Naming Unit Tests | Validates title cleaning and template formatting for all activity types | `tests/test_course_mapping.py` & `tests/test_date_parser.py` | 강의 고정 차시 네이밍 (D-01), 과제/퀴즈/토론 동사 분기 (D-02), 비주차 과제 폴백 (D-03), HTML 엔티티 및 중복 태그 정제 (D-04), 동사 중복 방지 ("제출 제출" 방지) |
| `tests/test_priority.py` | Priority Unit Tests | Validates priority ladders and 24-hour urgency boundary conditions | `tests/test_date_parser.py` (`test_is_past_deadline`) | 24시간 마감 임박 판정 (정확히 24h, 24h+1초, 23h59m), 과거 지연 항목(`P4`), 완료 항목(`P4`), 평상시 기본 우선순위(`P2`/`P3`), 노션 `선택` 속성 매핑 검증 |
| `tests/test_transformer.py` | Transformer Unit Tests | Validates full DTO -> `SyncTask` conversion pipeline | `tests/test_assessment_parser.py` & `tests/test_lecture_parser.py` | 동영상 강의 변환 및 OT 영상 제외 (D-11), 과제 변환 및 설명란 마감일 구출 (D-11), 메모 서식 및 1500자 절삭 (D-12~D-14), 미완료 항목 필터링 (D-09), 마감일 순 오름차순 정렬 |

---

## 3. Detailed Per-File Pattern Blueprints & Code Excerpts to Copy

### 3.1 `src/coursepilot/domain/__init__.py`
- **Role:** Package Root / Facade
- **Analog:** [`src/coursepilot/scraper/__init__.py`](../../../src/coursepilot/scraper/__init__.py)
- **Data Flow:** Downstream packages (`coursepilot.notion`, `coursepilot.cli`) import directly from `coursepilot.domain`.
- **Concrete Imports & Excerpt to Mirror:**
  ```python
  """CoursePilot domain modeling and task normalization package."""

  from coursepilot.domain.models import (
      Course,
      SyncTask,
      TaskPriority,
      TaskSelect,
      TaskStatus,
      TaskType,
  )
  from coursepilot.domain.naming import (
      clean_task_title,
      extract_week_and_title,
      format_task_title,
  )
  from coursepilot.domain.priority import (
      calculate_priority,
      get_task_selection,
  )
  from coursepilot.domain.transformer import (
      extract_deadline_from_description,
      format_memo,
      transform_assessment_to_task,
      transform_lecture_to_task,
      transform_to_sync_tasks,
  )

  __all__ = [
      "Course",
      "SyncTask",
      "TaskPriority",
      "TaskSelect",
      "TaskStatus",
      "TaskType",
      "calculate_priority",
      "clean_task_title",
      "extract_deadline_from_description",
      "extract_week_and_title",
      "format_memo",
      "format_task_title",
      "get_task_selection",
      "transform_assessment_to_task",
      "transform_lecture_to_task",
      "transform_to_sync_tasks",
  ]
  ```

---

### 3.2 `src/coursepilot/domain/models.py`
- **Role:** Domain Entities & Enums
- **Analog:** [`src/coursepilot/scraper/models.py`](../../../src/coursepilot/scraper/models.py)
- **Data Flow:** Instantiated by `transformer.py`; passed to Phase 4 `NotionSyncEngine` and Phase 5 CLI Rich reporter.
- **Concrete Imports & Excerpt to Mirror:**
  ```python
  """Domain models for CoursePilot task synchronization."""

  from datetime import datetime
  from enum import Enum
  from pydantic import BaseModel, Field, field_validator

  from coursepilot.scraper.date_parser import KST
  from coursepilot.scraper.models import AssessmentItem, CourseItem, LectureItem


  class TaskType(str, Enum):
      """Activity type of a task."""
      LECTURE = "lecture"
      ASSIGNMENT = "assignment"
      QUIZ = "quiz"
      FORUM = "forum"
      OTHER = "other"


  class TaskPriority(str, Enum):
      """Notion priority level (D-06)."""
      P1 = "P1"  # 🔴 Urgent: <= 24 hours to deadline
      P2 = "P2"  # 🟠 Normal: Default for assessments/quizzes/forums
      P3 = "P3"  # 🟡 Normal: Default for video lectures
      P4 = "P4"  # ⚪ Low: Overdue items or completed


  class TaskSelect(str, Enum):
      """Notion '선택' select property (D-05)."""
      ROUTINE = "루틴"  # Video lectures
      EVENT = "이벤트"    # Assignments, quizzes, exams, forums


  class TaskStatus(str, Enum):
      """Notion '상태' status property (D-10)."""
      NOT_STARTED = "시작 전"
      IN_PROGRESS = "진행 중"
      COMPLETED = "완료"
      DISCARDED = "폐기"


  class SyncTask(BaseModel):
      """Unified domain entity representing a schedulable task for Notion."""
      id: str
      course_id: str
      course_name: str
      course_abbr: str
      title: str
      raw_title: str
      task_type: TaskType
      selection: TaskSelect
      category: list[str] = Field(default_factory=lambda: ["학업"])
      due_date: datetime | None = None
      plan_date: datetime | None = None  # Always None by default (D-08)
      priority: TaskPriority
      status: TaskStatus = TaskStatus.NOT_STARTED  # D-10: '시작 전' even if overdue
      memo: str = ""
      is_completed: bool = False
      is_overdue: bool = False
      is_urgent: bool = False
      source_url: str = ""
      week_number: int | None = None
      clip_number: int | None = None

      @field_validator("due_date", "plan_date", mode="after")
      @classmethod
      def ensure_kst(cls, v: datetime | None) -> datetime | None:
          """Ensures that datetimes have KST timezone attached."""
          if v is not None and v.tzinfo is None:
              return v.replace(tzinfo=KST)
          return v

      @property
      def dedup_key(self) -> str:
          """Returns a stable deduplication key for Notion matching (Phase 4)."""
          due_str = self.due_date.strftime("%Y-%m-%d %H:%M") if self.due_date else "no_due"
          return f"{self.title}|{due_str}"


  class Course(BaseModel):
      """Domain model representing a course with its activities and tasks."""
      course_id: str
      name: str
      abbreviation: str
      url: str = ""
      term: str = ""
      lectures: list[LectureItem] = Field(default_factory=list)
      assessments: list[AssessmentItem] = Field(default_factory=list)
      tasks: list[SyncTask] = Field(default_factory=list)
  ```
- **Error Handling & Invariants:**
  - Pydantic v2 `BaseModel` guarantees typed schema validation on construction.
  - `@field_validator("due_date", "plan_date", mode="after")` protects against timezone-naive datetimes entering downstream Notion syncing.
  - `dedup_key` uses minute-level precision (`%Y-%m-%d %H:%M`) and clean `title` for stable page matching.

---

### 3.3 `src/coursepilot/domain/naming.py`
- **Role:** Utility / String Formatter
- **Analog:** [`src/coursepilot/course_mapping.py`](../../../src/coursepilot/course_mapping.py) (`get_abbreviation`) & [`src/coursepilot/scraper/lecture_parser.py`](../../../src/coursepilot/scraper/lecture_parser.py) (`clean_lecture_title`)
- **Data Flow:** Called by `transformer.py` to format standardized Notion task titles from raw scraped names.
- **Concrete Imports & Excerpt to Mirror:**
  ```python
  """Task naming rules and smart title cleaning engine (D-01 ~ D-04)."""

  import html
  import re

  from coursepilot.course_mapping import get_abbreviation
  from coursepilot.domain.models import TaskType


  def clean_task_title(raw_title: str) -> str:
      """Cleans activity title by unescaping HTML, normalizing whitespace, and removing redundant tags."""
      if not raw_title:
          return ""

      # 1. Unescape HTML entities (&amp; -> &, &#39; -> ', &nbsp; -> space, etc.)
      text = html.unescape(raw_title)
      text = text.replace("\xa0", " ")

      # 2. Strip redundant bracket tags at beginning
      # e.g., [과제], [숙제], [Assignment], [HW], [퀴즈], [Quiz], [토론], [Discussion]
      redundant_tag_pattern = (
          r"^\[\s*(?:과제|과제제출|숙제|Assignment|HW|H\.W|퀴즈|Quiz|쪽지시험|시험|Exam|토론|Forum|Discussion)\s*\]\s*"
      )
      text = re.sub(redundant_tag_pattern, "", text, flags=re.I)

      # 3. Normalize multiple whitespace
      text = re.sub(r"\s+", " ", text).strip()
      return text


  def extract_week_and_title(title: str) -> tuple[int | None, str]:
      """Extracts week number if present in the title and returns cleaned remainder title."""
      cleaned = clean_task_title(title)

      # Detect week pattern e.g. "3주차 과제", "3주차: 실습 1", "Week 4 Project"
      m_week = re.search(r"(?:제?\s*(\d+)\s*주차?|week\s*(\d+))\s*[:\-_]?\s*", cleaned, re.I)
      if m_week:
          week_num = int(m_week.group(1) or m_week.group(2))
          remainder = cleaned[:m_week.start()] + cleaned[m_week.end():]
          remainder = re.sub(r"\s+", " ", remainder).strip()
          if not remainder:
              remainder = "과제"
          return week_num, remainder

      return None, cleaned


  def format_task_title(
      course_name: str,
      raw_title: str,
      task_type: TaskType,
      week_number: int | None = None,
      clip_number: int | None = None,
      course_mappings: dict[str, str] | None = None,
  ) -> str:
      """Formats standardized task title according to user Notion scheduler conventions.

      Conventions:
        - Lecture: "[{과목약어}] {N}주차 {M}차시 강의 시청" (D-01)
        - Assignment: "[{과목약어}] {N}주차 {과제명} 제출" or "[{과목약어}] {과제명} 제출" (D-02, D-03)
        - Quiz: "[{과목약어}] {N}주차 [퀴즈] {이름} 응시" or "[{과목약어}] [퀴즈] {이름} 응시" (D-02, D-03)
        - Forum: "[{과목약어}] {N}주차 [토론] {이름} 참여" or "[{과목약어}] [토론] {이름} 참여" (D-02, D-03)
      """
      mappings = course_mappings if course_mappings is not None else {}
      abbr = get_abbreviation(course_name, mappings)

      # 1. Lecture: Fixed format (D-01)
      if task_type == TaskType.LECTURE:
          w = week_number if (week_number is not None and week_number > 0) else 1
          c = clip_number if (clip_number is not None and clip_number > 0) else 1
          return f"[{abbr}] {w}주차 {c}차시 강의 시청"

      # 2. Assessments: Assignment, Quiz, Forum (D-02, D-03)
      extracted_week, clean_name = extract_week_and_title(raw_title)
      effective_week = week_number if (week_number is not None and week_number > 0) else extracted_week

      # Clean redundant trailing verb if already in clean_name to avoid "제출 제출"
      clean_name = re.sub(r"\s*(?:제출|응시|참여|시청)$", "", clean_name).strip()
      if not clean_name:
          clean_name = "과제" if task_type == TaskType.ASSIGNMENT else "활동"

      week_prefix = f"{effective_week}주차 " if (effective_week is not None and effective_week > 0) else ""

      if task_type == TaskType.ASSIGNMENT:
          return f"[{abbr}] {week_prefix}{clean_name} 제출"
      elif task_type == TaskType.QUIZ:
          return f"[{abbr}] {week_prefix}[퀴즈] {clean_name} 응시"
      elif task_type == TaskType.FORUM:
          return f"[{abbr}] {week_prefix}[토론] {clean_name} 참여"
      else:
          return f"[{abbr}] {week_prefix}{clean_name} 제출"
  ```
- **Error Handling & Invariants:**
  - `get_abbreviation` safely falls back to the original course name if unmapped.
  - Trailing verb removal (`re.sub(r"\s*(?:제출|응시|참여|시청)$", "", clean_name)`) prevents embarrassing duplicate verbs (`제출 제출`).
  - Empty remainder fallback ensures title is never blank (falls back to `"과제"` or `"활동"`).

---

### 3.4 `src/coursepilot/domain/priority.py`
- **Role:** Business Logic / Rules Engine
- **Analog:** [`src/coursepilot/scraper/date_parser.py`](../../../src/coursepilot/scraper/date_parser.py) (`is_past_deadline`, `get_current_kst_time`, `KST`)
- **Data Flow:** Called by `transformer.py` during task generation to establish urgency and priority tags.
- **Concrete Imports & Excerpt to Mirror:**
  ```python
  """Urgency, priority determination, and Notion property mapper (D-05 ~ D-08)."""

  from datetime import datetime, timedelta

  from coursepilot.domain.models import TaskPriority, TaskSelect, TaskStatus, TaskType
  from coursepilot.scraper.date_parser import KST, get_current_kst_time


  def calculate_priority(
      task_type: TaskType,
      due_date: datetime | None,
      is_completed: bool = False,
      now: datetime | None = None,
  ) -> tuple[TaskPriority, bool, bool]:
      """Calculates task priority and status flags (D-06).

      Evaluation Order (Crucial):
        1. Completed -> P4, is_urgent=False, is_overdue=False
        2. No due date -> P3 (Lecture) or P2 (Assessment), is_urgent=False, is_overdue=False
        3. Past deadline (due_date < now) -> P4, is_urgent=False, is_overdue=True
        4. Imminent deadline (0 <= remaining <= 24h) -> P1, is_urgent=True, is_overdue=False
        5. Normal pending (> 24h) -> P3 (Lecture) or P2 (Assessment), is_urgent=False, is_overdue=False

      Returns:
          (priority, is_urgent, is_overdue)
      """
      if is_completed:
          return TaskPriority.P4, False, False

      if due_date is None:
          default_priority = TaskPriority.P3 if task_type == TaskType.LECTURE else TaskPriority.P2
          return default_priority, False, False

      current_time = now if now is not None else get_current_kst_time()
      if due_date.tzinfo is None:
          due_date = due_date.replace(tzinfo=KST)
      if current_time.tzinfo is None:
          current_time = current_time.replace(tzinfo=KST)

      # 1. Overdue: past deadline -> P4 (D-06)
      if due_date < current_time:
          return TaskPriority.P4, False, True

      # 2. Imminent: <= 24 hours -> P1 (DOMN-02, D-06)
      remaining_seconds = (due_date - current_time).total_seconds()
      if 0 <= remaining_seconds <= 24 * 3600:
          return TaskPriority.P1, True, False

      # 3. Normal pending tasks (> 24h)
      if task_type == TaskType.LECTURE:
          return TaskPriority.P3, False, False
      else:
          return TaskPriority.P2, False, False


  def get_task_selection(task_type: TaskType) -> TaskSelect:
      """Maps activity type to Notion '선택' property (D-05)."""
      if task_type == TaskType.LECTURE:
          return TaskSelect.ROUTINE
      return TaskSelect.EVENT
  ```
- **Error Handling & Invariants:**
  - Timezone alignment: Both `due_date` and `current_time` are explicitly verified to have `KST` timezone attached before subtraction, eliminating 9-hour UTC/KST offset bugs.
  - Exact ladder order prevents overdue items (`due_date < current_time`) from matching `remaining <= 24h` due to negative numbers.

---

### 3.5 `src/coursepilot/domain/transformer.py`
- **Role:** Domain Service / DTO Transformer
- **Analog:** [`src/coursepilot/scraper/assessment_parser.py`](../../../src/coursepilot/scraper/assessment_parser.py) & [`src/coursepilot/scraper/lecture_parser.py`](../../../src/coursepilot/scraper/lecture_parser.py)
- **Data Flow:** Ingests `CourseItem`, `LectureItem`, and `AssessmentItem` collections; outputs clean, sorted, filtered `list[SyncTask]`.
- **Concrete Imports & Excerpt to Mirror:**
  ```python
  """Scraper DTO to domain SyncTask transformer with memo building and deadline rescue (D-09 ~ D-15)."""

  from datetime import datetime
  import re

  from coursepilot.course_mapping import load_course_mappings
  from coursepilot.domain.models import Course, SyncTask, TaskPriority, TaskSelect, TaskStatus, TaskType
  from coursepilot.domain.naming import format_task_title
  from coursepilot.domain.priority import calculate_priority, get_task_selection
  from coursepilot.scraper.date_parser import parse_lms_date
  from coursepilot.scraper.models import (
      AssessmentItem,
      AssessmentType,
      AttendanceStatus,
      CourseItem,
      LectureItem,
      SubmissionStatus,
  )


  def extract_deadline_from_description(text: str) -> datetime | None:
      """Rescues deadline from assignment description when LMS has no formal due date (D-11)."""
      if not text:
          return None

      patterns = [
          r"(?:제출\s*기한|마감\s*일시|마감\s*기한|제출\s*마감)[:\s]*([0-9년월일\s\(\)\-./:~]+)",
          r"([0-9]{1,2}\s*월\s*[0-9]{1,2}\s*일[\s\(\)월화수목금토일]*\s*(?:자정|24시|23:59|[0-9]{1,2}:[0-9]{1,2}))\s*까지",
          r"([0-9]{4}[-./][0-9]{1,2}[-./][0-9]{1,2}\s+[0-9]{1,2}:[0-9]{1,2})\s*까지",
      ]

      for pat in patterns:
          m = re.search(pat, text, re.I)
          if m:
              date_snippet = m.group(1).strip()
              date_snippet = re.sub(r"(?:자정|24시)", "23:59:59", date_snippet)
              parsed_dt, _ = parse_lms_date(date_snippet)
              if parsed_dt:
                  return parsed_dt

      return None


  def format_memo(
      task_type: TaskType,
      url: str = "",
      cutoff_date: datetime | None = None,
      attachments: list | None = None,
      description_text: str = "",
  ) -> str:
      """Builds structured Notion memo payload with 1500-char safe truncation (D-12 ~ D-14)."""
      # Lecture: concise single line (D-12)
      if task_type == TaskType.LECTURE:
          return f"LMS 바로가기: {url}" if url else ""

      sections: list[str] = []

      # 1. LMS Link
      if url:
          sections.append(f"LMS 바로가기: {url}")

      # 2. Cutoff Date
      if cutoff_date:
          cutoff_str = cutoff_date.strftime("%Y-%m-%d %H:%M:%S (KST)")
          sections.append(f"지각 제출 마감: {cutoff_str}")

      # 3. Attachments
      if attachments:
          att_lines = ["첨부파일:"]
          for att in attachments:
              size_str = f" ({att.filesize})" if getattr(att, "filesize", "") else ""
              att_lines.append(f"- {att.filename}{size_str}: {att.url}")
          sections.append("\n".join(att_lines))

      # 4. Description with safe 1500-char truncation (D-14)
      if description_text:
          cleaned_desc = description_text.strip()
          if len(cleaned_desc) > 1500:
              cleaned_desc = cleaned_desc[:1500] + "\n... [이하 생략 - 전체 내용은 LMS 페이지 참조]"
          sections.append(f"과제 안내:\n{cleaned_desc}")

      memo_text = "\n\n".join(sections).strip()
      # Hard safety cap under Notion 2000-char limit
      if len(memo_text) > 1950:
          memo_text = memo_text[:1900] + "\n... [내용 초과 절삭]"
      return memo_text


  def transform_lecture_to_task(
      course: CourseItem,
      lecture: LectureItem,
      mappings: dict[str, str],
      now: datetime | None = None,
  ) -> SyncTask | None:
      """Transforms LectureItem to SyncTask. Excludes open/OT videos without deadline (D-11)."""
      if lecture.due_date is None:
          return None

      is_completed = (lecture.status == AttendanceStatus.COMPLETED)
      priority, is_urgent, is_overdue = calculate_priority(
          task_type=TaskType.LECTURE,
          due_date=lecture.due_date,
          is_completed=is_completed,
          now=now,
      )

      title = format_task_title(
          course_name=course.clean_name,
          raw_title=lecture.title,
          task_type=TaskType.LECTURE,
          week_number=lecture.week_number,
          clip_number=lecture.clip_number,
          course_mappings=mappings,
      )

      memo = format_memo(TaskType.LECTURE, url=lecture.link)

      return SyncTask(
          id=f"lec_{course.course_id}_{lecture.week_number}_{lecture.clip_number}",
          course_id=course.course_id,
          course_name=course.clean_name,
          course_abbr=mappings.get(course.clean_name, course.clean_name),
          title=title,
          raw_title=lecture.title,
          task_type=TaskType.LECTURE,
          selection=TaskSelect.ROUTINE,
          category=["학업"],
          due_date=lecture.due_date,
          priority=priority,
          status=TaskStatus.COMPLETED if is_completed else TaskStatus.NOT_STARTED,
          memo=memo,
          is_completed=is_completed,
          is_overdue=is_overdue,
          is_urgent=is_urgent,
          source_url=lecture.link,
          week_number=lecture.week_number,
          clip_number=lecture.clip_number,
      )


  def transform_assessment_to_task(
      course: CourseItem,
      assessment: AssessmentItem,
      mappings: dict[str, str],
      now: datetime | None = None,
  ) -> SyncTask | None:
      """Transforms AssessmentItem to SyncTask with deadline rescue (D-11)."""
      due_date = assessment.due_date
      if due_date is None:
          due_date = extract_deadline_from_description(assessment.description_text)

      type_map = {
          AssessmentType.ASSIGNMENT: TaskType.ASSIGNMENT,
          AssessmentType.QUIZ: TaskType.QUIZ,
          AssessmentType.FORUM: TaskType.FORUM,
      }
      task_type = type_map.get(assessment.item_type, TaskType.ASSIGNMENT)

      is_completed = assessment.status in (SubmissionStatus.SUBMITTED, SubmissionStatus.GRADED)
      priority, is_urgent, is_overdue = calculate_priority(
          task_type=task_type,
          due_date=due_date,
          is_completed=is_completed,
          now=now,
      )

      title = format_task_title(
          course_name=course.clean_name,
          raw_title=assessment.title,
          task_type=task_type,
          course_mappings=mappings,
      )

      memo = format_memo(
          task_type=task_type,
          url=assessment.url,
          cutoff_date=assessment.cutoff_date,
          attachments=assessment.attachments,
          description_text=assessment.description_text,
      )

      return SyncTask(
          id=f"assess_{course.course_id}_{assessment.item_id}",
          course_id=course.course_id,
          course_name=course.clean_name,
          course_abbr=mappings.get(course.clean_name, course.clean_name),
          title=title,
          raw_title=assessment.title,
          task_type=task_type,
          selection=TaskSelect.EVENT,
          category=["학업"],
          due_date=due_date,
          priority=priority,
          status=TaskStatus.COMPLETED if is_completed else TaskStatus.NOT_STARTED,
          memo=memo,
          is_completed=is_completed,
          is_overdue=is_overdue,
          is_urgent=is_urgent,
          source_url=assessment.url,
      )


  def transform_to_sync_tasks(
      courses: list[CourseItem],
      lectures_by_course: dict[str, list[LectureItem]],
      assessments_by_course: dict[str, list[AssessmentItem]],
      include_completed: bool = False,
      mappings: dict[str, str] | None = None,
      now: datetime | None = None,
  ) -> list[SyncTask]:
      """Transforms all collected course activities into normalized SyncTasks (D-09).

      Sorts resulting tasks by due_date (earliest first, None last).
      """
      active_mappings = mappings if mappings is not None else load_course_mappings()
      tasks: list[SyncTask] = []

      for course in courses:
          cid = course.course_id

          for lec in lectures_by_course.get(cid, []):
              task = transform_lecture_to_task(course, lec, active_mappings, now=now)
              if task is not None:
                  if include_completed or not task.is_completed:
                      tasks.append(task)

          for assess in assessments_by_course.get(cid, []):
              task = transform_assessment_to_task(course, assess, active_mappings, now=now)
              if task is not None:
                  if include_completed or not task.is_completed:
                      tasks.append(task)

      # Sort: earliest deadline first, tasks without deadline last
      tasks.sort(
          key=lambda t: (
              t.due_date is None,
              t.due_date or datetime.max.replace(tzinfo=t.due_date.tzinfo if t.due_date else None),
          )
      )
      return tasks
  ```
- **Error Handling & Invariants:**
  - Filtering: OT/open lectures without due dates return `None` and are excluded from scheduler tasks.
  - Deadline rescue: Assignment descriptions are scanned with keyword-bounded regexes; if no date is found, `due_date` stays `None` without crashing.
  - Safe truncation: Description capped at 1500 chars, total memo capped at 1950 chars, preventing Notion API `validation_error` (HTTP 400).
  - Sorting: Tuple key `(t.due_date is None, t.due_date)` reliably places valid datetimes in chronological order followed by `None` deadlines at the end.

---

## 4. Test Suite Blueprints & Verification Map

### 4.1 `tests/test_domain_models.py`
- **Analog:** [`tests/test_scraper_models.py`](../../../tests/test_scraper_models.py)
- **Key Patterns to Mirror:**
  ```python
  from datetime import datetime, timezone
  import pytest
  from pydantic import ValidationError

  from coursepilot.domain.models import (
      Course,
      SyncTask,
      TaskPriority,
      TaskSelect,
      TaskStatus,
      TaskType,
  )
  from coursepilot.scraper.date_parser import KST


  def test_task_enums():
      assert TaskType.LECTURE == "lecture"
      assert TaskPriority.P1 == "P1"
      assert TaskSelect.ROUTINE == "루틴"
      assert TaskSelect.EVENT == "이벤트"
      assert TaskStatus.NOT_STARTED == "시작 전"


  def test_sync_task_creation_and_defaults():
      task = SyncTask(
          id="task_1",
          course_id="10101",
          course_name="공학수학2",
          course_abbr="공수2",
          title="[공수2] 3주차 1차시 강의 시청",
          raw_title="1차시: 미분방정식",
          task_type=TaskType.LECTURE,
          selection=TaskSelect.ROUTINE,
          priority=TaskPriority.P3,
      )
      assert task.category == ["학업"]
      assert task.plan_date is None  # D-08
      assert task.status == TaskStatus.NOT_STARTED  # D-10
      assert task.is_completed is False
      assert task.dedup_key == "[공수2] 3주차 1차시 강의 시청|no_due"


  def test_sync_task_kst_enforcement():
      # Naive datetime should automatically receive KST timezone
      naive_dt = datetime(2026, 9, 25, 23, 59, 0)
      task = SyncTask(
          id="task_2",
          course_id="10101",
          course_name="공학수학2",
          course_abbr="공수2",
          title="[공수2] 3주차 과제 제출",
          raw_title="3주차 과제",
          task_type=TaskType.ASSIGNMENT,
          selection=TaskSelect.EVENT,
          due_date=naive_dt,
          priority=TaskPriority.P2,
      )
      assert task.due_date.tzinfo == KST
      assert task.dedup_key == "[공수2] 3주차 과제 제출|2026-09-25 23:59"
  ```

---

### 4.2 `tests/test_naming.py`
- **Analog:** [`tests/test_course_mapping.py`](../../../tests/test_course_mapping.py)
- **Key Patterns to Mirror:**
  ```python
  import pytest
  from coursepilot.domain.models import TaskType
  from coursepilot.domain.naming import clean_task_title, extract_week_and_title, format_task_title

  MAPPINGS = {"공학수학2": "공수2", "자료구조": "자구"}


  def test_lecture_naming_convention():
      # D-01: "[{과목약어}] {N}주차 {M}차시 강의 시청"
      title = format_task_title("공학수학2", "1차시: 라플라스", TaskType.LECTURE, week_number=3, clip_number=1, course_mappings=MAPPINGS)
      assert title == "[공수2] 3주차 1차시 강의 시청"


  def test_assignment_naming_conventions():
      # D-02: "[{과목약어}] {N}주차 {과제명} 제출"
      title = format_task_title("공학수학2", "행렬 연산 과제", TaskType.ASSIGNMENT, week_number=3, course_mappings=MAPPINGS)
      assert title == "[공수2] 3주차 행렬 연산 과제 제출"

      # D-03: Fallback without week
      title_no_week = format_task_title("자료구조", "기말 프로젝트", TaskType.ASSIGNMENT, course_mappings=MAPPINGS)
      assert title_no_week == "[자구] 기말 프로젝트 제출"


  def test_quiz_and_forum_naming_conventions():
      # D-02: Quiz -> [퀴즈], Forum -> [토론]
      q_title = format_task_title("공학수학2", "쪽지시험", TaskType.QUIZ, week_number=2, course_mappings=MAPPINGS)
      assert q_title == "[공수2] 2주차 [퀴즈] 쪽지시험 응시"

      f_title = format_task_title("자료구조", "알고리즘 토론", TaskType.FORUM, course_mappings=MAPPINGS)
      assert f_title == "[자구] [토론] 알고리즘 토론 참여"


  def test_smart_title_cleaning():
      # D-04: HTML entity decoding & tag stripping
      assert clean_task_title("과제 &amp; 실습 #1") == "과제 & 실습 #1"
      assert clean_task_title("[과제] 2주차 연습문제") == "2주차 연습문제"
      assert clean_task_title("[HW]   네트워크 프로그래밍   ") == "네트워크 프로그래밍"


  def test_double_verb_prevention():
      # Prevent "제출 제출"
      title = format_task_title("공학수학2", "과제 1차 제출", TaskType.ASSIGNMENT, week_number=1, course_mappings=MAPPINGS)
      assert title == "[공수2] 1주차 과제 1차 제출"
  ```

---

### 4.3 `tests/test_priority.py`
- **Analog:** [`tests/test_date_parser.py`](../../../tests/test_date_parser.py) (`test_is_past_deadline`)
- **Key Patterns to Mirror:**
  ```python
  from datetime import datetime, timedelta
  from coursepilot.domain.models import TaskPriority, TaskSelect, TaskType
  from coursepilot.domain.priority import calculate_priority, get_task_selection
  from coursepilot.scraper.date_parser import KST


  def test_urgent_24h_boundary():
      now = datetime(2026, 9, 21, 12, 0, 0, tzinfo=KST)

      # Case 1: 10 hours remaining -> P1, urgent (DOMN-02)
      due_10h = now + timedelta(hours=10)
      pri, urgent, overdue = calculate_priority(TaskType.ASSIGNMENT, due_10h, now=now)
      assert pri == TaskPriority.P1
      assert urgent is True
      assert overdue is False

      # Case 2: Exactly 24 hours remaining -> P1, urgent
      due_24h = now + timedelta(hours=24)
      pri, urgent, overdue = calculate_priority(TaskType.ASSIGNMENT, due_24h, now=now)
      assert pri == TaskPriority.P1
      assert urgent is True

      # Case 3: 24 hours + 1 minute -> P2 (Normal assignment)
      due_24h1m = now + timedelta(hours=24, minutes=1)
      pri, urgent, overdue = calculate_priority(TaskType.ASSIGNMENT, due_24h1m, now=now)
      assert pri == TaskPriority.P2
      assert urgent is False


  def test_overdue_and_completed_priorities():
      now = datetime(2026, 9, 21, 12, 0, 0, tzinfo=KST)

      # Overdue item -> P4, overdue=True, urgent=False (D-06)
      past_due = now - timedelta(hours=2)
      pri, urgent, overdue = calculate_priority(TaskType.LECTURE, past_due, now=now)
      assert pri == TaskPriority.P4
      assert overdue is True
      assert urgent is False

      # Completed item -> P4
      pri, urgent, overdue = calculate_priority(TaskType.ASSIGNMENT, past_due, is_completed=True, now=now)
      assert pri == TaskPriority.P4
      assert urgent is False


  def test_selection_mapping():
      # D-05: Lecture -> 루틴, Others -> 이벤트
      assert get_task_selection(TaskType.LECTURE) == TaskSelect.ROUTINE
      assert get_task_selection(TaskType.ASSIGNMENT) == TaskSelect.EVENT
      assert get_task_selection(TaskType.QUIZ) == TaskSelect.EVENT
  ```

---

### 4.4 `tests/test_transformer.py`
- **Analog:** [`tests/test_assessment_parser.py`](../../../tests/test_assessment_parser.py) & [`tests/test_lecture_parser.py`](../../../tests/test_lecture_parser.py)
- **Key Patterns to Mirror:**
  ```python
  from datetime import datetime
  import pytest

  from coursepilot.domain.models import TaskPriority, TaskSelect, TaskStatus, TaskType
  from coursepilot.domain.transformer import (
      extract_deadline_from_description,
      format_memo,
      transform_assessment_to_task,
      transform_lecture_to_task,
      transform_to_sync_tasks,
  )
  from coursepilot.scraper.date_parser import KST
  from coursepilot.scraper.models import (
      AssessmentItem,
      AssessmentType,
      AttachmentMeta,
      AttendanceStatus,
      CourseItem,
      LectureItem,
      SubmissionStatus,
  )


  @pytest.fixture
  def sample_course():
      return CourseItem(
          course_id="10101",
          raw_name="공학수학2(01분반)",
          clean_name="공학수학2",
          url="https://canvas.kau.ac.kr/course/view.php?id=10101",
      )


  def test_transform_lecture_excluding_no_due_date(sample_course):
      # D-11: OT/open lectures without due date should be excluded (return None)
      lec_no_due = LectureItem(
          course_id="10101",
          week_number=1,
          clip_number=1,
          title="오리엔테이션",
          full_title="[공수2] 1주차 1차시: 오리엔테이션",
          status=AttendanceStatus.INCOMPLETE,
          due_date=None,
      )
      task = transform_lecture_to_task(sample_course, lec_no_due, {"공학수학2": "공수2"})
      assert task is None


  def test_deadline_rescue_from_description():
      # D-11: Rescue date from contextual Korean description
      desc = "본 과제는 LMS 제출이 불가하므로 2026-10-15 23:59까지 담당 조교 이메일로 제출 바랍니다."
      rescued_dt = extract_deadline_from_description(desc)
      assert rescued_dt == datetime(2026, 10, 15, 23, 59, 0, tzinfo=KST)


  def test_format_memo_truncation():
      # D-14: Truncate >1500 chars safely
      long_text = "A" * 2000
      memo = format_memo(TaskType.ASSIGNMENT, url="https://link.com", description_text=long_text)
      assert "... [이하 생략 - 전체 내용은 LMS 페이지 참조]" in memo
      assert len(memo) <= 1950


  def test_transform_to_sync_tasks_filtering_and_sorting(sample_course):
      # D-09: Filter completed tasks and sort by due_date ascending
      due_early = datetime(2026, 9, 22, 23, 59, 0, tzinfo=KST)
      due_late = datetime(2026, 9, 28, 23, 59, 0, tzinfo=KST)

      lec_incomplete = LectureItem(
          course_id="10101",
          week_number=3,
          clip_number=1,
          title="3주차 1차시",
          full_title="[공수2] 3주차 1차시",
          status=AttendanceStatus.INCOMPLETE,
          due_date=due_late,
      )
      lec_completed = LectureItem(
          course_id="10101",
          week_number=2,
          clip_number=1,
          title="2주차 1차시",
          full_title="[공수2] 2주차 1차시",
          status=AttendanceStatus.COMPLETED,
          due_date=due_early,
      )
      assess_pending = AssessmentItem(
          course_id="10101",
          item_id="99",
          item_type=AssessmentType.ASSIGNMENT,
          title="과제 2",
          status=SubmissionStatus.NOT_ATTEMPTED,
          due_date=due_early,
      )

      tasks = transform_to_sync_tasks(
          courses=[sample_course],
          lectures_by_course={"10101": [lec_incomplete, lec_completed]},
          assessments_by_course={"10101": [assess_pending]},
          include_completed=False,
          mappings={"공학수학2": "공수2"},
      )

      assert len(tasks) == 2  # Completed lecture is excluded
      assert tasks[0].due_date == due_early  # Earliest first
      assert tasks[1].due_date == due_late
  ```

---

## 5. Architectural Invariants & Don't Hand-Roll Rules

1. **No Direct `os.environ` or Hardcoded Paths:**
   - Configuration and mappings must always go through `coursepilot.course_mapping.load_course_mappings()`.
2. **Pure Domain Isolation:**
   - Modules in `src/coursepilot/domain/` must **never** import `playwright`, `httpx`, or any networking libraries.
   - Any external dependency is restricted to standard library (`datetime`, `re`, `html`, `enum`, `zoneinfo`) and `pydantic` / `beautifulsoup4`.
3. **Double-Verb & Double-Bracket Prevention:**
   - Always run raw titles through `clean_task_title()` before formatting.
   - Always strip trailing activity verbs (`제출`, `응시`, `참여`, `시청`) before applying template suffixes.
4. **Notion Character Limit Defense:**
   - Notion API `rich_text` throws 400 if length exceeds 2000 chars.
   - Description text must be sliced at 1500 chars with ellipsis, and overall `memo` must have an absolute hard clamp at 1950 chars.
5. **KST Timezone Attachment:**
   - Naive datetimes are strictly disallowed. All datetime fields in `SyncTask` are validated and enriched with `KST` (`Asia/Seoul`, UTC+9).

---

*Phase: 03-domain-modeling-naming-rules*  
*Patterns mapped: 2026-09-21*  
