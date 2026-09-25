"""Rich Console formatting for course bulletin board reports and article viewer."""

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from kau_assistant.board.models import BoardPostItem, BoardReport


def _format_size(num_bytes: int) -> str:
    """Formats bytes into human-readable size string."""
    if num_bytes <= 0:
        return ""
    if num_bytes < 1024:
        return f"{num_bytes} B"
    if num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    return f"{num_bytes / (1024 * 1024):.1f} MB"


def render_board_report(report: BoardReport, console: Console, detail: bool = False) -> None:
    """Renders a Rich terminal briefing of course notices and Q&A boards."""
    # 1. Summary Header Panel
    summary_text = (
        f"총 과목: {report.summary.total_courses}개 | "
        f"공지사항: {report.summary.total_notices}개 (신규 {report.summary.unread_notices}개) | "
        f"Q&A: {report.summary.total_questions}개 (답변대기 {report.summary.unanswered_questions}개, "
        f"내 질문 {report.summary.my_questions}개)"
    )
    console.print(
        Panel(
            summary_text,
            title="[bold blue]게시판 브리핑 요약[/bold blue]",
            expand=False,
        )
    )

    # 2. Inactive courses handling (D-15-02: compact 1-line muted text)
    inactive_courses = [c for c in report.courses if not c.notices and not c.qna]
    if inactive_courses:
        for c in inactive_courses:
            console.print(f"[dim]• {c.course_name}: 최근 공지 및 질문 없음[/dim]")

    # 3. Active courses tables
    active_courses = [c for c in report.courses if c.notices or c.qna]
    for course in active_courses:
        table = Table(
            title=f"{course.course_name} ({course.course_abbr})",
            show_lines=True,
        )
        table.add_column("구분", justify="center", style="bold")
        table.add_column("번호", justify="right", style="dim")
        table.add_column("제목", ratio=3)
        table.add_column("작성자", style="white")
        table.add_column("작성일", style="dim")
        table.add_column("상태 / 뱃지", justify="center")

        # Notices
        for notice in course.notices:
            title_parts = []
            if not notice.is_read:
                title_parts.append("[bold red][NEW][/bold red] ")
            title_parts.append(notice.title)
            if detail and notice.summary_preview:
                title_parts.append(f"\n[dim italic]{notice.summary_preview}[/dim italic]")

            status_str = f"[dim]첨부 {len(notice.attachments)}개[/dim]" if notice.attachments else ""

            table.add_row(
                "[cyan]공지[/cyan]",
                str(notice.post_id),
                "".join(title_parts),
                notice.author,
                notice.created_at,
                status_str,
            )

        # Q&A
        for qna in course.qna:
            title_parts = []
            if not qna.is_read:
                title_parts.append("[bold red][NEW][/bold red] ")
            title_parts.append(qna.title)
            if detail and qna.summary_preview:
                title_parts.append(f"\n[dim italic]{qna.summary_preview}[/dim italic]")

            badges = []
            if qna.is_my_question:
                badges.append("[bold cyan][내 질문][/bold cyan]")
            if qna.is_answered is True:
                badges.append("[bold green][답변완료][/bold green]")
            elif qna.is_answered is False:
                badges.append("[bold yellow][답변대기][/bold yellow]")

            table.add_row(
                "[magenta]Q&A[/magenta]",
                str(qna.post_id),
                "".join(title_parts),
                qna.author,
                qna.created_at,
                " ".join(badges),
            )

        console.print(table)

    # 4. Errors section
    if report.errors:
        err_table = Table(title="[bold red]수집 오류[/bold red]", show_lines=True)
        err_table.add_column("과목", style="bold red")
        err_table.add_column("오류 내용", style="red")
        for err in report.errors:
            err_table.add_row(str(err.get("course_name", "-")), str(err.get("error", "-")))
        console.print(err_table)


def render_article_viewer(post: BoardPostItem, console: Console) -> None:
    """Renders single post details, attachments, markdown body, and replies."""
    # Metadata panel
    title_prefix = "[bold red][NEW][/bold red] " if not post.is_read else ""
    meta_lines = [
        f"{title_prefix}[bold]{post.title}[/bold]",
        f"[dim]작성자: {post.author}  |  작성일: {post.created_at}  |  조회수: {post.hit_count}[/dim]",
    ]
    if post.url:
        meta_lines.append(f"[dim]LMS 링크: {post.url}[/dim]")
    else:
        meta_lines.append("[dim]LMS 링크: (비공개 글)[/dim]")

    console.print(
        Panel(
            "\n".join(meta_lines),
            title=f"게시글 상세 (#{post.post_id})",
            border_style="cyan",
        )
    )

    # Attachments
    if post.attachments:
        console.print("[bold]첨부파일:[/bold]")
        for att in post.attachments:
            extra = []
            if att.filesize > 0:
                extra.append(_format_size(att.filesize))
            if att.saved_path:
                extra.append(f"저장: {att.saved_path}")
            extra_str = f" ({', '.join(extra)})" if extra else ""
            console.print(f"  • {att.filename}{extra_str}", highlight=False)

    # Body
    body_md = post.content if post.content else "본문 내용이 없습니다."
    console.print(Panel(Markdown(body_md), title="본문", border_style="blue"))

    # Replies / Official answers
    if post.replies:
        console.print("\n[bold green]교수/조교 답변 / 댓글 목록:[/bold green]")
        for reply in post.replies:
            reply_title = f"[bold green]답변: {reply.author}[/bold green] ([dim]{reply.created_at}[/dim])"
            console.print(Panel(Markdown(reply.content), title=reply_title, border_style="green"))
