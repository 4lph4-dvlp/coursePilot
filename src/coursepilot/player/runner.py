"""VOD watch pipeline and execution orchestrator with precision targeting and state tracking."""

from __future__ import annotations

import logging
import os
import re
import threading
from pathlib import Path
from typing import Callable

from pydantic import BaseModel, Field

from coursepilot.config import Settings
from coursepilot.course_mapping import load_course_mappings
from coursepilot.domain.models import TaskType
from coursepilot.domain.naming import format_task_title
from coursepilot.notion.client import NotionClient, index_unique_pages_by_title
from coursepilot.pipeline import scrape_course
from coursepilot.player.models import PlaybackOptions, PlaybackProgress, WatchState
from coursepilot.player.state import WatchStateManager
from coursepilot.player.vod_player import VodPlayer
from coursepilot.scraper.course_list import extract_courses
from coursepilot.scraper.models import AttendanceStatus, CourseItem, LectureItem
from coursepilot.scraper.navigator import CourseNavigator
from coursepilot.session_manager import SessionManager

logger = logging.getLogger(__name__)


class WatchResult(BaseModel):
    """Overall outcome of a course VOD watch execution."""

    course_id: str
    course_name: str
    target_week: str
    total_vods: int = 0
    completed_vods: int = 0
    skipped_vods: int = 0
    playback_results: list[PlaybackProgress] = Field(default_factory=list)
    notion_updated_count: int = 0
    dry_run: bool = False
    error_message: str | None = None


def find_target_course(
    courses: list[CourseItem],
    query: str,
    mappings: dict[str, str] | None = None,
) -> CourseItem | None:
    """Finds a CourseItem matching a natural language course query with fuzzy tolerance (D-12-03)."""
    q = query.strip().lower()
    maps = mappings or {}

    # 1. Exact match by clean_name, raw_name, course_id, or mapped abbr
    for c in courses:
        if q in (c.clean_name.lower(), c.raw_name.lower(), c.course_id.lower()):
            return c
        abbr = maps.get(c.clean_name, "").lower()
        if abbr and q == abbr:
            return c

    # 2. Substring match
    for c in courses:
        if q in c.clean_name.lower() or q in c.raw_name.lower():
            return c
        abbr = maps.get(c.clean_name, "").lower()
        if abbr and (q in abbr or abbr in q):
            return c

    # 3. Substring in reverse (course name in query)
    for c in courses:
        if c.clean_name.lower() in q or c.raw_name.lower() in q:
            return c

    # 4. Fuzzy & Token Overlap matching (D-12-03)
    def normalize_term(text: str) -> str:
        cleaned = re.sub(r"[\s\-_/()]+", "", text.lower())
        for generic in ("정보", "실험", "실습", "강의", "교과", "이론", "개론", "입문"):
            cleaned = cleaned.replace(generic, "")
        return cleaned

    norm_q = normalize_term(q)
    if len(norm_q) >= 2:
        for c in courses:
            norm_c = normalize_term(c.clean_name)
            if norm_c and (norm_q in norm_c or norm_c in norm_q):
                return c

    # Subsequence check: all characters of course appear in query in order
    def is_subseq(sub: str, full: str) -> bool:
        it = iter(full)
        return all(char in it for char in sub)

    for c in courses:
        clean_c = re.sub(r"[\s\-_/()]+", "", c.clean_name.lower())
        clean_q = re.sub(r"[\s\-_/()]+", "", q)
        if len(clean_c) >= 3 and is_subseq(clean_c, clean_q):
            return c

    return None


def resolve_candidate_vods(
    lectures: list[LectureItem],
    week_query: str | int | None = "current",
    video_index: int | None = None,
) -> tuple[str, list[LectureItem], int]:
    """Filters lectures into target week's unwatched VODs with optional video index filtering (D-12-02)."""
    # 1. Keep only VOD lectures, excluding OT/orientation lectures
    vods: list[LectureItem] = []
    for lec in lectures:
        if not lec.is_available:
            continue
        if lec.week_number == 0:
            continue
        title_lower = (lec.title + " " + lec.full_title).lower()
        if any(k in title_lower for k in ("오리엔테이션", "orientation", "강의 개요", "과목 소개")):
            continue
        if "/mod/vod/" in lec.link or "동영상" in lec.title or lec.link:
            vods.append(lec)

    if not vods:
        return ("none", [], 0)

    # 2. Week resolution
    w_str = str(week_query).strip().lower() if week_query is not None else "current"

    if w_str.isdigit():
        target_week = int(w_str)
        week_label = f"{target_week}주차"
        selected = [v for v in vods if v.week_number == target_week]
    elif w_str == "all":
        week_label = "전체 주차"
        selected = vods
    else:  # "current" or default
        # Find earliest week with incomplete VODs
        incomplete_weeks = [v.week_number for v in vods if v.status != AttendanceStatus.COMPLETED]
        if incomplete_weeks:
            target_week = min(incomplete_weeks)
            week_label = f"{target_week}주차"
            selected = [v for v in vods if v.week_number == target_week]
        else:
            # All complete; pick highest available week
            max_week = max(v.week_number for v in vods)
            week_label = f"{max_week}주차 (완강)"
            selected = [v for v in vods if v.week_number == max_week]

    unwatched = [v for v in selected if v.status != AttendanceStatus.COMPLETED]
    skipped_count = len(selected) - len(unwatched)

    # 3. Precision video index selection (D-12-02)
    if video_index is not None:
        if 1 <= video_index <= len(unwatched):
            selected_video = unwatched[video_index - 1]
            skipped_count += len(unwatched) - 1
            unwatched = [selected_video]
        else:
            skipped_count += len(unwatched)
            unwatched = []

    return (week_label, unwatched, skipped_count)


def watch_course_vods(
    settings: Settings,
    course_query: str,
    week_query: str | int | None = "current",
    video_index: int | None = None,
    *,
    dry_run: bool = False,
    update_notion: bool = False,
    download: bool = False,
    preferred_quality: str = "best",
    overwrite: bool = False,
    output_dir: Path | str | None = None,
    player: VodPlayer | None = None,
    playback_options: PlaybackOptions | None = None,
    session_manager: SessionManager | None = None,
    state_manager: WatchStateManager | None = None,
    on_vod_start: Callable[[LectureItem, int, int], None] | None = None,
    on_vod_progress: Callable[[PlaybackProgress], None] | None = None,
    on_vod_complete: Callable[[PlaybackProgress], None] | None = None,
) -> WatchResult:
    """Orchestrates discovering, filtering, and watching incomplete VODs with state tracking (D-12-01..D-12-07)."""
    mappings = load_course_mappings(settings.course_mappings_path)
    vod_player = player or VodPlayer(default_options=playback_options)
    sm = state_manager or WatchStateManager(settings=settings)

    mgr = session_manager or SessionManager(settings=settings, headful=not settings.headless)
    page = mgr.get_authenticated_page()
    navigator = CourseNavigator(settings=settings)
    target_course: CourseItem | None = None
    candidate_vods: list[LectureItem] = []
    week_label: str = ""

    try:
        # 1. Discover courses and resolve target
        all_courses = extract_courses(page, settings.lms_url)
        target_course = find_target_course(all_courses, course_query, mappings=mappings)

        if not target_course:
            available = ", ".join(c.clean_name for c in all_courses)
            err_msg = f"과목을 찾을 수 없습니다: '{course_query}' (수강 과목: {available})"
            sm.write_state(
                WatchState(
                    status="error",
                    course_name=course_query,
                    pid=os.getpid(),
                    error_message=err_msg,
                )
            )
            return WatchResult(
                course_id="",
                course_name=course_query,
                target_week=str(week_query),
                error_message=err_msg,
            )

        # 2. Scrape course lectures and activity completion
        lectures, _ = scrape_course(page, target_course, navigator)
        week_label, candidate_vods, skipped_count = resolve_candidate_vods(
            lectures, week_query, video_index=video_index
        )

        result = WatchResult(
            course_id=target_course.course_id,
            course_name=target_course.clean_name,
            target_week=week_label,
            total_vods=len(candidate_vods),
            skipped_vods=skipped_count,
            dry_run=dry_run,
        )

        if dry_run or not candidate_vods:
            return result

        # 3. Initialize initial state in watch_state.json (D-12-04)
        sm.write_state(
            WatchState(
                status="running",
                pid=os.getpid(),
                course_name=target_course.clean_name,
                course_id=target_course.course_id,
                target_week=week_label,
                video_index=video_index or 1,
                total_videos=len(candidate_vods),
                current_video_title=candidate_vods[0].title if candidate_vods else "",
            )
        )

        # 4. Initialize Notion client if requested
        notion_client = None
        existing_notion_pages = {}
        if update_notion and settings.is_notion_configured:
            try:
                notion_client = NotionClient(settings=settings)
                target = notion_client.resolve_target()
                existing_notion_pages, ambiguous_titles = index_unique_pages_by_title(
                    notion_client.query_existing_pages(target.data_source_id)
                )
                if ambiguous_titles:
                    logger.warning("Ambiguous Scheduler titles found; their completion updates will be skipped")
            except Exception as e:
                logger.warning(f"Failed to query Notion for status update: {e}")

        output_root = Path(output_dir) if output_dir else settings.download_dir

        # 5. Sequentially play unwatched VODs (D-12-01)
        for idx, vod in enumerate(candidate_vods, start=1):
            # Check if execution was stopped via watch stop (D-12-06)
            current_state = sm.read_state()
            if current_state and current_state.status == "stopped":
                logger.info("Watch state marked as stopped; aborting playback.")
                result.error_message = "사용자에 의해 시청이 중단되었습니다."
                break

            if on_vod_start:
                on_vod_start(vod, idx, len(candidate_vods))

            vod_url = vod.link
            if not vod_url.startswith("http"):
                vod_url = f"{settings.lms_url.rstrip('/')}/{vod_url.lstrip('/')}"

            def _wrapped_progress(p: PlaybackProgress) -> None:
                rem_secs = max(0.0, p.duration - p.current_time) if p.duration > 0 else 0.0
                sm.write_state(
                    WatchState(
                        status="running",
                        pid=os.getpid(),
                        course_name=target_course.clean_name,
                        course_id=target_course.course_id,
                        target_week=week_label,
                        video_index=idx,
                        total_videos=len(candidate_vods),
                        current_video_title=vod.title,
                        duration=p.duration,
                        current_time=p.current_time,
                        progress_percent=p.progress_percent,
                        remaining_seconds=rem_secs,
                    )
                )
                if on_vod_progress:
                    on_vod_progress(p)

            bg_thread: threading.Thread | None = None
            _on_stream_detected = None

            if download:
                from coursepilot.materials.filename_utils import sanitize_filename
                from coursepilot.stream.downloader import SegmentDownloader
                from coursepilot.stream.parser import parse_stream_manifest

                safe_title = sanitize_filename(vod.title)
                target_dir = output_root / target_course.clean_name / f"W{vod.week_number:02d}"
                target_file = target_dir / f"W{vod.week_number:02d}-{vod.clip_number:02d}_{safe_title}.mp4"

                def _create_stream_callback(t_file: Path, v_title: str):
                    def _on_detected(stream_url: str) -> None:
                        nonlocal bg_thread

                        def _bg_download() -> None:
                            try:
                                dl = SegmentDownloader(settings=settings)
                                resp = dl.client.get(stream_url, timeout=15.0)
                                resp.raise_for_status()
                                media_url, stream_info = parse_stream_manifest(
                                    resp.text, stream_url, preferred_quality=preferred_quality
                                )
                                if not stream_info.segments and not stream_info.is_direct_mp4:
                                    resp_media = dl.client.get(media_url, timeout=15.0)
                                    resp_media.raise_for_status()
                                    _, stream_info = parse_stream_manifest(
                                        resp_media.text, media_url, preferred_quality=preferred_quality
                                    )
                                dl.download_stream(stream_info, t_file, overwrite=overwrite)
                                logger.info("Background download completed: %s", t_file.name)
                            except Exception as exc:
                                logger.warning(
                                    "Background download failed for '%s': %s. Attendance playback continues unaffected (D-14-04).",
                                    v_title,
                                    exc,
                                )

                        bg_thread = threading.Thread(
                            target=_bg_download,
                            name=f"bg_dl_w{vod.week_number}_{vod.clip_number}",
                            daemon=True,
                        )
                        bg_thread.start()

                    return _on_detected

                _on_stream_detected = _create_stream_callback(target_file, vod.title)

            playback_res = vod_player.play_vod(
                page=page,
                vod_url=vod_url,
                title=vod.full_title or vod.title,
                options=playback_options,
                session_manager=mgr,
                on_progress=_wrapped_progress,
                on_stream_detected=_on_stream_detected,
            )

            if bg_thread and bg_thread.is_alive():
                logger.info("Waiting for background download thread for '%s'...", vod.title)
                bg_thread.join(timeout=60.0)
                if bg_thread.is_alive():
                    logger.warning(
                        "Background download for '%s' still running after join timeout.",
                        vod.title,
                    )
            result.playback_results.append(playback_res)

            # Check if stopped mid-playback
            current_state = sm.read_state()
            if current_state and current_state.status == "stopped":
                result.error_message = "사용자에 의해 시청이 중단되었습니다."
                break

            if playback_res.is_completed:
                result.completed_vods += 1
                if on_vod_complete:
                    on_vod_complete(playback_res)

                # Format task title
                task_title = format_task_title(
                    course_name=target_course.clean_name,
                    raw_title=vod.title,
                    task_type=TaskType.LECTURE,
                    week_number=vod.week_number,
                    clip_number=vod.clip_number,
                    course_mappings=mappings,
                )

                # 6. Optionally update Notion status
                notion_completed = False
                if notion_client:
                    notion_page = existing_notion_pages.get(task_title)
                    if notion_page:
                        try:
                            notion_client.mark_task_completed(notion_page.page_id)
                            result.notion_updated_count += 1
                            notion_completed = True
                            logger.info(f"Updated Notion task '{task_title}' to '완료'")
                        except Exception as e:
                            logger.warning(f"Failed to update Notion task '{task_title}': {e}")

                # 7. Record completed video to history (D-12-07)
                sm.record_completed_video(
                    course_id=target_course.course_id,
                    course_name=target_course.clean_name,
                    target_week=week_label,
                    video_title=vod.title,
                    task_title=task_title,
                    notion_completed=notion_completed,
                )

        return result

    except Exception as e:
        logger.error(f"VOD execution failed: {e}")
        result = WatchResult(
            course_id=target_course.course_id if target_course else "",
            course_name=target_course.clean_name if target_course else course_query,
            target_week=week_label or str(week_query),
            error_message=str(e),
        )
        return result

    finally:
        # Finalize watch state
        final_state = sm.read_state()
        if final_state and final_state.status != "stopped":
            if result.error_message:
                sm.write_state(
                    WatchState(
                        status="error",
                        course_name=target_course.clean_name if target_course else course_query,
                        pid=os.getpid(),
                        error_message=result.error_message,
                    )
                )
            elif not dry_run and candidate_vods:
                sm.write_state(
                    WatchState(
                        status="completed",
                        course_name=target_course.clean_name if target_course else course_query,
                        course_id=target_course.course_id if target_course else "",
                        target_week=week_label,
                        total_videos=len(candidate_vods),
                        video_index=len(candidate_vods),
                        current_video_title=candidate_vods[-1].title if candidate_vods else "",
                        progress_percent=100.0,
                        pid=os.getpid(),
                    )
                )

        if session_manager is None:
            mgr.close()
