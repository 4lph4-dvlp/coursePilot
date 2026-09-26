"""Assessment deep parser with submission status detection and detail enrichment."""

from datetime import datetime
import logging
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag
from playwright.sync_api import Page

from kau_assistant.scraper.date_parser import is_past_deadline, parse_lms_date
from kau_assistant.scraper.models import (
    AssessmentItem,
    AssessmentType,
    AttachmentMeta,
    CourseItem,
    SubmissionStatus,
)
from kau_assistant.scraper.navigator import CourseNavigator

logger = logging.getLogger(__name__)


def parse_assessment_list(
    html: str,
    course_id: str,
    item_type: AssessmentType = AssessmentType.ASSIGNMENT,
    base_url: str = "",
) -> list[AssessmentItem]:
    """Parses assessment summary table (e.g. /mod/assign/index.php?id=...) into AssessmentItem list."""
    soup = BeautifulSoup(html, "lxml")
    items: list[AssessmentItem] = []

    table = soup.find("table", class_=re.compile(r"generaltable", re.I))
    if not table:
        return []

    # Map column indexes: classified once in priority order (due -> submission -> grade -> title)
    header_row = table.find("tr")
    col_map: dict[str, int] = {}
    if header_row:
        for idx, cell in enumerate(header_row.find_all(["th", "td"])):
            txt = cell.get_text(strip=True)
            if "due" not in col_map and any(k in txt for k in ("마감", "종료", "Due")):
                col_map["due"] = idx
            elif "submission" not in col_map and any(k in txt for k in ("제출", "Status")):
                col_map["submission"] = idx
            elif "grade" not in col_map and any(k in txt for k in ("채점", "성적", "Grade")):
                col_map["grade"] = idx
            elif "week" not in col_map and any(k in txt for k in ("주차", "주", "Week")):
                col_map["week"] = idx
            elif "title" not in col_map and any(k in txt for k in ("이름", "과제", "퀴즈", "토론", "시험", "제목", "활동", "Name")):
                col_map["title"] = idx

    if col_map:
        col_title = col_map.get("title")
        col_due = col_map.get("due")
        col_submission = col_map.get("submission")
        col_grade = col_map.get("grade")
        col_week = col_map.get("week")
    else:
        col_title = 1
        col_due = 2
        col_submission = 3
        col_grade = 4
        col_week = None

    rows = table.find("tbody").find_all("tr") if table.find("tbody") else table.find_all("tr")[1:]

    for tr in rows:
        cells = tr.find_all(["td", "th"])
        if len(cells) < 2:
            continue

        # Extract title and link
        raw_title = ""
        item_id = ""
        link = ""
        if col_title is not None and col_title < len(cells):
            cell_title = cells[col_title]
            a_el = cell_title.find("a")
            if a_el:
                raw_title = a_el.get_text(strip=True)
                href = a_el.get("href", "")
                if href:
                    if not href.startswith("http") and not href.startswith("/"):
                        mod_segment = "quiz" if item_type == AssessmentType.QUIZ else "assign"
                        if href.startswith("view.php"):
                            href = f"/mod/{mod_segment}/{href}"
                    link = urljoin(base_url, href)
                m_id = re.search(r"[?&]id=(\d+)", href)
                if m_id:
                    item_id = m_id.group(1)
            else:
                raw_title = cell_title.get_text(strip=True)

        if not raw_title:
            continue

        if not item_id:
            item_id = f"gen_{abs(hash(raw_title)) % 100000}"

        # Extract due date
        raw_due_date = ""
        if col_due is not None and col_due < len(cells):
            raw_due_date = cells[col_due].get_text(strip=True)

        due_date, _ = parse_lms_date(raw_due_date)

        # Extract submission status and grade
        sub_text = cells[col_submission].get_text(strip=True) if (col_submission is not None and col_submission < len(cells)) else ""
        grade_text = cells[col_grade].get_text(strip=True) if (col_grade is not None and col_grade < len(cells)) else ""

        # Status determination (D-10):
        # - Submitted / Graded: complete
        # - Draft: incomplete
        # - Not attempted: incomplete
        has_numeric_grade = any(c.isdigit() for c in grade_text)
        if any(k in sub_text for k in ("제출 완료", "제출완료", "Submitted", "제출됨")):
            status = SubmissionStatus.SUBMITTED
        elif any(k in grade_text for k in ("채점 완료", "Graded")) or "채점 완료" in sub_text or has_numeric_grade:
            status = SubmissionStatus.GRADED
        elif any(k in sub_text for k in ("임시저장", "초안", "Draft")):
            status = SubmissionStatus.DRAFT
        else:
            status = SubmissionStatus.NOT_ATTEMPTED

        is_overdue = False
        if status in (SubmissionStatus.NOT_ATTEMPTED, SubmissionStatus.DRAFT) and is_past_deadline(due_date):
            is_overdue = True

        week_number: int | None = None
        if col_week is not None and col_week < len(cells):
            cell_week = cells[col_week].get_text(strip=True)
            m_week = re.search(r"(\d+)", cell_week)
            if m_week:
                week_number = int(m_week.group(1))

        item = AssessmentItem(
            course_id=course_id,
            item_id=item_id,
            item_type=item_type,
            title=raw_title,
            status=status,
            due_date=due_date,
            raw_due_date=raw_due_date,
            url=link,
            is_overdue=is_overdue,
            week_number=week_number,
        )
        items.append(item)

    return items


def is_quiz_attempt_completed(html: str) -> bool:
    """Checks whether a quiz view page shows evidence that the student completed an attempt."""
    soup = BeautifulSoup(html, "lxml")

    # 1. Review buttons or links (e.g. "답안 검토", "Review attempt")
    for el in soup.find_all(["a", "button", "input"], class_=re.compile(r"btn|singlebutton", re.I)):
        text = el.get_text(strip=True) if el.name != "input" else el.get("value", "")
        if any(k in text for k in ("답안 검토", "검토", "Review attempt", "Review")):
            if "답안 검토" in text or "Review attempt" in text or text == "검토":
                return True

    # 2. Status banners, feedback, or info boxes
    info_boxes = soup.find_all(class_=re.compile(r"quizinfo|feedback|alert|box|notifyproblem", re.I))
    for box in info_boxes:
        txt = box.get_text(strip=True)
        if any(
            phrase in txt
            for phrase in (
                "응시 가능 횟수를 초과하여 더 이상 응시할 수 없습니다",
                "응시 가능 횟수를 초과",
                "더 이상 응시할 수 없습니다",
                "최고 점수:",
                "최고 점수 :",
                "Highest grade:",
            )
        ):
            return True

    # 3. Moodle quiz attempt summary table
    for table in soup.find_all("table", class_=re.compile(r"generaltable|quizattemptsummary", re.I)):
        for tr in table.find_all("tr"):
            row_text = tr.get_text(separator=" ", strip=True)
            if any(k in row_text for k in ("완료됨", "Finished", "Submitted", "답안 검토")):
                return True

    return False


def enrich_assessment_detail(
    item: AssessmentItem,
    detail_html: str,
    base_url: str = "",
) -> AssessmentItem:
    """Enriches AssessmentItem with instructor instructions, attachments, cut-off date, and quiz attempt status."""
    soup = BeautifulSoup(detail_html, "lxml")

    # For quizzes with hidden grades, detect completed attempts from view page
    if item.item_type == AssessmentType.QUIZ and item.status in (
        SubmissionStatus.NOT_ATTEMPTED,
        SubmissionStatus.DRAFT,
    ):
        if is_quiz_attempt_completed(detail_html):
            item.status = SubmissionStatus.SUBMITTED
            item.is_overdue = False

    # Extract instructor description
    intro_box = soup.find(class_=re.compile(r"box\s*generalbox|generalbox\s*#intro|intro", re.I)) or soup.find(
        id="intro"
    )
    if intro_box:
        item.description_html = str(intro_box)
        item.description_text = intro_box.get_text(separator="\n", strip=True)

        # Extract attachments from intro or attachment areas
        attachments: list[AttachmentMeta] = []
        attach_links = soup.find_all("a", href=re.compile(r"/pluginfile\.php/|/mod_assign/intro/|\.(pdf|zip|docx|pptx|xlsx|py|ipynb|hwp|hwpx)\b", re.I))

        for a in attach_links:
            href = a.get("href", "")
            if not href:
                continue
            text = a.get_text(strip=True)
            if not text:
                continue

            full_file_url = urljoin(base_url, href) if base_url else href

            # Separate filename and filesize if present e.g. "spec.pdf (250KB)"
            m_size = re.search(r"\(([\d.]+\s*[KMGT]?B)\)", text, re.I)
            filesize = m_size.group(1) if m_size else ""
            clean_filename = re.sub(r"\s*\([\d.]+\s*[KMGT]?B\)", "", text).strip() or text

            attachments.append(
                AttachmentMeta(
                    filename=clean_filename,
                    url=full_file_url,
                    filesize=filesize,
                )
            )
        item.attachments = attachments

    # Detect cut-off date (지각 제출 마감일) (D-12)
    # Search table cells or paragraphs
    cutoff_keywords = ["지각 제출 마감일", "지각 마감", "최종 마감일", "Cut-off date", "Cutoff"]
    cutoff_text = ""
    for th in soup.find_all(["th", "td", "span", "div"]):
        t = th.get_text(strip=True)
        if any(k in t for k in cutoff_keywords):
            # Look for the sibling or parent cell
            sibling = th.find_next_sibling(["td", "div", "span"])
            if sibling:
                cutoff_text = sibling.get_text(strip=True)
                break
            # Or inside same element
            m = re.search(r"(?:마감일|Cut-off)[:\s]*(.*)", t)
            if m:
                cutoff_text = m.group(1).strip()
                break

    if cutoff_text:
        cutoff_dt, _ = parse_lms_date(cutoff_text)
        if cutoff_dt:
            item.cutoff_date = cutoff_dt

    return item


def merge_section_assessments(
    items: list[AssessmentItem], home_html: str, course: CourseItem,
) -> list[AssessmentItem]:
    """Enrich index items and recover omitted ones using authoritative section metadata."""
    from kau_assistant.scraper.course_sections import parse_course_activities

    by_id = {item.item_id: item for item in items}
    for activity in parse_course_activities(home_html, course):
        if activity.module_type not in {"assign", "quiz"}:
            continue
        item = by_id.get(activity.module_id)
        if item is None:
            item = AssessmentItem(
                course_id=course.course_id, item_id=activity.module_id,
                item_type=AssessmentType.QUIZ if activity.module_type == "quiz" else AssessmentType.ASSIGNMENT,
                title=activity.title, url=activity.url,
                status=SubmissionStatus.NOT_ATTEMPTED,
            )
            items.append(item)
            by_id[item.item_id] = item
        item.week_number = activity.week_number
        item.start_date = activity.start_date
        item.is_available = activity.is_available
        if activity.due_date is not None:
            item.due_date = activity.due_date
            item.raw_due_date = activity.raw_due_date
        if activity.completion_known:
            item.status = SubmissionStatus.SUBMITTED if activity.is_completed else SubmissionStatus.NOT_ATTEMPTED
        item.is_overdue = item.status in (SubmissionStatus.NOT_ATTEMPTED, SubmissionStatus.DRAFT) and is_past_deadline(item.due_date)
    return items


def scrape_course_assessments(
    page: Page,
    course: CourseItem,
    navigator: CourseNavigator,
    home_html: str = "",
) -> list[AssessmentItem]:
    """Navigates to assignment and quiz summary pages and deep-scrapes details."""
    all_assessments: list[AssessmentItem] = []

    base_lms_url = navigator.settings.lms_url.rstrip("/")

    # 1. Scrape assignments
    assign_html = navigator.navigate_assessment_page(page, course, item_type="assign")
    if assign_html:
        assign_index_url = f"{base_lms_url}/mod/assign/index.php?id={course.course_id}"
        assign_items = parse_assessment_list(
            assign_html,
            course_id=course.course_id,
            item_type=AssessmentType.ASSIGNMENT,
            base_url=assign_index_url,
        )
        all_assessments.extend(assign_items)

    # 2. Scrape quizzes
    quiz_html = navigator.navigate_assessment_page(page, course, item_type="quiz")
    if quiz_html:
        quiz_index_url = f"{base_lms_url}/mod/quiz/index.php?id={course.course_id}"
        quiz_items = parse_assessment_list(
            quiz_html,
            course_id=course.course_id,
            item_type=AssessmentType.QUIZ,
            base_url=quiz_index_url,
        )
        all_assessments.extend(quiz_items)

    all_assessments = merge_section_assessments(all_assessments, home_html, course)

    # 3. Deep detail extraction for each available item with polite delay
    for item in all_assessments:
        if item.url and item.is_available:
            navigator.polite_delay()
            logger.info(f"Deep scraping assessment detail: {item.title} ({item.item_id})")
            try:
                page.goto(item.url, wait_until="domcontentloaded")
                detail_html = page.content()
                enrich_assessment_detail(item, detail_html, base_url=course.url)
            except Exception as e:
                logger.warning(f"Failed to scrape details for {item.title}: {e}")

    return all_assessments
