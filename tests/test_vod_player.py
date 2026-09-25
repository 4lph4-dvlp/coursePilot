"""Unit tests for VodPlayer, playback resilience, and player models."""

import time
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
    mock_page.url = "https://lxp.kau.ac.kr/mod/vod/view.php?id=8967"

    eval_calls = []

    def mock_evaluate(script, *args):
        if "opts.muted" in script:
            return {"ok": True, "duration": 60.0, "currentTime": 0.0, "paused": False, "ended": False}
        if "duration" in script:
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
    mock_page.url = "https://lxp.kau.ac.kr/mod/vod/view.php?id=111"

    eval_history = []

    def mock_evaluate(script, *args):
        if "opts.muted" in script:
            return {"ok": True}
        if "duration" in script:
            eval_history.append("poll")
            if len(eval_history) == 1:
                return {"duration": 60.0, "currentTime": 10.0, "paused": True, "ended": False}
            else:
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


def test_vod_player_enforces_1_0x_playback_rate(monkeypatch):
    player = VodPlayer()
    mock_page = MagicMock()
    mock_page.title.return_value = "Test Rate Video"
    mock_page.url = "https://lxp.kau.ac.kr/mod/vod/view.php?id=222"

    eval_scripts = []

    def mock_evaluate(script, *args):
        eval_scripts.append(script)
        if "opts.muted" in script:
            return {"ok": True, "duration": 10.0, "currentTime": 10.0, "paused": False, "ended": True}
        return {"duration": 10.0, "currentTime": 10.0, "paused": False, "ended": True}

    mock_page.evaluate.side_effect = mock_evaluate

    options = PlaybackOptions(playback_rate=2.0, poll_interval_seconds=0.01)
    result = player.play_vod(
        mock_page,
        "https://lxp.kau.ac.kr/mod/vod/view.php?id=222",
        options=options,
    )

    assert result.is_completed is True


def test_vod_player_stall_detection_and_retry(monkeypatch):
    player = VodPlayer()
    mock_page = MagicMock()
    mock_page.title.return_value = "Stall Test Video"
    mock_page.url = "https://lxp.kau.ac.kr/mod/vod/view.php?id=333"

    eval_actions = []
    fake_time = 0.0

    def fake_monotonic():
        return fake_time

    monkeypatch.setattr(time, "monotonic", fake_monotonic)

    poll_count = 0

    def mock_evaluate(script, *args):
        nonlocal poll_count, fake_time
        if "opts.muted" in script:
            return {"ok": True}
        if "v.play()" in script:
            eval_actions.append("play_retry")
            return None
        if "duration" in script:
            poll_count += 1
            if poll_count == 1:
                return {"duration": 100.0, "currentTime": 10.0, "paused": False, "ended": False}
            elif poll_count == 2:
                # Advance time by 16s while currentTime remains 10.0s -> triggers stall retry
                fake_time += 16.0
                return {"duration": 100.0, "currentTime": 10.0, "paused": False, "ended": False}
            else:
                # Video recovered and ended
                return {"duration": 100.0, "currentTime": 100.0, "paused": False, "ended": True}
        return None

    mock_page.evaluate.side_effect = mock_evaluate

    options = PlaybackOptions(poll_interval_seconds=0.01)
    result = player.play_vod(
        mock_page,
        "https://lxp.kau.ac.kr/mod/vod/view.php?id=333",
        options=options,
    )

    assert result.is_completed is True
    assert "play_retry" in eval_actions


def test_vod_player_stall_reload_fallback(monkeypatch):
    player = VodPlayer()
    mock_page = MagicMock()
    mock_page.title.return_value = "Reload Test Video"
    mock_page.url = "https://lxp.kau.ac.kr/mod/vod/view.php?id=444"

    fake_time = 0.0

    def fake_monotonic():
        return fake_time

    monkeypatch.setattr(time, "monotonic", fake_monotonic)

    poll_count = 0

    def mock_evaluate(script, *args):
        nonlocal poll_count, fake_time
        if "opts.muted" in script:
            return {"ok": True}
        if "v.play()" in script:
            return None
        if "duration" in script:
            poll_count += 1
            if poll_count == 1:
                return {"duration": 100.0, "currentTime": 5.0, "paused": False, "ended": False}
            elif poll_count in (2, 3, 4, 5):
                fake_time += 16.0
                return {"duration": 100.0, "currentTime": 5.0, "paused": False, "ended": False}
            else:
                return {"duration": 100.0, "currentTime": 100.0, "paused": False, "ended": True}
        return None

    mock_page.evaluate.side_effect = mock_evaluate

    options = PlaybackOptions(poll_interval_seconds=0.01)
    result = player.play_vod(
        mock_page,
        "https://lxp.kau.ac.kr/mod/vod/view.php?id=444",
        options=options,
    )

    assert result.is_completed is True
    mock_page.reload.assert_called_once_with(wait_until="domcontentloaded")


def test_vod_player_moodle_session_expiry_recovery():
    player = VodPlayer()
    mock_page = MagicMock()
    mock_session_mgr = MagicMock()

    urls = [
        "https://lxp.kau.ac.kr/mod/vod/view.php?id=555",
        "https://lxp.kau.ac.kr/login/index.php",  # Expired redirect!
        "https://lxp.kau.ac.kr/mod/vod/view.php?id=555",
    ]

    def get_url():
        return urls.pop(0) if urls else "https://lxp.kau.ac.kr/mod/vod/view.php?id=555"

    type(mock_page).url = property(lambda self: get_url())

    eval_calls = 0

    def mock_evaluate(script, *args):
        nonlocal eval_calls
        if "opts.muted" in script:
            return {"ok": True}
        if "duration" in script:
            eval_calls += 1
            if eval_calls == 1:
                return {"duration": 60.0, "currentTime": 20.0, "paused": False, "ended": False}
            else:
                return {"duration": 60.0, "currentTime": 60.0, "paused": False, "ended": True}
        return None

    mock_page.evaluate.side_effect = mock_evaluate

    options = PlaybackOptions(poll_interval_seconds=0.01)
    result = player.play_vod(
        mock_page,
        "https://lxp.kau.ac.kr/mod/vod/view.php?id=555",
        options=options,
        session_manager=mock_session_mgr,
    )

    assert result.is_completed is True
    mock_session_mgr.ensure_authenticated.assert_called_once_with(mock_page)
