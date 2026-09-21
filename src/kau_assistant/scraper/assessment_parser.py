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

    # Map column indexes
    header_row = table.find("tr")
    col_map: dict[str, int] = {}
    if header_row:
        for idx, cell in enumerate(header_row.find_all(["th", "td"])):
            txt = cell.get_text(strip=True)
            if any(k in txt for k in ("과제", "퀴즈", "토론", "시험", "제목", "활동", "Name")):
                col_map["title"] = idx
            elif any(k in txt for k in ("마감일시", "마감일", "종료", "Due")):
                col_map["due"] = idx
            elif any(k in txt for k in ("제출여부", "제출 상태", "Status", "제출")):
                col_map["submission"] = idx
            elif any(k in txt for k in ("채점여부", "채점", "Grade")):
                col_map["grade"] = idx

    col_title = col_map.get("title", 1)
    col_due = col_map.get("due", 2)
    col_submission = col_map.get("submission", 3)
    col_grade = col_map.get("grade", 4)

    rows = table.find("tbody").find_all("tr") if table.find("tbody") else table.find_all("tr")[1:]

    for tr in rows:
        cells = tr.find_all(["td", "th"])
        if len(cells) < 2:
            continue

        # Extract title and link
        raw_title = ""
        item_id = ""
        link = ""
        if col_title < len(cells):
            cell_title = cells[col_title]
            a_el = cell_title.find("a")
            if a_el:
                raw_title = a_el.get_text(strip=True)
                href = a_el.get("href", "")
                link = urljoin(base_url, href) if href else ""
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
        if col_due < len(cells):
            raw_due_date = cells[col_due].get_text(strip=True)

        due_date, _ = parse_lms_date(raw_due_date)

        # Extract submission status and grade
        sub_text = cells[col_submission].get_text(strip=True) if col_submission < len(cells) else ""
        grade_text = cells[col_grade].get_text(strip=True) if col_grade < len(cells) else ""

        # Status determination (D-10):
        # - Submitted / Graded: complete
        # - Draft: incomplete
        # - Not attempted: incomplete
        if any(k in sub_text for k in ("제출 완료", "제출완료", "Submitted", "제출됨")):
            status = SubmissionStatus.SUBMITTED
        elif any(k in grade_text for k in ("채점 완료", "Graded")) or "채점 완료" in sub_text:
            status = SubmissionStatus.GRADED
        elif any(k in sub_text for k in ("임시저장", "초안", "Draft")):
            status = SubmissionStatus.DRAFT
        else:
            status = SubmissionStatus.NOT_ATTEMPTED

        is_overdue = False
        if status in (SubmissionStatus.NOT_ATTEMPTED, SubmissionStatus.DRAFT) and is_past_deadline(due_date):
            is_overdue = True

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
        )
        items.append(item)

    return items


def enrich_assessment_detail(
    item: AssessmentItem,
    detail_html: str,
    base_url: str = "",
) -> AssessmentItem:
    """Enriches AssessmentItem with instructor instructions, attachments, and cut-off date."""
    soup = BeautifulSoup(detail_html, "lxml")

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


def scrape_course_assessments(
    page: Page,
    course: CourseItem,
    navigator: CourseNavigator,
) -> list[AssessmentItem]:
    """Navigates to assignment and quiz summary pages and deep-scrapes details."""
    all_assessments: list[AssessmentItem] = []

    # 1. Scrape assignments
    assign_html = navigator.navigate_assessment_page(page, course, item_type="assign")
    if assign_html:
        assign_items = parse_assessment_list(
            assign_html,
            course_id=course.course_id,
            item_type=AssessmentType.ASSIGNMENT,
            base_url=course.url,
        )
        all_assessments.extend(assign_items)

    # 2. Scrape quizzes
    quiz_html = navigator.navigate_assessment_page(page, course, item_type="quiz")
    if quiz_html:
        quiz_items = parse_assessment_list(
            quiz_html,
            course_id=course.course_id,
            item_type=AssessmentType.QUIZ,
            base_url=course.url,
        )
        all_assessments.extend(quiz_items)

    # 3. Deep detail extraction for each item with polite delay
    for item in all_assessments:
        if item.url:
            navigator.polite_delay()
            logger.info(f"Deep scraping assessment detail: {item.title} ({item.item_id})")
            try:
                page.goto(item.url, wait_until="domcontentloaded")
                detail_html = page.content()
                enrich_assessment_detail(item, detail_html, base_url=course.url)
            except Exception as e:
                logger.warning(f"Failed to scrape details for {item.title}: {e}")

    return all_assessments
