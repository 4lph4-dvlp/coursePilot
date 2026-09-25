"""Coursemos Video.js VOD player automation engine with stall resilience and session recovery."""

from __future__ import annotations

import logging
import time
from typing import Callable

from playwright.sync_api import Dialog, Page, TimeoutError as PlaywrightTimeoutError

from kau_assistant.player.models import PlaybackOptions, PlaybackProgress
from kau_assistant.session_manager import SessionManager

logger = logging.getLogger(__name__)


class VodPlayer:
    """Controls Coursemos Video.js video playback in background, maintaining attendance heartbeats."""

    def __init__(
        self,
        default_options: PlaybackOptions | None = None,
        session_manager: SessionManager | None = None,
    ) -> None:
        self.default_options = default_options or PlaybackOptions()
        self.session_manager = session_manager

    def _init_video(self, page: Page, opts: PlaybackOptions) -> dict | None:
        """Initializes video element: mute audio, enforce 1.0x rate (D-12-01), and trigger play."""
        init_result = page.evaluate(
            """(opts) => {
                const v = document.querySelector('video');
                if (!v) return { ok: false, error: 'video not found' };
                v.muted = opts.muted;
                v.playbackRate = 1.0;
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
            {"muted": opts.muted, "playback_rate": 1.0},
        )

        try:
            big_play = page.query_selector(".vjs-big-play-button")
            if big_play and big_play.is_visible():
                big_play.click(timeout=2000)
        except Exception as e:
            logger.debug(f"Big play button click skipped: {e}")

        return init_result

    def play_vod(
        self,
        page: Page,
        vod_url: str,
        title: str = "",
        options: PlaybackOptions | None = None,
        session_manager: SessionManager | None = None,
        on_progress: Callable[[PlaybackProgress], None] | None = None,
    ) -> PlaybackProgress:
        """Navigates to a VOD page, starts playback, maintains session heartbeat, and monitors until completion."""
        opts = options or self.default_options
        # Enforce 1.0x playback rate (D-12-01)
        if opts.playback_rate != 1.0:
            logger.warning(
                f"Forcing playback_rate to 1.0x (requested {opts.playback_rate}x) to protect attendance integrity (D-12-01)"
            )
            opts = opts.model_copy(update={"playback_rate": 1.0})

        mgr = session_manager or self.session_manager
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

            # Initialize video
            self._init_video(page, opts)

            start_time = time.monotonic()
            last_progress_time = time.monotonic()
            last_current_time = 0.0
            stall_retry_count = 0
            poll_interval = max(0.5, opts.poll_interval_seconds)

            while True:
                # Check for session redirect (D-12-11)
                current_url = page.url.lower() if page.url else ""
                if "/login/" in current_url or "/user/login.php" in current_url:
                    logger.warning(
                        f"Detected Moodle session expiry redirect ({page.url}). Attempting re-authentication (D-12-11)..."
                    )
                    active_mgr = mgr or SessionManager()
                    active_mgr.ensure_authenticated(page)
                    logger.info(f"Re-authenticated. Re-navigating to VOD: {vod_url}")
                    page.goto(vod_url, wait_until="domcontentloaded")
                    try:
                        page.wait_for_selector("video", timeout=15000)
                    except Exception as e:
                        logger.error(f"Failed to find video tag after session renewal: {e}")
                        progress.error_message = "Video element not found after re-authentication"
                        break
                    self._init_video(page, opts)
                    last_progress_time = time.monotonic()
                    last_current_time = 0.0
                    stall_retry_count = 0
                    continue

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

                # Check completion conditions (D-12-10 DOM currentTime ground truth)
                is_near_end = duration > 0 and current_time >= max(0.0, duration - 1.5)
                if is_ended or is_near_end:
                    logger.info(f"VOD playback completed: {progress.title} ({current_time:.1f}s / {duration:.1f}s)")
                    progress.is_completed = True
                    progress.progress_percent = 100.0
                    break

                # Stall detection & recovery (D-12-09)
                if current_time > last_current_time:
                    last_current_time = current_time
                    last_progress_time = time.monotonic()
                    stall_retry_count = 0
                else:
                    stalled_duration = time.monotonic() - last_progress_time
                    if stalled_duration >= 15.0 and not is_near_end and not is_ended:
                        logger.warning(
                            f"Playback stall detected: currentTime ({current_time:.1f}s) stalled for {stalled_duration:.1f}s"
                        )
                        if stall_retry_count < 3:
                            stall_retry_count += 1
                            logger.info(f"Stall recovery retry {stall_retry_count}/3: dispatching video.play()...")
                            page.evaluate("() => { const v = document.querySelector('video'); if (v) v.play(); }")
                            page.wait_for_timeout(2000)
                            last_progress_time = time.monotonic()
                        else:
                            logger.warning("3 play retries failed to resume stalled video. Reloading page (D-12-09)...")
                            page.reload(wait_until="domcontentloaded")
                            try:
                                page.wait_for_selector("video", timeout=15000)
                            except Exception as e:
                                logger.error(f"Video not found after page reload: {e}")
                                progress.error_message = "Video not found after reload"
                                break
                            self._init_video(page, opts)
                            stall_retry_count = 0
                            last_progress_time = time.monotonic()

                # Sleep recovery & max wait safeguard (D-12-10)
                if opts.max_wait_seconds:
                    elapsed = time.monotonic() - start_time
                    if elapsed >= opts.max_wait_seconds:
                        if duration > 0 and current_time < max(0.0, duration - 1.5) and not is_paused:
                            # Monotonic time jumped due to sleep/wake, but video is actively playing
                            logger.info("Monotonic elapsed jumped (possible sleep/wake); resetting start_time.")
                            start_time = time.monotonic() - current_time
                        else:
                            logger.warning(f"VOD max_wait_seconds ({opts.max_wait_seconds}s) exceeded")
                            break

                # Resume playback if paused in background (e.g. system sleep/wake event D-12-10)
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
