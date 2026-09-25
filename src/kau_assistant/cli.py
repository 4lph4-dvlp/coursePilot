"""KAU LXP Assistant CLI: `check`/`sync` wire pipeline -> reporter -> the versioned report contract (D-07, D-10)."""

import logging
import sys
from datetime import datetime

import click
from rich.console import Console

from kau_assistant.config import DEFAULT_LMS_URL, Settings, get_settings
from kau_assistant.errors import exit_code_for, safe_cli_error
from kau_assistant.installer import AGENT_SKILL_PATHS, InstallError, install_skill
from kau_assistant.notion import NotionSyncEngine
from kau_assistant.notion.client import NotionClient
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
@click.option(
    "--link",
    "link",
    is_flag=True,
    help="복사 대신 심볼릭 링크(또는 Windows 접합점)로 설치합니다 (개발용).",
)
@click.pass_context
def install_skill_command(ctx: click.Context, agent: str, link: bool) -> None:
    """이 저장소의 kau-lxp 스킬을 에이전트의 사용자 스킬 폴더에 설치합니다 (D-21..D-23)."""
    err = Console(stderr=True)
    out = Console()

    try:
        result = install_skill(agent, link=link)
    except InstallError as error:
        err.print(str(error), markup=False, highlight=False)
        ctx.exit(2)

    mode_label = "링크" if result.mode == "link" else "복사"
    out.print(f"설치 완료 ({mode_label}): {result.target}", markup=False, highlight=False)
    out.print(
        "에이전트를 재시작(또는 새 세션 시작)한 뒤 '과제 확인해줘'라고 요청해 보세요.",
        markup=False,
        highlight=False,
    )
    out.print(
        f"LMS 주소(LMS_URL): 설정하지 않으면 한국항공대 LXP({DEFAULT_LMS_URL})를 조회합니다. 다른 Coursemos(Moodle) 기반 학교라면 저장소 .env의 LMS_URL을 학교 LXP/LMS 주소로 직접 설정하세요.",
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


@cli.group("watch", invoke_without_command=True)
@click.option(
    "--course",
    "course_query",
    type=str,
    default=None,
    help="시청할 과목 이름, 약칭, 또는 과목 ID (예: '기초전자실험', '디시설')",
)
@click.option(
    "--week",
    "week_query",
    type=str,
    default="current",
    show_default=True,
    help="시청할 주차 ('current', 'all', 또는 주차 번호 예: '4')",
)
@click.option(
    "--video-index",
    "video_index",
    type=int,
    default=None,
    help="시청할 주차 내 특정 영상 번호 (1-based, 예: 2)",
)
@click.option(
    "--update-notion",
    "update_notion",
    is_flag=True,
    help="시청 완료된 강의의 Notion Scheduler 작업 상태를 '완료'로 변경합니다.",
)
@click.option(
    "--dry-run",
    "dry_run",
    is_flag=True,
    help="실제 영상을 재생하지 않고 시청 대상 영상 목록만 미리 확인합니다.",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="결과를 JSON 형식으로 출력합니다.",
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
    help="브라우저 창을 화면에 표시합니다 (기본값: 헤드리스).",
)
@click.pass_context
def watch_group(
    ctx: click.Context,
    course_query: str | None,
    week_query: str,
    video_index: int | None,
    update_notion: bool,
    dry_run: bool,
    as_json: bool,
    relogin: bool,
    headed: bool,
) -> None:
    """지정된 과목의 미시청 VOD를 백그라운드에서 자동 재생합니다."""
    if ctx.invoked_subcommand is not None:
        return

    err = Console(stderr=True)
    out = Console()

    if not course_query:
        err.print("[오류] --course 옵션이 필요합니다. (예: kau-assistant watch --course 기초전자실험)", markup=False, highlight=False)
        ctx.exit(2)

    from kau_assistant.player.runner import watch_course_vods

    settings = get_settings().model_copy(
        update={
            "headless": not headed,
        }
    )

    if relogin and settings.session_cache_path.exists():
        settings.session_cache_path.unlink()

    def on_vod_start(vod, idx, total):
        err.print(f"[{idx}/{total}] VOD 재생 시작: {vod.title}...", markup=False, highlight=False)

    def on_vod_complete(progress):
        err.print(f"✓ VOD 시청 완료: {progress.title}", markup=False, highlight=False)

    result = watch_course_vods(
        settings=settings,
        course_query=course_query,
        week_query=week_query,
        video_index=video_index,
        dry_run=dry_run,
        update_notion=update_notion,
        on_vod_start=on_vod_start,
        on_vod_complete=on_vod_complete,
    )

    if as_json:
        click.echo(result.model_dump_json(indent=2))
    else:
        if result.error_message:
            err.print(f"[오류] {result.error_message}", markup=False, highlight=False)
            ctx.exit(1)

        if dry_run:
            out.print(f"VOD 시청 계획 미리보기 (--dry-run):", markup=False, highlight=False)
            out.print(f"과목: {result.course_name} ({result.course_id}) | 대상 주차: {result.target_week}", markup=False, highlight=False)
            out.print(f"시청 대상: {result.total_vods}개 영상 (이미 완료: {result.skipped_vods}개 건너뜀)", markup=False, highlight=False)
        else:
            out.print(
                f"VOD 시청 작업 완료: {result.course_name} ({result.target_week}) - 총 {result.completed_vods}/{result.total_vods}개 완료",
                markup=False,
                highlight=False,
            )
            if result.notion_updated_count > 0:
                out.print(
                    f"Notion Scheduler: {result.notion_updated_count}개 작업 상태를 '완료'로 변경했습니다.",
                    markup=False,
                    highlight=False,
                )

    exit_code = 1 if result.error_message or (result.total_vods > 0 and result.completed_vods < result.total_vods and not dry_run) else 0
    ctx.exit(exit_code)


@watch_group.command("status")
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="상태를 JSON 형식으로 출력합니다.",
)
@click.pass_context
def watch_status_command(ctx: click.Context, as_json: bool) -> None:
    """현재 실행 중인 VOD 시청 상태 및 진행률을 조회합니다 (D-12-05)."""
    from kau_assistant.player.state import WatchStateManager

    sm = WatchStateManager()
    state = sm.read_state()
    out = Console()

    if not state or state.status == "idle":
        if as_json:
            click.echo('{"status": "idle"}')
        else:
            out.print("진행 중인 VOD 시청 작업이 없습니다.", markup=False, highlight=False)
        return

    if as_json:
        click.echo(state.model_dump_json(indent=2))
        return

    if state.status == "running":
        mins, secs = divmod(int(state.remaining_seconds), 60)
        rem_str = f"{mins}분 {secs}초" if mins > 0 else f"{secs}초"
        out.print(f"[진행 중] 과목: {state.course_name} ({state.target_week})", markup=False, highlight=False)
        out.print(f"현재 영상 ({state.video_index}/{state.total_videos}): {state.current_video_title}", markup=False, highlight=False)
        cur_m, cur_s = divmod(int(state.current_time), 60)
        dur_m, dur_s = divmod(int(state.duration), 60)
        out.print(f"진행 시간: {cur_m:02d}:{cur_s:02d} / {dur_m:02d}:{dur_s:02d} ({state.progress_percent:.1f}%)", markup=False, highlight=False)
        out.print(f"남은 시간: {rem_str} | PID: {state.pid}", markup=False, highlight=False)
    elif state.status == "completed":
        out.print(f"[완료] 과목: {state.course_name} ({state.target_week}) - 총 {state.total_videos}개 영상 시청 완료", markup=False, highlight=False)
    elif state.status == "stopped":
        out.print(f"[중단됨] 과목: {state.course_name} - 시청이 중단되었습니다.", markup=False, highlight=False)
    elif state.status == "error":
        out.print(f"[오류] 과목: {state.course_name} - {state.error_message or '오류가 발생했습니다.'}", markup=False, highlight=False)


@watch_group.command("stop")
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="결과를 JSON 형식으로 출력합니다.",
)
@click.pass_context
def watch_stop_command(ctx: click.Context, as_json: bool) -> None:
    """실행 중인 VOD 시청 프로세스를 안전하게 중단합니다 (D-12-06)."""
    import json
    from kau_assistant.player.state import WatchStateManager

    sm = WatchStateManager()
    state = sm.read_state()
    pid = state.pid if state else 0
    stopped = sm.stop_running_process()

    out = Console()
    if as_json:
        if stopped:
            click.echo(json.dumps({"stopped": True, "pid": pid}, indent=2))
        else:
            click.echo(json.dumps({"stopped": False, "reason": "not_running"}, indent=2))
    else:
        if stopped:
            out.print(f"✓ VOD 시청 프로세스(PID: {pid})를 성공적으로 중단했습니다.", markup=False, highlight=False)
        else:
            out.print("실행 중인 시청 프로세스를 찾을 수 없습니다.", markup=False, highlight=False)


@watch_group.command("sync-notion")
@click.option(
    "--course",
    "course_query",
    type=str,
    default=None,
    help="동기화할 특정 과목명 필터",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="결과를 JSON 형식으로 출력합니다.",
)
@click.pass_context
def watch_sync_notion_command(ctx: click.Context, course_query: str | None, as_json: bool) -> None:
    """최근 시청 완료된 영상을 Notion Scheduler에 '완료'로 동기화합니다 (D-12-08)."""
    import json
    from kau_assistant.player.state import WatchStateManager

    out = Console()
    err = Console(stderr=True)
    settings = get_settings()

    if not settings.is_notion_configured:
        msg = "Notion 설정이 되어 있지 않습니다. .env의 NOTION_TOKEN 및 NOTION_DATABASE_ID를 확인하세요."
        if as_json:
            click.echo(json.dumps({"synced_count": 0, "error": msg}, ensure_ascii=False, indent=2))
        else:
            err.print(f"[오류] {msg}", markup=False, highlight=False)
        ctx.exit(1)

    sm = WatchStateManager()
    records = sm.get_recent_history(course_query=course_query, uncompleted_only=True)

    if not records:
        if as_json:
            click.echo(json.dumps({"synced_count": 0, "synced_tasks": []}, ensure_ascii=False, indent=2))
        else:
            out.print("동기화할 최근 미완료 시청 기록이 없습니다.", markup=False, highlight=False)
        return

    try:
        notion_client = NotionClient(settings=settings)
        target = notion_client.resolve_target()
        existing_pages = notion_client.query_existing_pages(target.data_source_id)
    except Exception as e:
        err.print(f"[오류] Notion 데이터베이스 연결 실패: {e}", markup=False, highlight=False)
        if as_json:
            click.echo(json.dumps({"synced_count": 0, "error": str(e)}, ensure_ascii=False, indent=2))
        ctx.exit(1)

    synced_titles: list[str] = []
    for rec in records:
        page = existing_pages.get(rec.task_title)
        if page:
            try:
                notion_client.mark_task_completed(page.page_id)
                synced_titles.append(rec.task_title)
            except Exception as e:
                err.print(f"[경고] 작업 '{rec.task_title}' Notion 완료 갱신 실패: {e}", markup=False, highlight=False)

    if synced_titles:
        sm.mark_history_notion_synced(synced_titles)

    if as_json:
        click.echo(json.dumps({"synced_count": len(synced_titles), "synced_tasks": synced_titles}, ensure_ascii=False, indent=2))
    else:
        out.print(f"Notion Scheduler 동기화 완료: 총 {len(synced_titles)}개 작업 '완료' 처리됨.", markup=False, highlight=False)
        for title in synced_titles:
            out.print(f"  ✓ {title}", markup=False, highlight=False)


@cli.command("materials")
@click.option(
    "--course",
    "course_query",
    type=str,
    default=None,
    help="과목 이름, 약칭, 또는 과목 ID (생략 시 전체 과목)",
)
@click.option(
    "--week",
    "week_query",
    type=str,
    default="current",
    show_default=True,
    help="주차 ('current', 'all', 또는 주차 번호)",
)
@click.option(
    "--output-dir",
    "output_dir",
    type=click.Path(),
    default=None,
    help="다운로드 저장 기본 디렉터리 경로",
)
@click.option(
    "--no-download",
    "no_download",
    is_flag=True,
    help="파일 다운로드 없이 미열람 자료의 진도율(100%) 이수만 수행",
)
@click.option(
    "--dry-run",
    "dry_run",
    is_flag=True,
    help="실제 다운로드/열람 없이 대상 자료 목록 및 저장 경로 미리 확인",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="결과를 JSON 형식으로 출력합니다.",
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
def materials_command(
    ctx: click.Context,
    course_query: str | None,
    week_query: str,
    output_dir: str | None,
    no_download: bool,
    dry_run: bool,
    as_json: bool,
    relogin: bool,
    headed: bool,
) -> None:
    """학습자료(ubfile/resource) 자동 열람 및 로컬 다운로드를 수행합니다."""
    from kau_assistant.materials.reporter import render_materials_report
    from kau_assistant.materials.runner import run_materials_pipeline

    err = Console(stderr=True)
    out = Console()

    def _on_progress(msg: str) -> None:
        err.print(msg, markup=False, highlight=False)

    try:
        result = run_materials_pipeline(
            course_query=course_query,
            week_query=week_query,
            output_dir=output_dir,
            no_download=no_download,
            dry_run=dry_run,
            relogin=relogin,
            headful=headed,
            progress_callback=_on_progress,
        )
    except Exception as e:
        err.print(f"[오류] 학습자료 처리 실패: {e}", markup=False, highlight=False)
        ctx.exit(2)

    if as_json:
        click.echo(result.model_dump_json(indent=2))
    else:
        render_materials_report(result, out)

    if result.failed_count > 0:
        ctx.exit(1)
    ctx.exit(0)


# Register alias `files` for `materials`
cli.add_command(materials_command, name="files")


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
