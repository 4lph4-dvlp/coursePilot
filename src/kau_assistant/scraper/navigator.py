"""Course navigator with smart wait, WAF delays, and access error handling."""

import logging
import random
import time
from playwright.sync_api import Page

from kau_assistant.config import Settings
from kau_assistant.exceptions import CourseAccessDeniedError
from kau_assistant.scraper.debug_dump import capture_debug_snapshot
from kau_assistant.scraper.models import CourseItem
from kau_assistant.scraper.course_sections import needs_section_view, sections_url, validate_activity_coverage

logger = logging.getLogger(__name__)


class CourseNavigator:
    """Manages resilient navigation across LMS courses, progress reports, and activities."""

    def __init__(
        self,
        settings: Settings,
        min_delay: float = 0.2,
        max_delay: float = 0.5,
    ) -> None:
        self.settings = settings
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.timeout_ms = settings.timeout_ms
        self.course_html: dict[str, str] = {}

    def polite_delay(self) -> None:
        """Applies a polite micro-delay to avoid WAF/DoS blocks."""
        if self.max_delay > 0:
            delay = random.uniform(self.min_delay, self.max_delay)
            time.sleep(delay)

    def smart_wait(self, page: Page, selector: str, timeout_ms: int = 15000) -> bool:
        """Explicitly waits for a selector to appear. Returns True on success, False on timeout."""
        try:
            page.wait_for_selector(selector, timeout=timeout_ms)
            return True
        except Exception:
            return False

    def navigate_to_course(self, page: Page, course: CourseItem) -> str:
        """Navigates to the main course page. Raises CourseAccessDeniedError on 403 or error alerts."""
        self.polite_delay()
        logger.info(f"Navigating to course: {course.clean_name} ({course.course_id})")

        response = page.goto(course.url, wait_until="domcontentloaded")
        if response and response.status in (403, 401):
            capture_debug_snapshot(page, f"access_denied_{course.course_id}")
            raise CourseAccessDeniedError(f"HTTP {response.status} access denied to course {course.course_id}")

        content = page.content()

        # Check for Moodle/Coursemos access denied or restricted indicators
        denied_indicators = [
            "접근 권한이 없습니다",
            "이 강좌에 등록되어 있지 않습니다",
            "비공개 강좌입니다",
            "access denied",
            "not enrolled in this course",
        ]
        has_error_box = self.smart_wait(page, ".alert-danger, .errorbox, .notifyproblem", timeout_ms=1000)
        if (has_error_box and any(ind in content for ind in denied_indicators)) or any(
            ind in content for ind in denied_indicators
        ):
            capture_debug_snapshot(page, f"access_denied_{course.course_id}")
            raise CourseAccessDeniedError(
                f"Access denied or course restricted for course {course.course_id}: {course.clean_name}"
            )

        if needs_section_view(content):
            self.polite_delay()
            response = page.goto(sections_url(course.url), wait_until="domcontentloaded")
            if response and response.status in (403, 401):
                raise CourseAccessDeniedError(f"HTTP {response.status} access denied to course {course.course_id}")
            content = page.content()
        validate_activity_coverage(content, course)
        self.course_html[course.course_id] = content
        return content

    def navigate_progress_page(self, page: Page, course: CourseItem) -> str | None:
        """Navigates to course progress/completion report page. Returns HTML if found, or None to trigger fallback."""
        self.polite_delay()
        base_url = self.settings.lms_url.rstrip("/")

        # 1. Try ublogs completion first (KAU LXP primary activity status page)
        ublogs_url = f"{base_url}/report/ublogs/completion.php?id={course.course_id}"
        logger.info(f"Attempting navigation to activity completion for course {course.course_id}")
        try:
            resp = page.goto(ublogs_url, wait_until="domcontentloaded")
            if resp and resp.status == 200:
                selectors = ".table-learning-student-activity, table.user_progress, .table-coursemos"
                found = self.smart_wait(page, selectors, timeout_ms=3000)
                content = page.content()
                if found and any(k in content for k in ("table-learning-student-activity", "학습활동", "완료 상태")):
                    return content
        except Exception as e:
            logger.debug(f"ublogs navigation failed: {e}")

        # 2. Fallback to ubcompletion progress report
        progress_url = f"{base_url}/report/ubcompletion/progress.php?id={course.course_id}"
        logger.info(f"Attempting navigation to progress report for course {course.course_id}")
        page.goto(progress_url, wait_until="domcontentloaded")

        selectors = "table.user_progress, table.progress-report, .generaltable.progress-report"
        found = self.smart_wait(page, selectors, timeout_ms=3000)
        content = page.content()

        # Validate that actual progress content exists
        if not found or not any(
            k in content for k in ("user_progress", "progress-report", "학습현황", "출석", "progress_report")
        ):
            logger.info(f"Progress report view not available for course {course.course_id}, falling back to course home")
            return None

        return content

    def navigate_assessment_page(self, page: Page, course: CourseItem, item_type: str = "assign") -> str | None:
        """Navigates to assessment summary page (e.g. /mod/assign/index.php?id=...)."""
        self.polite_delay()
        base_url = self.settings.lms_url.rstrip("/")
        assessment_url = f"{base_url}/mod/{item_type}/index.php?id={course.course_id}"
        logger.info(f"Navigating to {item_type} summary page for course {course.course_id}")

        page.goto(assessment_url, wait_until="domcontentloaded")

        found = self.smart_wait(page, "table.generaltable, .box.generalbox, #region-main", timeout_ms=5000)
        if not found:
            logger.warning(f"Could not load {item_type} page for course {course.course_id}")
            return None

        return page.content()
