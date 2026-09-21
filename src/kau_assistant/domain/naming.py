"""Task naming rules and smart title cleaning engine (D-01 ~ D-04, DOMN-03)."""

import html
import re

from kau_assistant.course_mapping import get_abbreviation
from kau_assistant.domain.models import TaskType


def clean_task_title(raw_title: str) -> str:
    """Cleans activity title by unescaping HTML, normalizing whitespace, and removing redundant tags."""
    if not raw_title:
        return ""

    # 1. Unescape HTML entities (&amp; -> &, &#39; -> ', &nbsp; -> space, etc.)
    text = html.unescape(raw_title)
    text = text.replace("\xa0", " ")

    # 2. Strip redundant bracket tags at beginning
    # e.g., [과제], [숙제], [Assignment], [HW], [퀴즈], [Quiz], [토론], [Discussion]
    redundant_tag_pattern = (
        r"^(?:\[\s*(?:과제|과제제출|숙제|Assignment|HW|H\.W|퀴즈|Quiz|쪽지시험|시험|Exam|토론|Forum|Discussion)\s*\]\s*)+"
    )
    text = re.sub(redundant_tag_pattern, "", text, flags=re.I)

    # 3. Normalize multiple whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_week_and_title(title: str) -> tuple[int | None, str]:
    """Extracts week number if present in the title and returns cleaned remainder title."""
    cleaned = clean_task_title(title)

    # Detect week pattern e.g. "3주차 과제", "3주차: 실습 1", "Week 4 Project"
    m_week = re.search(r"(?:제?\s*(\d+)\s*주차?|week\s*(\d+))\s*[:\-_]?\s*", cleaned, re.I)
    if m_week:
        week_num = int(m_week.group(1) or m_week.group(2))
        remainder = cleaned[: m_week.start()] + cleaned[m_week.end() :]
        remainder = re.sub(r"\s+", " ", remainder).strip()
        if not remainder:
            remainder = "과제"
        return week_num, remainder

    return None, cleaned


def format_task_title(
    course_name: str,
    raw_title: str,
    task_type: TaskType,
    week_number: int | None = None,
    clip_number: int | None = None,
    course_mappings: dict[str, str] | None = None,
) -> str:
    """Formats standardized task title according to user Notion scheduler conventions.

    Conventions:
      - Lecture: "[{과목약어}] {N}주차 {M}차시 강의 시청" (D-01)
      - Assignment: "[{과목약어}] {N}주차 {과제명} 제출" or "[{과목약어}] {과제명} 제출" (D-02, D-03)
      - Quiz: "[{과목약어}] {N}주차 [퀴즈] {이름} 응시" or "[{과목약어}] [퀴즈] {이름} 응시" (D-02, D-03)
      - Forum: "[{과목약어}] {N}주차 [토론] {이름} 참여" or "[{과목약어}] [토론] {이름} 참여" (D-02, D-03)
    """
    mappings = course_mappings if course_mappings is not None else {}
    abbr = get_abbreviation(course_name, mappings)

    # 1. Lecture: Fixed format (D-01)
    if task_type == TaskType.LECTURE:
        w = week_number if (week_number is not None and week_number > 0) else 1
        c = clip_number if (clip_number is not None and clip_number > 0) else 1
        return f"[{abbr}] {w}주차 {c}차시 강의 시청"

    # 2. Assessments: Assignment, Quiz, Forum, Other (D-02, D-03)
    extracted_week, clean_name = extract_week_and_title(raw_title)
    effective_week = (
        week_number if (week_number is not None and week_number > 0) else extracted_week
    )

    # Clean redundant trailing verb if already in clean_name to avoid "제출 제출"
    clean_name = re.sub(r"\s*(?:제출|응시|참여|시청)$", "", clean_name).strip()
    if not clean_name:
        clean_name = "과제" if task_type == TaskType.ASSIGNMENT else "활동"

    week_prefix = (
        f"{effective_week}주차 "
        if (effective_week is not None and effective_week > 0)
        else ""
    )

    if task_type == TaskType.ASSIGNMENT:
        return f"[{abbr}] {week_prefix}{clean_name} 제출"
    elif task_type == TaskType.QUIZ:
        return f"[{abbr}] {week_prefix}[퀴즈] {clean_name} 응시"
    elif task_type == TaskType.FORUM:
        return f"[{abbr}] {week_prefix}[토론] {clean_name} 참여"
    else:
        return f"[{abbr}] {week_prefix}{clean_name} 제출"
