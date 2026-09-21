"""Course list extractor and course name cleaner for LMS."""

import re
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag
from playwright.sync_api import Page

from kau_assistant.scraper.models import CourseItem


def clean_course_name(raw_name: str) -> str:
    """Sanitizes raw course names by removing division and term notations.

    Examples:
        '공학수학2(01분반) [2026-1학기]' -> '공학수학2'
        '2026-1 자료구조 02분반' -> '자료구조'
        '디지털시스템설계_01 [2026학년도 1학기]' -> '디지털시스템설계'
        '[03분반] 캡스톤디자인 [2026-1]' -> '캡스톤디자인'
    """
    if not raw_name:
        return ""

    cleaned = raw_name.strip()

    # 1. Remove bracketed or parenthesized tags like [지난 강좌], (종료), [종료]
    cleaned = re.sub(r"\[\s*(?:지난\s*강좌|종료)\s*\]", " ", cleaned)
    cleaned = re.sub(r"\(\s*(?:지난\s*강좌|종료)\s*\)", " ", cleaned)

    # 2. Remove year/semester indicators:
    # e.g., [2026-1학기], [2026학년도 1학기], 2026-1, [2026-1], 2026학년도 1학기, 2026년 1학기
    cleaned = re.sub(
        r"\[?\s*\d{4}\s*(?:[-/]|학년도|년)?\s*\d?\s*(?:학기)?\s*\]?",
        " ",
        cleaned,
    )

    # 3. Remove division indicators:
    # e.g., [01분반], [01], (01분반), (01), _01분반, _01, 01분반
    cleaned = re.sub(r"\[\s*\d+\s*(?:분반)?\s*\]", " ", cleaned)
    cleaned = re.sub(r"\(\s*\d+\s*(?:분반)?\s*\)", " ", cleaned)
    cleaned = re.sub(r"_\s*\d+\s*(?:분반)?\b", " ", cleaned)
    cleaned = re.sub(r"\b\d{1,2}\s*분반\b", " ", cleaned)

    # 4. Remove leftover punctuation like stray brackets or underscores at edges
    cleaned = re.sub(r"[\[\]\(\)]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def is_past_or_ended_course(container: Tag | None, link_text: str) -> bool:
    """Checks if a course container or text indicates an expired or past course."""
    if "[지난 강좌]" in link_text or "(종료)" in link_text:
        return True

    if not container:
        return False

    classes = container.get("class", [])
    if isinstance(classes, list):
        class_str = " ".join(classes).lower()
    else:
        class_str = str(classes).lower()

    if any(k in class_str for k in ("ended", "past", "expired", "closed")):
        return True

    text = container.get_text()
    if "지난 강좌" in text or "종료" in text:
        # If it explicitly says "진행 중", it's active
        if "진행 중" not in text and "진행중" not in text:
            return True

    return False


def extract_courses_from_html(html: str, base_url: str = "") -> list[CourseItem]:
    """Parses dashboard HTML and extracts active course items.

    Deduplicates by course ID and filters out ended/past courses.
    """
    soup = BeautifulSoup(html, "lxml")
    courses: list[CourseItem] = []
    seen_ids: set[str] = set()

    # Find links matching Moodle/Coursemos course view or Canvas course view
    course_links = soup.find_all("a", href=re.compile(r"/course/view\.php\?id=\d+|/courses/\d+"))

    for a in course_links:
        href = a.get("href", "")
        if not href:
            continue

        # Extract course ID
        id_match = re.search(r"[?&]id=(\d+)", href) or re.search(r"/courses/(\d+)", href)
        if not id_match:
            continue

        course_id = id_match.group(1)
        if course_id in seen_ids:
            continue

        # Get parent course card container to inspect status / term
        container = a.find_parent(
            class_=re.compile(r"course[_-]?box|coursebox|course-card|dashboard-card", re.I)
        )
        if not container:
            container = a.find_parent(class_=re.compile(r"coursename|course_list|my-course", re.I))
        if not container:
            container = a.parent

        raw_name = a.get_text(strip=True)
        if not raw_name:
            continue

        # Filter out past/ended courses
        if is_past_or_ended_course(container, raw_name):
            continue

        clean_name = clean_course_name(raw_name)
        if not clean_name:
            clean_name = raw_name

        # Extract term if available
        term = ""
        if container:
            term_el = container.find(class_=re.compile(r"term|semester", re.I))
            if term_el:
                term = term_el.get_text(strip=True)

        full_url = urljoin(base_url, href) if base_url else href

        course = CourseItem(
            course_id=course_id,
            raw_name=raw_name,
            clean_name=clean_name,
            url=full_url,
            term=term,
        )
        courses.append(course)
        seen_ids.add(course_id)

    return courses


def extract_courses(
    page: Page,
    lms_url: str,
    cached_courses: list[CourseItem] | None = None,
) -> list[CourseItem]:
    """Extracts course list from live LMS dashboard or returns cached courses."""
    if cached_courses is not None:
        return cached_courses

    dashboard_url = f"{lms_url.rstrip('/')}/my/"
    page.goto(dashboard_url, wait_until="domcontentloaded")

    # Smart wait for dashboard container
    try:
        page.wait_for_selector(
            ".block_coursemos_my_courses, .course_list, #dashboard, .my-course-lists, [role='main']",
            timeout=15000,
        )
    except Exception:
        # Fallback: proceed to extract whatever is in page.content()
        pass

    html = page.content()
    return extract_courses_from_html(html, base_url=lms_url)
