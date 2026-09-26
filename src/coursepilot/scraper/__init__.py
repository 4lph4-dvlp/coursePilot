"""CoursePilot LMS scraper core package."""

from coursepilot.scraper.assessment_parser import (
    enrich_assessment_detail,
    parse_assessment_list,
    scrape_course_assessments,
)
from coursepilot.scraper.course_list import (
    clean_course_name,
    extract_courses,
    extract_courses_from_html,
)
from coursepilot.scraper.date_parser import (
    KST,
    get_current_kst_time,
    is_past_deadline,
    parse_lms_date,
)
from coursepilot.scraper.debug_dump import capture_debug_snapshot
from coursepilot.scraper.lecture_parser import (
    clean_lecture_title,
    parse_lectures_from_course_sections,
    parse_lectures_from_progress_table,
)
from coursepilot.scraper.models import (
    AssessmentItem,
    AssessmentType,
    AttachmentMeta,
    AttendanceStatus,
    CourseItem,
    LectureItem,
    SubmissionStatus,
)
from coursepilot.scraper.navigator import CourseNavigator

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
