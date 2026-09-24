"""Coursemos Video.js VOD player automation engine."""

from __future__ import annotations

import logging
import time
from typing import Callable

from playwright.sync_api import Dialog, Page, TimeoutError as PlaywrightTimeoutError

from kau_assistant.player.models import PlaybackOptions, PlaybackProgress

logger = logging.getLogger(__name__)


class VodPlayer:
    """Controls Coursemos Video.js video playback in background, maintaining attendance heartbeats."""

    def __init__(self, default_options: PlaybackOptions | None = None) -> None:
        self.default_options = default_options or PlaybackOptions()

    def play_vod(
        self,
        page: Page,
        vod_url: str,
        title: str = "",
        options: PlaybackOptions | None = None,
        on_progress: Callable[[PlaybackProgress], None] | None = None,
    ) -> PlaybackProgress:
        """Navigates to a VOD page, starts playback, maintains session heartbeat, and monitors until completion."""
        opts = options or self.default_options
        progress = PlaybackProgress(vod_url=vod_url, title=title)

        def _on_dialog(dialog: Dialog) -> None:
            logger.info(f"VOD auto-accepting popup: '{dialog.message}'")
            try:
                dialog.accept()
            except Exception as e:
                logger.debug(f"Failed to accept dialog: {e}")

        page.on("dialog", _on_dialog)

        try:
            logger.info(f"Navigating to VOD: {vod_url}")
            page.goto(vod_url, wait_until="domcontentloaded")

            if not progress.title:
                try:
                    page_title = page.title()
                    progress.title = page_title.split("|")[0].strip() if page_title else ""
                except Exception:
                    pass

            # Wait for HTML5 <video> tag
            try:
                page.wait_for_selector("video", timeout=15000)
            except PlaywrightTimeoutError:
                err = "No <video> element found on VOD page (timed out after 15s)"
                logger.error(err)
                progress.error_message = err
                return progress

            # Initialize video: mute audio, set playback rate, and start playback
            init_result = page.evaluate(
                """(opts) => {
                    const v = document.querySelector('video');
                    if (!v) return { ok: false, error: 'video not found' };
                    v.muted = opts.muted;
                    v.playbackRate = opts.playback_rate || 1.0;
                    try {
                        const playPromise = v.play();
                        if (playPromise !== undefined) {
                            playPromise.catch(e => console.log('play error', e));
                        }
                    } catch (e) {
                        console.log('play exception', e);
                    }
                    return {
                        ok: true,
                        duration: v.duration || 0.0,
                        currentTime: v.currentTime || 0.0,
                        paused: v.paused,
                        ended: v.ended
                    };
                }""",
                {"muted": opts.muted, "playback_rate": opts.playback_rate},
            )

            # If still paused, attempt clicking the big play button
            try:
                big_play = page.query_selector(".vjs-big-play-button")
                if big_play and big_play.is_visible():
                    big_play.click(timeout=2000)
            except Exception as e:
                logger.debug(f"Big play button click skipped: {e}")

            start_time = time.monotonic()
            poll_interval = max(0.5, opts.poll_interval_seconds)

            while True:
                # Query video status
                status = page.evaluate(
                    """() => {
                        const v = document.querySelector('video');
                        if (!v) return null;
                        return {
                            duration: v.duration || 0.0,
                            currentTime: v.currentTime || 0.0,
                            paused: v.paused,
                            ended: v.ended
                        };
                    }"""
                )

                if not status:
                    progress.error_message = "Video element disappeared during playback"
                    logger.error(progress.error_message)
                    break

                duration = float(status.get("duration") or 0.0)
                current_time = float(status.get("currentTime") or 0.0)
                is_paused = bool(status.get("paused"))
                is_ended = bool(status.get("ended"))

                progress.duration = duration
                progress.current_time = current_time
                progress.is_paused = is_paused
                progress.progress_percent = (
                    round((current_time / duration) * 100.0, 1) if duration > 0 else 0.0
                )

                if on_progress:
                    try:
                        on_progress(progress)
                    except Exception as e:
                        logger.warning(f"Progress callback error: {e}")

                # Check completion conditions
                is_near_end = duration > 0 and current_time >= max(0.0, duration - 1.5)
                if is_ended or is_near_end:
                    logger.info(f"VOD playback completed: {progress.title} ({current_time:.1f}s / {duration:.1f}s)")
                    progress.is_completed = True
                    progress.progress_percent = 100.0
                    break

                # Max wait timeout safeguard
                elapsed = time.monotonic() - start_time
                if opts.max_wait_seconds and elapsed >= opts.max_wait_seconds:
                    logger.warning(f"VOD max_wait_seconds ({opts.max_wait_seconds}s) exceeded")
                    break

                # Resume playback if accidentally paused (e.g. system sleep or network stutter)
                if is_paused and not is_ended:
                    logger.debug("Video paused in background, resuming playback...")
                    page.evaluate("() => { const v = document.querySelector('video'); if (v) v.play(); }")

                # Wait before next poll
                page.wait_for_timeout(int(poll_interval * 1000))

            # Allow Coursemos final heartbeat ping to dispatch
            if progress.is_completed:
                page.wait_for_timeout(2000)

        except Exception as e:
            logger.error(f"VOD playback failed for {vod_url}: {e}")
            progress.error_message = str(e)
        finally:
            try:
                page.remove_listener("dialog", _on_dialog)
            except Exception:
                pass

        return progress
