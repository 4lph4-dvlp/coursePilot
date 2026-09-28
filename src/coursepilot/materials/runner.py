"""Materials execution orchestrator with multi-course and week filtering."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable
import httpx

from coursepilot.config import Settings, get_settings
from coursepilot.course_mapping import load_course_mappings
from coursepilot.materials.downloader import (
    ViewOnlyMaterialError,
    download_material_file,
    get_authenticated_httpx_client,
    mark_material_viewed,
)
from coursepilot.materials.filename_utils import sanitize_filename
from coursepilot.materials.models import (
    CourseMaterialsResult,
    MaterialDownloadResult,
    MaterialItem,
    MaterialsRunResult,
    MaterialStatus,
)
from coursepilot.player.runner import find_target_course
from coursepilot.scraper.course_list import extract_courses
from coursepilot.scraper.material_parser import parse_materials_from_course_sections
from coursepilot.scraper.models import CourseItem
from coursepilot.scraper.navigator import CourseNavigator
from coursepilot.session_manager import SessionManager

logger = logging.getLogger(__name__)


def resolve_candidate_materials(
    materials: list[MaterialItem],
    week_query: str | int | None = "current",
) -> tuple[str, list[MaterialItem]]:
    """Filters materials into target week according to week query ('current', 'all', or week number)."""
    if not materials:
        return ("none", [])

    w_str = str(week_query).strip().lower() if week_query is not None else "current"

    if w_str.isdigit():
        target_week = int(w_str)
        week_label = f"{target_week}주차"
        selected = [m for m in materials if m.week_number == target_week]
    elif w_str == "all":
        week_label = "전체 주차"
        selected = materials
    else:  # "current" or default
        uncompleted_weeks = [m.week_number for m in materials if not m.is_completed]
        if uncompleted_weeks:
            target_week = min(uncompleted_weeks)
            week_label = f"{target_week}주차"
            selected = [m for m in materials if m.week_number == target_week]
        else:
            # All complete; pick highest available week
            max_week = max(m.week_number for m in materials)
            week_label = f"{max_week}주차 (완료)"
            selected = [m for m in materials if m.week_number == max_week]

    return (week_label, selected)


def process_course_materials(
    course: CourseItem,
    materials: list[MaterialItem],
    target_week: str,
    output_root: Path,
    client: httpx.Client | None = None,
    dry_run: bool = False,
    no_download: bool = False,
    progress_callback: Callable[[str], None] | None = None,
) -> CourseMaterialsResult:
    """Processes a list of materials for a single course, handling smart visits and downloads."""
    results: list[MaterialDownloadResult] = []

    for idx, item in enumerate(materials, 1):
        target_dir = output_root / course.clean_name / f"W{item.week_number}"

        if not item.is_available:
            results.append(MaterialDownloadResult(
                item=item, status=MaterialStatus.SKIPPED,
                view_success=False, error_message="아직 공개되지 않은 학습자료입니다.",
            ))
            continue

        if progress_callback:
            progress_callback(
                f"[{course.clean_name}] ({idx}/{len(materials)}) {item.title}"
            )

        if dry_run:
            safe_name = sanitize_filename(item.suggested_filename or item.title)
            planned_path = target_dir / safe_name
            results.append(
                MaterialDownloadResult(
                    item=item,
                    status=MaterialStatus.PLANNED,
                    filename=safe_name,
                    saved_path=str(planned_path) if not no_download else "",
                    view_success=False,
                )
            )
            continue

        # Normal execution
        view_success = False
        if not item.is_completed and client is not None:
            view_success = mark_material_viewed(client, item)
        else:
            view_success = item.is_completed

        if no_download:
            results.append(
                MaterialDownloadResult(
                    item=item,
                    status=MaterialStatus.VIEWED_ONLY,
                    view_success=view_success,
                )
            )
            continue

        # Download file
        if client is None:
            results.append(
                MaterialDownloadResult(
                    item=item,
                    status=MaterialStatus.FAILED,
                    view_success=view_success,
                    error_message="HTTP client is not initialized",
                )
            )
            continue

        try:
            saved_path, size, is_skipped = download_material_file(client, item, target_dir)
            status = MaterialStatus.SKIPPED if is_skipped else MaterialStatus.DOWNLOADED
            results.append(
                MaterialDownloadResult(
                    item=item,
                    status=status,
                    filename=saved_path.name,
                    saved_path=str(saved_path),
                    filesize=size,
                    view_success=view_success,
                )
            )
        except ViewOnlyMaterialError as e:
            results.append(MaterialDownloadResult(
                item=item,
                status=MaterialStatus.VIEWED_ONLY if view_success else MaterialStatus.FAILED,
                view_success=view_success,
                error_message=str(e),
            ))
        except Exception as e:
            logger.exception("Failed to download material %s: %s", item.title, e)
            results.append(
                MaterialDownloadResult(
                    item=item,
                    status=MaterialStatus.FAILED,
                    view_success=view_success,
                    error_message=str(e),
                )
            )

    return CourseMaterialsResult(
        course_id=course.course_id,
        course_name=course.clean_name,
        target_week=target_week,
        items=results,
    )


def run_materials_pipeline(
    course_query: str | None = None,
    week_query: str | int | None = "current",
    output_dir: Path | str | None = None,
    no_download: bool = False,
    dry_run: bool = False,
    relogin: bool = False,
    headful: bool = False,
    settings: Settings | None = None,
    progress_callback: Callable[[str], None] | None = None,
) -> MaterialsRunResult:
    """Orchestrates materials viewing and downloading across courses and weeks."""
    cfg = settings or get_settings()

    if output_dir:
        output_root = Path(output_dir)
    else:
        output_root = cfg.download_dir

    if relogin and cfg.session_cache_path.exists():
        try:
            cfg.session_cache_path.unlink()
        except Exception:
            pass

    client: httpx.Client | None = None
    if not dry_run:
        client = get_authenticated_httpx_client(cfg)

    course_results: list[CourseMaterialsResult] = []

    try:
        with SessionManager(settings=cfg, headful=headful) as sm:
            page = sm.get_authenticated_page()
            courses = extract_courses(page, cfg.lms_url)

            if course_query:
                mappings = load_course_mappings(cfg.course_mappings_path)
                target_course = find_target_course(courses, course_query, mappings)
                if not target_course:
                    raise ValueError(f"과목 검색어와 일치하는 강좌를 찾을 수 없습니다: '{course_query}'")
                target_courses = [target_course]
            else:
                target_courses = courses

            navigator = CourseNavigator(cfg)
            for c in target_courses:
                if progress_callback:
                    progress_callback(f"과목 진입 중: {c.clean_name}")

                navigator.navigate_to_course(page, c)
                html = page.content()
                materials = parse_materials_from_course_sections(html, c)
                target_week, selected_materials = resolve_candidate_materials(materials, week_query)

                course_res = process_course_materials(
                    course=c,
                    materials=selected_materials,
                    target_week=target_week,
                    output_root=output_root,
                    client=client,
                    dry_run=dry_run,
                    no_download=no_download,
                    progress_callback=progress_callback,
                )
                course_results.append(course_res)
    finally:
        if client is not None:
            try:
                client.close()
            except Exception:
                pass

    total_courses = len(course_results)
    total_materials = sum(len(c.items) for c in course_results)
    downloaded_count = sum(
        1 for c in course_results for i in c.items if i.status == MaterialStatus.DOWNLOADED
    )
    skipped_count = sum(
        1 for c in course_results for i in c.items if i.status == MaterialStatus.SKIPPED
    )
    viewed_count = sum(1 for c in course_results for i in c.items if i.view_success)
    failed_count = sum(
        1 for c in course_results for i in c.items if i.status == MaterialStatus.FAILED
    )

    return MaterialsRunResult(
        total_courses=total_courses,
        total_materials=total_materials,
        downloaded_count=downloaded_count,
        skipped_count=skipped_count,
        viewed_count=viewed_count,
        failed_count=failed_count,
        dry_run=dry_run,
        no_download=no_download,
        courses=course_results,
    )
