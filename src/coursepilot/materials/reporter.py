"""Rich terminal reporting for learning materials downloading and completion."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from coursepilot.materials.models import MaterialsRunResult, MaterialStatus


def _format_size(num_bytes: int) -> str:
    """Formats bytes into human-readable size string."""
    if num_bytes <= 0:
        return "-"
    if num_bytes < 1024:
        return f"{num_bytes} B"
    if num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    return f"{num_bytes / (1024 * 1024):.1f} MB"


def render_materials_report(result: MaterialsRunResult, console: Console) -> None:
    """Renders a Rich table and summary metrics for materials run results."""
    if result.dry_run:
        console.print(
            "[yellow][드라이런] 실제 다운로드나 열람 없이 계획만 표시합니다.[/yellow]"
        )

    table = Table(title="학습 자료 처리 현황", show_lines=True)
    table.add_column("과목", style="bold cyan")
    table.add_column("주차", style="magenta")
    table.add_column("자료명", style="white")
    table.add_column("상태", justify="center")
    table.add_column("크기 / 저장 경로", style="dim")

    failures: list[tuple[str, str, str]] = []

    for course_res in result.courses:
        for item_res in course_res.items:
            # Determine status label and style
            if item_res.status == MaterialStatus.DOWNLOADED:
                status_text = "[green]다운로드 완료[/green]"
            elif item_res.status == MaterialStatus.SKIPPED:
                status_text = "[cyan]건너뜀(동일)[/cyan]"
            elif item_res.status == MaterialStatus.VIEWED_ONLY:
                status_text = "[blue]열람 완료[/blue]"
            else:  # FAILED
                status_text = "[red]실패[/red]"
                failures.append(
                    (course_res.course_name, item_res.item.title, item_res.error_message or "알 수 없는 오류")
                )

            # Details column
            detail_parts = []
            if item_res.filesize > 0:
                detail_parts.append(_format_size(item_res.filesize))
            if item_res.saved_path:
                detail_parts.append(item_res.saved_path)
            detail_str = " | ".join(detail_parts) if detail_parts else "-"

            table.add_row(
                course_res.course_name,
                course_res.target_week,
                item_res.item.title,
                status_text,
                detail_str,
            )

    console.print(table)

    summary_msg = (
        f"총 과목: {result.total_courses}개 | "
        f"총 자료: {result.total_materials}개 | "
        f"다운로드: {result.downloaded_count}개 | "
        f"건너뜀: {result.skipped_count}개 | "
        f"열람 완료: {result.viewed_count}개 | "
        f"실패: {result.failed_count}개"
    )
    console.print(Panel(summary_msg, title="요약", expand=False))

    if failures:
        console.print("\n[bold red]실패한 자료 목록:[/bold red]")
        for cname, title, err in failures:
            console.print(f"  [red]✗[/red] [{cname}] {title}: {err}")
