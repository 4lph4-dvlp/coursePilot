"""Rich terminal visualizer for 3-tier activity progress dashboard, matrix roadmap, and detail view."""

from collections import defaultdict
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from kau_assistant.progress.models import (
    ActivityItem,
    ActivityType,
    CourseProgress,
    ProgressReport,
)
from kau_assistant.scraper.date_parser import KST, get_current_kst_time


def _get_rate_style(rate: float) -> str:
    """Returns color-coded Rich style based on achievement percentage (D-16-06)."""
    if rate >= 100.0:
        return "bold green"
    if rate >= 80.0:
        return "bold blue"
    if rate >= 50.0:
        return "bold yellow"
    return "bold red"


def _format_activity_tag(activity_type: ActivityType) -> str:
    """Formats 4-activity type tags with distinctive colors (D-16-07)."""
    if activity_type == ActivityType.VOD:
        return "[bold blue][VOD][/bold blue]"
    if activity_type == ActivityType.ASSIGNMENT:
        return "[bold magenta][과제][/bold magenta]"
    if activity_type == ActivityType.QUIZ:
        return "[bold yellow][퀴즈][/bold yellow]"
    return "[bold cyan][자료][/bold cyan]"


def render_progress_dashboard(
    report: ProgressReport,
    console: Console,
    detail: bool = False,
    now: datetime | None = None,
) -> None:
    """Renders 3-tier progress dashboard (D-16-05).

    [1] Course Progress Summary Table (Color-coded bars, dual rates, activity breakdowns)
    [2] This Week Action Items Table (To-Do prioritized, due dates, urgent badges)
    [3] Past Weeks Alert or All-Clear Badge (Warning on missed items, green badge if clean)
    """
    from kau_assistant.reporter import format_remaining

    current_time = now or get_current_kst_time()
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=KST)

    # ─────────────────────────────────────────────────────────────
    # Tier 1: Course Summary Table (D-16-05, D-16-06)
    # ─────────────────────────────────────────────────────────────
    title = f"학습활동 종합 진척도 현황 ({report.summary.total_courses}개 과목)"
    table = Table(title=title, header_style="bold cyan", show_lines=True)

    table.add_column("과목명", justify="left", style="bold")
    table.add_column("현재주차", justify="center")
    table.add_column("현재 오픈 진도율", justify="right")
    table.add_column("과거 주차 이수율", justify="right")
    table.add_column("학기 전체", justify="right")
    table.add_column("세부 항목 (VOD / 과제 / 퀴즈 / 자료)", justify="center")

    for course in report.courses:
        if course.status == "error":
            table.add_row(
                course.course_name,
                f"{course.current_week}주차",
                "[bold red][수집실패][/bold red]",
                "[dim]-[/dim]",
                "[dim]-[/dim]",
                f"[dim red]{course.error_message or '수집 오류'}[/dim red]",
            )
            continue

        open_style = _get_rate_style(course.current_open_rate)
        open_cell = f"[{open_style}]{course.current_open_rate:.1f}% ({course.current_open_completed}/{course.current_open_total})[/{open_style}]"

        past_style = _get_rate_style(course.past_weeks_rate)
        if course.missed_past_items:
            past_cell = f"[{past_style}]{course.past_weeks_rate:.1f}% (⚠️ {len(course.missed_past_items)}건 누락)[/{past_style}]"
        else:
            past_cell = f"[{past_style}]{course.past_weeks_rate:.1f}% ({course.past_weeks_completed}/{course.past_weeks_total})[/{past_style}]"

        sem_cell = f"{course.semester_overall_rate:.1f}% ({course.semester_completed}/{course.semester_total})"

        bd = course.activity_breakdown
        breakdown_cell = (
            f"VOD {bd.vod.completed}/{bd.vod.total} | "
            f"과제 {bd.assignment.completed}/{bd.assignment.total} | "
            f"퀴즈 {bd.quiz.completed}/{bd.quiz.total} | "
            f"자료 {bd.material.completed}/{bd.material.total}"
        )

        table.add_row(
            course.course_name,
            f"{course.current_week}주차",
            open_cell,
            past_cell,
            sem_cell,
            breakdown_cell,
        )

    # Summary footer row
    sum_open_style = _get_rate_style(report.summary.current_open_rate)
    sum_past_style = _get_rate_style(report.summary.past_weeks_rate)
    sum_open = f"[{sum_open_style}]{report.summary.current_open_rate:.1f}% ({report.summary.current_open_completed}/{report.summary.current_open_total})[/{sum_open_style}]"
    sum_past = f"[{sum_past_style}]{report.summary.past_weeks_rate:.1f}% ({report.summary.past_weeks_completed}/{report.summary.past_weeks_total})[/{sum_past_style}]"
    sum_sem = f"{report.summary.semester_overall_rate:.1f}% ({report.summary.semester_completed}/{report.summary.semester_total})"
    s_bd = report.summary.activity_totals
    sum_bd = (
        f"VOD {s_bd.vod.completed}/{s_bd.vod.total} | "
        f"과제 {s_bd.assignment.completed}/{s_bd.assignment.total} | "
        f"퀴즈 {s_bd.quiz.completed}/{s_bd.quiz.total} | "
        f"자료 {s_bd.material.completed}/{s_bd.material.total}"
    )

    table.add_row(
        "[bold]전체 요약[/bold]",
        "-",
        sum_open,
        sum_past,
        sum_sem,
        sum_bd,
        style="on grey15",
    )

    console.print(table)
    console.print()

    # ─────────────────────────────────────────────────────────────
    # Tier 2: This Week Action Items Table (To-Do Prioritized) (D-16-05, D-16-07)
    # ─────────────────────────────────────────────────────────────
    all_current_items = [
        (c.course_abbr, item)
        for c in report.courses
        if c.status == "ok"
        for item in c.current_week_items
    ]

    # Separate into To-Do and Done across all courses
    todo_list = [(abbr, item) for abbr, item in all_current_items if not item.is_completed]
    done_list = [(abbr, item) for abbr, item in all_current_items if item.is_completed]

    todo_table = Table(
        title="이번 주차 주요 점검 항목 (To-Do 우선)",
        header_style="bold yellow",
        show_lines=False,
    )
    todo_table.add_column("과목", justify="left", style="bold")
    todo_table.add_column("유형", justify="center")
    todo_table.add_column("활동명", justify="left")
    todo_table.add_column("마감 기한 / 잔여 시간", justify="left")
    todo_table.add_column("상태", justify="center")

    if not all_current_items:
        todo_table.add_row("-", "-", "이번 주차 등록된 활동이 없습니다.", "-", "-")
    else:
        # 1. Incomplete To-Do items first
        for abbr, item in todo_list:
            tag = _format_activity_tag(item.activity_type)
            urgent_badge = "[bold red]🔴 긴급[/bold red] " if item.is_urgent else ""
            title_text = f"{urgent_badge}{item.title}"

            remaining_text = format_remaining(item.due_date, current_time)
            due_str = f"{item.raw_due_date} ({remaining_text})" if item.raw_due_date else remaining_text
            status_text = "[bold red]미완료[/bold red]" if item.is_overdue else "[bold yellow]미완료[/bold yellow]"

            todo_table.add_row(
                abbr,
                tag,
                title_text,
                due_str,
                status_text,
            )

        # 2. Completed items trailing at bottom
        for abbr, item in done_list:
            tag = _format_activity_tag(item.activity_type)
            due_str = f"[dim]{item.raw_due_date or '-'}[/dim]"
            todo_table.add_row(
                f"[dim]{abbr}[/dim]",
                tag,
                f"[dim]{item.title}[/dim]",
                due_str,
                "[dim green]✓ 완료[/dim green]",
            )

    console.print(todo_table)
    console.print()

    # ─────────────────────────────────────────────────────────────
    # Tier 3: Past Weeks Alert or All-Clear Badge (D-16-05, D-16-08)
    # ─────────────────────────────────────────────────────────────
    all_missed: list[tuple[str, ActivityItem]] = [
        (c.course_abbr, item)
        for c in report.courses
        if c.status == "ok"
        for item in c.missed_past_items
    ]

    if all_missed:
        missed_lines = []
        for abbr, item in all_missed:
            tag = _format_activity_tag(item.activity_type)
            date_info = f" (마감: {item.raw_due_date})" if item.raw_due_date else ""
            missed_lines.append(f"• [{abbr}] {tag} [bold]{item.title}[/bold] (제{item.week_number}주차){date_info}")

        panel_content = "\n".join(missed_lines)
        console.print(
            Panel(
                panel_content,
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

    if detail:
        console.print()
        render_detailed_activities(report, console)


def render_course_matrix(
    course: CourseProgress,
    console: Console,
    week_filter: int | None = None,
) -> None:
    """Renders 1~16 week matrix roadmap table when a specific course is queried (D-16-10)."""
    title = f"[{course.course_name}] 1~16주차 학습활동 로드맵"
    table = Table(title=title, header_style="bold magenta", show_lines=True)

    table.add_column("주차", justify="center", style="bold")
    table.add_column("VOD 현황", justify="center")
    table.add_column("과제 현황", justify="center")
    table.add_column("퀴즈 현황", justify="center")
    table.add_column("자료 현황", justify="center")
    table.add_column("주차 진도율", justify="right")
    table.add_column("상태", justify="center")

    # Group activities by week number
    week_map: dict[int, list[ActivityItem]] = defaultdict(list)
    for act in course.all_items:
        week_map[act.week_number].append(act)

    target_weeks = [week_filter] if week_filter is not None else sorted(set(list(range(1, 17)) + list(week_map.keys())))

    for w in target_weeks:
        if w <= 0:
            continue
        items = week_map.get(w, [])

        vods = [a for a in items if a.activity_type == ActivityType.VOD]
        asgs = [a for a in items if a.activity_type == ActivityType.ASSIGNMENT]
        qzs = [a for a in items if a.activity_type == ActivityType.QUIZ]
        mats = [a for a in items if a.activity_type == ActivityType.MATERIAL]

        v_done = sum(1 for a in vods if a.is_completed)
        a_done = sum(1 for a in asgs if a.is_completed)
        q_done = sum(1 for a in qzs if a.is_completed)
        m_done = sum(1 for a in mats if a.is_completed)

        total_items = len(items)
        done_items = sum(1 for a in items if a.is_completed)
        rate = round(done_items / total_items * 100.0, 1) if total_items > 0 else 100.0

        is_current_week = (w == course.current_week)
        week_label = f"▶ {w}주차 (이번 주)" if is_current_week else f"{w}주차"

        if total_items == 0:
            status_text = "[dim]등록 없음[/dim]"
            rate_text = "[dim]-[/dim]"
        elif is_current_week:
            rate_style = _get_rate_style(rate)
            rate_text = f"[{rate_style}]{rate:.1f}% ({done_items}/{total_items})[/{rate_style}]"
            status_text = "[bold green]완료[/bold green]" if rate >= 100.0 else "[bold yellow]진행중[/bold yellow]"
        elif w < course.current_week:
            rate_style = _get_rate_style(rate)
            rate_text = f"[{rate_style}]{rate:.1f}% ({done_items}/{total_items})[/{rate_style}]"
            status_text = "[bold green]완료[/bold green]" if rate >= 100.0 else "[bold red]⚠️ 미완료/누락[/bold red]"
        else:
            rate_text = f"[dim]{rate:.1f}% ({done_items}/{total_items})[/dim]"
            status_text = "[dim]예정[/dim]"

        row_style = "bold on grey23" if is_current_week else None

        table.add_row(
            week_label,
            f"{v_done}/{len(vods)}" if vods else "-",
            f"{a_done}/{len(asgs)}" if asgs else "-",
            f"{q_done}/{len(qzs)}" if qzs else "-",
            f"{m_done}/{len(mats)}" if mats else "-",
            rate_text,
            status_text,
            style=row_style,
        )

    console.print(table)


def render_detailed_activities(report: ProgressReport, console: Console) -> None:
    """Renders expanded breakdown of all individual activities per course (D-16-11)."""
    table = Table(title="전체 과목 세부 활동 내역", header_style="bold blue", show_lines=True)
    table.add_column("과목", justify="left", style="bold")
    table.add_column("주차", justify="center")
    table.add_column("유형", justify="center")
    table.add_column("활동명", justify="left")
    table.add_column("마감일시", justify="left")
    table.add_column("이수 여부", justify="center")

    for course in report.courses:
        if course.status == "error":
            continue
        for item in course.all_items:
            tag = _format_activity_tag(item.activity_type)
            done_text = "[bold green]✓ 이수 완료[/bold green]" if item.is_completed else (
                "[bold red]✗ 기한 초과 미완료[/bold red]" if item.is_overdue else "[yellow]미완료[/yellow]"
            )
            table.add_row(
                course.course_abbr,
                f"{item.week_number}주차",
                tag,
                item.title,
                item.raw_due_date or "-",
                done_text,
            )

    console.print(table)
