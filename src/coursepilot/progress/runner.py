"""Progress collection pipeline runner with single-trip HTML scraping, atomic caching, and course error isolation."""

from datetime import datetime
import json
import logging
from pathlib import Path
import re
from typing import Callable
from bs4 import BeautifulSoup
import httpx

from coursepilot.config import Settings, get_settings
from coursepilot.course_mapping import get_abbreviation, load_course_mappings
from coursepilot.materials.downloader import get_authenticated_httpx_client
from coursepilot.player.runner import find_target_course
from coursepilot.progress.calculator import (
    SectionMeta,
    aggregate_dashboard_summary,
    calculate_course_progress,
    detect_current_week,
)
from coursepilot.progress.models import (
    SCHEMA_VERSION,
    ActivityBreakdown,
    ActivityItem,
    ActivityType,
    CourseProgress,
    DashboardSummary,
    ProgressReport,
)
from coursepilot.report_models import ErrorItem, ReportNotice
from coursepilot.scraper.assessment_parser import (
    is_quiz_attempt_completed,
    parse_assessment_list,
    merge_section_assessments,
)
from coursepilot.scraper.course_list import extract_courses
from coursepilot.scraper.date_parser import KST, get_current_kst_time, parse_lms_date
from coursepilot.scraper.lecture_parser import (
    _parse_week_number,
    merge_ublogs_completion,
    parse_lectures_from_course_sections,
    parse_ublogs_completion,
)
from coursepilot.scraper.material_parser import parse_materials_from_course_sections
from coursepilot.scraper.course_sections import needs_section_view, sections_url, validate_activity_coverage
from coursepilot.scraper.models import (
    AssessmentType,
    AttendanceStatus,
    CourseItem,
    SubmissionStatus,
)
from coursepilot.session_manager import SessionManager

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 600  # 10 minutes (D-16-14)


def load_progress_cache(
    cache_path: Path,
    max_age_seconds: int = CACHE_TTL_SECONDS,
    now: datetime | None = None,
) -> ProgressReport | None:
    """Loads and validates cached progress report if within max_age_seconds TTL."""
    if not cache_path.exists():
        return None

    try:
        content = cache_path.read_text(encoding="utf-8")
        data = json.loads(content)
        report = ProgressReport.model_validate(data)

        current_time = now or get_current_kst_time()
        gen_time = report.generated_at
        if gen_time.tzinfo is None:
            gen_time = gen_time.replace(tzinfo=KST)
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=KST)

        age = (current_time - gen_time).total_seconds()
        if age > max_age_seconds:
            logger.debug(f"Progress cache expired: {age:.1f}s > {max_age_seconds}s")
            return None

        report.is_cached = True
        return report
    except Exception as e:
        logger.debug(f"Failed to load or validate progress cache: {e}")
        return None


def save_progress_cache(cache_path: Path, report: ProgressReport) -> None:
    """Atomically saves progress report to cache file using a temporary replacement."""
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_file = cache_path.with_suffix(".tmp")
        tmp_file.write_text(report.model_dump_json(indent=2), encoding="utf-8")
        tmp_file.replace(cache_path)
    except Exception as e:
        logger.warning(f"Failed to save progress cache to {cache_path}: {e}")


def extract_course_sections_meta(html: str) -> list[SectionMeta]:
    """Extracts section titles, week numbers, date boundaries, and .current flags from course home HTML."""
    soup = BeautifulSoup(html, "lxml")
    sections_meta: list[SectionMeta] = []

    # Find section elements (e.g. li.section or li.course-section)
    section_lis = soup.find_all("li", class_=re.compile(r"\bsection\b"))
    course_sections = [li for li in section_lis if li.get("id", "").startswith("section-")]
    if not course_sections:
        course_sections = soup.find_all("li", class_=re.compile(r"\bcourse-section\b"))

    for idx, li in enumerate(course_sections):
        classes = li.get("class", [])
        is_current = "current" in classes or "current-section" in classes

        # Extract title
        title = ""
        sec_name_el = li.find(["h3", "h4", "span", "div"], class_=re.compile(r"sectionname|section-title", re.I))
        if sec_name_el:
            title = sec_name_el.get_text(strip=True)
        elif li.get("aria-label"):
            title = li.get("aria-label", "").strip()

        # Parse week number
        week_num = None
        if title:
            week_num = _parse_week_number(title, default=None)
        if week_num is None:
            sec_id = li.get("id", "")
            m_sec = re.search(r"section-(\d+)", sec_id)
            if m_sec:
                week_num = int(m_sec.group(1))
            else:
                week_num = idx

        # Extract date range from display options or text-ubstrap
        start_date: datetime | None = None
        end_date: datetime | None = None

        date_el = li.find(class_=re.compile(r"text-ubstrap|period|date|displayoptions", re.I))
        raw_date_text = date_el.get_text(strip=True) if date_el else ""
        if not raw_date_text:
            for span in li.find_all(["span", "div"], class_=re.compile(r"text-muted|sub-title|date", re.I)):
                t = span.get_text(strip=True)
                if "~" in t or re.search(r"\d{4}[-./]\d{1,2}[-./]\d{1,2}", t):
                    raw_date_text = t
                    break

        if raw_date_text:
            if "~" in raw_date_text:
                parts = raw_date_text.split("~")
                start_part = parts[0].strip()
                end_part = parts[1].strip()
                start_date, _ = parse_lms_date(start_part)
                end_date, _ = parse_lms_date(end_part)
            else:
                end_date, _ = parse_lms_date(raw_date_text)

        sections_meta.append(
            SectionMeta(
                week_number=week_num or 0,
                title=title,
                start_date=start_date,
                end_date=end_date,
                is_current=is_current,
            )
        )

    return sections_meta


def _collect_single_course_progress(
    client: httpx.Client,
    course: CourseItem,
    settings: Settings,
    mappings: dict[str, str] | None = None,
    now: datetime | None = None,
) -> CourseProgress:
    """Collects all 4 activity types from an LXP course with single-trip home HTML extraction."""
    current_time = now or get_current_kst_time()
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=KST)

    base_lms_url = settings.lms_url.rstrip("/")

    # 1. Single-trip course home fetch (D-16-13)
    resp = client.get(course.url)
    resp.raise_for_status()
    course_html = resp.text
    if needs_section_view(course_html):
        resp = client.get(sections_url(course.url))
        resp.raise_for_status()
        course_html = resp.text
    validate_activity_coverage(course_html, course)

    # Extract lectures, materials, sections metadata from course home HTML
    lectures = parse_lectures_from_course_sections(course_html, course)
    materials = parse_materials_from_course_sections(course_html, course)
    sections_meta = extract_course_sections_meta(course_html)

    # 2. Fetch ublogs completion for video lectures
    ublogs_url = f"{base_lms_url}/report/ublogs/completion.php?id={course.course_id}"
    try:
        ub_resp = client.get(ublogs_url)
        if ub_resp.status_code == 200:
            ub_rows = parse_ublogs_completion(ub_resp.text)
            lectures = merge_ublogs_completion(lectures, ub_rows)
    except Exception as e:
        logger.debug(f"Failed to fetch/merge ubcompletion for course {course.course_id}: {e}")

    # 3. Fetch assessments (assignments and quizzes)
    assign_url = f"{base_lms_url}/mod/assign/index.php?id={course.course_id}"
    quiz_url = f"{base_lms_url}/mod/quiz/index.php?id={course.course_id}"

    assignments = []
    try:
        asg_resp = client.get(assign_url)
        asg_resp.raise_for_status()
        if asg_resp.status_code == 200:
            assignments = parse_assessment_list(
                asg_resp.text,
                course_id=course.course_id,
                item_type=AssessmentType.ASSIGNMENT,
                base_url=assign_url,
            )
    except Exception as e:
        raise RuntimeError("과제 목록 수집에 실패했습니다.") from e

    quizzes = []
    try:
        quiz_resp = client.get(quiz_url)
        quiz_resp.raise_for_status()
        if quiz_resp.status_code == 200:
            quizzes = parse_assessment_list(
                quiz_resp.text,
                course_id=course.course_id,
                item_type=AssessmentType.QUIZ,
                base_url=quiz_url,
            )
    except Exception as e:
        raise RuntimeError("퀴즈 목록 수집에 실패했습니다.") from e

    assessments = merge_section_assessments(assignments + quizzes, course_html, course)
    assignments = [a for a in assessments if a.item_type == AssessmentType.ASSIGNMENT]
    quizzes = [a for a in assessments if a.item_type == AssessmentType.QUIZ]

    # For quizzes: verify completion status via quiz view page (Pitfall 3)
    for q in quizzes:
        if q.status in (SubmissionStatus.NOT_ATTEMPTED, SubmissionStatus.DRAFT) and q.url and q.is_available:
            try:
                q_detail_resp = client.get(q.url)
                if q_detail_resp.status_code == 200:
                    if is_quiz_attempt_completed(q_detail_resp.text):
                        q.status = SubmissionStatus.SUBMITTED
                        q.is_overdue = False
            except Exception as e:
                logger.debug(f"Failed to verify quiz detail for {q.title}: {e}")

    # 4. Transform all items into unified ActivityItem DTOs
    activities: list[ActivityItem] = []

    # VOD
    for lec in lectures:
        is_done = (lec.status == AttendanceStatus.COMPLETED)
        is_urgent = bool(lec.due_date and 0 <= (lec.due_date - current_time).total_seconds() <= 86400 and not is_done)
        activities.append(
            ActivityItem(
                course_id=course.course_id,
                activity_type=ActivityType.VOD,
                week_number=lec.week_number or 1,
                title=lec.title,
                is_completed=is_done,
                due_date=lec.due_date,
                raw_due_date=lec.raw_due_date,
                is_overdue=lec.is_overdue,
                is_urgent=is_urgent,
                url=lec.link,
                module_id=lec.module_id,
                start_date=lec.start_date,
                is_available=lec.is_available,
                clip_number=lec.clip_number,
            )
        )

    # Assignments
    for asmt in assignments:
        is_done = (asmt.status in (SubmissionStatus.SUBMITTED, SubmissionStatus.GRADED))
        is_urgent = bool(asmt.due_date and 0 <= (asmt.due_date - current_time).total_seconds() <= 86400 and not is_done)
        activities.append(
            ActivityItem(
                course_id=course.course_id,
                activity_type=ActivityType.ASSIGNMENT,
                week_number=asmt.week_number or 1,
                title=asmt.title,
                is_completed=is_done,
                due_date=asmt.due_date,
                raw_due_date=asmt.raw_due_date,
                is_overdue=asmt.is_overdue,
                is_urgent=is_urgent,
                url=asmt.url,
                module_id=asmt.item_id,
                start_date=asmt.start_date,
                is_available=asmt.is_available,
            )
        )

    # Quizzes
    for qz in quizzes:
        is_done = (qz.status in (SubmissionStatus.SUBMITTED, SubmissionStatus.GRADED))
        is_urgent = bool(qz.due_date and 0 <= (qz.due_date - current_time).total_seconds() <= 86400 and not is_done)
        activities.append(
            ActivityItem(
                course_id=course.course_id,
                activity_type=ActivityType.QUIZ,
                week_number=qz.week_number or 1,
                title=qz.title,
                is_completed=is_done,
                due_date=qz.due_date,
                raw_due_date=qz.raw_due_date,
                is_overdue=qz.is_overdue,
                is_urgent=is_urgent,
                url=qz.url,
                module_id=qz.item_id,
                start_date=qz.start_date,
                is_available=qz.is_available,
            )
        )

    # Materials
    for mat in materials:
        is_done = mat.is_completed
        is_urgent = bool(mat.due_date and 0 <= (mat.due_date - current_time).total_seconds() <= 86400 and not is_done)
        activities.append(
            ActivityItem(
                course_id=course.course_id,
                activity_type=ActivityType.MATERIAL,
                week_number=mat.week_number or 1,
                title=mat.title,
                is_completed=is_done,
                due_date=mat.due_date,
                raw_due_date=mat.raw_due_date,
                is_overdue=mat.is_overdue,
                is_urgent=is_urgent,
                url=mat.url,
                module_id=mat.module_id,
                start_date=mat.start_date,
                is_available=mat.is_available,
            )
        )

    # 5. Hybrid week detection & multi-tier calculation
    current_week = detect_current_week(sections_meta, now=current_time)
    course_abbr = get_abbreviation(course.clean_name, mappings or {})

    return calculate_course_progress(
        course_id=course.course_id,
        course_name=course.clean_name,
        course_abbr=course_abbr,
        current_week=current_week,
        activities=activities,
        now=current_time,
    )


def run_progress_pipeline(
    course_query: str | None = None,
    week_query: int | None = None,
    cached: bool = False,
    refresh: bool = False,
    relogin: bool = False,
    headful: bool = False,
    progress_callback: Callable[[str], None] | None = None,
    settings: Settings | None = None,
    now: datetime | None = None,
) -> ProgressReport:
    """Orchestrates comprehensive progress collection with caching, error isolation, and CLI progress callbacks."""
    cfg = settings or get_settings()
    current_time = now or get_current_kst_time()
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=KST)

    cache_path = cfg.session_cache_path.parent / "progress_cache.json"

    # Fast-path cache return (D-16-14)
    if cached and not refresh:
        cached_report = load_progress_cache(cache_path, now=current_time)
        if cached_report:
            return cached_report

    if relogin and cfg.session_cache_path.exists():
        try:
            cfg.session_cache_path.unlink()
        except Exception:
            pass

    mappings = load_course_mappings(cfg.course_mappings_path)
    client = get_authenticated_httpx_client(cfg)
    course_results: list[CourseProgress] = []
    errors: list[ErrorItem] = []
    notices: list[ReportNotice] = []

    try:
        with SessionManager(settings=cfg, headful=headful) as sm:
            page = sm.get_authenticated_page()
            all_courses = extract_courses(page, cfg.lms_url)

            target_courses = all_courses
            if course_query:
                target = find_target_course(all_courses, course_query, mappings)
                if target:
                    target_courses = [target]
                else:
                    target_courses = []
                    notices.append(
                        ReportNotice(
                            code="NO_MATCHING_COURSE",
                            message=f"과목 검색어 '{course_query}'와 일치하는 강좌를 찾을 수 없습니다.",
                        )
                    )

            total_courses = len(target_courses)
            for idx, c in enumerate(target_courses):
                if progress_callback:
                    progress_callback(f"[{idx+1}/{total_courses}] [{c.clean_name}] 활동 내역 수집 중...")

                try:
                    cp = _collect_single_course_progress(client, c, cfg, mappings=mappings, now=current_time)
                    if week_query is not None:
                        cp = calculate_course_progress(
                            course_id=c.course_id,
                            course_name=c.clean_name,
                            course_abbr=cp.course_abbr,
                            current_week=week_query,
                            activities=cp.all_items,
                            now=current_time,
                        )
                    course_results.append(cp)
                except Exception as e:
                    logger.warning(f"Failed to collect progress for course {c.clean_name}: {e}")
                    errors.append(
                        ErrorItem(
                            scope="course",
                            code="COLLECTION_FAILED",
                            message=str(e),
                            course_id=c.course_id,
                            course_name=c.clean_name,
                        )
                    )
                    course_results.append(
                        CourseProgress(
                            course_id=c.course_id,
                            course_name=c.clean_name,
                            course_abbr=get_abbreviation(c.clean_name, mappings),
                            current_week=week_query or 1,
                            current_open_rate=0.0,
                            current_open_completed=0,
                            current_open_total=0,
                            past_weeks_rate=0.0,
                            past_weeks_completed=0,
                            past_weeks_total=0,
                            semester_overall_rate=0.0,
                            semester_completed=0,
                            semester_total=0,
                            activity_breakdown=ActivityBreakdown(),
                            status="error",
                            error_message=str(e),
                        )
                    )
    finally:
        try:
            client.close()
        except Exception:
            pass

    summary = aggregate_dashboard_summary(course_results)
    if not errors and not notices:
        status = "success"
    elif any(c.status == "ok" for c in course_results):
        status = "partial_success"
    else:
        status = "error"

    report = ProgressReport(
        schema_version=SCHEMA_VERSION,
        command="progress",
        status=status,
        generated_at=current_time,
        is_cached=False,
        summary=summary,
        courses=course_results,
        errors=errors,
        notices=notices,
    )

    save_progress_cache(cache_path, report)
    return report
