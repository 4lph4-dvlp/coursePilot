"""Unit tests for Coursemos board domain models and HTML parser."""

from datetime import datetime
import pytest
from pydantic import ValidationError

from coursepilot.board.models import (
    SCHEMA_VERSION,
    BoardArticleDetail,
    BoardAttachmentItem,
    BoardModuleInfo,
    BoardPostItem,
    BoardReplyItem,
    BoardReport,
    BoardSummary,
    BoardType,
    CourseBoardGroup,
)
from coursepilot.scraper.board_parser import (
    classify_board_type,
    extract_board_modules,
    parse_board_article_page,
    parse_board_list_page,
)


def test_board_models_default_values():
    """Verify default factories for attachments, replies, notices, qna, and errors."""
    post = BoardPostItem(
        post_id="101",
        board_id="5001",
        board_type=BoardType.NOTICE,
        title="Test Notice",
        author="Prof. Kim",
        created_at="2026-09-26",
        url="https://canvas.kau.ac.kr/mod/ubboard/article.php?id=5001&bwid=101",
    )
    assert post.attachments == []
    assert post.replies == []
    assert post.is_read is False
    assert post.is_my_question is False
    assert post.is_answered is None
    assert post.is_secret is False
    assert post.hit_count == 0

    group = CourseBoardGroup(
        course_id="20261_1234",
        course_name="Software Engineering",
        course_abbr="SE",
    )
    assert group.notices == []
    assert group.qna == []

    summary = BoardSummary(
        total_courses=1,
        total_notices=0,
        unread_notices=0,
        total_questions=0,
        unanswered_questions=0,
        my_questions=0,
    )
    report = BoardReport(
        generated_at=datetime(2026, 9, 26, 12, 0, 0),
        summary=summary,
    )
    assert report.schema_version == 1
    assert report.command == "board"
    assert report.courses == []
    assert report.errors == []


def test_board_report_schema_version_validation():
    """Verify schema_version must be 1."""
    summary = BoardSummary(
        total_courses=1,
        total_notices=0,
        unread_notices=0,
        total_questions=0,
        unanswered_questions=0,
        my_questions=0,
    )
    # Valid schema_version
    report = BoardReport(
        schema_version=1,
        generated_at=datetime(2026, 9, 26, 12, 0, 0),
        summary=summary,
    )
    assert report.schema_version == SCHEMA_VERSION

    # Invalid schema_version
    with pytest.raises(ValidationError):
        BoardReport(
            schema_version=2,  # type: ignore[arg-type]
            generated_at=datetime(2026, 9, 26, 12, 0, 0),
            summary=summary,
        )


def test_board_models_extra_fields_forbidden():
    """Verify ValidationError is raised when passing undeclared extra fields (extra='forbid')."""
    with pytest.raises(ValidationError):
        BoardModuleInfo(
            module_id="1",
            title="Notice",
            url="https://example.com",
            board_type=BoardType.NOTICE,
            extra_field="disallowed",  # type: ignore[call-arg]
        )

    with pytest.raises(ValidationError):
        BoardAttachmentItem(
            filename="doc.pdf",
            download_url="https://example.com/doc.pdf",
            unexpected="fail",  # type: ignore[call-arg]
        )

    with pytest.raises(ValidationError):
        BoardReplyItem(
            author="Assistant",
            created_at="2026-09-26",
            content="Answer",
            invalid_tag="fail",  # type: ignore[call-arg]
        )


def test_board_report_json_roundtrip():
    """Verify serialization with model_dump_json() and deserialization with model_validate_json()."""
    summary = BoardSummary(
        total_courses=1,
        total_notices=1,
        unread_notices=1,
        total_questions=1,
        unanswered_questions=0,
        my_questions=1,
    )
    notice = BoardPostItem(
        post_id="1",
        board_id="5001",
        board_type=BoardType.NOTICE,
        title="Welcome Notice",
        author="Professor",
        created_at="2026-09-20",
        hit_count=42,
        url="https://canvas.kau.ac.kr/mod/ubboard/article.php?id=5001&bwid=1",
        is_read=False,
    )
    qna = BoardPostItem(
        post_id="2",
        board_id="5002",
        board_type=BoardType.QNA,
        title="HW Question",
        author="Me",
        created_at="2026-09-21",
        hit_count=10,
        url="https://canvas.kau.ac.kr/mod/ubboard/article.php?id=5002&bwid=2",
        is_read=True,
        is_my_question=True,
        is_answered=True,
        replies=[
            BoardReplyItem(
                author="TA",
                created_at="2026-09-22",
                content="Please refer to slide 5.",
            )
        ],
    )
    course_group = CourseBoardGroup(
        course_id="101",
        course_name="Introduction to Programming",
        course_abbr="IP",
        notices=[notice],
        qna=[qna],
    )
    report = BoardReport(
        generated_at=datetime(2026, 9, 26, 12, 0, 0),
        summary=summary,
        courses=[course_group],
    )

    json_str = report.model_dump_json(indent=2)
    reloaded = BoardReport.model_validate_json(json_str)
    assert reloaded == report
    assert reloaded.schema_version == 1
    assert reloaded.courses[0].notices[0].title == "Welcome Notice"
    assert reloaded.courses[0].qna[0].replies[0].author == "TA"


def test_classify_board_type():
    """Verify board title classification."""
    assert classify_board_type("공지사항") == BoardType.NOTICE
    assert classify_board_type("Course Notice (안내)") == BoardType.NOTICE
    assert classify_board_type("질문 및 답변 (Q&A)") == BoardType.QNA
    assert classify_board_type("과제 문의 게시판") == BoardType.QNA
    assert classify_board_type("자유게시판") == BoardType.OTHER
    assert classify_board_type("중간고사 프로젝트 게시판", custom_name="프로젝트") == BoardType.CUSTOM


def test_extract_board_modules():
    """Verify extracting board modules from course home HTML and stripping .accesshide."""
    html = """
    <html>
      <body>
        <ul class="topics">
          <li class="activity ubboard modtype_ubboard" id="module-6001">
            <a href="/mod/ubboard/view.php?id=6001">
              <span class="instancename">
                과목 공지사항 <span class="accesshide">게시판</span>
              </span>
            </a>
          </li>
          <li class="activity ubboard modtype_ubboard" id="module-6002">
            <a href="/mod/ubboard/view.php?id=6002">
              <span class="instancename">
                질의응답 (Q&amp;A) <span class="accesshide">게시판</span>
              </span>
            </a>
          </li>
          <li class="activity forum modtype_forum" id="module-6003">
            <a href="/mod/forum/view.php?id=6003">
              <span class="instancename">
                자유 토론방 <span class="accesshide">포럼</span>
              </span>
            </a>
          </li>
        </ul>
      </body>
    </html>
    """
    base_url = "https://canvas.kau.ac.kr/course/view.php?id=123"
    modules = extract_board_modules(html, base_url)
    assert len(modules) == 3
    assert modules[0].module_id == "6001"
    assert modules[0].title == "과목 공지사항"
    assert modules[0].board_type == BoardType.NOTICE
    assert modules[0].url == "https://canvas.kau.ac.kr/mod/ubboard/view.php?id=6001"

    assert modules[1].module_id == "6002"
    assert modules[1].title == "질의응답 (Q&A)"
    assert modules[1].board_type == BoardType.QNA

    assert modules[2].module_id == "6003"
    assert modules[2].title == "자유 토론방"
    assert modules[2].board_type == BoardType.OTHER


def test_parse_notice_table_5_columns():
    """Verify parsing standard 5-column notice table."""
    html = """
    <table class="ubboard_table table table-hover">
      <thead>
        <tr>
          <th>번호</th>
          <th>제목</th>
          <th>작성자</th>
          <th>작성일</th>
          <th>조회수</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>공지</td>
          <td>
            <a href="/mod/ubboard/article.php?id=6001&bwid=1001">
              중간고사 일정 및 시험 범위 안내
              <span class="newicon">NEW</span>
            </a>
          </td>
          <td>김교수</td>
          <td><span title="2026-09-25 14:30:00">2026-09-25</span></td>
          <td>150</td>
        </tr>
        <tr>
          <td>1</td>
          <td>
            <a href="/mod/ubboard/article.php?id=6001&bwid=1000">
              수업 오리엔테이션 자료
              <span class="comment">[2]</span>
            </a>
          </td>
          <td>조교</td>
          <td>2026-09-01</td>
          <td>88</td>
        </tr>
      </tbody>
    </table>
    """
    base_url = "https://canvas.kau.ac.kr/mod/ubboard/view.php?id=6001"
    posts = parse_board_list_page(html, base_url, board_id="6001", board_type=BoardType.NOTICE)
    assert len(posts) == 2

    p1 = posts[0]
    assert p1.post_id == "1001"
    assert p1.bwid == "1001"
    assert p1.title == "중간고사 일정 및 시험 범위 안내"
    assert p1.author == "김교수"
    assert p1.created_at == "2026-09-25 14:30:00"
    assert p1.hit_count == 150
    assert p1.url == "https://canvas.kau.ac.kr/mod/ubboard/article.php?id=6001&bwid=1001"
    assert p1.is_read is False

    p2 = posts[1]
    assert p2.post_id == "1000"
    assert p2.bwid == "1000"
    assert p2.title == "수업 오리엔테이션 자료"
    assert p2.author == "조교"
    assert p2.created_at == "2026-09-01"
    assert p2.hit_count == 88


def test_parse_qna_table_6_columns():
    """Verify parsing 6-column Q&A table with status badges and my question identification."""
    html = """
    <table class="ubboard_table table">
      <thead>
        <tr>
          <th>번호</th>
          <th>상태</th>
          <th>제목</th>
          <th>작성자</th>
          <th>등록일</th>
          <th>조회</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>2</td>
          <td><span class="badge badge-success">답변완료</span></td>
          <td>
            <a href="/mod/ubboard/article.php?id=6002&bwid=2002">과제 1번 질문입니다.</a>
          </td>
          <td>홍길동</td>
          <td>2026-09-24</td>
          <td>15</td>
        </tr>
        <tr>
          <td>1</td>
          <td><span class="badge badge-warning">답변대기</span></td>
          <td>
            <a href="/mod/ubboard/article.php?id=6002&bwid=2001">강의 슬라이드 오타 문의</a>
          </td>
          <td>이몽룡</td>
          <td>2026-09-25</td>
          <td>5</td>
        </tr>
      </tbody>
    </table>
    """
    base_url = "https://canvas.kau.ac.kr/mod/ubboard/view.php?id=6002"
    posts = parse_board_list_page(
        html,
        base_url,
        board_id="6002",
        board_type=BoardType.QNA,
        current_user_name="홍길동",
    )
    assert len(posts) == 2

    q1 = posts[0]
    assert q1.bwid == "2002"
    assert q1.title == "과제 1번 질문입니다."
    assert q1.author == "홍길동"
    assert q1.is_answered is True
    assert q1.is_my_question is True

    q2 = posts[1]
    assert q2.bwid == "2001"
    assert q2.title == "강의 슬라이드 오타 문의"
    assert q2.author == "이몽룡"
    assert q2.is_answered is False
    assert q2.is_my_question is False


def test_parse_secret_post_without_link():
    """Verify parsing confidential/secret posts lacking <a> anchor tags."""
    html = """
    <table class="ubboard_table">
      <tbody>
        <tr>
          <td>3</td>
          <td>비공개 상담 요청입니다.</td>
          <td>김학생</td>
          <td>2026-09-26</td>
          <td>1</td>
        </tr>
      </tbody>
    </table>
    """
    base_url = "https://canvas.kau.ac.kr/mod/ubboard/view.php?id=6002"
    posts = parse_board_list_page(html, base_url, board_id="6002", board_type=BoardType.QNA)
    assert len(posts) == 1
    post = posts[0]
    assert post.is_secret is True
    assert post.url == ""
    assert post.title == "비공개 상담 요청입니다."
    assert post.author == "김학생"


def test_parse_board_article_page():
    """Verify parsing article detail page with subject, author, attachments, markdown body, and replies."""
    html = """
    <div class="ubboard_view">
      <div class="well">
        <div class="subject">2026년도 1학기 중간고사 상세 안내</div>
        <div class="info">
          <div class="writer">김교수</div>
          <div class="date">2026-09-25 10:00:00</div>
          <div class="hit">조회 230</div>
          <div class="files">
            <ul class="files">
              <li>
                <a href="/pluginfile.php/12345/mod_ubboard/attachment/1/midterm_guide.pdf">
                  midterm_guide.pdf
                </a>
              </li>
            </ul>
          </div>
        </div>
        <div class="content">
          <p>중간고사는 <strong>10월 20일</strong> 강의실에서 대면으로 진행됩니다.</p>
          <p>준비물: 신분증, 필기도구.<br>자세한 내용은 첨부파일을 확인하세요.</p>
        </div>
        <div class="comment_list">
          <div class="comment_item">
            <div class="writer">학생A</div>
            <div class="date">2026-09-25 11:00:00</div>
            <div class="content">계산기 사용 가능한가요?</div>
          </div>
          <div class="comment_item">
            <div class="writer">김교수</div>
            <div class="date">2026-09-25 11:30:00</div>
            <div class="content">계산기는 지참 불가능합니다.</div>
          </div>
        </div>
      </div>
    </div>
    """
    base_url = "https://canvas.kau.ac.kr/mod/ubboard/article.php?id=6001&bwid=1001"
    detail = parse_board_article_page(html, base_url)
    assert detail.subject == "2026년도 1학기 중간고사 상세 안내"
    assert detail.author == "김교수"
    assert detail.created_at == "2026-09-25 10:00:00"
    assert detail.hit_count == 230
    assert len(detail.attachments) == 1
    assert detail.attachments[0].filename == "midterm_guide.pdf"
    assert "midterm_guide.pdf" in detail.attachments[0].download_url
    assert "**10월 20일**" in detail.content
    assert "준비물: 신분증, 필기도구." in detail.content

    assert len(detail.replies) == 2
    assert detail.replies[0].author == "학생A"
    assert detail.replies[0].content == "계산기 사용 가능한가요?"
    assert detail.replies[1].author == "김교수"
    assert detail.replies[1].content == "계산기는 지참 불가능합니다."
