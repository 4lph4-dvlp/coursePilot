"""Pure report builder, remaining-time formatter, and JSON/Rich renderers for `check` (D-01..D-05, D-09)."""

from collections.abc import Sequence
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

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

SECTION_TITLES: dict[str, str] = {
    "overdue": "기한 초과",
    "due_within_24h": "24시간 이내",
    "later": "이후 일정",
}


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


def _format_due(due_date: datetime | None) -> str:
    if due_date is None:
        return "-"
    return due_date.strftime("%Y-%m-%d %H:%M KST")


def _render_section_table(title: str, groups: list[CourseGroup], console: Console) -> None:
    console.print(f"\n[bold]{title}[/bold]")

    if not groups:
        console.print("없음")
        return

    table = Table(show_lines=False, expand=False)
    table.add_column("과목", overflow="fold")
    table.add_column("작업", overflow="fold")
    table.add_column("마감일", overflow="fold")
    table.add_column("남은 시간", overflow="fold")

    for group in groups:
        item_count = len(group.items)
        for index, item in enumerate(group.items):
            course_label = Text(group.course_abbr) if index == 0 else Text("")
            table.add_row(
                course_label,
                Text(item.title),
                Text(_format_due(item.due_date)),
                Text(item.remaining_text),
                end_section=(index == item_count - 1),
            )

    console.print(table)


def _render_detail_blocks(groups: list[CourseGroup], console: Console) -> None:
    for group in groups:
        for item in group.items:
            console.print(Text(f"- {item.title}"))
            if item.detail:
                console.print(Text(item.detail))
            console.print(Text(f"LMS: {item.lms_url}"))


def _render_errors(errors: list[ErrorItem], console: Console) -> None:
    if not errors:
        return

    console.print("\n[bold]수집 오류[/bold]")
    table = Table(show_lines=False, expand=False)
    table.add_column("구분", overflow="fold")
    table.add_column("과목", overflow="fold")
    table.add_column("코드", overflow="fold")

    for error in errors:
        scope_label = "치명적 오류" if error.scope == "fatal" else error.scope
        table.add_row(
            Text(scope_label),
            Text(error.course_name or "-"),
            Text(error.code),
        )

    console.print(table)

    for error in errors:
        console.print(Text(error.message))


def render_check_report(report: CheckReport, console: Console) -> None:
    """Renders the full urgency-grouped Rich briefing (D-01..D-04, D-09)."""
    header = (
        f"과목 {report.summary.course_count}개 · "
        f"기한 초과 {report.summary.overdue_count} · "
        f"24시간 이내 {report.summary.due_within_24h_count} · "
        f"이후 일정 {report.summary.later_count}"
    )
    if report.errors:
        header += f" · 수집 오류 {len(report.errors)}"
    header += f"\n생성 시각: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S KST')}"
    console.print(Panel(header, title="check 결과"))

    _render_section_table(SECTION_TITLES["overdue"], report.items.overdue, console)
    _render_detail_blocks(report.items.overdue, console)

    _render_section_table(SECTION_TITLES["due_within_24h"], report.items.due_within_24h, console)
    _render_detail_blocks(report.items.due_within_24h, console)

    _render_section_table(SECTION_TITLES["later"], report.items.later, console)

    _render_errors(report.errors, console)
