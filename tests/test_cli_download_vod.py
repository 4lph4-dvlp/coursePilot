"""Unit tests for standalone download-vod CLI command and watch --download option plumbing."""

import json
from unittest.mock import MagicMock, patch
import pytest
from click.testing import CliRunner

from kau_assistant.cli import cli
from kau_assistant.stream.models import (
    CourseVodDownloadResult,
    VodDownloadItemResult,
    VodDownloadRunResult,
    VodDownloadStatus,
)


def test_cli_download_vod_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["download-vod", "--help"])
    assert result.exit_code == 0
    assert "--course" in result.output
    assert "--week" in result.output
    assert "--video-index" in result.output
    assert "--quality" in result.output
    assert "--output-dir" in result.output
    assert "--overwrite" in result.output
    assert "--dry-run" in result.output
    assert "--json" in result.output


def test_cli_download_vod_dry_run_json():
    mock_run_res = VodDownloadRunResult(
        total_courses=1,
        total_vods=2,
        downloaded_count=2,
        skipped_count=0,
        failed_count=0,
        dry_run=True,
        courses=[
            CourseVodDownloadResult(
                course_id="101",
                course_name="컴파일러",
                target_week="3주차",
                items=[
                    VodDownloadItemResult(
                        course_name="컴파일러",
                        week_number=3,
                        clip_number=1,
                        title="어휘분석기 구현",
                        status=VodDownloadStatus.DOWNLOADED,
                        saved_path="downloads/컴파일러/W03/W03-01_어휘분석기_구현.mp4",
                    ),
                    VodDownloadItemResult(
                        course_name="컴파일러",
                        week_number=3,
                        clip_number=2,
                        title="구문분석기 개요",
                        status=VodDownloadStatus.DOWNLOADED,
                        saved_path="downloads/컴파일러/W03/W03-02_구문분석기_개요.mp4",
                    ),
                ],
            )
        ],
    )

    runner = CliRunner()
    with patch("kau_assistant.stream.runner.run_vod_download_pipeline", return_value=mock_run_res):
        res = runner.invoke(cli, ["download-vod", "--course", "컴파일러", "--dry-run", "--json"])

        assert res.exit_code == 0
        parsed = json.loads(res.output)
        assert parsed["total_courses"] == 1
        assert parsed["total_vods"] == 2
        assert parsed["dry_run"] is True
        assert len(parsed["courses"][0]["items"]) == 2
        assert parsed["courses"][0]["items"][0]["title"] == "어휘분석기 구현"


def test_cli_watch_download_options_passed():
    runner = CliRunner()
    with patch("kau_assistant.player.runner.watch_course_vods") as mock_watch:
        mock_watch.return_value = MagicMock(
            error_message=None,
            total_vods=1,
            completed_vods=1,
            skipped_vods=0,
            course_name="컴파일러",
            course_id="101",
            target_week="3주차",
            notion_updated_count=0,
            model_dump_json=lambda indent=2: "{}",
        )

        res = runner.invoke(
            cli,
            [
                "watch",
                "--course",
                "컴파일러",
                "--download",
                "--quality",
                "720p",
                "--overwrite",
                "--dry-run",
            ],
        )

        assert res.exit_code == 0
        assert mock_watch.called
        kwargs = mock_watch.call_args[1]
        assert kwargs["download"] is True
        assert kwargs["preferred_quality"] == "720p"
        assert kwargs["overwrite"] is True
        assert kwargs["dry_run"] is True
