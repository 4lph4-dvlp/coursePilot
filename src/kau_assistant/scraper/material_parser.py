"""Parser for Coursemos LXP learning materials (ubfile and resource modules)."""

import copy
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from kau_assistant.materials.models import MaterialItem
from kau_assistant.scraper.lecture_parser import _parse_week_number
from kau_assistant.scraper.models import CourseItem


def parse_materials_from_course_sections(
    html: str,
    course: CourseItem,
) -> list[MaterialItem]:
    """Extracts learning materials (ubfile and resource) from main course sections.

    Strips Moodle accesshide spans from titles and extracts module IDs, week numbers,
    and completion status.
    """
    soup = BeautifulSoup(html, "lxml")
    materials: list[MaterialItem] = []

    # 1. Collect candidate section elements
    candidate_sections = soup.find_all(
        lambda tag: tag.name == "li"
        and (
            any(cls in ("section", "course-section") for cls in tag.get("class", []))
            or (tag.get("id") and re.match(r"^section-\d+$", tag.get("id")))
        )
    )

    # 2. Filter candidates: drop any candidate that has an ancestor also in candidates
    candidate_set = set(candidate_sections)
    top_sections = [
        sec
        for sec in candidate_sections
        if not any(parent in candidate_set for parent in sec.parents)
    ]
    if not top_sections:
        top_sections = [soup]

    seen_module_ids: set[str] = set()

    for sec_idx, sec in enumerate(top_sections):
        # Determine week number
        week_num: int | None = None
        sec_heading = sec.find(
            class_=re.compile(r"sectionname|section-title", re.I)
        ) or sec.find(["h3", "h4", "h5"])
        if sec_heading:
            parsed_w = _parse_week_number(sec_heading.get_text(strip=True), default=None)
            if parsed_w is not None:
                week_num = parsed_w

        if week_num is None:
            sec_id = sec.get("id", "")
            id_m = re.search(r"section-(\d+)", sec_id)
            if id_m:
                week_num = int(id_m.group(1))
            elif sec.has_attr("data-number"):
                try:
                    week_num = int(sec["data-number"])
                except (ValueError, TypeError):
                    week_num = sec_idx
            elif sec.has_attr("data-sectionid"):
                try:
                    week_num = int(sec["data-sectionid"])
                except (ValueError, TypeError):
                    week_num = sec_idx
            else:
                week_num = sec_idx

        # Find material activity items (ubfile, modtype_ubfile, resource, modtype_resource)
        activities = sec.find_all(
            lambda tag: tag.name == "li"
            and any(cls == "activity" for cls in tag.get("class", []))
            and any(
                cls in ("ubfile", "modtype_ubfile", "resource", "modtype_resource")
                for cls in tag.get("class", [])
            )
        )

        for act in activities:
            # Find link to view.php
            a_el = act.find("a", href=re.compile(r"/mod/(?:ubfile|resource)/view\.php", re.I))
            if not a_el:
                a_el = act.find("a")
                if not a_el or not a_el.get("href"):
                    continue

            raw_href = a_el.get("href", "")
            mod_match = re.search(r"[?&]id=(\d+)", raw_href)
            if mod_match:
                module_id = mod_match.group(1)
            else:
                act_id = act.get("id", "")
                id_sub = re.search(r"module-(\d+)", act_id)
                module_id = id_sub.group(1) if id_sub else ""

            if not module_id or module_id in seen_module_ids:
                continue
            seen_module_ids.add(module_id)

            # Clean title by removing accesshide spans
            name_el = a_el.find("span", class_="instancename") or a_el
            name_copy = copy.deepcopy(name_el)
            for ah in name_copy.find_all(class_="accesshide"):
                ah.decompose()
            raw_title = name_copy.get_text(strip=True)
            title = re.sub(r"\s+", " ", raw_title).strip()

            # Determine completion status from classes
            act_classes = " ".join(act.get("class", []))
            is_completed = "activity-complete" in act_classes or "iscompleted" in act_classes

            full_url = urljoin(course.url, raw_href)

            material = MaterialItem(
                course_id=course.course_id,
                course_name=getattr(course, "clean_name", getattr(course, "course_name", "")),
                week_number=week_num,
                module_id=module_id,
                title=title,
                url=full_url,
                is_completed=is_completed,
            )
            materials.append(material)

    return materials


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
