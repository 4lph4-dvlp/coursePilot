---
phase: 14-pure-python-vod-stream-downloader-integration
plan: "01"
status: completed
date: 2026-09-25
---

# Plan 14-01 Summary: Pure-Python HLS Manifest Parser, RFC 8216 AES-128 Decryptor & Atomic TS Downloader Engine

## Overview

Plan 14-01 established the pure-Python streaming, decryption, and segment assembly engine for KAU LXP lecture videos (VDL-01):
1. **Zero External Binaries (VDL-01, D-14-05, D-14-07)**: Integrated `m3u8>=6.0.0`, `cryptography>=50.0.0`, and `httpx>=0.28.0` without requiring `ffmpeg` or external system executables.
2. **RFC 8216 AES-128-CBC Decryption (D-14-06)**: Implemented AES-128 segment decryption supporting both explicit IV attributes and sequence-number-derived 16-octet big-endian implicit IVs, with robust fallback for block-aligned MPEG-TS padding.
3. **M3U8 Master & Media Parsing (D-14-07, D-14-08)**: Implemented stream manifest parsing with automatic variant resolution supporting quality targets (`best`, `1080p`, `720p`, `worst`) sorted by resolution and bandwidth.
4. **High-Speed Multi-Threaded Downloader (D-14-11, D-14-12, D-14-14, D-14-15)**: Implemented `SegmentDownloader` with thread-safe in-memory key caching, 3-attempt exponential backoff retry (1s, 2s, 4s), duplicate download skipping (`--overwrite`), and atomic temporary file concatenation (`assemble_ts_segments_atomic`).

## Key Accomplishments

1. **Domain Models (`src/coursepilot/stream/models.py`)**:
   - Defined `StreamVariant`, `StreamKeyInfo`, `StreamSegment`, and `StreamInfo` representing HLS playlist structures.
   - Defined telemetry schemas `DownloadProgress` and result structures `VodDownloadItemResult`, `CourseVodDownloadResult`, `VodDownloadRunResult`, and `VodDownloadStatus`.

2. **RFC 8216 Crypto Engine (`src/coursepilot/stream/crypto.py`)**:
   - Implemented `derive_implicit_iv(sequence_number)` returning 16-byte big-endian IVs per RFC 8216 §5.2.
   - Implemented `decrypt_aes_128_segment` with PKCS7 unpadding and graceful raw-byte fallback for block-aligned TS chunks.

3. **Playlist & Variant Parser (`src/coursepilot/stream/parser.py`)**:
   - Implemented `resolve_media_playlist_url` parsing master playlists and selecting variant playlists matching quality strings.
   - Implemented `parse_media_playlist` extracting segments, sequence numbers, durations, and `#EXT-X-KEY` definitions.
   - Implemented `parse_stream_manifest` distinguishing variant playlists, media playlists, and direct MP4 URLs.

4. **Multi-Threaded Downloader & Assembly (`src/coursepilot/stream/downloader.py`, `src/coursepilot/exceptions.py`)**:
   - Implemented `VodDownloadError` custom exception for stream downloader failures.
   - Implemented `SegmentDownloader` executing parallel downloads via `ThreadPoolExecutor` (default 6 workers).
   - Thread-safe key cache (`_key_cache` + `threading.Lock`) preventing redundant key queries across segments.
   - Implemented `assemble_ts_segments_atomic` concatenating downloaded TS chunks via temporary `.tmp` file and atomically replacing the target destination.

## Verification & Validation

- Automated unit test suites:
  - `tests/test_stream_crypto.py`: 5 passed
  - `tests/test_stream_parser.py`: 5 passed
  - `tests/test_stream_downloader.py`: 6 passed
  - Total Plan 14-01 test count: 16 passed in 2.48s with 0 errors or warnings.
