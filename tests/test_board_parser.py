"""Unit tests for Coursemos board domain models and HTML parser."""

from datetime import datetime
import pytest
from pydantic import ValidationError

from kau_assistant.board.models import (
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
