"""KAU LMS Scraper core package."""

from kau_assistant.scraper.assessment_parser import (
    enrich_assessment_detail,
    parse_assessment_list,
    scrape_course_assessments,
)
from kau_assistant.scraper.course_list import (
    clean_course_name,
    extract_courses,
    extract_courses_from_html,
)
from kau_assistant.scraper.date_parser import (
    KST,
    get_current_kst_time,
    is_past_deadline,
    parse_lms_date,
)
from kau_assistant.scraper.debug_dump import capture_debug_snapshot
from kau_assistant.scraper.lecture_parser import (
    clean_lecture_title,
    parse_lectures_from_course_sections,
    parse_lectures_from_progress_table,
)
from kau_assistant.scraper.models import (
    AssessmentItem,
    AssessmentType,
    AttachmentMeta,
    AttendanceStatus,
    CourseItem,
    LectureItem,
    SubmissionStatus,
)
from kau_assistant.scraper.navigator import CourseNavigator

__all__ = [
    "AssessmentItem",
    "AssessmentType",
    "AttachmentMeta",
    "AttendanceStatus",
    "CourseItem",
    "CourseNavigator",
    "LectureItem",
    "SubmissionStatus",
    "KST",
    "capture_debug_snapshot",
    "clean_course_name",
    "clean_lecture_title",
    "enrich_assessment_detail",
    "extract_courses",
    "extract_courses_from_html",
    "get_current_kst_time",
    "is_past_deadline",
    "parse_assessment_list",
    "parse_lectures_from_course_sections",
    "parse_lectures_from_progress_table",
    "parse_lms_date",
    "scrape_course_assessments",
]
