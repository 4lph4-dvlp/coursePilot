"""Playwright hybrid stream sniffer intercepting network responses with DOM probe fallback."""

from __future__ import annotations

import logging
import threading
from typing import Callable, Optional

from playwright.sync_api import Page, Response

logger = logging.getLogger(__name__)


class StreamSniffer:
    """Detects M3U8 and direct MP4 stream URLs via Playwright page network responses and DOM inspection."""

    def __init__(
        self,
        on_stream_detected: Optional[Callable[[str], None]] = None,
        timeout: float = 15.0,
    ) -> None:
        self.on_stream_detected = on_stream_detected
        self.timeout = timeout
        self.detected_url: Optional[str] = None
        self._event = threading.Event()
        self._listener: Optional[Callable[[Response], None]] = None
        self._attached_page: Optional[Page] = None

    def attach(self, page: Page) -> None:
        """Attach network response listener to page."""
        self.detach(self._attached_page) if self._attached_page else None
        self._attached_page = page

        def _on_response(response: Response) -> None:
            url = response.url
            content_type = response.headers.get("content-type", "")

            # Check for M3U8 manifest or direct MP4 media stream
            is_m3u8 = ".m3u8" in url or content_type.startswith("application/vnd.apple.mpegurl")
            is_mp4 = (
                ".mp4" in url
                and "blob:" not in url
                and not url.lower().endswith((".js", ".css", ".png", ".jpg", ".jpeg", ".ico"))
            )

            if (is_m3u8 or is_mp4) and not self._event.is_set():
                logger.info("Stream URL detected via network response: %s", url)
                self.detected_url = url
                self._event.set()
                if self.on_stream_detected:
                    try:
                        self.on_stream_detected(url)
                    except Exception as e:
                        logger.warning("Error in on_stream_detected callback: %s", e)

        self._listener = _on_response
        page.on("response", _on_response)

    def detach(self, page: Optional[Page] = None) -> None:
        """Detach network response listener from page."""
        target_page = page or self._attached_page
        if target_page and self._listener:
            try:
                target_page.remove_listener("response", self._listener)
            except Exception as e:
                logger.debug("Failed to remove response listener: %s", e)
        self._listener = None
        if target_page == self._attached_page:
            self._attached_page = None

    def wait_for_stream(self, page: Page, timeout: Optional[float] = None) -> Optional[str]:
        """Wait for stream URL to be detected, falling back to probing the DOM video element."""
        wait_time = timeout if timeout is not None else self.timeout
        if self._event.wait(timeout=wait_time) and self.detected_url:
            return self.detected_url

        # Fallback DOM probe (Decision D-14-13)
        try:
            dom_src = page.evaluate(
                "() => { const v = document.querySelector('video'); return v ? (v.currentSrc || v.src) : null; }"
            )
            if dom_src and not str(dom_src).startswith("blob:"):
                logger.info("Stream URL detected via DOM probe fallback: %s", dom_src)
                self.detected_url = str(dom_src)
                self._event.set()
                if self.on_stream_detected:
                    try:
                        self.on_stream_detected(self.detected_url)
                    except Exception as e:
                        logger.warning("Error in on_stream_detected callback: %s", e)
                return self.detected_url
        except Exception as e:
            logger.debug("DOM probe failed during wait_for_stream: %s", e)

        return self.detected_url

    def __enter__(self) -> StreamSniffer:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._attached_page:
            self.detach(self._attached_page)
