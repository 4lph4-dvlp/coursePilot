"""Integration tests for concurrent watch downloading and attendance error isolation."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import httpx
import pytest

from coursepilot.config import Settings
from coursepilot.player.models import PlaybackProgress
from coursepilot.player.runner import watch_course_vods
from coursepilot.scraper.models import AttendanceStatus, CourseItem, LectureItem


@pytest.fixture
def mock_environment(tmp_path: Path):
    settings = Settings(
        lms_url="https://lxp.kau.ac.kr",
        download_dir=tmp_path / "downloads",
        session_cache_path=tmp_path / "session.json",
        course_mappings_path=tmp_path / "mappings.json",
    )
    courses = [
        CourseItem(
            course_id="1103",
            clean_name="기초전자실험",
            raw_name="기초전자실험(02분반)",
            url="https://lxp.kau.ac.kr/course/view.php?id=1103",
        )
    ]
    lectures = [
        LectureItem(
            course_id="1103",
            week_number=2,
            clip_number=1,
            title="2주차 오실로스코프 사용법",
            full_title="2주차 1차시 오실로스코프",
            link="https://lxp.kau.ac.kr/mod/vod/view.php?id=101",
            status=AttendanceStatus.INCOMPLETE,
        )
    ]
    return settings, courses, lectures


def test_watch_course_vods_triggers_concurrent_download(mock_environment, tmp_path: Path):
    settings, courses, lectures = mock_environment
    session_mgr = MagicMock()
    page = MagicMock()
    session_mgr.get_authenticated_page.return_value = page

    player = MagicMock()
    captured_callbacks = {}

    def mock_play_vod(page, vod_url, **kwargs):
        on_stream = kwargs.get("on_stream_detected")
        captured_callbacks["on_stream_detected"] = on_stream
        if on_stream:
            # Simulate stream sniffer firing mid-playback
            on_stream("https://cdn.kau.ac.kr/vod/master.m3u8")
        return PlaybackProgress(
            vod_url=vod_url,
            title="2주차 오실로스코프 사용법",
            duration=100.0,
            current_time=100.0,
            is_completed=True,
            progress_percent=100.0,
        )

    player.play_vod.side_effect = mock_play_vod

    with patch("coursepilot.player.runner.extract_courses", return_value=courses), \
         patch("coursepilot.player.runner.scrape_course", return_value=(lectures, [])), \
         patch("coursepilot.stream.downloader.SegmentDownloader") as mock_downloader_cls:

        mock_downloader = MagicMock()
        mock_downloader_cls.return_value = mock_downloader
        mock_downloader.client.get.return_value = MagicMock(
            status_code=200,
            text="#EXTM3U\n#EXTINF:10.0,\nseg1.ts\n#EXT-X-ENDLIST",
        )
        mock_downloader.download_stream.return_value = (tmp_path / "video.mp4", 1024, False)

        result = watch_course_vods(
            settings=settings,
            course_query="기초전자실험",
            week_query="2",
            download=True,
            player=player,
            session_manager=session_mgr,
        )

        assert result.completed_vods == 1
        assert result.playback_results[0].is_completed is True
        assert captured_callbacks.get("on_stream_detected") is not None
        # Verify download_stream was invoked in background thread
        assert mock_downloader.download_stream.called


def test_watch_download_failure_does_not_abort_attendance(mock_environment, tmp_path: Path):
    settings, courses, lectures = mock_environment
    session_mgr = MagicMock()
    player = MagicMock()

    def mock_play_vod(page, vod_url, **kwargs):
        on_stream = kwargs.get("on_stream_detected")
        if on_stream:
            on_stream("https://cdn.kau.ac.kr/vod/master.m3u8")
        return PlaybackProgress(
            vod_url=vod_url,
            title="2주차 오실로스코프 사용법",
            duration=100.0,
            current_time=100.0,
            is_completed=True,
            progress_percent=100.0,
        )

    player.play_vod.side_effect = mock_play_vod

    with patch("coursepilot.player.runner.extract_courses", return_value=courses), \
         patch("coursepilot.player.runner.scrape_course", return_value=(lectures, [])), \
         patch("coursepilot.stream.downloader.SegmentDownloader") as mock_downloader_cls:

        mock_downloader = MagicMock()
        mock_downloader_cls.return_value = mock_downloader
        # Simulate network drop during download
        mock_downloader.client.get.side_effect = httpx.ConnectError("Network dropped")

        result = watch_course_vods(
            settings=settings,
            course_query="기초전자실험",
            week_query="2",
            download=True,
            player=player,
            session_manager=session_mgr,
        )

        # Fault isolation guarantee: attendance completes 100% despite download failure (D-14-04)
        assert result.completed_vods == 1
        assert result.playback_results[0].is_completed is True
        assert result.error_message is None


def test_watch_without_download_flag_skips_downloader(mock_environment):
    settings, courses, lectures = mock_environment
    session_mgr = MagicMock()
    player = MagicMock()
    captured_callbacks = {}

    def mock_play_vod(page, vod_url, **kwargs):
        captured_callbacks["on_stream_detected"] = kwargs.get("on_stream_detected")
        return PlaybackProgress(
            vod_url=vod_url,
            title="2주차 오실로스코프 사용법",
            duration=50.0,
            current_time=50.0,
            is_completed=True,
        )

    player.play_vod.side_effect = mock_play_vod

    with patch("coursepilot.player.runner.extract_courses", return_value=courses), \
         patch("coursepilot.player.runner.scrape_course", return_value=(lectures, [])):

        result = watch_course_vods(
            settings=settings,
            course_query="기초전자실험",
            download=False,
            player=player,
            session_manager=session_mgr,
        )

        assert result.completed_vods == 1
        assert captured_callbacks["on_stream_detected"] is None
