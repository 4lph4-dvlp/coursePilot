"""Integration tests for board runner orchestrator, filters, and viewer."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import httpx
import pytest

from coursepilot.board.models import BoardType
from coursepilot.board.read_state import BoardReadStateManager
from coursepilot.board.runner import run_board_pipeline, view_board_article
from coursepilot.config import Settings
from coursepilot.scraper.models import CourseItem


@pytest.fixture
def dummy_settings(tmp_path: Path) -> Settings:
    """Fixture providing dummy settings with temporary cache and download directories."""
    return Settings(
        lms_id="testuser",
        lms_password="testpassword",
        lms_url="https://canvas.kau.ac.kr",
        session_cache_path=tmp_path / "cache" / "session.json",
        download_dir=tmp_path / "downloads",
        course_mappings_path=tmp_path / "course_mappings.json",
    )


@pytest.fixture
def mock_courses():
    """Fixture returning 2 mock courses."""
    return [
        CourseItem(
            course_id="101",
            raw_name="알고리즘 (Algo)",
            clean_name="알고리즘",
            url="https://canvas.kau.ac.kr/course/view.php?id=101",
        ),
        CourseItem(
            course_id="102",
            raw_name="운영체제 (OS)",
            clean_name="운영체제",
            url="https://canvas.kau.ac.kr/course/view.php?id=102",
        ),
    ]


COURSE_101_HOME = """
<html><body>
  <li class="activity ubboard" id="module-501">
    <a href="/mod/ubboard/view.php?id=501">
      <span class="instancename">공지사항<span class="accesshide">게시판</span></span>
    </a>
  </li>
  <li class="activity ubboard" id="module-502">
    <a href="/mod/ubboard/view.php?id=502">
      <span class="instancename">질문답변 (Q&A)<span class="accesshide">게시판</span></span>
    </a>
  </li>
</body></html>
"""

COURSE_102_HOME = """
<html><body>
  <li class="activity ubboard" id="module-601">
    <a href="/mod/ubboard/view.php?id=601">
      <span class="instancename">공지사항<span class="accesshide">게시판</span></span>
    </a>
  </li>
</body></html>
"""

BOARD_501_LIST = """
<table class="ubboard_table">
  <thead><tr><th>번호</th><th>제목</th><th>작성자</th><th>작성일</th><th>조회</th></tr></thead>
  <tbody>
    <tr>
      <td>1</td>
      <td><a href="/mod/ubboard/article.php?id=501&bwid=1001">알고리즘 1주차 공지</a></td>
      <td>이교수</td>
      <td>2026-09-01</td>
      <td>100</td>
    </tr>
    <tr>
      <td>2</td>
      <td><a href="/mod/ubboard/article.php?id=501&bwid=1002">알고리즘 과제 안내</a></td>
      <td>이교수</td>
      <td>2026-09-10</td>
      <td>80</td>
    </tr>
    <tr>
      <td>3</td>
      <td><a href="/mod/ubboard/article.php?id=501&bwid=1003">알고리즘 중간고사 안내</a></td>
      <td>이교수</td>
      <td>2026-09-20</td>
      <td>120</td>
    </tr>
  </tbody>
</table>
"""

BOARD_502_LIST = """
<table class="ubboard_table">
  <thead><tr><th>번호</th><th>상태</th><th>제목</th><th>작성자</th><th>작성일</th><th>조회</th></tr></thead>
  <tbody>
    <tr>
      <td>1</td>
      <td>답변대기</td>
      <td><a href="/mod/ubboard/article.php?id=502&bwid=2001">다익스트라 질문</a></td>
      <td>홍길동</td>
      <td>2026-09-21</td>
      <td>12</td>
    </tr>
    <tr>
      <td>2</td>
      <td>답변완료</td>
      <td><a href="/mod/ubboard/article.php?id=502&bwid=2002">시간복잡도 질문</a></td>
      <td>김철수</td>
      <td>2026-09-22</td>
      <td>34</td>
    </tr>
  </tbody>
</table>
"""

BOARD_601_LIST = """
<table class="ubboard_table">
  <thead><tr><th>번호</th><th>제목</th><th>작성자</th><th>작성일</th><th>조회</th></tr></thead>
  <tbody>
    <tr>
      <td>1</td>
      <td><a href="/mod/ubboard/article.php?id=601&bwid=3001">OS 환영 공지</a></td>
      <td>박교수</td>
      <td>2026-09-02</td>
      <td>95</td>
    </tr>
  </tbody>
</table>
"""

ARTICLE_1001_DETAIL = """
<div class="ubboard_view">
  <div class="subject">알고리즘 1주차 공지</div>
  <div class="writer">이교수</div>
  <div class="date">2026-09-01 10:00:00</div>
  <div class="content"><p>수업 소개 및 <strong>선수과목</strong> 안내입니다.</p></div>
  <div class="files">
    <ul><li><a href="/pluginfile.php/1/mod_ubboard/attachment/1/syllabus.pdf">syllabus.pdf</a></li></ul>
  </div>
</div>
"""


def test_run_board_pipeline_multi_course(dummy_settings, mock_courses):
    """Verify board pipeline aggregates notices and Q&A across multiple courses."""

    def mock_get(url, **kwargs):
        url_str = str(url)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        if "id=101" in url_str and "view.php" in url_str and "ubboard" not in url_str:
            mock_resp.text = COURSE_101_HOME
        elif "id=102" in url_str and "view.php" in url_str and "ubboard" not in url_str:
            mock_resp.text = COURSE_102_HOME
        elif "id=501" in url_str:
            mock_resp.text = BOARD_501_LIST
        elif "id=502" in url_str:
            mock_resp.text = BOARD_502_LIST
        elif "id=601" in url_str:
            mock_resp.text = BOARD_601_LIST
        else:
            mock_resp.text = "<html></html>"
        return mock_resp

    mock_client = MagicMock()
    mock_client.get.side_effect = mock_get

    with patch("coursepilot.board.runner.SessionManager") as MockSM, patch(
        "coursepilot.board.runner.get_authenticated_httpx_client", return_value=mock_client
    ), patch("coursepilot.board.runner.extract_courses", return_value=mock_courses):
        mock_page = MagicMock()
        mock_page.locator.return_value.count.return_value = 0
        MockSM.return_value.__enter__.return_value.get_authenticated_page.return_value = mock_page

        report = run_board_pipeline(settings=dummy_settings, limit=None, fetch_all=True)

        assert report.schema_version == 1
        assert report.command == "board"
        assert report.summary.total_courses == 2
        assert report.summary.total_notices == 4  # 3 in Algo, 1 in OS
        assert report.summary.total_questions == 2
        assert len(report.courses) == 2
        assert report.errors == []


def test_run_board_pipeline_course_error_isolation(dummy_settings, mock_courses):
    """Verify that a 500 error in one course does not stop collection for subsequent courses."""

    def mock_get(url, **kwargs):
        url_str = str(url)
        if "id=101" in url_str and "ubboard" not in url_str:
            resp = httpx.Response(500, request=httpx.Request("GET", url_str))
            resp.raise_for_status()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        if "id=102" in url_str and "ubboard" not in url_str:
            mock_resp.text = COURSE_102_HOME
        elif "id=601" in url_str:
            mock_resp.text = BOARD_601_LIST
        return mock_resp

    mock_client = MagicMock()
    mock_client.get.side_effect = mock_get

    with patch("coursepilot.board.runner.SessionManager") as MockSM, patch(
        "coursepilot.board.runner.get_authenticated_httpx_client", return_value=mock_client
    ), patch("coursepilot.board.runner.extract_courses", return_value=mock_courses):
        mock_page = MagicMock()
        mock_page.locator.return_value.count.return_value = 0
        MockSM.return_value.__enter__.return_value.get_authenticated_page.return_value = mock_page

        report = run_board_pipeline(settings=dummy_settings, limit=None, fetch_all=True)

        assert len(report.errors) == 1
        assert report.errors[0]["course_id"] == "101"
        assert len(report.courses) == 1
        assert report.courses[0].course_id == "102"
        assert len(report.courses[0].notices) == 1


def test_run_board_pipeline_filters(dummy_settings, mock_courses):
    """Verify limit, unread-only, unanswered, and my-only filters."""

    def mock_get(url, **kwargs):
        url_str = str(url)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        if "id=101" in url_str and "ubboard" not in url_str:
            mock_resp.text = COURSE_101_HOME
        elif "id=501" in url_str:
            mock_resp.text = BOARD_501_LIST
        elif "id=502" in url_str:
            mock_resp.text = BOARD_502_LIST
        return mock_resp

    mock_client = MagicMock()
    mock_client.get.side_effect = mock_get

    with patch("coursepilot.board.runner.SessionManager") as MockSM, patch(
        "coursepilot.board.runner.get_authenticated_httpx_client", return_value=mock_client
    ), patch("coursepilot.board.runner.extract_courses", return_value=[mock_courses[0]]):
        mock_page = MagicMock()
        # Set user name to 홍길동
        mock_user = MagicMock()
        mock_user.count.return_value = 1
        mock_user.text_content.return_value = "홍길동"
        mock_page.locator.return_value.first = mock_user
        MockSM.return_value.__enter__.return_value.get_authenticated_page.return_value = mock_page

        # Pre-mark post 1001 as read
        read_state_path = dummy_settings.session_cache_path.parent / "board_read_state.json"
        state_mgr = BoardReadStateManager(read_state_path)
        state_mgr.mark_as_read("101", ["1001"])

        # 1. Test limit 2
        r_limit = run_board_pipeline(settings=dummy_settings, limit=2)
        assert len(r_limit.courses[0].notices) == 2

        # 2. Test unread_only (1001 skipped)
        r_unread = run_board_pipeline(settings=dummy_settings, unread_only=True, fetch_all=True)
        notice_ids = [n.post_id for n in r_unread.courses[0].notices]
        assert "1001" not in notice_ids
        assert "1002" in notice_ids

        # 3. Test unanswered (only post 2001 has 답변대기)
        r_unanswered = run_board_pipeline(
            settings=dummy_settings, command_scope="qna", unanswered=True, fetch_all=True
        )
        assert len(r_unanswered.courses[0].qna) == 1
        assert r_unanswered.courses[0].qna[0].post_id == "2001"

        # 4. Test my_only (only post 2001 was written by 홍길동)
        r_my = run_board_pipeline(
            settings=dummy_settings, command_scope="qna", my_only=True, fetch_all=True
        )
        assert len(r_my.courses[0].qna) == 1
        assert r_my.courses[0].qna[0].is_my_question is True
        assert r_my.courses[0].qna[0].post_id == "2001"


def test_view_board_article_auto_marks_read(dummy_settings, mock_courses):
    """Verify view_board_article retrieves detail and auto marks as read in read state."""

    def mock_get(url, **kwargs):
        url_str = str(url)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        if "id=101" in url_str and "ubboard" not in url_str:
            mock_resp.text = COURSE_101_HOME
        elif "id=501" in url_str and "article.php" not in url_str:
            mock_resp.text = BOARD_501_LIST
        elif "bwid=1001" in url_str:
            mock_resp.text = ARTICLE_1001_DETAIL
        return mock_resp

    mock_client = MagicMock()
    mock_client.get.side_effect = mock_get

    read_state_path = dummy_settings.session_cache_path.parent / "board_read_state.json"
    state_mgr = BoardReadStateManager(read_state_path)
    assert state_mgr.is_read("101", "1001") is False

    with patch("coursepilot.board.runner.SessionManager") as MockSM, patch(
        "coursepilot.board.runner.get_authenticated_httpx_client", return_value=mock_client
    ), patch("coursepilot.board.runner.extract_courses", return_value=[mock_courses[0]]):
        MockSM.return_value.__enter__.return_value.get_authenticated_page.return_value = MagicMock()

        article = view_board_article(
            post_id_or_bwid="1001",
            course_query="알고리즘",
            settings=dummy_settings,
        )

        assert article.post_id == "1001"
        assert "**선수과목**" in article.content
        assert article.is_read is True
        assert len(article.attachments) == 1
        assert article.attachments[0].filename == "syllabus.pdf"

        # Re-check read state from disk
        reloaded_mgr = BoardReadStateManager(read_state_path)
        assert reloaded_mgr.is_read("101", "1001") is True


def test_view_board_article_downloads_attachments(dummy_settings, mock_courses):
    """Verify --download-attachments downloads attachment files and sets saved_path."""

    def mock_get(url, **kwargs):
        url_str = str(url)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        if "id=101" in url_str and "ubboard" not in url_str:
            mock_resp.text = COURSE_101_HOME
        elif "id=501" in url_str and "article.php" not in url_str:
            mock_resp.text = BOARD_501_LIST
        elif "bwid=1001" in url_str:
            mock_resp.text = ARTICLE_1001_DETAIL
        return mock_resp

    mock_client = MagicMock()
    mock_client.get.side_effect = mock_get

    with patch("coursepilot.board.runner.SessionManager") as MockSM, patch(
        "coursepilot.board.runner.get_authenticated_httpx_client", return_value=mock_client
    ), patch("coursepilot.board.runner.extract_courses", return_value=[mock_courses[0]]), patch(
        "coursepilot.board.runner.download_material_file",
        return_value=(Path("downloads/알고리즘/notices/syllabus.pdf"), 2048, False),
    ) as mock_download:
        MockSM.return_value.__enter__.return_value.get_authenticated_page.return_value = MagicMock()

        article = view_board_article(
            post_id_or_bwid="1001",
            course_query="알고리즘",
            download_attachments=True,
            settings=dummy_settings,
        )

        assert mock_download.called
        assert article.attachments[0].saved_path == "downloads\\알고리즘\\notices\\syllabus.pdf" or "downloads/알고리즘/notices/syllabus.pdf" in article.attachments[0].saved_path
        assert article.attachments[0].filesize == 2048


def test_render_board_report():
    """Verify Rich console rendering for board summary, inactive courses, badges, and errors."""
    import io
    from datetime import datetime
    from rich.console import Console
    from coursepilot.board.models import (
        BoardAttachmentItem,
        BoardPostItem,
        BoardReport,
        BoardSummary,
        BoardType,
        CourseBoardGroup,
    )
    from coursepilot.reporter import render_board_report

    active_group = CourseBoardGroup(
        course_id="101",
        course_name="알고리즘",
        course_abbr="Algo",
        notices=[
            BoardPostItem(
                post_id="1",
                board_id="501",
                board_type=BoardType.NOTICE,
                title="시험 안내",
                author="이교수",
                created_at="2026-09-20",
                url="https://canvas.kau.ac.kr/mod/ubboard/article.php?id=501&bwid=1",
                is_read=False,
                summary_preview="중간고사 시험 범위 안내입니다.",
                attachments=[
                    BoardAttachmentItem(filename="guide.pdf", download_url="https://example.com/guide.pdf")
                ],
            )
        ],
        qna=[
            BoardPostItem(
                post_id="2",
                board_id="502",
                board_type=BoardType.QNA,
                title="과제 질문",
                author="홍길동",
                created_at="2026-09-21",
                url="https://canvas.kau.ac.kr/mod/ubboard/article.php?id=502&bwid=2",
                is_read=True,
                is_my_question=True,
                is_answered=True,
            ),
            BoardPostItem(
                post_id="3",
                board_id="502",
                board_type=BoardType.QNA,
                title="강의 오타 문의",
                author="이학생",
                created_at="2026-09-22",
                url="https://canvas.kau.ac.kr/mod/ubboard/article.php?id=502&bwid=3",
                is_read=False,
                is_my_question=False,
                is_answered=False,
            ),
        ],
    )
    inactive_group = CourseBoardGroup(
        course_id="102",
        course_name="운영체제",
        course_abbr="OS",
    )
    summary = BoardSummary(
        total_courses=2,
        total_notices=1,
        unread_notices=1,
        total_questions=2,
        unanswered_questions=1,
        my_questions=1,
    )
    report = BoardReport(
        generated_at=datetime(2026, 9, 26, 12, 0, 0),
        summary=summary,
        courses=[active_group, inactive_group],
        errors=[{"course_name": "실패과목", "error": "Connection Timeout"}],
    )

    buf = io.StringIO()
    console = Console(file=buf, no_color=True, highlight=False, width=120)
    render_board_report(report, console, detail=True)
    output = buf.getvalue()

    # 1. Summary Header
    assert "게시판 브리핑 요약" in output
    assert "총 과목: 2개" in output
    assert "공지사항: 1개 (신규 1개)" in output
    assert "Q&A: 2개 (답변대기 1개, 내 질문 1개)" in output

    # 2. Inactive course compact 1-line muted text (D-15-02)
    assert "• 운영체제: 최근 공지 및 질문 없음" in output

    # 3. Active table and badges
    assert "알고리즘 (Algo)" in output
    assert "[NEW]" in output
    assert "시험 안내" in output
    assert "중간고사 시험 범위 안내입니다." in output
    assert "첨부 1개" in output
    assert "[내 질문]" in output
    assert "[답변완료]" in output
    assert "[답변대기]" in output

    # 4. Errors
    assert "수집 오류" in output
    assert "실패과목" in output
    assert "Connection Timeout" in output


def test_render_article_viewer():
    """Verify Rich console rendering for single article viewer."""
    import io
    from rich.console import Console
    from coursepilot.board.models import (
        BoardAttachmentItem,
        BoardPostItem,
        BoardReplyItem,
        BoardType,
    )
    from coursepilot.reporter import render_article_viewer

    post = BoardPostItem(
        post_id="5001",
        board_id="10",
        board_type=BoardType.NOTICE,
        title="2026학기 중간고사 안내",
        author="김교수",
        created_at="2026-09-25",
        hit_count=145,
        url="https://canvas.kau.ac.kr/mod/ubboard/article.php?id=10&bwid=5001",
        content="중간고사는 **10월 20일** 진행됩니다.",
        attachments=[
            BoardAttachmentItem(
                filename="exam_guide.pdf",
                download_url="https://example.com/guide.pdf",
                filesize=1024 * 500,
                saved_path="downloads/Algo/notices/exam_guide.pdf",
            )
        ],
        replies=[
            BoardReplyItem(
                author="조교",
                created_at="2026-09-25 15:00",
                content="강의실은 101호입니다.",
            )
        ],
    )

    buf = io.StringIO()
    console = Console(file=buf, no_color=True, highlight=False, width=120)
    render_article_viewer(post, console)
    output = buf.getvalue()

    assert "게시글 상세 (#5001)" in output
    assert "2026학기 중간고사 안내" in output
    assert "작성자: 김교수" in output
    assert "조회수: 145" in output
    assert "exam_guide.pdf" in output
    assert "500.0 KB" in output
    assert "exam_guide.pdf" in output
    assert "중간고사는" in output
    assert "10월 20일" in output
    assert "진행됩니다." in output
    assert "답변: 조교" in output
    assert "강의실은 101호입니다." in output

