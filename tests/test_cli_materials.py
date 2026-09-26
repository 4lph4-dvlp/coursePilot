"""CLI tests for materials and files commands."""

import json
from unittest.mock import MagicMock, patch
from click.testing import CliRunner

from coursepilot.cli import cli
from coursepilot.materials.models import (
    CourseMaterialsResult,
    MaterialDownloadResult,
    MaterialItem,
    MaterialsRunResult,
    MaterialStatus,
)


def test_materials_and_files_help():
    runner = CliRunner()
    res_materials = runner.invoke(cli, ["materials", "--help"])
    assert res_materials.exit_code == 0
    assert "--course" in res_materials.output
    assert "--week" in res_materials.output
    assert "--output-dir" in res_materials.output
    assert "--no-download" in res_materials.output
    assert "--dry-run" in res_materials.output
    assert "--json" in res_materials.output

    res_files = runner.invoke(cli, ["files", "--help"])
    assert res_files.exit_code == 0
    assert "--course" in res_files.output
    assert "--no-download" in res_files.output


@patch("coursepilot.materials.runner.run_materials_pipeline")
def test_materials_dry_run_json(mock_run_pipeline):
    item = MaterialItem(
        course_id="101",
        course_name="자료구조",
        week_number=1,
        module_id="8001",
        title="1주차_강의자료.pdf",
        url="https://lxp.kau.ac.kr/mod/ubfile/view.php?id=8001",
        is_completed=True,
    )
    mock_run_pipeline.return_value = MaterialsRunResult(
        total_courses=1,
        total_materials=1,
        downloaded_count=1,
        dry_run=True,
        courses=[
            CourseMaterialsResult(
                course_id="101",
                course_name="자료구조",
                target_week="1주차",
                items=[
                    MaterialDownloadResult(
                        item=item,
                        status=MaterialStatus.DOWNLOADED,
                        filename="1주차_강의자료.pdf",
                        saved_path="downloads/자료구조/W1/1주차_강의자료.pdf",
                    )
                ],
            )
        ],
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["materials", "--dry-run", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["dry_run"] is True
    assert data["total_courses"] == 1
    assert data["courses"][0]["course_name"] == "자료구조"


@patch("coursepilot.materials.runner.run_materials_pipeline")
def test_materials_flags_passed(mock_run_pipeline):
    mock_run_pipeline.return_value = MaterialsRunResult()

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "materials",
            "--course",
            "자료구조",
            "--week",
            "2",
            "--output-dir",
            "custom_downloads",
            "--no-download",
            "--dry-run",
        ],
    )
    assert result.exit_code == 0
    mock_run_pipeline.assert_called_once()
    kwargs = mock_run_pipeline.call_args.kwargs
    assert kwargs["course_query"] == "자료구조"
    assert kwargs["week_query"] == "2"
    assert kwargs["output_dir"] == "custom_downloads"
    assert kwargs["no_download"] is True
    assert kwargs["dry_run"] is True


@patch("coursepilot.materials.runner.run_materials_pipeline")
def test_materials_failure_exit_code_1(mock_run_pipeline):
    mock_run_pipeline.return_value = MaterialsRunResult(
        total_materials=1,
        failed_count=1,
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["materials"])
    assert result.exit_code == 1


@patch("coursepilot.materials.runner.run_materials_pipeline")
def test_materials_exception_exit_code_2(mock_run_pipeline):
    mock_run_pipeline.side_effect = RuntimeError("Fatal connection error")
    runner = CliRunner()
    result = runner.invoke(cli, ["materials"])
    assert result.exit_code == 2
