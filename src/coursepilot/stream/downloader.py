"""Multi-threaded segment downloader, key caching, exponential backoff, and atomic TS merger."""

from __future__ import annotations

import concurrent.futures
import logging
import shutil
import threading
import time
import uuid
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import httpx

from coursepilot.config import Settings
from coursepilot.exceptions import VodDownloadError
from coursepilot.materials.downloader import get_authenticated_httpx_client
from coursepilot.stream.crypto import (
    decrypt_aes_128_segment,
    derive_implicit_iv,
)
from coursepilot.stream.models import (
    DownloadProgress,
    StreamInfo,
    StreamSegment,
)

logger = logging.getLogger(__name__)


def assemble_ts_segments_atomic(segment_paths: List[Path], target_file: Path) -> Path:
    """Sequentially concatenate ordered TS segments and atomically move to target_file.
    
    Args:
        segment_paths: List of segment file paths in strictly sorted order.
        target_file: Final destination path (e.g. .mp4).
        
    Returns:
        The target_file Path.
    """
    target_file.parent.mkdir(parents=True, exist_ok=True)
    temp_target = target_file.with_suffix(target_file.suffix + ".tmp")

    try:
        with open(temp_target, "wb") as outfile:
            for seg_path in segment_paths:
                with open(seg_path, "rb") as infile:
                    shutil.copyfileobj(infile, outfile, length=65536)

        # Atomic replacement on same filesystem volume
        temp_target.replace(target_file)
        return target_file
    except Exception:
        temp_target.unlink(missing_ok=True)
        raise


class SegmentDownloader:
    """Thread-safe multi-worker downloader for HLS video segments with key caching."""

    def __init__(
        self,
        client: Optional[httpx.Client] = None,
        max_workers: int = 6,
        settings: Optional[Settings] = None,
    ) -> None:
        self.max_workers = max_workers
        self.settings = settings or Settings()
        self._own_client = False

        if client is not None:
            self.client = client
        else:
            self.client = get_authenticated_httpx_client(self.settings)
            self._own_client = True

        self._key_cache: Dict[str, bytes] = {}
        self._key_lock = threading.Lock()

    def _fetch_key(self, key_uri: str) -> bytes:
        """Fetch and cache a 16-byte AES-128 encryption key thread-safely."""
        with self._key_lock:
            if key_uri in self._key_cache:
                return self._key_cache[key_uri]

        resp = self.client.get(key_uri, timeout=15.0)
        resp.raise_for_status()
        key_bytes = resp.content

        if len(key_bytes) != 16:
            raise VodDownloadError(
                f"Invalid AES-128 key length ({len(key_bytes)} bytes) received from {key_uri}"
            )

        with self._key_lock:
            self._key_cache[key_uri] = key_bytes

        return key_bytes

    def _download_single_segment(
        self,
        segment: StreamSegment,
        cache_dir: Path,
        retry_count: int = 3,
    ) -> Path:
        """Download and decrypt a single segment with exponential backoff retry."""
        seg_path = cache_dir / f"seg_{segment.sequence_number:06d}.ts"
        last_err: Optional[Exception] = None

        for attempt in range(1, retry_count + 1):
            try:
                resp = self.client.get(segment.uri, timeout=30.0)
                resp.raise_for_status()
                data = resp.content

                if segment.key_info:
                    key = self._fetch_key(segment.key_info.uri)
                    iv = (
                        segment.key_info.iv
                        if segment.key_info.iv is not None
                        else derive_implicit_iv(segment.sequence_number)
                    )
                    data = decrypt_aes_128_segment(data, key, iv)

                with open(seg_path, "wb") as f:
                    f.write(data)

                return seg_path
            except Exception as e:
                last_err = e
                logger.warning(
                    "Download attempt %d/%d failed for segment %d (%s): %s",
                    attempt,
                    retry_count,
                    segment.sequence_number,
                    segment.uri,
                    e,
                )
                if attempt < retry_count:
                    time.sleep(2 ** (attempt - 1))  # 1s, 2s, 4s
                else:
                    raise VodDownloadError(
                        f"Failed to download segment {segment.sequence_number} after {retry_count} attempts: {e}"
                    ) from e

        raise VodDownloadError(
            f"Segment {segment.sequence_number} download failed: {last_err}"
        )

    def download_stream(
        self,
        stream_info: StreamInfo,
        target_file: Path,
        overwrite: bool = False,
        on_progress: Optional[Callable[[DownloadProgress], None]] = None,
    ) -> Tuple[Path, int, bool]:
        """Download all segments of a stream and atomically assemble into target_file.
        
        Args:
            stream_info: StreamInfo with media segments or direct MP4 flag.
            target_file: Destination file path.
            overwrite: If False, skip download if target_file already exists.
            on_progress: Progress update callback.
            
        Returns:
            Tuple of (saved_file_path, file_size_in_bytes, is_skipped).
        """
        # Duplicate skip check (Decision D-14-11)
        if target_file.exists() and not overwrite:
            return target_file, target_file.stat().st_size, True

        target_file.parent.mkdir(parents=True, exist_ok=True)

        # Direct MP4 fallback
        if stream_info.is_direct_mp4:
            temp_mp4 = target_file.with_suffix(target_file.suffix + ".tmp")
            try:
                with self.client.stream("GET", stream_info.media_url, timeout=60.0) as resp:
                    resp.raise_for_status()
                    total_bytes = int(resp.headers.get("content-length", 0))
                    downloaded = 0
                    with open(temp_mp4, "wb") as f:
                        for chunk in resp.iter_bytes(chunk_size=65536):
                            f.write(chunk)
                            downloaded += len(chunk)
                            if on_progress:
                                pct = (downloaded / total_bytes * 100.0) if total_bytes > 0 else 0.0
                                on_progress(
                                    DownloadProgress(
                                        current_segment=1,
                                        total_segments=1,
                                        downloaded_bytes=downloaded,
                                        percent=round(pct, 1),
                                    )
                                )
                temp_mp4.replace(target_file)
                return target_file, target_file.stat().st_size, False
            except Exception:
                temp_mp4.unlink(missing_ok=True)
                raise

        total_segments = len(stream_info.segments)
        if total_segments == 0:
            raise VodDownloadError("Stream contains 0 segments to download.")

        # Staging cache directory on same filesystem root (Decision D-14-12, Assumption A-14-04)
        cache_parent = target_file.parent.parent if target_file.parent.parent.exists() else target_file.parent
        cache_dir = cache_parent / ".cache" / f"stream_{uuid.uuid4().hex[:8]}"
        cache_dir.mkdir(parents=True, exist_ok=True)

        try:
            downloaded_bytes = 0
            completed_segments = 0

            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_map = {
                    executor.submit(self._download_single_segment, seg, cache_dir): seg
                    for seg in stream_info.segments
                }

                for future in concurrent.futures.as_completed(future_map):
                    seg_file = future.result()  # Propagates VodDownloadError on failure
                    completed_segments += 1
                    downloaded_bytes += seg_file.stat().st_size

                    if on_progress:
                        pct = (completed_segments / total_segments) * 100.0
                        on_progress(
                            DownloadProgress(
                                current_segment=completed_segments,
                                total_segments=total_segments,
                                downloaded_bytes=downloaded_bytes,
                                percent=round(pct, 1),
                            )
                        )

            # Assemble segments in strict sequence order
            sorted_segment_paths = [
                cache_dir / f"seg_{seg.sequence_number:06d}.ts"
                for seg in stream_info.segments
            ]
            assemble_ts_segments_atomic(sorted_segment_paths, target_file)

            return target_file, target_file.stat().st_size, False
        finally:
            shutil.rmtree(cache_dir, ignore_errors=True)

    def close(self) -> None:
        """Close HTTP client if owned by this downloader instance."""
        if self._own_client and self.client:
            self.client.close()

    def __enter__(self) -> SegmentDownloader:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
