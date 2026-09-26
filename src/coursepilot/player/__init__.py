"""VOD playback automation package."""

from coursepilot.player.models import PlaybackOptions, PlaybackProgress
from coursepilot.player.runner import (
    WatchResult,
    find_target_course,
    resolve_candidate_vods,
    watch_course_vods,
)
from coursepilot.player.vod_player import VodPlayer

__all__ = [
    "PlaybackOptions",
    "PlaybackProgress",
    "VodPlayer",
    "WatchResult",
    "find_target_course",
    "resolve_candidate_vods",
    "watch_course_vods",
]
