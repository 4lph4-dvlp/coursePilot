"""Coursemos LXP bulletin board scraper for notices, Q&A boards, and articles."""

import copy
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup, Tag

from coursepilot.board.models import (
    BoardArticleDetail,
    BoardAttachmentItem,
    BoardModuleInfo,
    BoardPostItem,
    BoardReplyItem,
    BoardType,
)
from coursepilot.board.text_converter import html_to_markdown


def classify_board_type(title: str, custom_name: str | None = None) -> BoardType:
    """Classifies a board title into NOTICE, QNA, CUSTOM, or OTHER (D-15-12)."""
    if custom_name and custom_name.strip().lower() in title.lower():
        return BoardType.CUSTOM

    t = title.lower()
    if any(k in t for k in ("공지", "notice", "안내")):
        return BoardType.NOTICE
    if any(k in t for k in ("q&a", "질문", "문의", "질의", "qna")):
        return BoardType.QNA
    return BoardType.OTHER


def extract_board_modules(html: str, base_url: str) -> list[BoardModuleInfo]:
    """Discovers Coursemos board modules (ubboard, forum) on a course homepage."""
    if not html or not html.strip():
        return []

    soup = BeautifulSoup(html, "lxml")
    modules: list[BoardModuleInfo] = []
    seen_module_ids: set[str] = set()

    # Locate activity items for ubboard and forum
    activities = soup.find_all(
        lambda tag: tag.name == "li"
        and any(cls == "activity" for cls in tag.get("class", []))
        and any(
            cls in ("ubboard", "modtype_ubboard", "forum", "modtype_forum")
            for cls in tag.get("class", [])
        )
    )

    for act in activities:
        a_el = act.find("a", href=re.compile(r"/mod/(?:ubboard|forum)/view\.php", re.I))
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

        board_type = classify_board_type(title)
        full_url = urljoin(base_url, raw_href)

        modules.append(
            BoardModuleInfo(
                module_id=module_id,
                title=title,
                url=full_url,
                board_type=board_type,
            )
        )

    return modules


def parse_board_list_page(
    html: str,
    base_url: str,
    board_id: str,
    board_type: BoardType,
    current_user_name: str = "",
) -> list[BoardPostItem]:
    """Parses a Coursemos board list page (view.php) into BoardPostItem objects.

    Supports dynamic column mapping (5-column notice vs 6-column Q&A), secret posts,
    badges, comment counts, and my-question detection.
    """
    if not html or not html.strip():
        return []

    soup = BeautifulSoup(html, "lxml")
    table = soup.find(
        "table",
        class_=lambda c: c
        and any(k in str(c) for k in ("ubboard_table", "generaltable", "table-hover")),
    )
    if not table:
        table = soup.find("table")
    if not table:
        return []

    # Dynamic column mapping
    col_map = {"num": 0, "status": -1, "subject": 1, "writer": 2, "date": 3, "hit": 4}
    header_tr = None
    thead = table.find("thead")
    if thead:
        header_tr = thead.find("tr")
    if not header_tr:
        first_tr = table.find("tr")
        if first_tr and first_tr.find("th"):
            header_tr = first_tr

    if header_tr:
        headers = [th.get_text(strip=True).lower() for th in header_tr.find_all(["th", "td"])]
        for idx, h in enumerate(headers):
            if any(k in h for k in ("번호", "no", "num")):
                col_map["num"] = idx
            elif any(k in h for k in ("상태", "status")):
                col_map["status"] = idx
            elif any(k in h for k in ("제목", "subject", "title")):
                col_map["subject"] = idx
            elif any(k in h for k in ("작성자", "writer", "author")):
                col_map["writer"] = idx
            elif any(k in h for k in ("작성일", "date", "created", "등록일", "일시")):
                col_map["date"] = idx
            elif any(k in h for k in ("조회", "hit", "view")):
                col_map["hit"] = idx

    posts: list[BoardPostItem] = []
    tbody = table.find("tbody")
    rows = tbody.find_all("tr") if tbody else table.find_all("tr")

    for row_idx, tr in enumerate(rows, start=1):
        cells = tr.find_all("td")
        if not cells:
            continue

        # If no explicit header was found and columns count is 6, adjust default status col
        if col_map["status"] == -1 and len(cells) >= 6:
            col_map = {"num": 0, "status": 1, "subject": 2, "writer": 3, "date": 4, "hit": 5}

        # Number / ID
        num_cell = cells[col_map["num"]] if 0 <= col_map["num"] < len(cells) else None
        num_text = num_cell.get_text(strip=True) if num_cell else str(row_idx)

        # Subject / Title
        subj_idx = col_map["subject"] if 0 <= col_map["subject"] < len(cells) else 1
        subj_cell = cells[subj_idx] if subj_idx < len(cells) else cells[0]

        a_tag = subj_cell.find("a")
        is_secret = False
        post_url = ""
        bwid: str | None = None
        comment_count = 0

        if a_tag and a_tag.get("href"):
            raw_href = a_tag["href"]
            post_url = urljoin(base_url, raw_href)
            bw_m = re.search(r"bwid=(\d+)", raw_href)
            if bw_m:
                bwid = bw_m.group(1)

            # Check comment count
            comment_span = a_tag.find("span", class_="comment") or subj_cell.find(
                "span", class_="comment"
            )
            if comment_span:
                cm = re.search(r"\d+", comment_span.get_text())
                if cm:
                    comment_count = int(cm.group(0))

            a_copy = copy.deepcopy(a_tag)
            for bad in a_copy.find_all(
                class_=lambda c: c and any(k in str(c) for k in ("comment", "newicon", "secret", "accesshide"))
            ):
                bad.decompose()
            title = re.sub(r"\s+", " ", a_copy.get_text()).strip()
        else:
            # Secret post or non-anchor cell
            is_secret = True
            cell_copy = copy.deepcopy(subj_cell)
            for bad in cell_copy.find_all(
                class_=lambda c: c and any(k in str(c) for k in ("comment", "newicon", "secret", "accesshide"))
            ):
                bad.decompose()
            title = re.sub(r"\s+", " ", cell_copy.get_text()).strip()
            if not title:
                title = "비밀글입니다."

        post_id = bwid or num_text or str(row_idx)

        # Author / Writer
        writer_idx = col_map["writer"] if 0 <= col_map["writer"] < len(cells) else 2
        writer_cell = cells[writer_idx] if writer_idx < len(cells) else None
        author = re.sub(r"\s+", " ", writer_cell.get_text()).strip() if writer_cell else ""

        # Date
        date_idx = col_map["date"] if 0 <= col_map["date"] < len(cells) else 3
        date_cell = cells[date_idx] if date_idx < len(cells) else None
        created_at = ""
        if date_cell:
            title_span = date_cell.find("span", title=True)
            if title_span and title_span.get("title"):
                created_at = title_span["title"].strip()
            else:
                created_at = re.sub(r"\s+", " ", date_cell.get_text()).strip()

        # Hits
        hit_idx = col_map["hit"] if 0 <= col_map["hit"] < len(cells) else 4
        hit_cell = cells[hit_idx] if hit_idx < len(cells) else None
        hit_count = 0
        if hit_cell:
            hm = re.search(r"\d+", hit_cell.get_text())
            if hm:
                hit_count = int(hm.group(0))

        # Q&A Answer status
        is_answered: bool | None = None
        if board_type == BoardType.QNA:
            status_text = ""
            if 0 <= col_map["status"] < len(cells):
                status_text = cells[col_map["status"]].get_text(strip=True)

            if "완료" in status_text or comment_count > 0 or title.lower().startswith("[re]") or "[re]" in title.lower() or "re:" in title.lower():
                is_answered = True
            elif "대기" in status_text or "접수" in status_text:
                is_answered = False
            else:
                is_answered = (comment_count > 0)

        # My question detection
        is_my_question = False
        if current_user_name and current_user_name.strip() and author:
            c_name = current_user_name.strip()
            a_name = author.strip()
            if c_name in a_name or a_name in c_name:
                is_my_question = True

        posts.append(
            BoardPostItem(
                post_id=post_id,
                bwid=bwid,
                board_id=board_id,
                board_type=board_type,
                title=title,
                author=author,
                created_at=created_at,
                hit_count=hit_count,
                url=post_url,
                is_read=False,
                is_my_question=is_my_question,
                is_answered=is_answered,
                is_secret=is_secret,
            )
        )

    return posts


def parse_board_article_page(html: str, base_url: str) -> BoardArticleDetail:
    """Parses a Coursemos article detail page (article.php)."""
    if not html or not html.strip():
        return BoardArticleDetail(
            subject="",
            author="",
            created_at="",
            hit_count=0,
            content="",
            attachments=[],
            replies=[],
        )

    soup = BeautifulSoup(html, "lxml")
    container = soup.find("div", class_="ubboard_view") or soup

    # Subject
    subject_el = container.find("div", class_="subject") or container.find(["h3", "h4", "h2"])
    subject = subject_el.get_text(strip=True) if subject_el else ""

    # Author
    writer_el = container.find("div", class_="writer") or container.find(
        class_=re.compile(r"\b(writer|author)\b", re.I)
    )
    author = writer_el.get_text(strip=True) if writer_el else ""

    # Date
    date_el = container.find("div", class_="date") or container.find(
        class_=re.compile(r"\b(date|created)\b", re.I)
    )
    created_at = date_el.get_text(strip=True) if date_el else ""

    # Hit count
    hit_el = container.find("div", class_="hit") or container.find(
        class_=re.compile(r"\b(hit|view)\b", re.I)
    )
    hit_count = 0
    if hit_el:
        hm = re.search(r"\d+", hit_el.get_text())
        if hm:
            hit_count = int(hm.group(0))

    # Attachments
    attachments: list[BoardAttachmentItem] = []
    files_container = container.find(class_=re.compile(r"\b(files|attachments)\b", re.I))
    if files_container:
        for a in files_container.find_all("a", href=True):
            href = a.get("href", "").strip()
            fname = a.get_text(strip=True)
            if href and fname:
                full_url = urljoin(base_url, href)
                attachments.append(
                    BoardAttachmentItem(
                        filename=fname,
                        download_url=full_url,
                    )
                )

    # Content
    content_el = container.find("div", class_="content") or container.find(
        "div", class_="text_to_html"
    )
    content_md = html_to_markdown(str(content_el)) if content_el else ""

    # Replies / Official answers
    replies: list[BoardReplyItem] = []
    comment_list = container.find(
        class_=lambda c: c and any(k in str(c).lower() for k in ("comment", "reply"))
    )
    if comment_list:
        comment_items = comment_list.find_all(
            ["div", "li"],
            class_=lambda c: c and any(k in str(c).lower() for k in ("comment", "reply")),
        )
        for item in comment_items:
            c_writer_el = item.find(
                class_=lambda c: c and any(k in str(c).lower() for k in ("writer", "author", "name"))
            )
            c_date_el = item.find(
                class_=lambda c: c and any(k in str(c).lower() for k in ("date", "time", "created"))
            )
            c_content_el = item.find(
                class_=lambda c: c and any(k in str(c).lower() for k in ("content", "text", "body", "message"))
            )

            c_writer = c_writer_el.get_text(strip=True) if c_writer_el else "작성자"
            c_date = c_date_el.get_text(strip=True) if c_date_el else ""

            if c_content_el:
                c_body = html_to_markdown(str(c_content_el))
            else:
                item_copy = copy.deepcopy(item)
                for meta_tag in (c_writer_el, c_date_el):
                    if meta_tag and meta_tag.name:
                        matched = item_copy.find(meta_tag.name, class_=meta_tag.get("class", []))
                        if matched:
                            matched.decompose()
                c_body = html_to_markdown(str(item_copy))

            if c_body:
                replies.append(
                    BoardReplyItem(
                        author=c_writer,
                        created_at=c_date,
                        content=c_body,
                    )
                )

    return BoardArticleDetail(
        subject=subject,
        author=author,
        created_at=created_at,
        hit_count=hit_count,
        content=content_md,
        attachments=attachments,
        replies=replies,
    )
