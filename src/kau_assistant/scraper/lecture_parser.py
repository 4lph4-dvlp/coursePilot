"""Lecture video and clip parser with hybrid attendance/progress evaluation."""

import copy
from datetime import datetime
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag
from pydantic import BaseModel, ConfigDict

from kau_assistant.scraper.date_parser import is_past_deadline, parse_lms_date
from kau_assistant.scraper.models import AttendanceStatus, CourseItem, LectureItem


class LectureProgress(BaseModel):
    """Progress row data parsed from Coursemos ubcompletion progress report."""

    model_config = ConfigDict(extra="forbid")

    week_number: int
    title: str
    module_id: str | None = None
    required_seconds: int | None = None
    studied_seconds: int | None = None
    is_completed: bool | None = None


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


def _parse_week_number(text: str, default: int | None = 1) -> int | None:
    """Extracts integer week number from text like '1주차', '3주', 'Week 2'."""
    m = re.search(r"(\d+)\s*주", text, re.I) or re.search(r"week\s*(\d+)", text, re.I)
    if m:
        return int(m.group(1))
    return default


def _parse_duration_seconds(text: str) -> int | None:
    """Parses duration string like 'HH:MM:SS', 'MM:SS', or 'N시간 N분 N초' into total seconds."""
    if not text:
        return None
    cleaned = text.strip()
    if not cleaned or cleaned in ("-", "—", "N/A"):
        return None

    # Check HH:MM:SS or MM:SS
    colon_match = re.match(r"^(?:(\d+):)?(\d+):(\d+)$", cleaned)
    if colon_match:
        h = int(colon_match.group(1)) if colon_match.group(1) is not None else 0
        m = int(colon_match.group(2))
        s = int(colon_match.group(3))
        return h * 3600 + m * 60 + s

    # Check Korean format: [N시간] [N분] [N초]
    h_match = re.search(r"(\d+)\s*시간", cleaned)
    m_match = re.search(r"(\d+)\s*분", cleaned)
    s_match = re.search(r"(\d+)\s*초", cleaned)
    if h_match or m_match or s_match:
        h = int(h_match.group(1)) if h_match else 0
        m = int(m_match.group(1)) if m_match else 0
        s = int(s_match.group(1)) if s_match else 0
        return h * 3600 + m * 60 + s

    return None


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
                parsed_w = _parse_week_number(w_text, default=current_week)
                if parsed_w is not None:
                    current_week = parsed_w

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

        is_completed = False
        if any(mark in attendance_str.upper() for mark in ("O", "출석", "PASS", "COMPLETE")):
            is_completed = True
        elif progress_val >= 100.0:
            is_completed = True

        status = AttendanceStatus.COMPLETED if is_completed else AttendanceStatus.INCOMPLETE

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
    """Extracts video lectures from main course home sections (top-level only)."""
    soup = BeautifulSoup(html, "lxml")
    lectures: list[LectureItem] = []

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
        sec for sec in candidate_sections
        if not any(parent in candidate_set for parent in sec.parents)
    ]
    if not top_sections:
        top_sections = [soup]

    seen_module_ids: set[str] = set()
    clip_counter_per_week: dict[int, int] = {}

    for sec_idx, sec in enumerate(top_sections):
        # Determine week number
        week_num: int | None = None
        sec_heading = sec.find(class_=re.compile(r"sectionname|section-title", re.I)) or sec.find(["h3", "h4", "h5"])
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
                week_num = int(sec["data-number"])
            elif sec.has_attr("data-sectionid"):
                week_num = int(sec["data-sectionid"])
            else:
                week_num = sec_idx

        # Find VOD activity items
        activities = sec.find_all(
            lambda tag: tag.name == "li"
            and any(cls == "activity" for cls in tag.get("class", []))
            and any(cls in ("vod", "modtype_vod") for cls in tag.get("class", []))
        )

        for act in activities:
            a_el = act.find("a")
            if not a_el:
                continue

            href = a_el.get("href", "")
            link = urljoin(course.url, href) if href else ""

            # Extract module ID
            module_id: str | None = None
            act_id = act.get("id", "")
            m_id_match = re.search(r"module-(\d+)", act_id)
            if m_id_match:
                module_id = m_id_match.group(1)
            elif href:
                h_match = re.search(r"[?&]id=(\d+)", href)
                if h_match:
                    module_id = h_match.group(1)

            if module_id:
                if module_id in seen_module_ids:
                    continue
                seen_module_ids.add(module_id)

            # Week-based clip indexing
            clip_counter_per_week[week_num] = clip_counter_per_week.get(week_num, 0) + 1
            clip_idx = clip_counter_per_week[week_num]

            # Title extraction: prefer span.instancename without accesshide
            name_el = a_el.find("span", class_="instancename") or a_el
            name_copy = copy.deepcopy(name_el)
            for ah in name_copy.find_all(class_="accesshide"):
                ah.decompose()
            raw_title = name_copy.get_text(strip=True)
            title = clean_lecture_title(raw_title)

            # Check completion status
            is_completed = False
            comp_el = act.find(class_=re.compile(r"completion|autocompletion", re.I))
            if comp_el:
                comp_text = comp_el.get_text(strip=True)
                if any(m in comp_text for m in ("완료", "출석", "수강 완료")):
                    is_completed = True
                img = comp_el.find("img")
                if img and any(m in img.get("alt", "") for m in ("완료", "출석")):
                    is_completed = True

            # Availability / Period text: check span.text-ubstrap first
            raw_due = ""
            ubstrap = act.find("span", class_="text-ubstrap")
            if ubstrap:
                raw_due = ubstrap.get_text(strip=True)
            else:
                avail_el = act.find(class_=re.compile(r"availabilityinfo|activity-dates", re.I))
                if avail_el:
                    raw_due = avail_el.get_text(strip=True)

            due_date = None
            if raw_due:
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


def parse_ubcompletion_progress(html: str) -> list[LectureProgress]:
    """Parses /report/ubcompletion/progress.php table with row-spanned week cells."""
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table", class_=re.compile(r"user_progress", re.I))
    if not table:
        return []

    # Map header columns
    col_map: dict[str, int] = {}
    header_row = table.find("thead").find("tr") if table.find("thead") else table.find("tr")
    if not header_row:
        return []

    headers = header_row.find_all(["th", "td"])
    for idx, th in enumerate(headers):
        txt = th.get_text(strip=True)
        if "주" in txt:
            col_map["week"] = idx
        elif "강의 자료" in txt or "강의자료" in txt or "학습내용" in txt or "자료" in txt:
            col_map["title"] = idx
        elif "출석인정" in txt or "요구시간" in txt:
            col_map["required"] = idx
        elif "학습시간" in txt:
            col_map["studied"] = idx

    num_headers = len(headers)
    current_week = 1
    progress_rows: list[LectureProgress] = []

    tbody = table.find("tbody")
    rows = tbody.find_all("tr") if tbody else table.find_all("tr")[1:]

    for tr in rows:
        cells = tr.find_all(["td", "th"])
        if not cells:
            continue

        if len(cells) == num_headers:
            # Row has full cells including week cell
            w_idx = col_map.get("week", 0)
            w_text = cells[w_idx].get_text(strip=True)
            parsed_w = _parse_week_number(w_text, default=current_week)
            if parsed_w is not None:
                current_week = parsed_w

            t_idx = col_map.get("title", 1)
            req_idx = col_map.get("required", 2)
            std_idx = col_map.get("studied", 3)
        elif len(cells) == num_headers - 1:
            # Row spans week from previous row (missing week cell)
            # Remaining columns shift by 1 relative to headers that had week at index 0
            w_idx = col_map.get("week", 0)
            t_idx = col_map.get("title", 1) - (1 if col_map.get("title", 1) > w_idx else 0)
            req_idx = col_map.get("required", 2) - (1 if col_map.get("required", 2) > w_idx else 0)
            std_idx = col_map.get("studied", 3) - (1 if col_map.get("studied", 3) > w_idx else 0)
        else:
            continue

        if t_idx >= len(cells) or req_idx >= len(cells) or std_idx >= len(cells):
            continue

        title_cell = cells[t_idx]
        title_copy = copy.deepcopy(title_cell)
        for ah in title_copy.find_all(class_="accesshide"):
            ah.decompose()
        raw_title = title_copy.get_text(strip=True)
        title = clean_lecture_title(raw_title)

        # Extract module ID from link if present
        module_id: str | None = None
        a_el = title_cell.find("a")
        if a_el and a_el.get("href"):
            m_match = re.search(r"[?&]id=(\d+)", a_el["href"])
            if m_match:
                module_id = m_match.group(1)

        req_sec = _parse_duration_seconds(cells[req_idx].get_text(strip=True))
        std_sec = _parse_duration_seconds(cells[std_idx].get_text(strip=True))

        is_completed: bool | None = None
        if req_sec is not None and std_sec is not None:
            if req_sec > 0:
                is_completed = std_sec >= req_sec
            else:
                is_completed = None

        progress_rows.append(
            LectureProgress(
                week_number=current_week,
                title=title,
                module_id=module_id,
                required_seconds=req_sec,
                studied_seconds=std_sec,
                is_completed=is_completed,
            )
        )

    return progress_rows


def merge_lecture_progress(
    lectures: list[LectureItem],
    rows: list[LectureProgress],
    now: datetime | None = None,
) -> list[LectureItem]:
    """Merges ubcompletion progress data into course-section lectures."""
    if not rows:
        return lectures

    unmatched_rows = list(rows)
    merged: list[LectureItem] = []

    # Helper: extract module id from lecture link
    def get_lec_mod_id(lec: LectureItem) -> str | None:
        if lec.link:
            m = re.search(r"[?&]id=(\d+)", lec.link)
            if m:
                return m.group(1)
        return None

    # Step 1: match by module_id
    matches: dict[int, LectureProgress] = {}
    for lec_idx, lec in enumerate(lectures):
        mod_id = get_lec_mod_id(lec)
        if mod_id:
            for r_idx, r in enumerate(unmatched_rows):
                if r.module_id and r.module_id == mod_id:
                    matches[lec_idx] = r
                    unmatched_rows.pop(r_idx)
                    break

    # Step 2: match by normalized title within same week
    def norm_title(t: str) -> str:
        return re.sub(r"\s+", " ", t).strip().lower()

    for lec_idx, lec in enumerate(lectures):
        if lec_idx in matches:
            continue
        lec_norm = norm_title(lec.title)
        for r_idx, r in enumerate(unmatched_rows):
            if r.week_number == lec.week_number and norm_title(r.title) == lec_norm:
                matches[lec_idx] = r
                unmatched_rows.pop(r_idx)
                break

    # Step 3: fallback to order within a week when unmatched counts match exactly
    # Group remaining by week
    unmatched_lec_by_week: dict[int, list[int]] = {}
    for lec_idx, lec in enumerate(lectures):
        if lec_idx not in matches:
            unmatched_lec_by_week.setdefault(lec.week_number, []).append(lec_idx)

    unmatched_rows_by_week: dict[int, list[LectureProgress]] = {}
    for r in list(unmatched_rows):
        unmatched_rows_by_week.setdefault(r.week_number, []).append(r)

    for week_num, lec_indices in unmatched_lec_by_week.items():
        row_candidates = unmatched_rows_by_week.get(week_num, [])
        if len(lec_indices) == len(row_candidates):
            for l_idx, r_prog in zip(lec_indices, row_candidates):
                matches[l_idx] = r_prog
                if r_prog in unmatched_rows:
                    unmatched_rows.remove(r_prog)

    # Apply matches
    for lec_idx, lec in enumerate(lectures):
        prog = matches.get(lec_idx)
        if prog is None or prog.is_completed is None:
            merged.append(lec)
            continue

        if prog.is_completed:
            status = AttendanceStatus.COMPLETED
            progress_percent = 100.0
            is_overdue = False
        else:
            status = AttendanceStatus.INCOMPLETE
            if prog.required_seconds and prog.required_seconds > 0 and prog.studied_seconds is not None:
                progress_percent = min(100.0, (prog.studied_seconds / prog.required_seconds) * 100.0)
            else:
                progress_percent = 0.0

            is_overdue = False
            if is_past_deadline(lec.due_date, now):
                is_overdue = True
                status = AttendanceStatus.OVERDUE

        updated_lec = lec.model_copy(
            update={
                "status": status,
                "progress_percent": progress_percent,
                "is_overdue": is_overdue,
            }
        )
        merged.append(updated_lec)

    return merged
