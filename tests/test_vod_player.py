"""Unit tests for VodPlayer and player models."""

from unittest.mock import MagicMock
import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from kau_assistant.player.models import PlaybackOptions, PlaybackProgress
from kau_assistant.player.vod_player import VodPlayer


def test_playback_models_defaults():
    opts = PlaybackOptions()
    assert opts.muted is True
    assert opts.poll_interval_seconds == 5.0
    assert opts.playback_rate == 1.0
    assert opts.max_wait_seconds is None

    prog = PlaybackProgress(vod_url="https://lxp.kau.ac.kr/mod/vod/view.php?id=123")
    assert prog.is_completed is False
    assert prog.progress_percent == 0.0
    assert prog.error_message is None


def test_vod_player_successful_play_to_completion():
    player = VodPlayer()
    mock_page = MagicMock()
    mock_page.title.return_value = "4주차 1차시 강의 | 한국항공대학교 LXP"

    eval_calls = []

    def mock_evaluate(script, *args):
        if "opts.muted" in script:
            # Init evaluation
            return {"ok": True, "duration": 60.0, "currentTime": 0.0, "paused": False, "ended": False}
        if "duration" in script:
            # Status polling
            eval_calls.append(1)
            if len(eval_calls) == 1:
                return {"duration": 60.0, "currentTime": 30.0, "paused": False, "ended": False}
            else:
                return {"duration": 60.0, "currentTime": 59.0, "paused": False, "ended": True}
        return None

    mock_page.evaluate.side_effect = mock_evaluate

    progress_reports = []

    def on_progress(p: PlaybackProgress):
        progress_reports.append(p.progress_percent)

    options = PlaybackOptions(poll_interval_seconds=0.01)
    result = player.play_vod(
        mock_page,
        "https://lxp.kau.ac.kr/mod/vod/view.php?id=8967",
        options=options,
        on_progress=on_progress,
    )

    assert result.is_completed is True
    assert result.progress_percent == 100.0
    assert result.title == "4주차 1차시 강의"
    assert result.error_message is None
    assert len(progress_reports) >= 2
    mock_page.goto.assert_called_once_with(
        "https://lxp.kau.ac.kr/mod/vod/view.php?id=8967", wait_until="domcontentloaded"
    )
    mock_page.wait_for_selector.assert_called_once_with("video", timeout=15000)


def test_vod_player_resumes_if_paused():
    player = VodPlayer()
    mock_page = MagicMock()
    mock_page.title.return_value = "Test Video"

    eval_history = []

    def mock_evaluate(script, *args):
        if "opts.muted" in script:
            return {"ok": True}
        if "duration" in script:
            eval_history.append("poll")
            if len(eval_history) == 1:
                # Video paused mid-play
                return {"duration": 60.0, "currentTime": 10.0, "paused": True, "ended": False}
            else:
                # Now ended
                return {"duration": 60.0, "currentTime": 60.0, "paused": False, "ended": True}
        if "v.play()" in script:
            eval_history.append("resume")
            return None
        return None

    mock_page.evaluate.side_effect = mock_evaluate

    options = PlaybackOptions(poll_interval_seconds=0.01)
    result = player.play_vod(
        mock_page,
        "https://lxp.kau.ac.kr/mod/vod/view.php?id=111",
        options=options,
    )

    assert result.is_completed is True
    assert "resume" in eval_history


def test_vod_player_handles_missing_video_tag():
    player = VodPlayer()
    mock_page = MagicMock()
    mock_page.wait_for_selector.side_effect = PlaywrightTimeoutError("Selector timeout")

    result = player.play_vod(
        mock_page,
        "https://lxp.kau.ac.kr/mod/vod/view.php?id=999",
    )

    assert result.is_completed is False
    assert "No <video> element found" in (result.error_message or "")
