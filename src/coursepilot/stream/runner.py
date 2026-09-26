"""Standalone VOD downloader pipeline and course orchestrator."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Optional

from coursepilot.config import Settings, get_settings
from coursepilot.course_mapping import load_course_mappings
from coursepilot.materials.filename_utils import sanitize_filename
from coursepilot.pipeline import scrape_course
from coursepilot.player.runner import find_target_course
from coursepilot.scraper.course_list import extract_courses
from coursepilot.scraper.models import AttendanceStatus, CourseItem, LectureItem
from coursepilot.scraper.navigator import CourseNavigator
from coursepilot.session_manager import SessionManager
from coursepilot.stream.downloader import SegmentDownloader
from coursepilot.stream.models import (
    CourseVodDownloadResult,
    VodDownloadItemResult,
    VodDownloadRunResult,
    VodDownloadStatus,
)
from coursepilot.stream.parser import parse_stream_manifest
from coursepilot.stream.sniffer import StreamSniffer

logger = logging.getLogger(__name__)


def resolve_candidate_vods_for_download(
    lectures: list[LectureItem],
    week_query: str | int | None = "current",
    video_index: int | None = None,
) -> tuple[str, list[LectureItem]]:
    """Resolves lectures for download without skipping completed lectures (D-14-02, Assumption A-14-03)."""
    if not lectures:
        return ("none", [])

    w_str = str(week_query).strip().lower() if week_query is not None else "current"

    if w_str.isdigit():
        target_week = int(w_str)
        week_label = f"{target_week}주차"
        candidates = [lec for lec in lectures if lec.week_number == target_week]
    elif w_str == "all":
        week_label = "전체 주차"
        candidates = list(lectures)
    else:  # "current"
        uncompleted_weeks = [
            lec.week_number
            for lec in lectures
            if lec.status != AttendanceStatus.COMPLETED and lec.week_number > 0
        ]
        if uncompleted_weeks:
            target_week = min(uncompleted_weeks)
            week_label = f"{target_week}주차"
            candidates = [lec for lec in lectures if lec.week_number == target_week]
        elif lectures:
            max_week = max(lec.week_number for lec in lectures)
            week_label = f"{max_week}주차 (완료)"
            candidates = [lec for lec in lectures if lec.week_number == max_week]
        else:
            week_label = "none"
            candidates = []

    if video_index is not None:
        if 1 <= video_index <= len(candidates):
            candidates = [candidates[video_index - 1]]
        else:
            candidates = []

    return week_label, candidates


def run_vod_download_pipeline(
    course_query: Optional[str] = None,
    week_query: str | int | None = "current",
    video_index: Optional[int] = None,
    preferred_quality: str = "best",
    output_dir: Optional[Path | str] = None,
    overwrite: bool = False,
    dry_run: bool = False,
    relogin: bool = False,
    headful: bool = False,
    settings: Optional[Settings] = None,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> VodDownloadRunResult:
    """Executes high-speed parallel VOD stream downloads without real-time playback delays (D-14-02)."""
    cfg = settings or get_settings()
    output_root = Path(output_dir) if output_dir else cfg.download_dir

    if relogin and cfg.session_cache_path.exists():
        cfg.session_cache_path.unlink()

    sm = SessionManager(settings=cfg, headful=headful, relogin=relogin)
    run_result = VodDownloadRunResult(dry_run=dry_run)

    with sm:
        page = sm.get_authenticated_page()
        all_courses = extract_courses(page, cfg.lms_url)
        mappings = load_course_mappings(cfg.course_mappings_path)

        target_courses: list[CourseItem] = []
        if course_query:
            matched = find_target_course(all_courses, course_query, mappings=mappings)
            if matched:
                target_courses.append(matched)
            else:
                logger.error("No course found matching: %s", course_query)
                return run_result
        else:
            target_courses = all_courses

        run_result.total_courses = len(target_courses)
        navigator = CourseNavigator(settings=cfg)

        for course in target_courses:
            lectures, _ = scrape_course(page, course, navigator)
            week_label, candidate_vods = resolve_candidate_vods_for_download(
                lectures, week_query=week_query, video_index=video_index
            )

            course_res = CourseVodDownloadResult(
                course_id=course.course_id,
                course_name=course.clean_name,
                target_week=week_label,
            )
            run_result.total_vods += len(candidate_vods)

            for vod in candidate_vods:
                safe_title = sanitize_filename(vod.title)
                target_dir = output_root / course.clean_name / f"W{vod.week_number:02d}"
                target_file = target_dir / f"W{vod.week_number:02d}-{vod.clip_number:02d}_{safe_title}.mp4"

                if progress_callback:
                    progress_callback(f"[{course.clean_name}] {vod.title}")

                if dry_run:
                    if target_file.exists() and not overwrite:
                        status = VodDownloadStatus.SKIPPED
                        run_result.skipped_count += 1
                        filesize = target_file.stat().st_size
                    else:
                        status = VodDownloadStatus.DOWNLOADED
                        run_result.downloaded_count += 1
                        filesize = 0

                    course_res.items.append(
                        VodDownloadItemResult(
                            course_name=course.clean_name,
                            week_number=vod.week_number,
                            clip_number=vod.clip_number,
                            title=vod.title,
                            status=status,
                            saved_path=str(target_file),
                            filesize=filesize,
                        )
                    )
                    continue

                # Live download
                if target_file.exists() and not overwrite:
                    run_result.skipped_count += 1
                    course_res.items.append(
                        VodDownloadItemResult(
                            course_name=course.clean_name,
                            week_number=vod.week_number,
                            clip_number=vod.clip_number,
                            title=vod.title,
                            status=VodDownloadStatus.SKIPPED,
                            saved_path=str(target_file),
                            filesize=target_file.stat().st_size,
                        )
                    )
                    continue

                vod_url = vod.link if vod.link.startswith("http") else f"{cfg.lms_url.rstrip('/')}/{vod.link.lstrip('/')}"
                sniffer = StreamSniffer(timeout=10.0)
                sniffer.attach(page)

                stream_url: Optional[str] = None
                try:
                    page.goto(vod_url, wait_until="domcontentloaded")
                    stream_url = sniffer.wait_for_stream(page, timeout=10.0)
                except Exception as e:
                    logger.debug("Page navigation or sniffer error: %s", e)
                finally:
                    sniffer.detach(page)

                if not stream_url:
                    err = f"Failed to detect stream URL within 10s for '{vod.title}'"
                    logger.warning(err)
                    run_result.failed_count += 1
                    course_res.items.append(
                        VodDownloadItemResult(
                            course_name=course.clean_name,
                            week_number=vod.week_number,
                            clip_number=vod.clip_number,
                            title=vod.title,
                            status=VodDownloadStatus.FAILED,
                            error_message=err,
                        )
                    )
                    continue

                # Download stream
                try:
                    dl = SegmentDownloader(settings=cfg)
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

                    saved_path, sz, is_skipped = dl.download_stream(
                        stream_info, target_file, overwrite=overwrite
                    )
                    if is_skipped:
                        status = VodDownloadStatus.SKIPPED
                        run_result.skipped_count += 1
                    else:
                        status = VodDownloadStatus.DOWNLOADED
                        run_result.downloaded_count += 1

                    course_res.items.append(
                        VodDownloadItemResult(
                            course_name=course.clean_name,
                            week_number=vod.week_number,
                            clip_number=vod.clip_number,
                            title=vod.title,
                            status=status,
                            saved_path=str(saved_path),
                            filesize=sz,
                            duration=stream_info.total_duration,
                        )
                    )
                except Exception as exc:
                    logger.error("Download failed for %s: %s", vod.title, exc)
                    run_result.failed_count += 1
                    course_res.items.append(
                        VodDownloadItemResult(
                            course_name=course.clean_name,
                            week_number=vod.week_number,
                            clip_number=vod.clip_number,
                            title=vod.title,
                            status=VodDownloadStatus.FAILED,
                            error_message=str(exc),
                        )
                    )

            run_result.courses.append(course_res)

    return run_result
