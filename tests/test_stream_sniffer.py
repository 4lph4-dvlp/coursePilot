"""Unit tests for Playwright hybrid StreamSniffer and VodPlayer integration."""

from unittest.mock import MagicMock
import pytest

from kau_assistant.player.vod_player import VodPlayer
from kau_assistant.stream.sniffer import StreamSniffer


def test_sniffer_response_interception():
    page = MagicMock()
    callback_calls = []

    sniffer = StreamSniffer(on_stream_detected=callback_calls.append, timeout=2.0)
    sniffer.attach(page)

    assert page.on.called
    event_name, listener = page.on.call_args[0]
    assert event_name == "response"

    # Mock response with .m3u8 URL
    resp = MagicMock()
    resp.url = "https://cdn.kau.ac.kr/vod/hls/master.m3u8"
    resp.headers = {"content-type": "application/vnd.apple.mpegurl"}

    listener(resp)

    assert sniffer.detected_url == "https://cdn.kau.ac.kr/vod/hls/master.m3u8"
    assert callback_calls == ["https://cdn.kau.ac.kr/vod/hls/master.m3u8"]

    # wait_for_stream should return immediately
    detected = sniffer.wait_for_stream(page, timeout=0.1)
    assert detected == "https://cdn.kau.ac.kr/vod/hls/master.m3u8"

    sniffer.detach(page)
    assert page.remove_listener.called


def test_sniffer_dom_video_fallback():
    page = MagicMock()
    callback_calls = []

    sniffer = StreamSniffer(on_stream_detected=callback_calls.append, timeout=0.1)
    sniffer.attach(page)

    # DOM returns direct mp4 video url
    page.evaluate.return_value = "https://lms.kau.ac.kr/videos/lecture.mp4"

    detected = sniffer.wait_for_stream(page, timeout=0.1)
    assert detected == "https://lms.kau.ac.kr/videos/lecture.mp4"
    assert callback_calls == ["https://lms.kau.ac.kr/videos/lecture.mp4"]


def test_sniffer_filters_blob_urls():
    page = MagicMock()
    sniffer = StreamSniffer(timeout=0.1)
    sniffer.attach(page)

    # DOM returns blob: URL
    page.evaluate.return_value = "blob:https://lms.kau.ac.kr/d934-1234-abcd"

    detected = sniffer.wait_for_stream(page, timeout=0.1)
    assert detected is None
    assert sniffer.detected_url is None


def test_vod_player_integrates_stream_sniffer(monkeypatch):
    player = VodPlayer()
    page = MagicMock()
    page.title.return_value = "Week 1 Video"
    page.url = "https://lms.kau.ac.kr/mod/vod/view.php?id=10"
    page.evaluate.side_effect = [
        {"ok": True},  # _init_video
        {"duration": 10.0, "currentTime": 10.0, "paused": False, "ended": True},  # first poll completed
    ]

    detected_urls = []

    def mock_goto(url, **kwargs):
        # Trigger response during navigation
        pass

    page.goto.side_effect = mock_goto

    res = player.play_vod(
        page=page,
        vod_url="https://lms.kau.ac.kr/mod/vod/view.php?id=10",
        on_stream_detected=detected_urls.append,
    )

    assert res.is_completed is True
    # Verify listener was attached to page
    attached_events = [call[0][0] for call in page.on.call_args_list]
    assert "response" in attached_events
    # Verify listener was removed in finally
    removed_events = [call[0][0] for call in page.remove_listener.call_args_list]
    assert "response" in removed_events
