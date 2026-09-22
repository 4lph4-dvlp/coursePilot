"""KAU LXP Assistant CLI: `check` wires pipeline -> reporter -> the versioned report contract (D-07, D-10)."""

import logging
import sys

import click
from rich.console import Console

from kau_assistant.config import get_settings
from kau_assistant.pipeline import collect_tasks
from kau_assistant.reporter import build_check_report, render_check_report, to_json
from kau_assistant.scraper.date_parser import get_current_kst_time


@click.group()
def cli() -> None:
    """KAU LXP Assistant 명령행 도구."""


@cli.command()
@click.option("--json", "as_json", is_flag=True, help="결과를 JSON으로 출력합니다.")
@click.option("--headed", is_flag=True, help="브라우저 창을 표시하며 실행합니다.")
@click.option("--relogin", is_flag=True, help="캐시된 세션을 무시하고 다시 로그인합니다.")
@click.pass_context
def check(ctx: click.Context, as_json: bool, headed: bool, relogin: bool) -> None:
    """LMS에 로그인해 미완료 강의/과제 현황을 확인합니다 (Notion에는 접근하지 않습니다)."""
    err = Console(stderr=True)
    out = Console()

    settings = get_settings()
    now = get_current_kst_time()

    err.print("LMS 로그인 및 과목 목록 수집 중…", markup=False, highlight=False)

    def _on_progress(index: int, total: int, name: str) -> None:
        err.print(f"[{index}/{total}] {name} 수집 중", markup=False, highlight=False)

    result = collect_tasks(
        settings,
        headed=headed,
        relogin=relogin,
        progress=_on_progress,
        now=now,
    )
    report = build_check_report(
        result.tasks,
        course_count=result.course_count,
        errors=result.errors,
        now=now,
    )

    if as_json:
        click.echo(to_json(report))
    else:
        render_check_report(report, out)

    ctx.exit(0 if not report.errors else 1)


def _configure_streams() -> None:
    """Reconfigures stdout/stderr to UTF-8 so Korean text survives a cp949 parent pipe (D-11)."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def _configure_logging() -> None:
    """Routes all stdlib logging to stderr so stdout only ever carries the report/JSON (D-11)."""
    logging.basicConfig(
        stream=sys.stderr,
        level=logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )


def main(argv: list[str] | None = None) -> None:
    """`python -m kau_assistant` process entry point."""
    _configure_streams()
    _configure_logging()
    cli.main(args=argv, prog_name="python -m kau_assistant")
