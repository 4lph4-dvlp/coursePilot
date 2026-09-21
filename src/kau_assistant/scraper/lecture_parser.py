"""Lecture video and clip parser with hybrid attendance/progress evaluation."""

from datetime import datetime
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from kau_assistant.scraper.date_parser import is_past_deadline, parse_lms_date
from kau_assistant.scraper.models import AttendanceStatus, CourseItem, LectureItem


def clean_lecture_title(raw_title: str) -> str:
    """Cleans lecture title by removing video/VOD tags and trailing indicators."""
    if not raw_title:
        return ""
    cleaned = raw_title.strip()
    # Remove tags like (동영상), [동영상], (VOD), [VOD], (웹콘텐츠), [영상]
    cleaned = re.sub(
        r"[\(\[]\s*(?:동영상|VOD|웹콘텐츠|온라인\s*강의|영상)\s*[\)\]]",
        " ",
        cleaned,
        flags=re.I,
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _parse_week_number(text: str, default: int = 1) -> int:
    """Extracts integer week number from text like '1주차', '3주', 'Week 2'."""
    m = re.search(r"(\d+)\s*주", text, re.I) or re.search(r"week\s*(\d+)", text, re.I)
    if m:
        return int(m.group(1))
    return default


def parse_lectures_from_progress_table(
    html: str,
    course: CourseItem,
    term_start_date: datetime | None = None,
) -> list[LectureItem]:
    """Parses video lecture progress from Coursemos progress report table.

    Evaluates completion via attendance mark ('O') or 100% progress rate.
    Flags overdue incomplete lectures with is_overdue=True and AttendanceStatus.OVERDUE.
    """
    soup = BeautifulSoup(html, "lxml")
    lectures: list[LectureItem] = []

    # Find progress table
    table = (
        soup.find("table", class_=re.compile(r"progress[-_]report|user_progress", re.I))
        or soup.find("table", class_="generaltable")
    )
    if not table:
        return []

    # Map column headers
    header_cells = table.find_all(["th", "td"])
    col_map: dict[str, int] = {}
    header_row = table.find("tr")
    if header_row:
        for idx, th in enumerate(header_row.find_all(["th", "td"])):
            txt = th.get_text(strip=True)
            if "주차" in txt:
                col_map["week"] = idx
            elif "차시" in txt:
                col_map["clip"] = idx
            elif "강의명" in txt or "콘텐츠" in txt or "제목" in txt or "학습내용" in txt:
                col_map["title"] = idx
            elif "진도" in txt or "진척" in txt:
                col_map["progress"] = idx
            elif "출석" in txt or "인정여부" in txt:
                col_map["attendance"] = idx
            elif "기간" in txt or "마감" in txt or "인정기간" in txt:
                col_map["period"] = idx

    # If column mapping could not be resolved from header, use defaults
    col_week = col_map.get("week", 0)
    col_clip = col_map.get("clip", 1)
    col_title = col_map.get("title", 2)
    col_progress = col_map.get("progress", 5)
    col_attendance = col_map.get("attendance", 6)
    col_period = col_map.get("period", 7)

    current_week = 1
    clip_counter_per_week: dict[int, int] = {}

    rows = table.find("tbody").find_all("tr") if table.find("tbody") else table.find_all("tr")[1:]

    for tr in rows:
        cells = tr.find_all(["td", "th"])
        if len(cells) < 3:
            continue

        # Week number
        if col_week < len(cells):
            w_text = cells[col_week].get_text(strip=True)
            if w_text:
                current_week = _parse_week_number(w_text, default=current_week)

        # Clip number
        clip_number = 0
        if col_clip < len(cells):
            c_text = cells[col_clip].get_text(strip=True)
            m_clip = re.search(r"\d+", c_text)
            if m_clip:
                clip_number = int(m_clip.group(0))

        if clip_number == 0:
            # Auto-assign clip number per week
            clip_counter_per_week[current_week] = clip_counter_per_week.get(current_week, 0) + 1
            clip_number = clip_counter_per_week[current_week]

        # Title & link
        raw_title = ""
        link = ""
        if col_title < len(cells):
            cell_title = cells[col_title]
            a_el = cell_title.find("a")
            if a_el:
                raw_title = a_el.get_text(strip=True)
                href = a_el.get("href", "")
                link = urljoin(course.url, href) if href else ""
            else:
                raw_title = cell_title.get_text(strip=True)

        if not raw_title:
            continue

        title = clean_lecture_title(raw_title)

        # Progress percent
        progress_val = 0.0
        if col_progress < len(cells):
            prog_text = cells[col_progress].get_text(strip=True)
            m_prog = re.search(r"(\d+(?:\.\d+)?)\s*%", prog_text)
            if m_prog:
                progress_val = float(m_prog.group(1))

        # Attendance mark
        attendance_str = ""
        if col_attendance < len(cells):
            att_cell = cells[col_attendance]
            # Check img alt or span text
            img = att_cell.find("img")
            if img and img.get("alt"):
                attendance_str = img["alt"].strip()
            else:
                attendance_str = att_cell.get_text(strip=True)

        # Period / Due Date
        raw_due_date = ""
        if col_period < len(cells):
            raw_due_date = cells[col_period].get_text(strip=True)

        due_date, _ = parse_lms_date(
            raw_due_date,
            fallback_week=current_week,
            term_start_date=term_start_date,
        )

        # Hybrid completion check (D-05):
        # Attendance mark ('O', '출석', 'attend', 'pass') takes priority.
        # Fallback to 100% progress.
        is_completed = False
        if any(mark in attendance_str.upper() for mark in ("O", "출석", "PASS", "COMPLETE")):
            is_completed = True
        elif progress_val >= 100.0:
            is_completed = True

        status = AttendanceStatus.COMPLETED if is_completed else AttendanceStatus.INCOMPLETE

        # Overdue check (D-06):
        is_overdue = False
        if not is_completed and is_past_deadline(due_date):
            is_overdue = True
            status = AttendanceStatus.OVERDUE

        full_title = f"[{course.clean_name}] {current_week}주차 {clip_number}차시: {title}"

        item = LectureItem(
            course_id=course.course_id,
            week_number=current_week,
            clip_number=clip_number,
            title=title,
            full_title=full_title,
            status=status,
            progress_percent=progress_val,
            due_date=due_date,
            raw_due_date=raw_due_date,
            is_overdue=is_overdue,
            link=link,
        )
        lectures.append(item)

    return lectures


def parse_lectures_from_course_sections(
    html: str,
    course: CourseItem,
    term_start_date: datetime | None = None,
) -> list[LectureItem]:
    """Fallback parser: extracts video lectures from main course home sections."""
    soup = BeautifulSoup(html, "lxml")
    lectures: list[LectureItem] = []

    sections = soup.find_all(
        ["li", "div"],
        class_=re.compile(r"section\s*main|topics\s*>\s*li|course-section", re.I),
    )
    if not sections:
        sections = soup.find_all("li", class_="section")

    for sec_idx, sec in enumerate(sections, start=1):
        # Determine week number from section heading
        sec_heading = sec.find(class_=re.compile(r"sectionname|section-title|heading", re.I))
        sec_text = sec_heading.get_text(strip=True) if sec_heading else f"{sec_idx}주차"
        week_num = _parse_week_number(sec_text, default=sec_idx)

        # Find vod/video activities
        activities = sec.find_all(
            ["li", "div"],
            class_=re.compile(r"activity\s*vod|activity\s*modtype_vod|activity-item", re.I),
        )

        for clip_idx, act in enumerate(activities, start=1):
            a_el = act.find("a")
            if not a_el:
                continue

            raw_title = a_el.get_text(strip=True)
            title = clean_lecture_title(raw_title)
            href = a_el.get("href", "")
            link = urljoin(course.url, href) if href else ""

            # Check completion status in course section
            # Coursemos/Moodle often uses button or completion status icon
            is_completed = False
            comp_el = act.find(class_=re.compile(r"completion|autocompletion", re.I))
            if comp_el:
                comp_text = comp_el.get_text(strip=True)
                if any(m in comp_text for m in ("완료", "출석", "수강 완료")):
                    is_completed = True
                img = comp_el.find("img")
                if img and any(m in img.get("alt", "") for m in ("완료", "출석")):
                    is_completed = True

            # Availability / due date text
            avail_el = act.find(class_=re.compile(r"availabilityinfo|activity-dates", re.I))
            raw_due = avail_el.get_text(strip=True) if avail_el else ""
            due_date, _ = parse_lms_date(
                raw_due,
                fallback_week=week_num,
                term_start_date=term_start_date,
            )

            status = AttendanceStatus.COMPLETED if is_completed else AttendanceStatus.INCOMPLETE
            is_overdue = False
            if not is_completed and is_past_deadline(due_date):
                is_overdue = True
                status = AttendanceStatus.OVERDUE

            full_title = f"[{course.clean_name}] {week_num}주차 {clip_idx}차시: {title}"

            item = LectureItem(
                course_id=course.course_id,
                week_number=week_num,
                clip_number=clip_idx,
                title=title,
                full_title=full_title,
                status=status,
                progress_percent=100.0 if is_completed else 0.0,
                due_date=due_date,
                raw_due_date=raw_due,
                is_overdue=is_overdue,
                link=link,
            )
            lectures.append(item)

    return lectures
