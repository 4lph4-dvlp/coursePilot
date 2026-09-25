---
phase: 14-pure-python-vod-stream-downloader-integration
plan: "02"
status: completed
date: 2026-09-25
---

# Plan 14-02 Summary: Playwright Hybrid Stream Sniffer, Watch Concurrent Downloader & Standalone CLI Integration

## Overview

Plan 14-02 integrated the pure-Python streaming downloader into KAU Assistant's operational workflows (VDL-02):
1. **Playwright Hybrid Stream Sniffer (D-14-13)**: Implemented `StreamSniffer` combining `page.on("response")` network interception with DOM `<video>` fallback probing, safely filtering `blob:` URLs and capturing master/media m3u8 addresses within seconds.
2. **Attendance Fault Isolation (VDL-02, D-14-01, D-14-03, D-14-04)**: Integrated background segment downloading into `watch_course_vods` via daemon threads, strictly guaranteeing that any download network timeout, 5xx error, or decryption failure never interrupts Coursemos 1.0x attendance playback heartbeats or Notion completion updates.
3. **Standalone High-Speed Downloader Pipeline (D-14-02)**: Implemented `run_vod_download_pipeline` and the `kau-assistant download-vod` CLI command, enabling users and agents to batch download lectures (including already completed videos) at full line speed without real-time playback delays.
4. **Unified CLI Options & Clean Output (D-14-08, D-14-11, D-14-16)**: Added `--download`, `--quality`, `--output-dir`, and `--overwrite` to `watch`, alongside full option support for `download-vod` with formatted Rich tables on stdout and clean, unescaped JSON output when `--json` is supplied.

## Key Accomplishments

1. **Hybrid Stream Sniffer (`src/kau_assistant/stream/sniffer.py`, `src/kau_assistant/player/vod_player.py`)**:
   - Implemented `StreamSniffer` listening for `.m3u8` and media `.mp4` URLs on Playwright response events.
   - Provided fallback DOM probe querying `video.currentSrc` or `video.src` while explicitly skipping `blob:` schemes.
   - Updated `VodPlayer.play_vod` with `on_stream_detected` parameter and clean listener attachment/detachment in `finally:` block.

2. **Concurrent Watch Downloader (`src/kau_assistant/player/runner.py`)**:
   - Extended `watch_course_vods` to support `download`, `preferred_quality`, `overwrite`, and `output_dir`.
   - Dispatched background download daemon threads upon stream URL detection.
   - Verified that all playback progress, completion statuses, and Notion sync events remain 100% intact if download errors occur.

3. **Standalone Downloader Pipeline (`src/kau_assistant/stream/runner.py`)**:
   - Implemented `resolve_candidate_vods_for_download` targeting specified or current weeks across all candidate lectures.
   - Implemented `run_vod_download_pipeline` navigating rapidly to VOD pages, sniffing streams, closing/navigating away immediately, and downloading multi-threaded segments to `downloads/<과목명>/W{주차}/`.

4. **CLI Integration (`src/kau_assistant/cli.py`)**:
   - Added `--download`, `--quality`, `--output-dir`, and `--overwrite` options to `kau-assistant watch`.
   - Added standalone `kau-assistant download-vod` command supporting `--course`, `--week`, `--video-index`, `--quality`, `--output-dir`, `--overwrite`, `--dry-run`, `--json`, `--relogin`, and `--headed`.
   - Implemented `render_vod_download_report` displaying Rich status tables, file sizes, and summary metrics.

## Verification & Validation

- Automated unit & integration tests:
  - `tests/test_stream_sniffer.py`: 4 passed
  - `tests/test_watch_download.py`: 3 passed
  - `tests/test_cli_download_vod.py`: 3 passed
  - Plan 14-02 suite: 10 passed in 2.11s.
- Entire Phase 14 stream suite: 26 passed across all 6 test files (`tests/test_stream_crypto.py`, `tests/test_stream_parser.py`, `tests/test_stream_downloader.py`, `tests/test_stream_sniffer.py`, `tests/test_watch_download.py`, `tests/test_cli_download_vod.py`).
