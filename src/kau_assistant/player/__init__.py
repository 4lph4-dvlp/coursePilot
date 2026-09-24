"""VOD playback automation package."""

from kau_assistant.player.models import PlaybackOptions, PlaybackProgress
from kau_assistant.player.runner import (
    WatchResult,
    find_target_course,
    resolve_candidate_vods,
    watch_course_vods,
)
from kau_assistant.player.vod_player import VodPlayer

__all__ = [
    "PlaybackOptions",
    "PlaybackProgress",
    "VodPlayer",
    "WatchResult",
    "find_target_course",
    "resolve_candidate_vods",
    "watch_course_vods",
]
