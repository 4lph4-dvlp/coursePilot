"""Pure report builder, remaining-time formatter, and JSON/Rich renderers for `check` (D-01..D-05, D-09)."""

from collections.abc import Sequence
from datetime import datetime

from kau_assistant.domain.models import SyncTask
from kau_assistant.report_models import (
    BriefingSections,
    CheckReport,
    CourseGroup,
    ErrorItem,
    ReportItem,
    ReportSummary,
)
from kau_assistant.scraper.date_parser import get_current_kst_time

MINUTES_PER_HOUR = 60
MINUTES_PER_DAY = 24 * MINUTES_PER_HOUR


def format_remaining(due_date: datetime | None, now: datetime) -> str:
    """Formats remaining/elapsed time in Korean relative to `now` (Claude's discretion)."""
    if due_date is None:
        return "마감일 없음"

    delta_seconds = (due_date - now).total_seconds()
    is_overdue = delta_seconds < 0
    total_minutes = int(abs(delta_seconds) // 60)
    days, rem_minutes = divmod(total_minutes, MINUTES_PER_DAY)
    hours, minutes = divmod(rem_minutes, MINUTES_PER_HOUR)

    if is_overdue:
        if days >= 1:
            return f"{days}일 {hours}시간 지남"
        return f"{hours}시간 {minutes}분 지남"

    if days >= 1:
        return f"{days}일 {hours}시간 남음"
    if hours >= 1:
        return f"{hours}시간 {minutes}분 남음"
    return f"{minutes}분 남음"


def _group_by_course(items: list[ReportItem]) -> list[CourseGroup]:
    """Groups report items by course, preserving first-appearance and incoming item order."""
    order: list[str] = []
    buckets: dict[str, list[ReportItem]] = {}
    meta: dict[str, tuple[str, str]] = {}

    for item in items:
        if item.course_id not in buckets:
            buckets[item.course_id] = []
            order.append(item.course_id)
            meta[item.course_id] = (item.course_name, item.course_abbr)
        buckets[item.course_id].append(item)

    return [
        CourseGroup(
            course_id=course_id,
            course_name=meta[course_id][0],
            course_abbr=meta[course_id][1],
            items=buckets[course_id],
        )
        for course_id in order
    ]


def _to_report_item(task: SyncTask, current: datetime, *, include_detail: bool) -> ReportItem:
    remaining_minutes: int | None = None
    if task.due_date is not None:
        remaining_minutes = int((task.due_date - current).total_seconds() // 60)

    detail = task.memo if (include_detail and task.memo) else None

    return ReportItem(
        task_id=task.id,
        title=task.title,
        course_id=task.course_id,
        course_name=task.course_name,
        course_abbr=task.course_abbr,
        task_type=task.task_type.value,
        due_date=task.due_date,
        remaining_minutes=remaining_minutes,
        remaining_text=format_remaining(task.due_date, current),
        lms_url=task.source_url,
        detail=detail,
    )


def build_check_report(
    tasks: list[SyncTask],
    *,
    course_count: int,
    errors: Sequence[ErrorItem] = (),
    now: datetime | None = None,
) -> CheckReport:
    """Classifies tasks into urgency sections purely from existing SyncTask flags (D-01, D-05)."""
    current = now or get_current_kst_time()

    overdue_tasks = [t for t in tasks if t.is_overdue]
    due_within_24h_tasks = [t for t in tasks if t.is_urgent and not t.is_overdue]
    later_tasks = [t for t in tasks if not t.is_overdue and not t.is_urgent]

    overdue_items = [_to_report_item(t, current, include_detail=True) for t in overdue_tasks]
    due_within_24h_items = [
        _to_report_item(t, current, include_detail=True) for t in due_within_24h_tasks
    ]
    later_items = [_to_report_item(t, current, include_detail=False) for t in later_tasks]

    sections = BriefingSections(
        overdue=_group_by_course(overdue_items),
        due_within_24h=_group_by_course(due_within_24h_items),
        later=_group_by_course(later_items),
    )

    summary = ReportSummary(
        course_count=course_count,
        total_count=len(tasks),
        overdue_count=len(overdue_items),
        due_within_24h_count=len(due_within_24h_items),
        later_count=len(later_items),
        error_count=len(errors),
    )

    return CheckReport(
        generated_at=current,
        summary=summary,
        items=sections,
        errors=list(errors),
    )


def to_json(report: CheckReport) -> str:
    """Serializes the report via Pydantic's own serializer, keeping Korean text unescaped (Pitfall 3)."""
    return report.model_dump_json(indent=2)
