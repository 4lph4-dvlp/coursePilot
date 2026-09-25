import pytest

from kau_assistant.stream.parser import (
    parse_media_playlist,
    parse_stream_manifest,
    resolve_media_playlist_url,
)

SAMPLE_MASTER_M3U8 = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-STREAM-INF:BANDWIDTH=600000,RESOLUTION=854x480
480p/index.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=2500000,RESOLUTION=1920x1080
1080p/index.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=1200000,RESOLUTION=1280x720
720p/index.m3u8
"""

SAMPLE_MEDIA_AES_M3U8 = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:10
#EXT-X-MEDIA-SEQUENCE:100
#EXT-X-KEY:METHOD=AES-128,URI="https://lms.kau.ac.kr/key.php?id=123",IV=0x1234567890abcdef1234567890abcdef
#EXTINF:9.800,
seg_000.ts
#EXTINF:10.000,
seg_001.ts
#EXT-X-ENDLIST
"""

SAMPLE_MEDIA_IMPLICIT_IV_M3U8 = """#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:10
#EXT-X-MEDIA-SEQUENCE:50
#EXT-X-KEY:METHOD=AES-128,URI="https://lms.kau.ac.kr/key.php?id=999"
#EXTINF:10.000,
part1.ts
#EXTINF:10.000,
part2.ts
#EXT-X-ENDLIST
"""


def test_resolve_media_playlist_variants():
    base_url = "https://cdn.kau.ac.kr/vod/hls/master.m3u8"

    # 'best' should pick 1080p
    best_url = resolve_media_playlist_url(SAMPLE_MASTER_M3U8, base_url, "best")
    assert best_url == "https://cdn.kau.ac.kr/vod/hls/1080p/index.m3u8"

    # 'worst' should pick 480p
    worst_url = resolve_media_playlist_url(SAMPLE_MASTER_M3U8, base_url, "worst")
    assert worst_url == "https://cdn.kau.ac.kr/vod/hls/480p/index.m3u8"

    # '720p' should pick 720p
    p720_url = resolve_media_playlist_url(SAMPLE_MASTER_M3U8, base_url, "720p")
    assert p720_url == "https://cdn.kau.ac.kr/vod/hls/720p/index.m3u8"

    # Fallback to best for unmatched quality string
    fallback_url = resolve_media_playlist_url(SAMPLE_MASTER_M3U8, base_url, "4k")
    assert fallback_url == "https://cdn.kau.ac.kr/vod/hls/1080p/index.m3u8"


def test_parse_media_playlist_with_aes_128_key():
    base_url = "https://lms.kau.ac.kr/stream/720p/index.m3u8"
    info = parse_media_playlist(SAMPLE_MEDIA_AES_M3U8, base_url)

    assert len(info.segments) == 2
    assert info.total_duration == pytest.approx(19.8)

    # First segment
    seg0 = info.segments[0]
    assert seg0.uri == "https://lms.kau.ac.kr/stream/720p/seg_000.ts"
    assert seg0.sequence_number == 100
    assert seg0.duration == 9.8
    assert seg0.key_info is not None
    assert seg0.key_info.method == "AES-128"
    assert seg0.key_info.uri == "https://lms.kau.ac.kr/key.php?id=123"
    assert seg0.key_info.iv == bytes.fromhex("1234567890abcdef1234567890abcdef")

    # Second segment
    seg1 = info.segments[1]
    assert seg1.uri == "https://lms.kau.ac.kr/stream/720p/seg_001.ts"
    assert seg1.sequence_number == 101


def test_parse_media_playlist_implicit_iv():
    base_url = "https://lms.kau.ac.kr/stream/media.m3u8"
    info = parse_media_playlist(SAMPLE_MEDIA_IMPLICIT_IV_M3U8, base_url)

    assert len(info.segments) == 2
    seg0 = info.segments[0]
    assert seg0.sequence_number == 50
    assert seg0.key_info is not None
    assert seg0.key_info.iv is None  # Implicit IV to be derived from sequence_number
    assert seg0.key_info.uri == "https://lms.kau.ac.kr/key.php?id=999"

    seg1 = info.segments[1]
    assert seg1.sequence_number == 51
    assert seg1.key_info is not None
    assert seg1.key_info.iv is None


def test_parse_direct_mp4_fallback():
    mp4_url = "https://lms.kau.ac.kr/videos/lecture_01.mp4"
    target_url, info = parse_stream_manifest("", mp4_url)

    assert target_url == mp4_url
    assert info.is_direct_mp4 is True
    assert info.media_url == mp4_url


def test_parse_stream_manifest_master():
    base_url = "https://cdn.kau.ac.kr/master.m3u8"
    media_url, info = parse_stream_manifest(SAMPLE_MASTER_M3U8, base_url, "720p")

    assert media_url == "https://cdn.kau.ac.kr/720p/index.m3u8"
    assert info.is_direct_mp4 is False
    assert len(info.variants) == 3
