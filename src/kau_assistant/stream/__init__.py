"""Pure-Python HLS/m3u8 streaming, decryption, and segment assembly engine."""

from kau_assistant.stream.crypto import (
    decrypt_aes_128_segment,
    derive_implicit_iv,
)
from kau_assistant.stream.downloader import (
    SegmentDownloader,
    assemble_ts_segments_atomic,
)
from kau_assistant.stream.parser import (
    parse_media_playlist,
    parse_stream_manifest,
    resolve_media_playlist_url,
)
from kau_assistant.stream.models import (
    CourseVodDownloadResult,
    DownloadProgress,
    StreamInfo,
    StreamKeyInfo,
    StreamSegment,
    StreamVariant,
    VodDownloadItemResult,
    VodDownloadRunResult,
    VodDownloadStatus,
)

__all__ = [
    "SegmentDownloader",
    "assemble_ts_segments_atomic",
    "derive_implicit_iv",
    "decrypt_aes_128_segment",
    "resolve_media_playlist_url",
    "parse_media_playlist",
    "parse_stream_manifest",
    "StreamVariant",
    "StreamKeyInfo",
    "StreamSegment",
    "StreamInfo",
    "VodDownloadStatus",
    "DownloadProgress",
    "VodDownloadItemResult",
    "CourseVodDownloadResult",
    "VodDownloadRunResult",
]
