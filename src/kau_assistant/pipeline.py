"""First end-to-end LMS collection orchestrator: login -> course list -> per-course scrape -> normalize.

Never writes to stdout; progress is reported through the caller-supplied callback only.
"""

import logging
from collections.abc import Callable
from datetime import datetime

from pydantic import BaseModel, Field

from kau_assistant.config import Settings
from kau_assistant.course_mapping import load_course_mappings
from kau_assistant.domain.models import SyncTask
from kau_assistant.domain.transformer import transform_to_sync_tasks
from kau_assistant.errors import safe_cli_error
from kau_assistant.report_models import ErrorItem
from kau_assistant.scraper.assessment_parser import scrape_course_assessments
from kau_assistant.scraper.course_list import extract_courses
from kau_assistant.scraper.lecture_parser import (
    parse_lectures_from_course_sections,
    parse_lectures_from_progress_table,
)
from kau_assistant.scraper.models import AssessmentItem, CourseItem, LectureItem
from kau_assistant.scraper.navigator import CourseNavigator
from kau_assistant.session_manager import SessionManager

logger = logging.getLogger("kau_assistant.pipeline")

ProgressCallback = Callable[[int, int, str], None]


class PipelineResult(BaseModel):
    """Outcome of one `collect_tasks` run: courses seen, normalized tasks, and collected errors."""

    course_count: int
    tasks: list[SyncTask]
    errors: list[ErrorItem] = Field(default_factory=list)


def scrape_course(
    page,
    course: CourseItem,
    navigator: CourseNavigator,
) -> tuple[list[LectureItem], list[AssessmentItem]]:
    """Scrapes one course's lectures (progress table, falling back to course sections) and assessments."""
    home_html = navigator.navigate_to_course(page, course)
    progress_html = navigator.navigate_progress_page(page, course)

    if progress_html:
        lectures = parse_lectures_from_progress_table(progress_html, course)
    else:
        lectures = parse_lectures_from_course_sections(home_html, course)

    assessments = scrape_course_assessments(page, course, navigator)
    return lectures, assessments


def collect_tasks(
    settings: Settings,
    *,
    headed: bool = False,
    relogin: bool = False,
    progress: ProgressCallback | None = None,
    session_factory: Callable[..., SessionManager] | None = None,
    now: datetime | None = None,
) -> PipelineResult:
    """Runs LMS login -> course list -> per-course scrape -> transform_to_sync_tasks (D-07, D-09)."""
    if relogin:
        settings.session_cache_path.unlink(missing_ok=True)

    factory = session_factory or SessionManager

    errors: list[ErrorItem] = []

    with factory(settings=settings, headful=headed) as session:
        page = session.get_authenticated_page()
        courses = extract_courses(page, settings.lms_url)
        navigator = CourseNavigator(settings)

        lectures_by_course: dict[str, list[LectureItem]] = {}
        assessments_by_course: dict[str, list[AssessmentItem]] = {}

        for index, course in enumerate(courses, start=1):
            if progress is not None:
                progress(index, len(courses), course.clean_name)
            try:
                lectures, assessments = scrape_course(page, course, navigator)
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

        tasks = transform_to_sync_tasks(
            courses,
            lectures_by_course,
            assessments_by_course,
            mappings=load_course_mappings(settings.course_mappings_path),
            now=now,
        )

    return PipelineResult(course_count=len(courses), tasks=tasks, errors=errors)
