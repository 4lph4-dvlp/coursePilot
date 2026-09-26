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
from kau_assistant.progress.reporter import (
    render_course_matrix,
    render_detailed_activities,
    render_progress_dashboard,
)
from kau_assistant.progress.runner import run_progress_pipeline
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
    "--download",
    "download",
    is_flag=True,
    help="출석 시청과 함께 고속 백그라운드 영상 다운로드를 병행합니다.",
)
@click.option(
    "--quality",
    "quality",
    type=str,
    default="best",
    show_default=True,
    help="다운로드 영상 화질 ('best', '1080p', '720p', 'worst')",
)
@click.option(
    "--output-dir",
    "output_dir",
    type=click.Path(),
    default=None,
    help="다운로드 저장 디렉터리 경로",
)
@click.option(
    "--overwrite",
    "overwrite",
    is_flag=True,
    help="이미 존재하는 영상 파일도 덮어쓰기하여 새로 다운로드합니다.",
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
    download: bool,
    quality: str,
    output_dir: str | None,
    overwrite: bool,
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
        download=download,
        preferred_quality=quality,
        overwrite=overwrite,
        output_dir=output_dir,
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


def render_vod_download_report(result, console: Console) -> None:
    """Render Rich table report for VOD stream downloads."""
    from rich.table import Table
    from rich.text import Text
    from kau_assistant.stream.models import VodDownloadStatus

    if result.dry_run:
        console.print("[bold yellow]VOD 다운로드 계획 미리보기 (--dry-run)[/bold yellow]")
    else:
        console.print("[bold green]VOD 다운로드 작업 결과[/bold green]")

    for course in result.courses:
        table = Table(
            title=f"{course.course_name} ({course.target_week})",
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("주차", justify="center", width=6)
        table.add_column("차시", justify="center", width=6)
        table.add_column("강의명", justify="left")
        table.add_column("상태", justify="center", width=12)
        table.add_column("크기", justify="right", width=10)
        table.add_column("저장 경로", justify="left")

        for item in course.items:
            sz_str = f"{item.filesize / (1024 * 1024):.1f} MB" if item.filesize > 0 else "-"
            if item.status == VodDownloadStatus.DOWNLOADED:
                st = Text("다운로드", style="bold green")
            elif item.status == VodDownloadStatus.SKIPPED:
                st = Text("건너뜀", style="dim yellow")
            else:
                st = Text("실패", style="bold red")

            table.add_row(
                f"W{item.week_number}",
                f"{item.clip_number}차시",
                item.title,
                st,
                sz_str,
                item.saved_path or (item.error_message or "-"),
            )
        console.print(table)

    summary_str = (
        f"총 {result.total_vods}개 영상 중: "
        f"성공 {result.downloaded_count}개 | 건너뜀 {result.skipped_count}개 | 실패 {result.failed_count}개"
    )
    console.print(f"[bold]{summary_str}[/bold]")


@cli.command("download-vod")
@click.option("--course", "course_query", type=str, default=None, help="다운로드할 과목 이름 또는 약칭")
@click.option("--week", "week_query", type=str, default="current", show_default=True, help="다운로드할 주차 ('current', 'all', 또는 주차 번호)")
@click.option("--video-index", "video_index", type=int, default=None, help="특정 영상 순번 (1-based)")
@click.option("--quality", "quality", type=str, default="best", show_default=True, help="다운로드 영상 화질 ('best', '1080p', '720p', 'worst')")
@click.option("--output-dir", "output_dir", type=click.Path(), default=None, help="다운로드 저장 디렉터리 경로")
@click.option("--overwrite", "overwrite", is_flag=True, help="이미 존재하는 파일도 덮어쓰기하여 재다운로드")
@click.option("--dry-run", "dry_run", is_flag=True, help="실제 다운로드 없이 대상 영상 및 저장 경로 미리 확인")
@click.option("--json", "as_json", is_flag=True, help="결과를 JSON 형식으로 출력합니다.")
@click.option("--relogin", "relogin", is_flag=True, help="캐시된 세션을 무시하고 새로 로그인합니다.")
@click.option("--headed", "headed", is_flag=True, help="브라우저 창을 화면에 표시합니다.")
@click.pass_context
def download_vod_command(
    ctx: click.Context,
    course_query: str | None,
    week_query: str,
    video_index: int | None,
    quality: str,
    output_dir: str | None,
    overwrite: bool,
    dry_run: bool,
    as_json: bool,
    relogin: bool,
    headed: bool,
) -> None:
    """고속 병렬 스트림 다운로드로 VOD 영상을 로컬에 저장합니다 (출석 시청 대기 없음)."""
    from kau_assistant.stream.runner import run_vod_download_pipeline

    err = Console(stderr=True)
    out = Console()

    def _on_progress(msg: str) -> None:
        err.print(msg, markup=False, highlight=False)

    try:
        result = run_vod_download_pipeline(
            course_query=course_query,
            week_query=week_query,
            video_index=video_index,
            preferred_quality=quality,
            output_dir=output_dir,
            overwrite=overwrite,
            dry_run=dry_run,
            relogin=relogin,
            headful=headed,
            progress_callback=_on_progress,
        )
    except Exception as e:
        err.print(f"[오류] VOD 다운로드 처리 실패: {e}", markup=False, highlight=False)
        ctx.exit(2)

    if as_json:
        click.echo(result.model_dump_json(indent=2))
    else:
        render_vod_download_report(result, out)

    if result.failed_count > 0 and not dry_run:
        ctx.exit(1)
    ctx.exit(0)


def _handle_board_command(
    ctx: click.Context,
    command_scope: str,
    course_query: str | None,
    limit: int | None,
    fetch_all: bool,
    detail: bool,
    view_id: str | None,
    unread_only: bool,
    unanswered: bool,
    my_only: bool,
    board_name: str | None,
    mark_read: bool,
    download_attachments: bool,
    as_json: bool,
    relogin: bool,
    headed: bool,
) -> None:
    from kau_assistant.board.reporter import render_article_viewer, render_board_report
    from kau_assistant.board.runner import run_board_pipeline, view_board_article

    _configure_streams()
    err = Console(stderr=True)
    out = Console()

    def _on_progress(msg: str) -> None:
        err.print(msg, markup=False, highlight=False)

    if view_id:
        try:
            post = view_board_article(
                post_id_or_bwid=view_id,
                course_query=course_query,
                download_attachments=download_attachments,
                relogin=relogin,
                headful=headed,
                progress_callback=_on_progress,
            )
        except Exception as e:
            err.print(f"[오류] 게시글 조회 실패: {e}", markup=False, highlight=False)
            ctx.exit(2)

        if as_json:
            click.echo(post.model_dump_json(indent=2))
        else:
            render_article_viewer(post, out)
        ctx.exit(0)

    try:
        report = run_board_pipeline(
            course_query=course_query,
            command_scope=command_scope,  # type: ignore[arg-type]
            limit=limit,
            fetch_all=fetch_all,
            detail=detail,
            unread_only=unread_only,
            unanswered=unanswered,
            my_only=my_only,
            board_name=board_name,
            mark_read=mark_read,
            relogin=relogin,
            headful=headed,
            progress_callback=_on_progress,
        )
    except Exception as e:
        err.print(f"[오류] 게시판 조회 실패: {e}", markup=False, highlight=False)
        ctx.exit(2)

    if as_json:
        click.echo(report.model_dump_json(indent=2))
    else:
        render_board_report(report, out, detail=detail)

    if report.errors:
        ctx.exit(1)
    ctx.exit(0)


def _board_options(func):
    """Decorator sharing options across board, notices, and qna commands."""
    options = [
        click.option("--course", "course_query", type=str, default=None, help="과목 이름, 약칭, 또는 과목 ID (생략 시 전체 수강 과목)"),
        click.option("--limit", "limit", type=int, default=3, show_default=True, help="과목당 조회할 최근 게시글 개수"),
        click.option("--all", "fetch_all", is_flag=True, help="게시판의 모든 게시글을 조회합니다."),
        click.option("--detail", "detail", is_flag=True, help="본문 요약 및 상세 내용을 함께 조회합니다."),
        click.option("--view", "view_id", type=str, default=None, help="특정 게시글 ID(또는 번호)의 본문 전문과 답변을 단독 뷰어로 조회합니다."),
        click.option("--unread-only", "unread_only", is_flag=True, help="아직 확인하지 않은 신규[NEW] 공지만 필터링합니다."),
        click.option("--unanswered", "unanswered", is_flag=True, help="답변 대기 중인 질문만 필터링합니다."),
        click.option("--my", "my_only", is_flag=True, help="내가 작성한 질문만 필터링합니다."),
        click.option("--board-name", "board_name", type=str, default=None, help="조회할 특정 게시판 이름 (비표준 게시판용)"),
        click.option("--mark-read", "mark_read", is_flag=True, help="조회한 게시글을 모두 읽음 처리합니다."),
        click.option("--download-attachments", "download_attachments", is_flag=True, help="게시글에 포함된 첨부파일을 로컬에 다운로드합니다."),
        click.option("--json", "as_json", is_flag=True, help="표준 JSON 계약(schema_version: 1) 형식으로 출력합니다."),
        click.option("--relogin", "relogin", is_flag=True, help="캐시된 세션을 무시하고 새로 로그인합니다."),
        click.option("--headed", "headed", is_flag=True, help="브라우저 창을 화면에 표시합니다."),
        click.pass_context,
    ]
    for opt in reversed(options):
        func = opt(func)
    return func


@cli.command("board")
@_board_options
def board_command(ctx: click.Context, **kwargs) -> None:
    """과목별 공지사항과 Q&A 게시판을 통합 브리핑합니다."""
    _handle_board_command(ctx, command_scope="board", **kwargs)


@cli.command("notices")
@_board_options
def notices_command(ctx: click.Context, **kwargs) -> None:
    """과목별 공지사항 게시판을 브리핑합니다."""
    _handle_board_command(ctx, command_scope="notices", **kwargs)


@cli.command("qna")
@_board_options
def qna_command(ctx: click.Context, **kwargs) -> None:
    """과목별 Q&A(질의응답) 게시판 및 답변 현황을 브리핑합니다."""
    _handle_board_command(ctx, command_scope="qna", **kwargs)


@cli.command("progress")
@click.option("--course", "course_query", type=str, default=None, help="특정 과목 이름, 약칭, 또는 과목 ID (생략 시 전체 수강 과목)")
@click.option("--week", "week_query", type=int, default=None, help="조회할 특정 주차 번호 (생략 시 자동 판별된 이번 주차)")
@click.option("--detail", "detail", is_flag=True, help="모든 주차의 세부 활동 목록을 전개하여 조회합니다.")
@click.option("--cached", "use_cache", is_flag=True, help="10분 이내에 저장된 로컬 캐시 데이터가 있으면 즉시 반환합니다.")
@click.option("--refresh", "refresh", is_flag=True, help="기존 캐시를 무시하고 LMS에서 실시간으로 새로 수집합니다.")
@click.option("--json", "as_json", is_flag=True, help="표준 JSON 계약(schema_version: 1) 규격으로 결과를 출력합니다.")
@click.option("--relogin", "relogin", is_flag=True, help="캐시된 세션을 무시하고 새로 로그인합니다.")
@click.option("--headed", "headed", is_flag=True, help="브라우저 창을 화면에 표시합니다.")
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
    """수강 과목의 4대 활동(동영상, 과제, 퀴즈, 학습자료) 진척도를 종합 대시보드로 브리핑합니다."""
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
            render_course_matrix(report.courses[0], out, week_filter=week_query)
        elif detail:
            render_detailed_activities(report, out)
        else:
            render_progress_dashboard(report, out, detail=detail)

    if report.status == "error" or report.errors:
        ctx.exit(1)
    elif report.summary.missed_past_count > 0:
        ctx.exit(1)
    else:
        ctx.exit(0)


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
