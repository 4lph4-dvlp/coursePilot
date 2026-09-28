"""First end-to-end LMS collection orchestrator: login -> course list -> per-course scrape -> normalize.

Never writes to stdout; progress is reported through the caller-supplied callback only.
"""

import logging
from collections.abc import Callable
from datetime import datetime

from pydantic import BaseModel, Field

from coursepilot.config import Settings
from coursepilot.course_mapping import load_course_mappings
from coursepilot.domain.models import SyncTask
from coursepilot.domain.transformer import transform_to_sync_tasks
from coursepilot.errors import safe_cli_error
from coursepilot.exceptions import ConfigError
from coursepilot.report_models import ErrorItem
from coursepilot.scraper.assessment_parser import scrape_course_assessments
from coursepilot.scraper.course_list import extract_courses
from coursepilot.scraper.lecture_parser import (
    merge_lecture_progress,
    merge_ublogs_completion,
    parse_lectures_from_course_sections,
    parse_lectures_from_progress_table,
    parse_ubcompletion_progress,
    parse_ublogs_completion,
)
from coursepilot.scraper.models import AssessmentItem, CourseItem, LectureItem
from coursepilot.scraper.navigator import CourseNavigator
from coursepilot.scraper.material_parser import parse_materials_from_course_sections
from coursepilot.materials.models import MaterialItem
from coursepilot.session_manager import SessionManager

logger = logging.getLogger("coursepilot.pipeline")

ProgressCallback = Callable[[int, int, str], None]


def validate_lms_settings(settings: Settings) -> None:
    """Raises ConfigError naming only the missing LMS env-var keys, before any browser starts (D-18).

    Never asks for or echoes values — the message tells the user to fill the
    repository `.env` themselves.
    """
    missing: list[str] = []
    if not settings.lms_url.strip():
        missing.append("LMS_URL")
    if not settings.lms_username.strip():
        missing.append("LMS_USERNAME")
    if not settings.lms_password.strip():
        missing.append("LMS_PASSWORD")

    if missing:
        keys = ", ".join(missing)
        raise ConfigError(
            f"{keys} 값이 비어 있습니다. ~/.coursepilot/.env 파일에 직접 입력한 뒤 다시 시도하세요."
        )


class PipelineResult(BaseModel):
    """Outcome of one `collect_tasks` run: courses seen, normalized tasks, and collected errors."""

    course_count: int
    courses: list[CourseItem] = Field(default_factory=list)
    tasks: list[SyncTask]
    errors: list[ErrorItem] = Field(default_factory=list)


def scrape_course(
    page,
    course: CourseItem,
    navigator: CourseNavigator,
) -> tuple[list[LectureItem], list[AssessmentItem]]:
    """Scrapes one course's lectures (course home + ublogs/ubcompletion merge, falling back to legacy progress table) and assessments."""
    home_html = navigator.navigate_to_course(page, course)
    lectures = parse_lectures_from_course_sections(home_html, course)

    progress_html = navigator.navigate_progress_page(page, course)
    if progress_html:
        if "table-learning-student-activity" in progress_html or "완료 상태" in progress_html:
            ublogs_records = parse_ublogs_completion(progress_html)
            if lectures and ublogs_records:
                lectures = merge_ublogs_completion(lectures, ublogs_records)
        else:
            ub_rows = parse_ubcompletion_progress(progress_html)
            if lectures and ub_rows:
                lectures = merge_lecture_progress(lectures, ub_rows)
            elif not lectures and not ub_rows:
                lectures = parse_lectures_from_progress_table(progress_html, course)

    assessments = scrape_course_assessments(page, course, navigator, home_html=home_html)
    return lectures, assessments


def collect_tasks(
    settings: Settings,
    *,
    headed: bool = False,
    relogin: bool = False,
    progress: ProgressCallback | None = None,
    session_factory: Callable[..., SessionManager] | None = None,
    now: datetime | None = None,
    include_completed: bool = False,
) -> PipelineResult:
    """Runs LMS login -> course list -> per-course scrape -> transform_to_sync_tasks (D-07, D-09)."""
    validate_lms_settings(settings)

    if relogin:
        settings.session_cache_path.unlink(missing_ok=True)

    factory = session_factory or SessionManager

    errors: list[ErrorItem] = []

    with factory(settings=settings, headful=headed) as session:
        page = session.get_authenticated_page()
        courses = extract_courses(page, settings.lms_url)

        if not courses:
            logger.warning(
                "수강 과목을 찾지 못했습니다: 해당 학기에 등록된 과목이 없거나 LMS 목록 조회에 문제가 있을 수 있습니다."
            )
            return PipelineResult(course_count=0, tasks=[], errors=[])

        navigator = CourseNavigator(settings)

        lectures_by_course: dict[str, list[LectureItem]] = {}
        assessments_by_course: dict[str, list[AssessmentItem]] = {}
        materials_by_course: dict[str, list[MaterialItem]] = {}

        for index, course in enumerate(courses, start=1):
            if progress is not None:
                progress(index, len(courses), course.clean_name)
            try:
                lectures, assessments = scrape_course(page, course, navigator)
                materials = parse_materials_from_course_sections(
                    navigator.course_html.get(course.course_id, ""), course
                )
            except Exception as error:
                logger.warning(
                    "과목 수집 실패: course_id=%s (%s)",
                    course.course_id,
                    type(error).__name__,
                )
                errors.append(
                    safe_cli_error(
                        error,
                        scope="course",
                        course_id=course.course_id,
                        course_name=course.clean_name,
                    )
                )
                continue
            lectures_by_course[course.course_id] = lectures
            assessments_by_course[course.course_id] = assessments
            materials_by_course[course.course_id] = materials

        tasks = transform_to_sync_tasks(
            courses,
            lectures_by_course,
            assessments_by_course,
            mappings=load_course_mappings(settings.course_mappings_path),
            now=now,
            include_completed=include_completed,
            materials_by_course=materials_by_course,
        )

    return PipelineResult(course_count=len(courses), courses=courses, tasks=tasks, errors=errors)
