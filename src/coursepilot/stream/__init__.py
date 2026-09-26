"""Pure-Python HLS/m3u8 streaming, decryption, and segment assembly engine."""

from coursepilot.stream.crypto import (
    decrypt_aes_128_segment,
    derive_implicit_iv,
)
from coursepilot.stream.downloader import (
    SegmentDownloader,
    assemble_ts_segments_atomic,
)
from coursepilot.stream.runner import (
    resolve_candidate_vods_for_download,
    run_vod_download_pipeline,
)
from coursepilot.stream.sniffer import StreamSniffer
from coursepilot.stream.parser import (
    parse_media_playlist,
    parse_stream_manifest,
    resolve_media_playlist_url,
)
from coursepilot.stream.models import (
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
    "StreamSniffer",
    "assemble_ts_segments_atomic",
    "resolve_candidate_vods_for_download",
    "run_vod_download_pipeline",
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
