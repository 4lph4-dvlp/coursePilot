"""Integration tests for Click CLI commands (board, notices, qna) and JSON contract."""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch
from click.testing import CliRunner

from coursepilot.board.models import (
    BoardAttachmentItem,
    BoardPostItem,
    BoardReplyItem,
    BoardReport,
    BoardSummary,
    BoardType,
    CourseBoardGroup,
)
from coursepilot.cli import cli


def test_cli_board_help():
    """Verify that board, notices, and qna commands display help with options."""
    runner = CliRunner()

    for cmd in ["board", "notices", "qna"]:
        result = runner.invoke(cli, [cmd, "--help"])
        assert result.exit_code == 0
        assert "--course" in result.output
        assert "--limit" in result.output
        assert "--all" in result.output
        assert "--view" in result.output
        assert "--unread-only" in result.output
        assert "--unanswered" in result.output
        assert "--my" in result.output
        assert "--board-name" in result.output
        assert "--mark-read" in result.output
        assert "--download-attachments" in result.output
        assert "--json" in result.output


def test_cli_board_json_contract():
    """Verify board --json adheres strictly to schema_version: 1 JSON contract (D-15-04)."""
    runner = CliRunner()

    mock_report = BoardReport(
        schema_version=1,
        command="board",
        generated_at=datetime(2026, 9, 26, 12, 0, 0),
        summary=BoardSummary(
            total_courses=1,
            total_notices=1,
            unread_notices=1,
            total_questions=1,
            unanswered_questions=0,
            my_questions=1,
        ),
        courses=[
            CourseBoardGroup(
                course_id="101",
                course_name="알고리즘",
                course_abbr="Algo",
                notices=[
                    BoardPostItem(
                        post_id="1001",
                        board_id="501",
                        board_type=BoardType.NOTICE,
                        title="중간고사 공지",
                        author="김교수",
                        created_at="2026-09-20",
                        url="https://canvas.kau.ac.kr/mod/ubboard/article.php?id=501&bwid=1001",
                    )
                ],
                qna=[],
            )
        ],
        errors=[],
    )

    with patch("coursepilot.board.runner.run_board_pipeline", return_value=mock_report):
        result = runner.invoke(cli, ["board", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["schema_version"] == 1
        assert data["command"] == "board"
        assert data["summary"]["total_courses"] == 1
        assert data["courses"][0]["course_name"] == "알고리즘"
        assert data["courses"][0]["notices"][0]["title"] == "중간고사 공지"


def test_cli_notices_and_qna_invocations():
    """Verify notices and qna commands pass correct command_scope to runner."""
    runner = CliRunner()
    mock_report = BoardReport(
        schema_version=1,
        command="notices",
        generated_at=datetime(2026, 9, 26, 12, 0, 0),
        summary=BoardSummary(
            total_courses=1,
            total_notices=0,
            unread_notices=0,
            total_questions=0,
            unanswered_questions=0,
            my_questions=0,
        ),
        courses=[],
        errors=[],
    )

    with patch("coursepilot.board.runner.run_board_pipeline", return_value=mock_report) as mock_run:
        # 1. notices command
        res1 = runner.invoke(cli, ["notices", "--limit", "5", "--unread-only"])
        assert res1.exit_code == 0
        mock_run.assert_called_with(
            course_query=None,
            command_scope="notices",
            limit=5,
            fetch_all=False,
            detail=False,
            unread_only=True,
            unanswered=False,
            my_only=False,
            board_name=None,
            mark_read=False,
            relogin=False,
            headful=False,
            progress_callback=mock_run.call_args.kwargs["progress_callback"],
        )

        # 2. qna command
        mock_report.command = "qna"
        res2 = runner.invoke(cli, ["qna", "--my", "--unanswered"])
        assert res2.exit_code == 0
        mock_run.assert_called_with(
            course_query=None,
            command_scope="qna",
            limit=3,
            fetch_all=False,
            detail=False,
            unread_only=False,
            unanswered=True,
            my_only=True,
            board_name=None,
            mark_read=False,
            relogin=False,
            headful=False,
            progress_callback=mock_run.call_args.kwargs["progress_callback"],
        )


def test_cli_board_view_command():
    """Verify board --view <id> invokes view_board_article and renders article detail."""
    runner = CliRunner()

    mock_post = BoardPostItem(
        post_id="1001",
        board_id="501",
        board_type=BoardType.NOTICE,
        title="단독 공지 확인",
        author="이교수",
        created_at="2026-09-25",
        url="https://canvas.kau.ac.kr/mod/ubboard/article.php?id=501&bwid=1001",
        content="전문 본문 내용입니다.",
        attachments=[
            BoardAttachmentItem(
                filename="attached.pdf",
                download_url="https://example.com/attached.pdf",
            )
        ],
        replies=[
            BoardReplyItem(
                author="조교",
                created_at="2026-09-25 12:00",
                content="확인했습니다.",
            )
        ],
    )

    with patch("coursepilot.board.runner.view_board_article", return_value=mock_post) as mock_view:
        # Text view
        res = runner.invoke(cli, ["board", "--view", "1001", "--course", "알고리즘"])
        assert res.exit_code == 0
        assert "단독 공지 확인" in res.output
        mock_view.assert_called_with(
            post_id_or_bwid="1001",
            course_query="알고리즘",
            download_attachments=False,
            relogin=False,
            headful=False,
            progress_callback=mock_view.call_args.kwargs["progress_callback"],
        )

        # JSON view
        res_json = runner.invoke(cli, ["board", "--view", "1001", "--json"])
        assert res_json.exit_code == 0
        data = json.loads(res_json.output)
        assert data["post_id"] == "1001"
        assert data["title"] == "단독 공지 확인"
        assert data["attachments"][0]["filename"] == "attached.pdf"


def test_cli_board_exit_codes():
    """Verify CLI exit codes: 0 (success), 1 (partial errors), 2 (fatal error)."""
    runner = CliRunner()

    # 1. Success -> 0
    report_ok = BoardReport(
        schema_version=1,
        command="board",
        generated_at=datetime(2026, 9, 26, 12, 0, 0),
        summary=BoardSummary(
            total_courses=1,
            total_notices=0,
            unread_notices=0,
            total_questions=0,
            unanswered_questions=0,
            my_questions=0,
        ),
        courses=[],
        errors=[],
    )
    with patch("coursepilot.board.runner.run_board_pipeline", return_value=report_ok):
        res = runner.invoke(cli, ["board"])
        assert res.exit_code == 0

    # 2. Report with errors -> 1
    report_err = BoardReport(
        schema_version=1,
        command="board",
        generated_at=datetime(2026, 9, 26, 12, 0, 0),
        summary=BoardSummary(
            total_courses=1,
            total_notices=0,
            unread_notices=0,
            total_questions=0,
            unanswered_questions=0,
            my_questions=0,
        ),
        courses=[],
        errors=[{"course_name": "CourseA", "error": "timeout"}],
    )
    with patch("coursepilot.board.runner.run_board_pipeline", return_value=report_err):
        res = runner.invoke(cli, ["board"])
        assert res.exit_code == 1

    # 3. Fatal exception -> 2
    with patch("coursepilot.board.runner.run_board_pipeline", side_effect=RuntimeError("Login failed")):
        res = runner.invoke(cli, ["board"])
        assert res.exit_code == 2
        assert "게시판 조회 실패" in res.output or "게시판 조회 실패" in res.stderr
