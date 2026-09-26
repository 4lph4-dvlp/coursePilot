# Phase 16: Comprehensive Activity Progress Dashboard - Pattern Map

## Summary

Phase 16 introduces a multi-tier academic activity progress dashboard (`coursepilot progress`) tracking the 4 core learning activities: Video Lectures (VOD), Assignments, Quizzes, and Learning Materials.

To ensure consistency and high code quality, new code directly mirrors established patterns in the codebase:
- **Models & Contracts:** Follows `src/coursepilot/board/models.py` and `src/coursepilot/report_models.py` using Pydantic `BaseModel` with `ConfigDict(extra="forbid")` and explicit `schema_version: Literal[1] = 1`.
- **Parsing Enhancement:** Extends `src/coursepilot/scraper/models.py` (`AssessmentItem`) and `src/coursepilot/scraper/assessment_parser.py` (`parse_assessment_list`) with backward-compatible `week_number` extraction based on existing table header parsing.
- **Calculator Logic:** Pure functional engine in `src/coursepilot/progress/calculator.py` mirroring `src/coursepilot/scraper/lecture_parser.py` for date/section parsing and `src/coursepilot/reporter.py` for KPI aggregation.
- **Runner & Caching:** Orchestrator in `src/coursepilot/progress/runner.py` adopting `src/coursepilot/board/runner.py` for session management and error isolation, `src/coursepilot/materials/downloader.py` for authenticated HTTP client retrieval, and an atomic 10-minute file cache (`progress_cache.json`).
- **Rich Reporting:** Terminal renderer in `src/coursepilot/progress/reporter.py` drawing on `src/coursepilot/reporter.py` and `src/coursepilot/board/reporter.py` for 3-tier layouts (Summary table with color-coded progress bars, Action items To-Do list, Alert / All-Clear badge panel).
- **CLI Commands:** Integration in `src/coursepilot/cli.py` mirroring `board_command` and `materials_command` with clean stream separation (stderr spinners, stdout reports/JSON).
- **Testing Suite:** Comprehensive pytest tests covering models, calculation math, runner mocks, reporter rendering, and CLI invocation mirroring `test_board_runner.py` and `test_cli_board.py`.

---

## File Classification & Analogs

| File | Role | Data Flow | Closest Analog | Key Differences / Additions |
|---|---|---|---|---|
| `src/coursepilot/scraper/models.py` | Scraper DTO | LMS HTML -> AssessmentItem | `AssessmentItem` (same file) | Adds `week_number: int \| None = None` to store parsed week metadata. |
| `src/coursepilot/scraper/assessment_parser.py` | Scraper Parser | HTML table -> `list[AssessmentItem]` | `parse_assessment_list` (same file) | Detects `"주차"`, `"주"`, `"Week"` header columns and parses `week_number`. |
| `src/coursepilot/progress/models.py` | Progress DTO & Contract | Activity collections -> JSON / CLI | `src/coursepilot/board/models.py` | Models 4-tier activity counts, dual progress rates, and `ProgressReport` (`schema_version: 1`). |
| `src/coursepilot/progress/calculator.py` | Calculation Engine | Raw activities -> Metric aggregations | `src/coursepilot/scraper/lecture_parser.py` & `src/coursepilot/reporter.py` | Hybrid current week detection, open vs semester rates, past-weeks missed accounting. |
| `src/coursepilot/progress/runner.py` | Pipeline & Cache Orchestrator | LMS HTTP / Cache -> Unified Progress | `src/coursepilot/board/runner.py` | Single-trip HTML scraping (VOD + materials), atomic 10m TTL cache, course error isolation. |
| `src/coursepilot/progress/reporter.py` | Terminal Visualizer | `ProgressReport` -> Rich Terminal UI | `src/coursepilot/board/reporter.py` & `src/coursepilot/reporter.py` | 3-tier view: Color progress bar table, To-Do list with tags, Alert/All Clear badges, week matrix. |
| `src/coursepilot/cli.py` | CLI Command | CLI flags -> Runner -> Output | `materials_command` & `board_command` | Implements `@cli.command("progress")` with `--course`, `--week`, `--detail`, `--cached`, `--refresh`, `--json`. |
| `tests/test_progress_models.py` | Model Unit Tests | Pydantic validation & JSON roundtrip | `tests/test_material_models.py` | Tests `ActivityBreakdown`, `CourseProgress`, and `ProgressReport` contract. |
| `tests/test_progress_calculator.py` | Engine Unit Tests | Synthetic items -> Calculated metrics | `tests/test_priority.py` & `tests/test_lecture_parser.py` | Tests week detection, dual rates, past missed items, and Week 1 edge cases. |
| `tests/test_progress_runner.py` | Pipeline Mock Tests | Mock HTTP / HTML fixtures -> Report | `tests/test_board_runner.py` | Tests single-trip scraping, cache TTL expiration, `--refresh`, and error isolation. |
| `tests/test_progress_reporter.py` | UI Unit Tests | `ProgressReport` -> Rich Console buffer | `tests/test_reporter.py` | Verifies color thresholds, To-Do ordering, Alert vs All-Clear panels, and matrix output. |
| `tests/test_cli_progress.py` | CLI Integration Tests | CliRunner -> CLI command execution | `tests/test_cli_board.py` | Tests flags, stderr/stdout stream separation, JSON contract, and exit codes (0, 1, 2). |

---

## Concrete Code Excerpts

### 1. `src/coursepilot/scraper/models.py`
**Analog:** Existing `AssessmentItem` in `src/coursepilot/scraper/models.py`.

```python
# In src/coursepilot/scraper/models.py:
class AssessmentItem(BaseModel):
    """Assessment item (assignment, quiz, exam, discussion) in LMS."""

    course_id: str
    item_id: str
    item_type: AssessmentType
    title: str
    description_html: str = ""
    description_text: str = ""
    attachments: list[AttachmentMeta] = Field(default_factory=list)
    status: SubmissionStatus
    due_date: datetime | None = None
    cutoff_date: datetime | None = None
    raw_due_date: str = ""
    url: str = ""
    is_overdue: bool = False
    week_number: int | None = None  # Added for Phase 16 activity tracking
```

### 2. `src/coursepilot/scraper/assessment_parser.py`
**Analog:** Existing `parse_assessment_list` in `src/coursepilot/scraper/assessment_parser.py`.

```python
# Header column detection in parse_assessment_list:
    if header_row:
        for idx, cell in enumerate(header_row.find_all(["th", "td"])):
            txt = cell.get_text(strip=True)
            if "due" not in col_map and any(k in txt for k in ("마감", "종료", "Due")):
                col_map["due"] = idx
            elif "submission" not in col_map and any(k in txt for k in ("제출", "Status")):
                col_map["submission"] = idx
            elif "grade" not in col_map and any(k in txt for k in ("채점", "성적", "Grade")):
                col_map["grade"] = idx
            elif "title" not in col_map and any(k in txt for k in ("이름", "과제", "퀴즈", "토론", "시험", "제목", "활동", "Name")):
                col_map["title"] = idx
            elif "week" not in col_map and any(k in txt for k in ("주차", "주", "Week")):
                col_map["week"] = idx

    col_week = col_map.get("week")

# In row extraction loop:
    for tr in rows:
        cells = tr.find_all(["td", "th"])
        if len(cells) < 2:
            continue

        # Extract week number if column exists
        week_number: int | None = None
        if col_week is not None and col_week < len(cells):
            raw_week = cells[col_week].get_text(strip=True)
            m_week = re.search(r"(\d+)", raw_week)
            if m_week:
                week_number = int(m_week.group(1))

        # ... (title, due_date, status extraction) ...

        item = AssessmentItem(
            course_id=course_id,
            item_id=item_id,
            item_type=item_type,
            title=raw_title,
            status=status,
            due_date=due_date,
            raw_due_date=raw_due_date,
            url=link,
            is_overdue=is_overdue,
            week_number=week_number,
        )
        items.append(item)
```

### 3. `src/coursepilot/progress/models.py`
**Analog:** `src/coursepilot/board/models.py` and `src/coursepilot/report_models.py`.

```python
"""Domain models and versioned JSON contract (schema_version: 1) for activity progress dashboard."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from coursepilot.report_models import ErrorItem, ReportNotice

SCHEMA_VERSION: Literal[1] = 1


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
    command: Literal["progress"] = "progress"
    status: Literal["success", "partial_success", "error"]
    generated_at: datetime
    is_cached: bool = False
    summary: DashboardSummary
    courses: list[CourseProgress]
    errors: list[ErrorItem] = Field(default_factory=list)
    notices: list[ReportNotice] = Field(default_factory=list)
```

### 4. `src/coursepilot/progress/calculator.py`
**Analog:** Logic pattern in `src/coursepilot/scraper/lecture_parser.py` and `src/coursepilot/reporter.py`.

```python
"""Progress calculation engine for multi-tier activity completion."""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict

from coursepilot.progress.models import (
    ActivityBreakdown,
    ActivityCount,
    ActivityItem,
    ActivityType,
    CourseProgress,
    DashboardSummary,
)
from coursepilot.scraper.date_parser import get_current_kst_time


class SectionMeta(BaseModel):
    """Section metadata extracted from course home HTML."""
    model_config = ConfigDict(extra="forbid")

    week_number: int
    title: str = ""
    start_date: datetime | None = None
    end_date: datetime | None = None
    is_current: bool = False


def detect_current_week(sections: list[SectionMeta], now: datetime | None = None) -> int:
    """Determines current week using hybrid 3-step logic (D-16-02)."""
    current_time = now or get_current_kst_time()

    # Step 1: Current date matches section date range
    for sec in sections:
        if sec.start_date and sec.end_date and sec.start_date <= current_time <= sec.end_date:
            if sec.week_number > 0:
                return sec.week_number

    # Step 2: Section has LMS .current active class
    for sec in sections:
        if sec.is_current and sec.week_number > 0:
            return sec.week_number

    # Step 3: Fallback to lowest positive week, or 1
    valid_weeks = [sec.week_number for sec in sections if sec.week_number > 0]
    return min(valid_weeks) if valid_weeks else 1


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

    # 3. Past Weeks Cumulative Rate (D-16-03, Pitfall 1: current_week == 1 -> no past)
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


def aggregate_dashboard_summary(courses: list[CourseProgress]) -> DashboardSummary:
    """Aggregates summary KPI metrics across all courses."""
    valid_courses = [c for c in courses if c.status == "ok"]
    total_courses = len(courses)

    open_comp = sum(c.current_open_completed for c in valid_courses)
    open_tot = sum(c.current_open_total for c in valid_courses)
    open_rate = round(open_comp / open_tot * 100.0, 1) if open_tot > 0 else 100.0

    past_comp = sum(c.past_weeks_completed for c in valid_courses)
    past_tot = sum(c.past_weeks_total for c in valid_courses)
    past_rate = round(past_comp / past_tot * 100.0, 1) if past_tot > 0 else 100.0

    sem_comp = sum(c.semester_completed for c in valid_courses)
    sem_tot = sum(c.semester_total for c in valid_courses)
    sem_rate = round(sem_comp / sem_tot * 100.0, 1) if sem_tot > 0 else 100.0

    missed_count = sum(len(c.missed_past_items) for c in valid_courses)
    todo_count = sum(sum(1 for a in c.current_week_items if not a.is_completed) for c in valid_courses)

    # Aggregate breakdown
    all_open_items = [
        item
        for c in valid_courses
        for item in c.all_items
        if item.week_number <= c.current_week
    ]
    totals_breakdown = compute_breakdown(all_open_items)

    return DashboardSummary(
        total_courses=total_courses,
        current_open_rate=open_rate,
        current_open_completed=open_comp,
        current_open_total=open_tot,
        past_weeks_rate=past_rate,
        past_weeks_completed=past_comp,
        past_weeks_total=past_tot,
        semester_overall_rate=sem_rate,
        semester_completed=sem_comp,
        semester_total=sem_tot,
        missed_past_count=missed_count,
        current_week_todo_count=todo_count,
        activity_totals=totals_breakdown,
    )
```

### 5. `src/coursepilot/progress/runner.py`
**Analog:** Orchestrator in `src/coursepilot/board/runner.py` and `src/coursepilot/materials/downloader.py`.

```python
"""Progress collection pipeline and 10-minute cache orchestrator."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
import re
from typing import Callable
from bs4 import BeautifulSoup
import httpx

from coursepilot.config import Settings, get_settings
from coursepilot.course_mapping import load_course_mappings
from coursepilot.materials.downloader import get_authenticated_httpx_client
from coursepilot.player.runner import find_target_course
from coursepilot.progress.calculator import (
    SectionMeta,
    aggregate_dashboard_summary,
    calculate_course_progress,
    detect_current_week,
)
from coursepilot.progress.models import (
    ActivityItem,
    ActivityType,
    CourseProgress,
    ProgressReport,
)
from coursepilot.report_models import ErrorItem
from coursepilot.scraper.assessment_parser import (
    enrich_assessment_detail,
    is_quiz_attempt_completed,
    parse_assessment_list,
)
from coursepilot.scraper.course_list import extract_courses
from coursepilot.scraper.date_parser import get_current_kst_time, parse_lms_date
from coursepilot.scraper.lecture_parser import (
    _parse_week_number,
    merge_lecture_progress,
    parse_lectures_from_course_sections,
    parse_ublogs_completion,
)
from coursepilot.scraper.material_parser import parse_materials_from_course_sections
from coursepilot.scraper.models import (
    AssessmentType,
    AttendanceStatus,
    SubmissionStatus,
)
from coursepilot.session_manager import SessionManager

logger = logging.getLogger(__name__)
CACHE_TTL_SECONDS = 600  # 10 minutes


def load_progress_cache(cache_path: Path, max_age_seconds: int = CACHE_TTL_SECONDS) -> ProgressReport | None:
    """Loads cached progress report if present and within TTL (D-16-14)."""
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
    """Atomically writes progress report to local cache file using .tmp file (Claude's discretion)."""
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_file = cache_path.with_suffix(".tmp")
        tmp_file.write_text(report.model_dump_json(indent=2), encoding="utf-8")
        tmp_file.replace(cache_path)
    except Exception as e:
        logger.warning("Failed to save progress cache: %s", e)


def extract_course_sections_meta(html: str) -> list[SectionMeta]:
    """Single-trip helper: parses section numbers, titles, dates, and .current class (D-16-02, D-16-13)."""
    soup = BeautifulSoup(html, "lxml")
    sections_meta: list[SectionMeta] = []

    candidate_sections = soup.find_all(
        lambda tag: tag.name == "li"
        and (
            any(cls in ("section", "course-section") for cls in tag.get("class", []))
            or (tag.get("id") and re.match(r"^section-\d+$", tag.get("id")))
        )
    )
    candidate_set = set(candidate_sections)
    top_sections = [
        sec for sec in candidate_sections
        if not any(parent in candidate_set for parent in sec.parents)
    ]

    for sec_idx, sec in enumerate(top_sections):
        classes = sec.get("class", [])
        is_current = "current" in classes or "current-section" in classes

        sec_heading = sec.find(class_=re.compile(r"sectionname|section-title", re.I)) or sec.find(["h3", "h4", "h5"])
        title = sec_heading.get_text(strip=True) if sec_heading else ""
        week_num = _parse_week_number(title, default=None)
        if week_num is None:
            sec_id = sec.get("id", "")
            id_m = re.search(r"section-(\d+)", sec_id)
            week_num = int(id_m.group(1)) if id_m else sec_idx

        # Date parsing from subtitle / text-ubstrap
        start_date: datetime | None = None
        end_date: datetime | None = None
        period_el = sec.find(class_=re.compile(r"text-ubstrap|period|date", re.I))
        if period_el:
            start_date, end_date = parse_lms_date(period_el.get_text(strip=True))

        sections_meta.append(
            SectionMeta(
                week_number=week_num,
                title=title,
                start_date=start_date,
                end_date=end_date,
                is_current=is_current,
            )
        )

    return sections_meta
```

### 6. `src/coursepilot/progress/reporter.py`
**Analog:** `src/coursepilot/reporter.py` and `src/coursepilot/board/reporter.py`.

```python
"""Rich Console visualizer for 3-tier comprehensive activity progress dashboard."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.progress_bar import ProgressBar
from rich.table import Table
from rich.text import Text

from coursepilot.progress.models import CourseProgress, ProgressReport
from coursepilot.reporter import format_remaining
from coursepilot.scraper.date_parser import get_current_kst_time


def _get_rate_style(rate: float) -> str:
    """Returns Rich color style based on completion rate thresholds (D-16-06)."""
    if rate >= 100.0:
        return "bold green"
    if rate >= 80.0:
        return "bold blue"
    if rate >= 50.0:
        return "bold yellow"
    return "bold red"


def render_progress_dashboard(
    report: ProgressReport,
    console: Console,
    detail: bool = False,
    now: datetime | None = None,
) -> None:
    """Renders the 3-tier progress dashboard (D-16-05)."""
    current_time = now or get_current_kst_time()

    # SECTION 1: Summary Table with Color-Coded Progress Bars
    table = Table(
        title=f"학습활동 종합 진척도 현황 ({report.summary.total_courses}개 과목)",
        header_style="bold cyan",
        show_lines=True,
    )
    table.add_column("과목명", style="bold", ratio=2)
    table.add_column("현재주차", justify="center", width=8)
    table.add_column("현재 오픈 진도율", ratio=3)
    table.add_column("과거 주차 이수율", justify="center", width=14)
    table.add_column("학기 전체", justify="center", width=12)
    table.add_column("세부 항목 (VOD / 과제 / 퀴즈 / 자료)", justify="center", ratio=3)

    for c in report.courses:
        if c.status == "error":
            table.add_row(
                c.course_name,
                f"W{c.current_week}",
                Text("[수집실패]", style="bold red"),
                "-",
                "-",
                Text(c.error_message or "에러", style="dim red"),
            )
            continue

        # Color bar + text
        open_rate_style = _get_rate_style(c.current_open_rate)
        open_bar_text = Text(f"{c.current_open_rate}% ({c.current_open_completed}/{c.current_open_total})", style=open_rate_style)

        past_style = _get_rate_style(c.past_weeks_rate)
        past_text = Text(f"{c.past_weeks_rate}% ({c.past_weeks_completed}/{c.past_weeks_total})", style=past_style)
        if c.missed_past_items:
            past_text.append(f"\n[⚠️ {len(c.missed_past_items)}건 누락]", style="bold red")

        sem_text = f"{c.semester_overall_rate}% ({c.semester_completed}/{c.semester_total})"

        b = c.activity_breakdown
        breakdown_text = f"V:{b.vod.completed}/{b.vod.total} A:{b.assignment.completed}/{b.assignment.total} Q:{b.quiz.completed}/{b.quiz.total} M:{b.material.completed}/{b.material.total}"

        table.add_row(
            f"{c.course_name} ({c.course_abbr})",
            f"{c.current_week}주차",
            open_bar_text,
            past_text,
            sem_text,
            breakdown_text,
        )

    console.print(table)

    # SECTION 2: This Week Action Items (To-Do prioritized) (D-16-07)
    todo_table = Table(
        title="이번 주차 주요 점검 항목 (To-Do 우선)",
        header_style="bold yellow",
        show_lines=False,
    )
    todo_table.add_column("과목", style="bold", width=16)
    todo_table.add_column("유형", justify="center", width=8)
    todo_table.add_column("활동명", ratio=3)
    todo_table.add_column("마감 기한 / 잔여 시간", justify="right", ratio=2)
    todo_table.add_column("상태", justify="center", width=10)

    for c in report.courses:
        if c.status != "ok":
            continue
        for item in c.current_week_items:
            # Tag styling
            tag_map = {
                "vod": "[bold blue][VOD][/bold blue]",
                "assignment": "[bold magenta][과제][/bold magenta]",
                "quiz": "[bold yellow][퀴즈][/bold yellow]",
                "material": "[bold cyan][자료][/bold cyan]",
            }
            tag = tag_map.get(item.activity_type.value, f"[{item.activity_type.value}]")

            rem = format_remaining(item.due_date, current_time)
            status_text = Text("✓ 완료", style="dim green") if item.is_completed else Text("미완료", style="bold red")

            todo_table.add_row(
                c.course_abbr,
                tag,
                item.title,
                rem,
                status_text,
            )

    console.print(todo_table)

    # SECTION 3: Past Weeks Alert or All-Clear Badge (D-16-08)
    all_missed = [item for c in report.courses if c.status == "ok" for item in c.missed_past_items]
    if all_missed:
        alert_body = "\n".join(
            f"• [{item.course_id}] {item.title} (마감: {item.raw_due_date or '기한초과'})"
            for item in all_missed
        )
        console.print(
            Panel(
                alert_body,
                title=f"[bold red]⚠️ 과거 주차 누락/결석 경고 ({len(all_missed)}건)[/bold red]",
                border_style="red",
            )
        )
    else:
        console.print(
            Panel(
                "[bold green]지나온 주차의 모든 필수 활동(동영상/과제/퀴즈/자료)을 완벽히 이수했습니다.[/bold green]",
                title="[bold green]🎉 All Clear - 과거 주차 누락 없음[/bold green]",
                border_style="green",
            )
        )
```

### 7. `src/coursepilot/cli.py`
**Analog:** Existing `board_command` and `materials_command` in `src/coursepilot/cli.py`.

```python
@cli.command("progress")
@click.option(
    "--course",
    "course_query",
    type=str,
    default=None,
    help="특정 과목 이름, 약칭, 또는 과목 ID (생략 시 전체 수강 과목)",
)
@click.option(
    "--week",
    "week_query",
    type=int,
    default=None,
    help="조회할 특정 주차 번호 (생략 시 자동 판별된 이번 주차)",
)
@click.option(
    "--detail",
    "detail",
    is_flag=True,
    help="모든 주차의 세부 활동 목록을 전개하여 조회합니다.",
)
@click.option(
    "--cached",
    "use_cache",
    is_flag=True,
    help="10분 이내에 저장된 로컬 캐시 데이터가 있으면 즉시 반환합니다.",
)
@click.option(
    "--refresh",
    "refresh",
    is_flag=True,
    help="기존 캐시를 무시하고 LMS에서 실시간으로 새로 수집합니다.",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="표준 JSON 계약(schema_version: 1) 규격으로 결과를 출력합니다.",
)
@click.option(
    "--relogin",
    "relogin",
    is_flag=True,
    help="캐시된 세션을 무시하고 새로 로그인합니다.",
)
@click.option(
    "--headed",
    "headed",
    is_flag=True,
    help="브라우저 창을 화면에 표시합니다.",
)
@click.pass_context
def progress_command(
    ctx: click.Context,
    course_query: str | None,
    week_query: int | None,
    detail: bool,
    use_cache: bool,
    refresh: bool,
    as_json: bool,
    relogin: bool,
    headed: bool,
) -> None:
    """전체 학습활동(동영상/과제/퀴즈/자료)의 종합 진척도 및 현황을 브리핑합니다."""
    from coursepilot.progress.reporter import (
        render_course_matrix,
        render_detailed_activities,
        render_progress_dashboard,
    )
    from coursepilot.progress.runner import run_progress_pipeline

    err = Console(stderr=True)
    out = Console()

    def _on_progress(msg: str) -> None:
        err.print(msg, markup=False, highlight=False)

    try:
        report = run_progress_pipeline(
            course_query=course_query,
            week_query=week_query,
            cached=use_cache,
            refresh=refresh,
            relogin=relogin,
            headful=headed,
            progress_callback=_on_progress,
        )
    except Exception as e:
        err.print(f"[오류] 진척도 집계 실패: {e}", markup=False, highlight=False)
        ctx.exit(2)

    if as_json:
        click.echo(report.model_dump_json(indent=2))
    else:
        if course_query and len(report.courses) == 1:
            render_course_matrix(report.courses[0], out)
        elif detail:
            render_detailed_activities(report, out)
        else:
            render_progress_dashboard(report, out, detail=detail)

    # Exit codes: 0 = full success, 1 = partial success / missed items, 2 = fatal
    if report.status == "error" or report.errors:
        ctx.exit(1)
    if report.summary.missed_past_count > 0:
        ctx.exit(1)
    ctx.exit(0)
```

### 8. `tests/test_progress_models.py`
**Analog:** `tests/test_material_models.py`.

```python
"""Unit tests for progress DTOs and JSON contract serialization."""

from datetime import datetime
import json
import pytest
from pydantic import ValidationError

from coursepilot.progress.models import (
    SCHEMA_VERSION,
    ActivityBreakdown,
    ActivityCount,
    ActivityItem,
    ActivityType,
    CourseProgress,
    DashboardSummary,
    ProgressReport,
)


def test_activity_type_enum():
    assert ActivityType.VOD == "vod"
    assert ActivityType.ASSIGNMENT == "assignment"
    assert ActivityType.QUIZ == "quiz"
    assert ActivityType.MATERIAL == "material"


def test_progress_report_json_contract():
    item = ActivityItem(
        course_id="101",
        activity_type=ActivityType.VOD,
        week_number=1,
        title="1강 동영상",
        is_completed=True,
    )
    breakdown = ActivityBreakdown(vod=ActivityCount(completed=1, total=1, rate=100.0))
    course = CourseProgress(
        course_id="101",
        course_name="알고리즘",
        course_abbr="Algo",
        current_week=2,
        current_open_rate=100.0,
        current_open_completed=1,
        current_open_total=1,
        past_weeks_rate=100.0,
        past_weeks_completed=1,
        past_weeks_total=1,
        semester_overall_rate=50.0,
        semester_completed=1,
        semester_total=2,
        activity_breakdown=breakdown,
        all_items=[item],
    )
    summary = DashboardSummary(
        total_courses=1,
        current_open_rate=100.0,
        current_open_completed=1,
        current_open_total=1,
        past_weeks_rate=100.0,
        past_weeks_completed=1,
        past_weeks_total=1,
        semester_overall_rate=50.0,
        semester_completed=1,
        semester_total=2,
        missed_past_count=0,
        current_week_todo_count=0,
        activity_totals=breakdown,
    )
    report = ProgressReport(
        status="success",
        generated_at=datetime(2026, 9, 26, 12, 0, 0),
        summary=summary,
        courses=[course],
    )
    data = json.loads(report.model_dump_json())
    assert data["schema_version"] == 1
    assert data["command"] == "progress"
    assert data["status"] == "success"
```

### 9. `tests/test_progress_calculator.py`
**Analog:** `tests/test_lecture_parser.py` and `tests/test_priority.py`.

```python
"""Unit tests for progress calculation engine and hybrid week detection."""

from datetime import datetime
from coursepilot.progress.calculator import (
    SectionMeta,
    calculate_course_progress,
    compute_breakdown,
    detect_current_week,
)
from coursepilot.progress.models import ActivityItem, ActivityType


def test_detect_current_week_by_date():
    sections = [
        SectionMeta(
            week_number=1,
            start_date=datetime(2026, 9, 1),
            end_date=datetime(2026, 9, 7),
        ),
        SectionMeta(
            week_number=2,
            start_date=datetime(2026, 9, 8),
            end_date=datetime(2026, 9, 14),
        ),
    ]
    now = datetime(2026, 9, 10, 15, 0)
    assert detect_current_week(sections, now=now) == 2


def test_week_1_boundary_past_weeks_all_clear():
    """Verify Week 1 execution does not falsely trigger past weeks missed alerts (Pitfall 1)."""
    items = [
        ActivityItem(
            course_id="101",
            activity_type=ActivityType.VOD,
            week_number=1,
            title="1강",
            is_completed=False,
        )
    ]
    progress = calculate_course_progress(
        course_id="101",
        course_name="자료구조",
        course_abbr="DS",
        current_week=1,
        activities=items,
    )
    assert progress.past_weeks_total == 0
    assert progress.past_weeks_rate == 100.0
    assert len(progress.missed_past_items) == 0
```

### 10. `tests/test_progress_runner.py`
**Analog:** `tests/test_board_runner.py`.

```python
"""Integration tests for progress runner, caching, and error isolation."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from coursepilot.config import Settings
from coursepilot.progress.runner import load_progress_cache, run_progress_pipeline, save_progress_cache
from coursepilot.scraper.models import CourseItem


@pytest.fixture
def dummy_settings(tmp_path: Path) -> Settings:
    return Settings(
        lms_id="testuser",
        lms_password="testpassword",
        lms_url="https://canvas.kau.ac.kr",
        session_cache_path=tmp_path / "cache" / "session.json",
        download_dir=tmp_path / "downloads",
        course_mappings_path=tmp_path / "course_mappings.json",
    )


def test_progress_runner_course_error_isolation(dummy_settings):
    """Verify that an error in Course 1 is isolated and Course 2 succeeds (D-16-16)."""
    courses = [
        CourseItem(course_id="101", raw_name="알고리즘", clean_name="알고리즘", url="http://test/101"),
        CourseItem(course_id="102", raw_name="운영체제", clean_name="운영체제", url="http://test/102"),
    ]
    # Runner test with mock_client returning 500 for 101 and 200 for 102
```

### 11. `tests/test_progress_reporter.py`
**Analog:** `tests/test_reporter.py`.

```python
"""Unit tests for Rich terminal dashboard rendering."""

from io import StringIO
from rich.console import Console

from coursepilot.progress.models import ActivityItem, ActivityType, CourseProgress, ProgressReport
from coursepilot.progress.reporter import render_progress_dashboard


def test_render_all_clear_panel():
    buffer = StringIO()
    console = Console(file=buffer, force_terminal=False, width=120)
    # Renders report without missed items -> checks for "All Clear" in buffer.getvalue()
```

### 12. `tests/test_cli_progress.py`
**Analog:** `tests/test_cli_board.py`.

```python
"""Integration tests for Click CLI `coursepilot progress` command."""

import json
from click.testing import CliRunner
from unittest.mock import patch

from coursepilot.cli import cli


def test_cli_progress_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["progress", "--help"])
    assert result.exit_code == 0
    assert "--course" in result.output
    assert "--week" in result.output
    assert "--detail" in result.output
    assert "--cached" in result.output
    assert "--refresh" in result.output
    assert "--json" in result.output
```

---

## Shared Patterns

### 1. Pydantic Strict Modeling
All domain DTOs must declare `model_config = ConfigDict(extra="forbid")` to prevent silent field typos and preserve strict contract guarantees.

### 2. Stream Separation (D-16-15)
- **stderr:** Used for real-time progress callbacks and dynamic spinners (`Console(stderr=True).print(...)`).
- **stdout:** Reserved strictly for final terminal reports (`Console().print(...)`) or machine-parseable JSON (`click.echo(report.model_dump_json(indent=2))`).

### 3. Exit Code Contract
- `0`: Complete success (all courses scraped ok, zero past weeks missed items).
- `1`: Partial success (one or more courses had scraping errors, or one or more past weeks missed items detected).
- `2`: Fatal error (uncaught exception, authentication failure, missing environment setup).

### 4. Atomic Cache File Writing (Claude's Discretion)
Cache files are written to a temporary sibling file (`progress_cache.json.tmp`) before calling `replace()` to ensure atomicity and eliminate file corruption risks on sudden interruption.

### 5. Independent Course Error Isolation (D-08, D-16-16)
When processing multiple courses in a loop, each course is enclosed in its own `try ... except Exception as e` block. A failure in one course marks that specific course with `status="error"` and records an `ErrorItem`, while continuing execution for all remaining courses.
