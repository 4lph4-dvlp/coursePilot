"""VOD watch pipeline and execution orchestrator."""

from __future__ import annotations

import logging
import re
from typing import Callable

from pydantic import BaseModel, Field

from kau_assistant.config import Settings
from kau_assistant.course_mapping import load_course_mappings
from kau_assistant.domain.models import TaskType
from kau_assistant.domain.naming import format_task_title
from kau_assistant.notion.client import NotionClient
from kau_assistant.pipeline import scrape_course
from kau_assistant.player.models import PlaybackOptions, PlaybackProgress
from kau_assistant.player.vod_player import VodPlayer
from kau_assistant.scraper.course_list import extract_courses
from kau_assistant.scraper.models import AttendanceStatus, CourseItem, LectureItem
from kau_assistant.scraper.navigator import CourseNavigator
from kau_assistant.session_manager import SessionManager

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
    """Finds a CourseItem matching a natural language course query."""
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

    return None


def resolve_candidate_vods(
    lectures: list[LectureItem],
    week_query: str | int | None = "current",
) -> tuple[str, list[LectureItem], int]:
    """Filters lectures into target week's unwatched VODs, returning (week_label, candidate_vods, skipped_count)."""
    # 1. Keep only VOD lectures, excluding OT/orientation lectures
    vods: list[LectureItem] = []
    for lec in lectures:
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

    return (week_label, unwatched, skipped_count)


def watch_course_vods(
    settings: Settings,
    course_query: str,
    week_query: str | int | None = "current",
    *,
    dry_run: bool = False,
    update_notion: bool = False,
    player: VodPlayer | None = None,
    playback_options: PlaybackOptions | None = None,
    session_manager: SessionManager | None = None,
    on_vod_start: Callable[[LectureItem, int, int], None] | None = None,
    on_vod_progress: Callable[[PlaybackProgress], None] | None = None,
    on_vod_complete: Callable[[PlaybackProgress], None] | None = None,
) -> WatchResult:
    """Orchestrates discovering, filtering, and watching incomplete VODs for a course."""
    mappings = load_course_mappings(settings.course_mappings_path)
    vod_player = player or VodPlayer(default_options=playback_options)

    mgr = session_manager or SessionManager(settings=settings, headful=not settings.headless)
    page = mgr.get_authenticated_page()
    navigator = CourseNavigator(settings=settings)

    try:
        # 1. Discover courses and resolve target
        all_courses = extract_courses(page, settings.lms_url)
        target_course = find_target_course(all_courses, course_query, mappings=mappings)

        if not target_course:
            available = ", ".join(c.clean_name for c in all_courses)
            return WatchResult(
                course_id="",
                course_name=course_query,
                target_week=str(week_query),
                error_message=f"과목을 찾을 수 없습니다: '{course_query}' (수강 과목: {available})",
            )

        # 2. Scrape course lectures and activity completion
        lectures, _ = scrape_course(page, target_course, navigator)
        week_label, candidate_vods, skipped_count = resolve_candidate_vods(lectures, week_query)

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

        # 3. Initialize Notion client if requested
        notion_client = None
        existing_notion_pages = {}
        if update_notion and settings.is_notion_configured:
            try:
                notion_client = NotionClient(settings=settings)
                target = notion_client.resolve_target()
                existing_notion_pages = notion_client.query_existing_pages(target.data_source_id)
            except Exception as e:
                logger.warning(f"Failed to query Notion for status update: {e}")

        # 4. Sequentially play unwatched VODs
        for idx, vod in enumerate(candidate_vods, start=1):
            if on_vod_start:
                on_vod_start(vod, idx, len(candidate_vods))

            vod_url = vod.link
            if not vod_url.startswith("http"):
                vod_url = f"{settings.lms_url.rstrip('/')}/{vod_url.lstrip('/')}"

            playback_res = vod_player.play_vod(
                page=page,
                vod_url=vod_url,
                title=vod.full_title or vod.title,
                options=playback_options,
                on_progress=on_vod_progress,
            )
            result.playback_results.append(playback_res)

            if playback_res.is_completed:
                result.completed_vods += 1
                if on_vod_complete:
                    on_vod_complete(playback_res)

                # 5. Optionally update Notion status
                if notion_client:
                    task_title = format_task_title(
                        course_name=target_course.clean_name,
                        raw_title=vod.title,
                        task_type=TaskType.LECTURE,
                        week_number=vod.week_number,
                        clip_number=vod.clip_number,
                        course_mappings=mappings,
                    )
                    notion_page = existing_notion_pages.get(task_title)
                    if notion_page:
                        try:
                            notion_client.mark_task_completed(notion_page.page_id)
                            result.notion_updated_count += 1
                            logger.info(f"Updated Notion task '{task_title}' to '완료'")
                        except Exception as e:
                            logger.warning(f"Failed to update Notion task '{task_title}': {e}")

        return result

    finally:
        if session_manager is None:
            mgr.close()
