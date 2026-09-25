"""HTML to Markdown converter and summary preview extractor with CP949 safety."""

import re
from bs4 import BeautifulSoup


def html_to_markdown(html_content: str | None) -> str:
    """Converts HTML content (e.g. from Moodle Atto editor) into readable Markdown.

    Normalizes non-breaking spaces (\xa0) to standard spaces to prevent
    UnicodeEncodeError on Windows CP949 console environments (Pitfall 1, D-15-07).
    """
    if not html_content or not html_content.strip():
        return ""

    soup = BeautifulSoup(html_content, "lxml")

    # Decompose unwanted elements
    for tag in soup.find_all(["script", "style", "meta", "link"]):
        tag.decompose()

    for ah in soup.find_all(class_="accesshide"):
        ah.decompose()

    # Convert line breaks and horizontal rules
    for br in soup.find_all(["br", "hr"]):
        br.replace_with("\n")

    # Convert anchors to Markdown links
    for a in soup.find_all("a"):
        href = (a.get("href") or "").strip()
        text = a.get_text()
        if href and not href.lower().startswith("javascript:"):
            a.replace_with(f"[{text}]({href})")
        else:
            a.replace_with(text)

    # Convert bold / strong
    for b in soup.find_all(["strong", "b"]):
        text = b.get_text()
        b.replace_with(f"**{text}**")

    # Convert italic / em
    for i in soup.find_all(["em", "i"]):
        text = i.get_text()
        i.replace_with(f"*{text}*")

    # Convert list items
    for li in soup.find_all("li"):
        text = li.get_text().strip()
        li.replace_with(f"\n- {text}")

    # Add spacing around block elements
    for block in soup.find_all(["p", "div", "blockquote", "h1", "h2", "h3", "h4", "h5", "h6"]):
        block.insert_before("\n\n")
        block.insert_after("\n\n")

    raw_text = soup.get_text()

    # Replace non-breaking space (\xa0) with regular space (Windows CP949 safety)
    raw_text = raw_text.replace("\xa0", " ")

    # Clean whitespace and lines
    lines = []
    for line in raw_text.splitlines():
        cleaned_line = re.sub(r"[ \t]+", " ", line).strip()
        lines.append(cleaned_line)

    result = "\n".join(lines)
    # Collapse 3+ consecutive newlines to \n\n
    result = re.sub(r"\n{3,}", "\n\n", result).strip()

    return result


def extract_summary_preview(text: str | None, max_lines: int = 2, max_chars: int = 140) -> str:
    """Extracts a 1-2 line summary preview (up to max_chars) from text/markdown.

    Decision D-15-05: preview capped at 1-2 lines and 140 characters.
    """
    if not text or not text.strip():
        return ""

    non_empty_lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not non_empty_lines:
        return ""

    selected_lines = non_empty_lines[:max_lines]
    preview = " ".join(selected_lines)
    preview = re.sub(r"\s+", " ", preview).strip()

    if len(preview) > max_chars:
        return preview[: max_chars - 3].rstrip() + "..."

    return preview
