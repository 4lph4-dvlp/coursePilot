"""Tests for Click CLI `progress` command, options, stream separation, JSON contract, and exit codes."""

from datetime import datetime
import json
from unittest.mock import MagicMock, patch
from click.testing import CliRunner
import pytest

from kau_assistant.cli import cli
from kau_assistant.progress.models import (
    SCHEMA_VERSION,
    ActivityBreakdown,
    CourseProgress,
    DashboardSummary,
    ProgressReport,
)
from kau_assistant.report_models import ErrorItem
from kau_assistant.scraper.date_parser import KST


def _sample_report(missed_past: int = 0, errors: list[ErrorItem] | None = None) -> ProgressReport:
    now = datetime(2026, 9, 26, 12, 0, tzinfo=KST)
    course = CourseProgress(
        course_id="101",
        course_name="자료구조(01분반)",
        course_abbr="자구",
        current_week=3,
        current_open_rate=100.0 if missed_past == 0 else 80.0,
        current_open_completed=5,
        current_open_total=5,
        past_weeks_rate=100.0 if missed_past == 0 else 75.0,
        past_weeks_completed=4,
        past_weeks_total=4,
        semester_overall_rate=50.0,
        semester_completed=5,
        semester_total=10,
        activity_breakdown=ActivityBreakdown(),
        status="ok" if not errors else "error",
    )
    summary = DashboardSummary(
        total_courses=1,
        current_open_rate=course.current_open_rate,
        current_open_completed=5,
        current_open_total=5,
        past_weeks_rate=course.past_weeks_rate,
        past_weeks_completed=4,
        past_weeks_total=4,
        semester_overall_rate=50.0,
        semester_completed=5,
        semester_total=10,
        missed_past_count=missed_past,
        current_week_todo_count=0,
        activity_totals=ActivityBreakdown(),
    )
    return ProgressReport(
        schema_version=SCHEMA_VERSION,
        command="progress",
        status="success" if not errors else "error",
        generated_at=now,
        is_cached=False,
        summary=summary,
        courses=[course],
        errors=errors or [],
    )


def test_cli_progress_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["progress", "--help"])
    assert result.exit_code == 0
    assert "--course" in result.output
    assert "--week" in result.output
    assert "--detail" in result.output
    assert "--cached" in result.output
    assert "--refresh" in result.output
    assert "--json" in result.output


@patch("kau_assistant.cli.run_progress_pipeline")
def test_cli_progress_json_contract(mock_pipeline):
    mock_pipeline.return_value = _sample_report(missed_past=0)

    runner = CliRunner()
    result = runner.invoke(cli, ["progress", "--json"])
    assert result.exit_code == 0

    data = json.loads(result.output)
    assert data["schema_version"] == 1
    assert data["command"] == "progress"
    assert data["status"] == "success"
    assert "summary" in data
    assert "courses" in data
    assert data["courses"][0]["course_name"] == "자료구조(01분반)"


@patch("kau_assistant.cli.run_progress_pipeline")
def test_cli_progress_stream_separation(mock_pipeline):
    def fake_pipeline(**kwargs):
        cb = kwargs.get("progress_callback")
        if cb:
            cb("[1/1] [자료구조] 활동 내역 수집 중...")
        return _sample_report(missed_past=0)

    mock_pipeline.side_effect = fake_pipeline

    runner = CliRunner()
    result = runner.invoke(cli, ["progress", "--json"])

    assert result.exit_code == 0
    # Stderr must contain progress callback text
    assert "활동 내역 수집 중" in result.stderr
    # Stdout must contain clean json and zero progress callback text
    assert "활동 내역 수집 중" not in result.stdout
    data = json.loads(result.stdout)
    assert data["schema_version"] == 1


@patch("kau_assistant.cli.render_course_matrix")
@patch("kau_assistant.cli.run_progress_pipeline")
def test_cli_progress_course_matrix_dispatch(mock_pipeline, mock_matrix):
    mock_pipeline.return_value = _sample_report(missed_past=0)

    runner = CliRunner()
    result = runner.invoke(cli, ["progress", "--course", "자구"])
    assert result.exit_code == 0
    assert mock_matrix.called


@patch("kau_assistant.cli.render_detailed_activities")
@patch("kau_assistant.cli.run_progress_pipeline")
def test_cli_progress_detail_dispatch(mock_pipeline, mock_detail):
    mock_pipeline.return_value = _sample_report(missed_past=0)

    runner = CliRunner()
    result = runner.invoke(cli, ["progress", "--detail"])
    assert result.exit_code == 0
    assert mock_detail.called


@patch("kau_assistant.cli.run_progress_pipeline")
def test_cli_progress_exit_codes(mock_pipeline):
    runner = CliRunner()

    # Case 1: All clear -> exit 0
    mock_pipeline.return_value = _sample_report(missed_past=0)
    res_ok = runner.invoke(cli, ["progress", "--json"])
    assert res_ok.exit_code == 0

    # Case 2: Past missed items exist -> exit 1
    mock_pipeline.return_value = _sample_report(missed_past=2)
    res_missed = runner.invoke(cli, ["progress", "--json"])
    assert res_missed.exit_code == 1

    # Case 3: Course scraping error -> exit 1
    mock_pipeline.return_value = _sample_report(
        missed_past=0,
        errors=[ErrorItem(scope="course", code="COLLECTION_FAILED", message="HTTP 500")],
    )
    res_err = runner.invoke(cli, ["progress", "--json"])
    assert res_err.exit_code == 1

    # Case 4: Fatal crash in pipeline -> exit 2
    mock_pipeline.side_effect = RuntimeError("Fatal DB or network crash")
    res_fatal = runner.invoke(cli, ["progress", "--json"])
    assert res_fatal.exit_code == 2
