"""Shared section navigation and activity metadata for current and legacy Coursemos."""

import copy
from datetime import datetime
import re
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup
from pydantic import BaseModel

from kau_assistant.exceptions import ActivityCollectionError
from kau_assistant.scraper.date_parser import parse_lms_date
from kau_assistant.scraper.models import CourseItem


class CourseActivity(BaseModel):
    module_id: str
    module_type: str
    week_number: int
    title: str
    url: str
    is_completed: bool = False
    completion_known: bool = False
    start_date: datetime | None = None
    due_date: datetime | None = None
    raw_due_date: str = ""
    is_available: bool = True


def sections_url(url: str) -> str:
    """Keep the course identity while selecting the full section view."""
    parts = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parts.query) if k not in {"mode", "section", "expandsection"}]
    query.append(("mode", "sections"))
    return urlunsplit(parts._replace(query=urlencode(query), fragment=""))


def needs_section_view(html: str) -> bool:
    soup = BeautifulSoup(html, "lxml")
    return bool(soup.select_one(".current-activity, .coursemos-course-main")) and not bool(
        soup.select_one("li.activity, li[id^='section-']")
    )


def course_sections(soup: BeautifulSoup) -> list:
    """Avoid hashing entire nested BeautifulSoup trees when removing nested sections."""
    candidates = soup.find_all(
        lambda tag: tag.name == "li" and (
            any(cls in {"section", "course-section"} for cls in tag.get("class", []))
            or re.match(r"^section-\d+$", tag.get("id", ""))
        )
    )
    candidate_ids = {id(tag) for tag in candidates}
    return [tag for tag in candidates if not any(id(p) in candidate_ids for p in tag.parents)] or [soup]


def section_week(section, index: int) -> int:
    heading = section.find(class_=re.compile(r"sectionname|section-title", re.I)) or section.find(["h3", "h4", "h5"])
    if heading:
        text = heading.get_text(" ", strip=True)
        match = re.search(r"(\d+)\s*주|week\s*(\d+)", text, re.I)
        if match:
            return int(match.group(1) or match.group(2))
    match = re.search(r"section-(\d+)", section.get("id", ""))
    if match:
        return int(match.group(1))
    for attr in ("data-number", "data-sectionid"):
        try:
            if section.has_attr(attr):
                return int(section[attr])
        except (TypeError, ValueError):
            pass
    return index


def parse_course_activities(html: str, course: CourseItem) -> list[CourseActivity]:
    soup = BeautifulSoup(html, "lxml")
    results: list[CourseActivity] = []
    seen: set[str] = set()
    for index, section in enumerate(course_sections(soup)):
        week = section_week(section, index)
        for act in section.select("li.activity"):
            module_type = next((cls.removeprefix("modtype_") for cls in act.get("class", []) if cls.startswith("modtype_")), "")
            if not module_type:
                module_type = next((cls for cls in act.get("class", []) if cls in {"vod", "ubfile", "resource", "assign", "quiz"}), "")
            if module_type not in {"vod", "ubfile", "resource", "assign", "quiz"}:
                continue
            link = act.find("a", href=re.compile(r"(?:/mod/" + module_type + r"/)?view\.php\?"))
            module_match = re.search(r"module-(\d+)", act.get("id", ""))
            if not module_match and link:
                module_match = re.search(r"[?&]id=(\d+)", link.get("href", ""))
            if not module_match:
                continue
            module_id = module_match.group(1)
            if module_id in seen:
                continue
            seen.add(module_id)
            name = act.select_one(".instancename, .activityname") or link
            if name is None:
                name = act.select_one(".activitytitle")
            if name is None:
                continue
            name_copy = copy.deepcopy(name)
            for hidden in name_copy.select(".accesshide, .sr-only"):
                hidden.decompose()
            title = name_copy.get_text(" ", strip=True)
            if not title:
                continue
            classes = set(act.get("class", []))
            completed = bool(classes & {"activity-completed", "activity-complete", "iscompleted"})
            known = completed or "activity-incomplete" in classes
            for el in act.find_all(class_=re.compile(r"completion|autocompletion|csms-chips-dot", re.I)):
                text = el.get_text(" ", strip=True)
                img = el.find("img")
                if img:
                    text += " " + img.get("alt", "")
                if "미완료" in text or "미출석" in text:
                    completed, known = False, True
                elif any(mark in text for mark in ("완료", "출석")):
                    completed, known = True, True
            period = act.select_one(".text-ubstrap, .availabilityinfo, .activity-dates")
            raw_due = period.get_text(" ", strip=True) if period else ""
            close = act.select_one(".timeclose")
            opened = act.select_one(".timeopen")
            start, _ = parse_lms_date(opened.get_text(" ", strip=True)) if opened else (None, False)
            if close:
                due, _ = parse_lms_date(close.get_text(" ", strip=True))
            elif opened:
                due = None  # An opening date alone is not a deadline.
            else:
                due, _ = parse_lms_date(raw_due)
            results.append(CourseActivity(
                module_id=module_id, module_type=module_type, week_number=week,
                title=title, url=urljoin(course.url, link["href"]) if link else urljoin(course.url, f"/mod/{module_type}/view.php?id={module_id}"),
                is_completed=completed, completion_known=known,
                start_date=start, due_date=due, raw_due_date=raw_due, is_available=link is not None,
            ))
    return results


def validate_activity_coverage(html: str, course: CourseItem) -> None:
    """Visible supported activities must not silently disappear from the inventory."""
    soup = BeautifulSoup(html, "lxml")
    expected: set[str] = set()
    for link in soup.find_all("a", href=re.compile(r"/mod/(?:vod|ubfile|resource|assign|quiz)/view\.php")):
        match = re.search(r"[?&]id=(\d+)", link.get("href", ""))
        if match:
            expected.add(match.group(1))
    for activity in soup.select("li.activity[id^='module-']"):
        if any(cls in {"vod", "ubfile", "resource", "assign", "quiz"}
               or cls in {"modtype_vod", "modtype_ubfile", "modtype_resource", "modtype_assign", "modtype_quiz"}
               for cls in activity.get("class", [])):
            match = re.fullmatch(r"module-(\d+)", activity["id"])
            if match:
                expected.add(match.group(1))
    parsed = {a.module_id for a in parse_course_activities(html, course)}
    if expected - parsed or needs_section_view(html):
        raise ActivityCollectionError("학습활동 목록을 해석하지 못했습니다.")
