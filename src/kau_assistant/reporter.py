"""Pure report builder, remaining-time formatter, and JSON/Rich renderers for `check` (D-01..D-05, D-09)."""

from collections.abc import Sequence
from datetime import datetime
from enum import Enum

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from kau_assistant.config import DEFAULT_LMS_URL
from kau_assistant.domain.models import SyncTask
from kau_assistant.notion.models import SyncResult
from kau_assistant.report_models import (
    BriefingSections,
    CheckReport,
    CourseGroup,
    ErrorItem,
    ReportItem,
    ReportNotice,
    ReportSummary,
    SyncChange,
    SyncCounts,
    SyncCreateItem,
    SyncReport,
    SyncSection,
    SyncSkipItem,
    SyncUpdateItem,
)
from kau_assistant.board.reporter import render_article_viewer, render_board_report
from kau_assistant.scraper.date_parser import get_current_kst_time

MINUTES_PER_HOUR = 60
MINUTES_PER_DAY = 24 * MINUTES_PER_HOUR

NO_COURSES_NOTICE_CODE = "no_courses_found"
NO_COURSES_NOTICE_MESSAGE = (
    "수강 중인 과목을 찾지 못했습니다. 저장소 .env의 LMS_URL이 이번 학기 강의가 열리는 학교의 Coursemos LXP/LMS 주소인지"
    f"(설정하지 않으면 기본값 {DEFAULT_LMS_URL} 사용), 그리고 현재 학기에 등록된 과목이 있는지 확인하세요."
)


def _build_notices(course_count: int, errors: Sequence[ErrorItem]) -> list[ReportNotice]:
    if course_count == 0 and not any(e.scope == "fatal" for e in errors):
        return [ReportNotice(code=NO_COURSES_NOTICE_CODE, message=NO_COURSES_NOTICE_MESSAGE)]
    return []


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
        week_number=task.week_number,
        is_completed=task.is_completed,
        start_date=task.start_date,
        is_available=task.is_available,
        preparation_date=task.preparation_date,
    )


def _classify_by_urgency(
    tasks: list[SyncTask],
) -> tuple[list[SyncTask], list[SyncTask], list[SyncTask]]:
    """Splits tasks into overdue / due-within-24h / later purely from existing flags (D-01, D-05).

    Shared by build_check_report and build_sync_report so both summary headers
    agree on the same urgency classification.
    """
    overdue_tasks = [t for t in tasks if t.is_overdue]
    due_within_24h_tasks = [t for t in tasks if t.is_urgent and not t.is_overdue]
    later_tasks = [t for t in tasks if not t.is_overdue and not t.is_urgent]
    return overdue_tasks, due_within_24h_tasks, later_tasks


def build_check_report(
    tasks: list[SyncTask],
    *,
    course_count: int,
    errors: Sequence[ErrorItem] = (),
    now: datetime | None = None,
) -> CheckReport:
    """Classifies tasks into urgency sections purely from existing SyncTask flags (D-01, D-05)."""
    current = now or get_current_kst_time()

    overdue_tasks, due_within_24h_tasks, later_tasks = _classify_by_urgency(tasks)

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
        notices=_build_notices(course_count, errors),
    )


def to_json(report: CheckReport | SyncReport) -> str:
    """Serializes the report via Pydantic's own serializer, keeping Korean text unescaped (Pitfall 3)."""
    return report.model_dump_json(indent=2)


_NOTION_DISABLED_NOTICE = (
    "NOTION_TOKEN, NOTION_DATABASE_NAME 또는 NOTION_DATABASE_ID 값이 비어 있습니다. "
    "저장소의 .env 파일에 직접 입력한 뒤 다시 시도하세요."
)

SKIP_REASON_LABELS: dict[str, str] = {
    "unchanged": "변경 없음",
    "notion_disabled": "Notion 미설정",
}


def notion_page_url(page_id: str) -> str:
    """Builds a Notion page URL from a page id, matching Notion's own hyphen-free format."""
    return "https://www.notion.so/" + page_id.replace("-", "")


def _display(value: object) -> str | None:
    """Renders a FieldDiff before/after value as a display string (None/datetime/Enum/other)."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    return str(value)


def _build_sync_section(sync_result: SyncResult) -> SyncSection:
    create_items = [
        SyncCreateItem(
            task_id=action.task_id,
            title=action.title,
            course_name=action.task.course_name,
            due_date=action.task.due_date,
        )
        for action in sync_result.created
    ]
    update_items = [
        SyncUpdateItem(
            task_id=action.task_id,
            title=action.title,
            page_id=action.page_id,
            notion_url=notion_page_url(action.page_id),
            changes=[
                SyncChange(
                    field=diff.property_name,
                    before=_display(diff.before),
                    after=_display(diff.after),
                )
                for diff in action.diffs
            ],
        )
        for action in sync_result.updated
    ]
    skip_items = [
        SyncSkipItem(
            task_id=action.task_id,
            title=action.title,
            page_id=action.page_id,
            notion_url=notion_page_url(action.page_id) if action.page_id else None,
            reason=action.reason,
        )
        for action in sync_result.skipped
    ]

    return SyncSection(
        enabled=sync_result.enabled,
        dry_run=sync_result.dry_run,
        applied=sync_result.enabled and not sync_result.dry_run,
        target_title=sync_result.target.title if sync_result.target else None,
        notice=None if sync_result.enabled else _NOTION_DISABLED_NOTICE,
        create=create_items,
        update=update_items,
        skip=skip_items,
        counts=SyncCounts(
            total=sync_result.stats.total,
            create=sync_result.stats.created,
            update=sync_result.stats.updated,
            skip=sync_result.stats.skipped,
            error=sync_result.stats.errors,
        ),
    )


def build_sync_report(
    tasks: list[SyncTask],
    sync_result: SyncResult | None,
    *,
    course_count: int,
    errors: Sequence[ErrorItem] = (),
    now: datetime | None = None,
) -> SyncReport:
    """Maps a real SyncResult into the sync half of contract v1, never model_dump()'d (D-13, D-16)."""
    current = now or get_current_kst_time()
    overdue_tasks, due_within_24h_tasks, later_tasks = _classify_by_urgency(tasks)

    sync_section: SyncSection | None = None
    notion_errors: list[ErrorItem] = []
    if sync_result is not None:
        sync_section = _build_sync_section(sync_result)
        notion_errors = [
            ErrorItem(
                scope="notion",
                code=action.code,
                message=action.message,
                task_title=action.title or None,
            )
            for action in sync_result.errors
        ]

    all_errors = [*errors, *notion_errors]

    summary = ReportSummary(
        course_count=course_count,
        total_count=len(tasks),
        overdue_count=len(overdue_tasks),
        due_within_24h_count=len(due_within_24h_tasks),
        later_count=len(later_tasks),
        error_count=len(all_errors),
    )

    return SyncReport(
        generated_at=current,
        summary=summary,
        sync=sync_section,
        errors=all_errors,
        notices=_build_notices(course_count, errors),
    )


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


def _summary_header(report: CheckReport | SyncReport) -> str:
    """Shared summary header used by both `check` and `sync` Rich reports (D-03)."""
    header = (
        f"과목 {report.summary.course_count}개 · "
        f"기한 초과 {report.summary.overdue_count} · "
        f"24시간 이내 {report.summary.due_within_24h_count} · "
        f"이후 일정 {report.summary.later_count}"
    )
    if report.errors:
        header += f" · 수집 오류 {len(report.errors)}"
    header += f"\n생성 시각: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S KST')}"
    return header


def _render_notices(notices: list[ReportNotice], console: Console) -> None:
    if not notices:
        return
    console.print("\n[bold]안내[/bold]")
    for notice in notices:
        console.print(Text(notice.message))


def render_check_report(report: CheckReport, console: Console) -> None:
    """Renders the full urgency-grouped Rich briefing (D-01..D-04, D-09)."""
    console.print(Panel(_summary_header(report), title="check 결과"))
    _render_notices(report.notices, console)

    _render_section_table(SECTION_TITLES["overdue"], report.items.overdue, console)
    _render_detail_blocks(report.items.overdue, console)

    _render_section_table(SECTION_TITLES["due_within_24h"], report.items.due_within_24h, console)
    _render_detail_blocks(report.items.due_within_24h, console)

    _render_section_table(SECTION_TITLES["later"], report.items.later, console)

    _render_errors(report.errors, console)


def _sync_mode_banner(sync: SyncSection | None) -> str:
    if sync is None:
        return "Notion 동기화를 진행하지 않았습니다."
    if not sync.enabled:
        return sync.notice or "Notion 동기화를 진행하지 않았습니다."
    if sync.dry_run:
        return "노션 동기화 미리보기 — 아직 아무것도 쓰지 않았습니다. 적용하려면 --apply"
    return "노션 동기화 적용 완료"


def _render_sync_create_table(title: str, items: list[SyncCreateItem], console: Console) -> None:
    console.print(f"\n[bold]{title}[/bold]")
    if not items:
        console.print("없음")
        return

    table = Table(show_lines=False, expand=False)
    table.add_column("작업", overflow="fold")
    table.add_column("과목", overflow="fold")
    table.add_column("마감일", overflow="fold")

    for item in items:
        table.add_row(Text(item.title), Text(item.course_name), Text(_format_due(item.due_date)))

    console.print(table)


def _render_sync_update_table(title: str, items: list[SyncUpdateItem], console: Console) -> None:
    console.print(f"\n[bold]{title}[/bold]")
    if not items:
        console.print("없음")
        return

    table = Table(show_lines=False, expand=False)
    table.add_column("작업", overflow="fold")
    table.add_column("변경 내용", overflow="fold")
    table.add_column("Notion 링크", overflow="fold")

    for item in items:
        changes_text = "\n".join(
            f"{change.field}: {change.before} -> {change.after}" for change in item.changes
        )
        table.add_row(Text(item.title), Text(changes_text), Text(item.notion_url))

    console.print(table)


def _render_sync_skip_table(items: list[SyncSkipItem], console: Console) -> None:
    console.print("\n[bold]건너뜀[/bold]")
    if not items:
        console.print("없음")
        return

    table = Table(show_lines=False, expand=False)
    table.add_column("작업", overflow="fold")
    table.add_column("사유", overflow="fold")

    for item in items:
        reason_label = SKIP_REASON_LABELS.get(item.reason, item.reason)
        table.add_row(Text(item.title), Text(reason_label))

    console.print(table)


def render_sync_report(report: SyncReport, console: Console) -> None:
    """Renders the Rich `sync` report: header, mode banner, plan tables, errors (D-03, D-14, D-16)."""
    console.print(Panel(_summary_header(report), title="sync 결과"))
    _render_notices(report.notices, console)
    console.print(f"\n{_sync_mode_banner(report.sync)}")

    if report.sync is not None:
        create_title = "생성됨" if report.sync.applied else "생성 예정"
        update_title = "수정됨" if report.sync.applied else "수정 예정"
        _render_sync_create_table(create_title, report.sync.create, console)
        _render_sync_update_table(update_title, report.sync.update, console)
        _render_sync_skip_table(report.sync.skip, console)

    _render_errors(report.errors, console)


# Re-exports for unified reporting interface
from kau_assistant.progress.reporter import (
    render_course_matrix,
    render_detailed_activities,
    render_progress_dashboard,
)

__all__ = [
    "format_remaining",
    "render_check_report",
    "render_sync_report",
    "render_board_report",
    "render_article_viewer",
    "render_progress_dashboard",
    "render_course_matrix",
    "render_detailed_activities",
]
