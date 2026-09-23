"""KAU LXP Assistant CLI: `check`/`sync` wire pipeline -> reporter -> the versioned report contract (D-07, D-10)."""

import logging
import sys
from datetime import datetime

import click
from rich.console import Console

from kau_assistant.config import Settings, get_settings
from kau_assistant.errors import exit_code_for, safe_cli_error
from kau_assistant.installer import AGENT_SKILL_PATHS, InstallError, install_skill
from kau_assistant.notion import NotionSyncEngine
from kau_assistant.pipeline import PipelineResult, collect_tasks
from kau_assistant.reporter import (
    build_check_report,
    build_sync_report,
    render_check_report,
    render_sync_report,
    to_json,
)
from kau_assistant.scraper.date_parser import get_current_kst_time


@click.group()
def cli() -> None:
    """KAU LXP Assistant 명령행 도구."""


def _collect_lms_tasks(
    *,
    headed: bool,
    relogin: bool,
    err: Console,
    now: datetime,
    status_message: str,
) -> tuple[Settings, PipelineResult]:
    """Shared settings-load + LMS-collect step for `check` and `sync` (D-07, D-08).

    Progress lines go to stderr only; any exception (fatal config/login stage)
    propagates unconverted for the caller's own fatal-report boundary.
    """
    err.print(status_message, markup=False, highlight=False)
    settings = get_settings()

    def _on_progress(index: int, total: int, name: str) -> None:
        err.print(f"[{index}/{total}] {name} 수집 중", markup=False, highlight=False)

    result = collect_tasks(
        settings,
        headed=headed,
        relogin=relogin,
        progress=_on_progress,
        now=now,
    )
    return settings, result


@cli.command()
@click.option("--json", "as_json", is_flag=True, help="결과를 JSON으로 출력합니다.")
@click.option("--headed", is_flag=True, help="브라우저 창을 표시하며 실행합니다.")
@click.option("--relogin", is_flag=True, help="캐시된 세션을 무시하고 다시 로그인합니다.")
@click.pass_context
def check(ctx: click.Context, as_json: bool, headed: bool, relogin: bool) -> None:
    """LMS에 로그인해 미완료 강의/과제 현황을 확인합니다 (Notion에는 접근하지 않습니다)."""
    err = Console(stderr=True)
    out = Console()

    now = get_current_kst_time()

    try:
        _settings, result = _collect_lms_tasks(
            headed=headed,
            relogin=relogin,
            err=err,
            now=now,
            status_message="LMS 로그인 및 과목 목록 수집 중…",
        )
        report = build_check_report(
            result.tasks,
            course_count=result.course_count,
            errors=result.errors,
            now=now,
        )
    except Exception as error:  # noqa: BLE001 - top-level fatal boundary (D-08, D-12)
        fatal = safe_cli_error(error, scope="fatal")
        report = build_check_report([], course_count=0, errors=[fatal], now=now)

    if as_json:
        click.echo(to_json(report))
    else:
        render_check_report(report, out)

    ctx.exit(exit_code_for(report.errors))


@cli.command()
@click.option("--json", "as_json", is_flag=True, help="결과를 JSON으로 출력합니다.")
@click.option("--headed", is_flag=True, help="브라우저 창을 표시하며 실행합니다.")
@click.option("--relogin", is_flag=True, help="캐시된 세션을 무시하고 다시 로그인합니다.")
@click.option("--apply", "apply_changes", is_flag=True, help="미리보기 대신 실제로 Notion에 반영합니다.")
@click.pass_context
def sync(ctx: click.Context, as_json: bool, headed: bool, relogin: bool, apply_changes: bool) -> None:
    """LMS 현황을 Notion Scheduler에 동기화합니다 (기본은 미리보기, --apply로만 실제 반영, D-06)."""
    err = Console(stderr=True)
    out = Console()

    now = get_current_kst_time()

    try:
        settings, result = _collect_lms_tasks(
            headed=headed,
            relogin=relogin,
            err=err,
            now=now,
            status_message="LMS 로그인 및 과목 목록 수집 중…",
        )
    except Exception as error:  # noqa: BLE001 - top-level fatal boundary (D-08, D-12)
        fatal = safe_cli_error(error, scope="fatal")
        report = build_sync_report([], None, course_count=0, errors=[fatal], now=now)
    else:
        err.print("Notion Scheduler 조회 및 동기화 계획 수립 중…", markup=False, highlight=False)
        sync_result = NotionSyncEngine(settings=settings).sync(
            result.tasks, dry_run=not apply_changes
        )
        report = build_sync_report(
            result.tasks,
            sync_result,
            course_count=result.course_count,
            errors=result.errors,
            now=now,
        )

    if as_json:
        click.echo(to_json(report))
    else:
        render_sync_report(report, out)

    ctx.exit(exit_code_for(report.errors))


@cli.command("install-skill")
@click.option(
    "--agent",
    "agent",
    type=click.Choice(sorted(AGENT_SKILL_PATHS)),
    required=True,
    help="스킬을 설치할 에이전트를 선택하세요.",
)
@click.pass_context
def install_skill_command(ctx: click.Context, agent: str) -> None:
    """이 저장소의 kau-lxp 스킬을 에이전트의 사용자 스킬 폴더에 설치합니다 (D-21..D-23)."""
    err = Console(stderr=True)
    out = Console()

    try:
        result = install_skill(agent)
    except InstallError as error:
        err.print(str(error), markup=False, highlight=False)
        ctx.exit(2)

    out.print(f"설치 완료 (복사): {result.target}", markup=False, highlight=False)
    out.print(
        "에이전트를 재시작(또는 새 세션 시작)한 뒤 '과제 확인해줘'라고 요청해 보세요.",
        markup=False,
        highlight=False,
    )
    if not result.agent_home_found:
        display_name = AGENT_SKILL_PATHS[agent].display_name
        err.print(
            f"[경고] {display_name} 홈 폴더를 찾지 못했습니다. 해당 에이전트가 설치되어 있는지 확인하세요.",
            markup=False,
            highlight=False,
        )


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
