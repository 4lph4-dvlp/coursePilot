"""Parser for Coursemos LXP learning materials (ubfile and resource modules)."""

import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from coursepilot.materials.models import MaterialItem
from coursepilot.scraper.models import CourseItem


def parse_materials_from_course_sections(
    html: str,
    course: CourseItem,
) -> list[MaterialItem]:
    """Extracts materials with actual section week and explicit LMS completion."""
    from coursepilot.scraper.course_sections import parse_course_activities
    from coursepilot.scraper.date_parser import is_past_deadline

    return [
        MaterialItem(
            course_id=course.course_id, course_name=course.clean_name,
            week_number=activity.week_number, module_id=activity.module_id,
            title=activity.title, url=activity.url,
            is_completed=activity.is_completed, start_date=activity.start_date,
            due_date=activity.due_date, raw_due_date=activity.raw_due_date,
            is_overdue=not activity.is_completed and is_past_deadline(activity.due_date),
            is_available=activity.is_available,
        )
        for activity in parse_course_activities(html, course)
        if activity.module_type in {"ubfile", "resource"}
    ]


def extract_pluginfile_url(html: str, base_url: str = "") -> str | None:
    """Extracts direct pluginfile.php download URL from an embedded HTML viewer page."""
    if not html:
        return None

    soup = BeautifulSoup(html, "lxml")

    # 1. Check anchor tag with pluginfile.php
    a_tag = soup.find("a", href=re.compile(r"pluginfile\.php", re.I))
    if a_tag and a_tag.get("href"):
        return urljoin(base_url, a_tag["href"])

    # 2. Check object data
    obj_tag = soup.find("object", data=re.compile(r"pluginfile\.php", re.I))
    if obj_tag and obj_tag.get("data"):
        return urljoin(base_url, obj_tag["data"])

    # 3. Check iframe src
    iframe_tag = soup.find("iframe", src=re.compile(r"pluginfile\.php", re.I))
    if iframe_tag and iframe_tag.get("src"):
        return urljoin(base_url, iframe_tag["src"])

    # 4. Check embed src
    embed_tag = soup.find("embed", src=re.compile(r"pluginfile\.php", re.I))
    if embed_tag and embed_tag.get("src"):
        return urljoin(base_url, embed_tag["src"])

    return None
