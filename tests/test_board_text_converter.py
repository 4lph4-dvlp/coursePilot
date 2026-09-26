"""Unit tests for HTML-to-Markdown text converter and summary preview extractor."""

from coursepilot.board.text_converter import extract_summary_preview, html_to_markdown


def test_html_to_markdown_tags():
    """Verify conversion of standard HTML formatting tags into Markdown."""
    html = """
    <p>Welcome to <strong>Software Engineering</strong>!</p>
    <p>Please read the <em>syllabus</em> and visit <a href="https://kau.ac.kr">KAU Website</a>.<br>Next line.</p>
    <ul>
        <li>Item 1</li>
        <li>Item 2</li>
    </ul>
    """
    md = html_to_markdown(html)
    assert "**Software Engineering**" in md
    assert "*syllabus*" in md
    assert "[KAU Website](https://kau.ac.kr)" in md
    assert "- Item 1" in md
    assert "- Item 2" in md
    assert "Next line." in md


def test_html_to_markdown_removes_unwanted():
    """Verify that script, style, and .accesshide elements are stripped."""
    html = """
    <div>
        <script>alert('xss');</script>
        <style>.hide { display: none; }</style>
        <h3>Notice Title<span class="accesshide"> 게시판 글</span></h3>
        <p>Actual content here.</p>
    </div>
    """
    md = html_to_markdown(html)
    assert "alert" not in md
    assert "display: none" not in md
    assert "게시판 글" not in md
    assert "Notice Title" in md
    assert "Actual content here." in md


def test_non_breaking_space_replacement():
    """Verify that \\xa0 (non-breaking space) is converted to normal space for CP949 compatibility."""
    html = "<p>Notice:\xa0중간고사\xa0일정\xa0안내입니다.</p>"
    md = html_to_markdown(html)
    assert "\xa0" not in md
    assert "Notice: 중간고사 일정 안내입니다." in md


def test_extract_summary_preview():
    """Verify 2-line capping and 140-character truncation with '...'."""
    # Empty
    assert extract_summary_preview("") == ""
    assert extract_summary_preview(None) == ""

    # Short 2 lines
    text = "첫 번째 줄 내용입니다.\n두 번째 줄 내용입니다.\n세 번째 줄은 제외됩니다."
    preview = extract_summary_preview(text, max_lines=2, max_chars=140)
    assert "첫 번째 줄 내용입니다. 두 번째 줄 내용입니다." == preview
    assert "세 번째 줄" not in preview

    # Long text truncation
    long_line = "가나다라마바사 " * 25  # ~200 chars
    long_preview = extract_summary_preview(long_line, max_lines=2, max_chars=140)
    assert len(long_preview) <= 140
    assert long_preview.endswith("...")
