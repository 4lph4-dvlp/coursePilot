"""M3U8 master and media playlist parser with quality resolution."""

from __future__ import annotations

import re
from typing import List, Optional, Tuple
from urllib.parse import urljoin

import m3u8

from coursepilot.stream.models import (
    StreamInfo,
    StreamKeyInfo,
    StreamSegment,
    StreamVariant,
)


def _extract_height(resolution: Optional[Tuple[int, int]]) -> int:
    """Extract height dimension from resolution tuple (width, height)."""
    if resolution and len(resolution) == 2:
        return resolution[1]
    return 0


def resolve_media_playlist_url(
    master_content: str,
    master_url: str,
    preferred_quality: str = "best",
) -> str:
    """Resolve the target media playlist URL from a master playlist according to quality preference.
    
    Args:
        master_content: Raw text content of the M3U8 master playlist.
        master_url: Base URL of the master playlist for resolving relative URLs.
        preferred_quality: Desired quality ('best', '1080p', '720p', 'worst', etc.).
        
    Returns:
        Absolute URL of the selected variant media playlist.
    """
    parsed = m3u8.loads(master_content, uri=master_url)
    if not parsed.is_variant or not parsed.playlists:
        return master_url

    # Sort playlists descending by height, then by bandwidth
    sorted_playlists = sorted(
        parsed.playlists,
        key=lambda p: (
            _extract_height(p.stream_info.resolution if p.stream_info else None),
            (p.stream_info.bandwidth or 0) if p.stream_info else 0,
        ),
        reverse=True,
    )

    norm_quality = preferred_quality.strip().lower()
    selected_playlist = sorted_playlists[0]

    if norm_quality in ("best", "highest", "max"):
        selected_playlist = sorted_playlists[0]
    elif norm_quality in ("worst", "lowest", "min"):
        selected_playlist = sorted_playlists[-1]
    else:
        # Check if user specified a resolution like '1080p', '720', etc.
        match = re.search(r"(\d+)", norm_quality)
        if match:
            target_height = int(match.group(1))
            matched = [
                p
                for p in sorted_playlists
                if p.stream_info
                and p.stream_info.resolution
                and p.stream_info.resolution[1] == target_height
            ]
            if matched:
                selected_playlist = matched[0]
            else:
                # Fallback to closest or highest
                selected_playlist = sorted_playlists[0]
        else:
            selected_playlist = sorted_playlists[0]

    return urljoin(master_url, selected_playlist.uri)


def parse_media_playlist(media_content: str, media_url: str) -> StreamInfo:
    """Parse an M3U8 media playlist and extract segment and encryption metadata.
    
    Args:
        media_content: Raw text content of the M3U8 media playlist.
        media_url: Base URL of the media playlist.
        
    Returns:
        StreamInfo containing segments with absolute URIs, sequence numbers, and keys.
    """
    parsed = m3u8.loads(media_content, uri=media_url)
    base_sequence = parsed.media_sequence or 0
    segments: List[StreamSegment] = []

    # Active key tracking (M3U8 allows key changes mid-stream)
    current_key_info: Optional[StreamKeyInfo] = None

    if parsed.keys:
        for k in parsed.keys:
            if k and k.method and k.method != "NONE":
                iv_bytes = None
                if k.iv:
                    iv_str = k.iv[2:] if k.iv.lower().startswith("0x") else k.iv
                    iv_bytes = bytes.fromhex(iv_str)
                current_key_info = StreamKeyInfo(
                    method=k.method,
                    uri=urljoin(media_url, k.uri),
                    iv=iv_bytes,
                )
                break

    for idx, seg in enumerate(parsed.segments):
        seq_num = base_sequence + idx
        seg_key_info = current_key_info

        if seg.key and seg.key.method and seg.key.method != "NONE":
            iv_bytes = None
            if seg.key.iv:
                iv_str = seg.key.iv[2:] if seg.key.iv.lower().startswith("0x") else seg.key.iv
                iv_bytes = bytes.fromhex(iv_str)
            seg_key_info = StreamKeyInfo(
                method=seg.key.method,
                uri=urljoin(media_url, seg.key.uri),
                iv=iv_bytes,
            )
            current_key_info = seg_key_info

        segment_uri = urljoin(media_url, seg.uri)
        segments.append(
            StreamSegment(
                uri=segment_uri,
                duration=float(seg.duration or 0.0),
                sequence_number=seq_num,
                key_info=seg_key_info,
            )
        )

    total_duration = sum(s.duration for s in segments)
    return StreamInfo(
        master_url="",
        media_url=media_url,
        is_direct_mp4=False,
        segments=segments,
        total_duration=total_duration,
    )


def parse_stream_manifest(
    content: str,
    base_url: str,
    preferred_quality: str = "best",
) -> Tuple[str, StreamInfo]:
    """Inspect and parse a stream manifest which may be a master or media playlist.
    
    Args:
        content: Playlist text content or URL response.
        base_url: Base URL used to resolve relative paths.
        preferred_quality: Desired quality for master playlists.
        
    Returns:
        Tuple of (target_media_url, StreamInfo).
    """
    stripped = content.strip()
    if not stripped.startswith("#EXTM3U") and (".mp4" in base_url.lower() or not stripped.startswith("#")):
        # Direct MP4 fallback
        return (
            base_url,
            StreamInfo(
                master_url=base_url,
                media_url=base_url,
                is_direct_mp4=True,
            ),
        )

    parsed = m3u8.loads(content, uri=base_url)

    if parsed.is_variant and parsed.playlists:
        variants = [
            StreamVariant(
                bandwidth=(p.stream_info.bandwidth or 0) if p.stream_info else 0,
                resolution=p.stream_info.resolution if p.stream_info else None,
                uri=urljoin(base_url, p.uri),
            )
            for p in parsed.playlists
        ]
        media_url = resolve_media_playlist_url(content, base_url, preferred_quality)
        return (
            media_url,
            StreamInfo(
                master_url=base_url,
                media_url=media_url,
                is_direct_mp4=False,
                variants=variants,
            ),
        )

    # Media playlist directly
    info = parse_media_playlist(content, base_url)
    return (base_url, info)
