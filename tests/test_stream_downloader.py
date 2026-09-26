"""Unit tests for multi-threaded SegmentDownloader and atomic TS merger."""

import time
from pathlib import Path
import httpx
import pytest
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding

from coursepilot.exceptions import VodDownloadError
from coursepilot.stream.downloader import (
    SegmentDownloader,
    assemble_ts_segments_atomic,
)
from coursepilot.stream.models import (
    DownloadProgress,
    StreamInfo,
    StreamKeyInfo,
    StreamSegment,
)


def test_assemble_ts_segments_atomic(tmp_path: Path):
    target = tmp_path / "output.mp4"
    seg1 = tmp_path / "seg1.ts"
    seg2 = tmp_path / "seg2.ts"

    seg1.write_bytes(b"DATA_PART_1_")
    seg2.write_bytes(b"DATA_PART_2")

    res = assemble_ts_segments_atomic([seg1, seg2], target)

    assert res == target
    assert target.exists()
    assert target.read_bytes() == b"DATA_PART_1_DATA_PART_2"
    assert not (tmp_path / "output.mp4.tmp").exists()


def test_parallel_segment_download_and_atomic_merge(tmp_path: Path):
    # Setup 5 mock segments
    seg_contents = {
        f"https://example.com/seg_{i}.ts": f"SEGMENT_{i}_PAYLOAD".encode("utf-8")
        for i in range(5)
    }

    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if url_str in seg_contents:
            return httpx.Response(200, content=seg_contents[url_str])
        return httpx.Response(404)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    downloader = SegmentDownloader(client=client, max_workers=3)

    segments = [
        StreamSegment(
            uri=f"https://example.com/seg_{i}.ts",
            duration=5.0,
            sequence_number=i,
        )
        for i in range(5)
    ]
    stream_info = StreamInfo(
        media_url="https://example.com/index.m3u8",
        segments=segments,
        total_duration=25.0,
    )

    progress_events = []
    target = tmp_path / "video.mp4"

    res_path, size, skipped = downloader.download_stream(
        stream_info,
        target,
        overwrite=False,
        on_progress=progress_events.append,
    )

    assert res_path == target
    assert not skipped
    expected_data = b"".join(seg_contents[f"https://example.com/seg_{i}.ts"] for i in range(5))
    assert target.read_bytes() == expected_data
    assert size == len(expected_data)
    assert len(progress_events) == 5
    assert progress_events[-1].percent == 100.0


def test_key_caching_across_segments(tmp_path: Path):
    key = b"0123456789abcdef"  # 16 bytes
    key_uri = "https://example.com/key.bin"
    key_fetch_count = 0

    # Encrypt 3 segments with AES-128
    segments = []
    seg_contents = {}

    for i in range(3):
        iv = i.to_bytes(16, "big")
        plaintext = f"SECRET_SEG_{i}".encode("utf-8")
        padder = padding.PKCS7(128).padder()
        padded = padder.update(plaintext) + padder.finalize()
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
        ciphertext = cipher.encryptor().update(padded) + cipher.encryptor().finalize()

        url = f"https://example.com/enc_{i}.ts"
        seg_contents[url] = ciphertext
        segments.append(
            StreamSegment(
                uri=url,
                duration=4.0,
                sequence_number=i,
                key_info=StreamKeyInfo(uri=key_uri),
            )
        )

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal key_fetch_count
        url_str = str(request.url)
        if url_str == key_uri:
            key_fetch_count += 1
            return httpx.Response(200, content=key)
        if url_str in seg_contents:
            return httpx.Response(200, content=seg_contents[url_str])
        return httpx.Response(404)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    downloader = SegmentDownloader(client=client, max_workers=2)

    stream_info = StreamInfo(
        media_url="https://example.com/enc.m3u8",
        segments=segments,
        total_duration=12.0,
    )
    target = tmp_path / "enc_video.mp4"

    res_path, size, skipped = downloader.download_stream(stream_info, target)
    assert res_path == target
    assert target.exists()
    assert target.read_bytes() == b"SECRET_SEG_0SECRET_SEG_1SECRET_SEG_2"
    # Thread-safe cache ensures key is fetched only once despite 3 encrypted segments
    assert key_fetch_count == 1


def test_download_skip_and_overwrite(tmp_path: Path):
    target = tmp_path / "existing.mp4"
    target.write_bytes(b"EXISTING_CONTENT")

    downloader = SegmentDownloader(client=httpx.Client())
    stream_info = StreamInfo(
        media_url="https://example.com/test.m3u8",
        segments=[StreamSegment(uri="https://example.com/s.ts", duration=1.0, sequence_number=1)],
    )

    # 1. overwrite=False should skip
    res_path, size, skipped = downloader.download_stream(stream_info, target, overwrite=False)
    assert skipped is True
    assert size == len(b"EXISTING_CONTENT")
    assert target.read_bytes() == b"EXISTING_CONTENT"

    # 2. overwrite=True with mock client returning new content
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"NEW_STREAM_DATA")

    downloader.client = httpx.Client(transport=httpx.MockTransport(handler))
    res_path, size, skipped = downloader.download_stream(stream_info, target, overwrite=True)
    assert skipped is False
    assert size == len(b"NEW_STREAM_DATA")
    assert target.read_bytes() == b"NEW_STREAM_DATA"


def test_segment_retry_backoff(tmp_path: Path, monkeypatch):
    # Mock time.sleep to avoid waiting during test
    sleep_calls = []
    monkeypatch.setattr(time, "sleep", lambda s: sleep_calls.append(s))

    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            return httpx.Response(500, content=b"Internal Server Error")
        return httpx.Response(200, content=b"SUCCESSFUL_DATA")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    downloader = SegmentDownloader(client=client, max_workers=1)

    stream_info = StreamInfo(
        media_url="https://example.com/retry.m3u8",
        segments=[StreamSegment(uri="https://example.com/retry.ts", duration=1.0, sequence_number=1)],
    )
    target = tmp_path / "retry.mp4"

    res_path, size, skipped = downloader.download_stream(stream_info, target)
    assert res_path == target
    assert target.read_bytes() == b"SUCCESSFUL_DATA"
    assert attempts == 3
    # Slept for 2^0 = 1s and 2^1 = 2s
    assert sleep_calls == [1, 2]


def test_atomic_cleanup_on_failure(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda s: None)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, content=b"Unavailable")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    downloader = SegmentDownloader(client=client, max_workers=1)

    stream_info = StreamInfo(
        media_url="https://example.com/fail.m3u8",
        segments=[StreamSegment(uri="https://example.com/fail.ts", duration=1.0, sequence_number=1)],
    )
    target = tmp_path / "fail.mp4"

    with pytest.raises(VodDownloadError):
        downloader.download_stream(stream_info, target)

    assert not target.exists()
    assert not (tmp_path / "fail.mp4.tmp").exists()
    # Cache directory cleaned up
    cache_dirs = list(tmp_path.glob(".cache/stream_*"))
    assert len(cache_dirs) == 0
