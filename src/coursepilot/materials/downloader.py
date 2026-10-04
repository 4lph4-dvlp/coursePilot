"""Cookie-authenticated HTTP client and streaming file downloader with atomic write."""

import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlsplit
import httpx
from bs4 import BeautifulSoup
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from coursepilot.config import Settings
from coursepilot.materials.filename_utils import resolve_filename, sanitize_filename
from coursepilot.materials.models import MaterialItem
from coursepilot.scraper.material_parser import extract_pluginfile_url
from coursepilot.session_manager import SessionManager


class ViewOnlyMaterialError(ValueError):
    """The LMS exposes a protected viewer without an accessible download."""


def get_authenticated_httpx_client(
    settings: Settings,
    session_manager: SessionManager | None = None,
) -> httpx.Client:
    """Extracts session cookies from cache or active SessionManager and creates an httpx.Client."""
    cookies: dict[str, str] = {}
    cache_path = settings.session_cache_path

    if cache_path.exists():
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for cookie in data.get("cookies", []):
                    cookies[cookie["name"]] = cookie["value"]
        except Exception:
            cookies = {}

    if not cookies or "MoodleSession" not in cookies:
        sm = session_manager or SessionManager(settings=settings)
        with sm:
            page = sm.get_authenticated_page()
            for cookie in page.context.cookies():
                cookies[cookie["name"]] = cookie["value"]

    return httpx.Client(
        cookies=cookies,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ),
            "Referer": settings.lms_url,
        },
        follow_redirects=True,
        timeout=30.0,
    )


def mark_material_viewed(client: httpx.Client, item: MaterialItem) -> bool:
    """Performs authenticated HTTP GET to item.url to trigger Coursemos view completion (RES-01)."""
    try:
        response = client.get(item.url)
        return 200 <= response.status_code < 400
    except Exception:
        return False


def download_material_file(
    client: httpx.Client,
    item: MaterialItem,
    target_dir: Path,
    chunk_size: int = 65536,
) -> tuple[Path, int, bool]:
    """Streams and saves material file to target_dir with atomic rename and duplicate skipping.

    Returns:
        tuple[Path, int, bool]: (saved_path, filesize, is_skipped)
    """
    req_url = item.download_url or item.url

    with client.stream("GET", req_url) as response:
        response.raise_for_status()

        # Handle embedded HTML viewer pages
        content_type = response.headers.get("content-type", "")
        if "text/html" in content_type:
            html = response.read().decode("utf-8", errors="replace")
            real_url = extract_pluginfile_url(html, base_url=str(response.url))
            if real_url:
                updated_item = item.model_copy(update={"download_url": real_url})
                return download_material_file(
                    client, updated_item, target_dir, chunk_size=chunk_size
                )
            viewer = BeautifulSoup(html, "lxml").find(
                "a", href=re.compile(r"/mod/ubfile/viewer\.php(?:\?|$)", re.I)
            )
            if viewer and viewer.get("href"):
                viewer_url = urljoin(str(response.url), viewer["href"])
                viewer_response = client.get(viewer_url)
                viewer_response.raise_for_status()
                viewer_type = viewer_response.headers.get("content-type", "")
                if "text/html" in viewer_type:
                    nested_url = extract_pluginfile_url(
                        viewer_response.text, base_url=str(viewer_response.url)
                    )
                    if nested_url:
                        updated_item = item.model_copy(update={"download_url": nested_url})
                        return download_material_file(
                            client, updated_item, target_dir, chunk_size=chunk_size
                        )
                if urlsplit(str(viewer_response.url)).path.rstrip("/") == "/local/csmsdoc":
                    raise ViewOnlyMaterialError(
                        "LMS 문서 뷰어의 다운로드 버튼은 브라우저에서 확인해야 합니다."
                    )
            raise ValueError(f"Could not locate download link in HTML viewer: {item.url}")

        # Resolve filename
        content_disposition = response.headers.get("content-disposition")
        resolved_name = resolve_filename(
            content_disposition=content_disposition,
            url=str(response.url),
            default_name=item.title,
            content_type=content_type,
        )
        safe_name = sanitize_filename(resolved_name)
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / safe_name

        content_length = response.headers.get("content-length")
        expected_bytes = (
            int(content_length) if (content_length and content_length.isdigit()) else None
        )

        # Duplicate check (D-13-02): same name and matching size -> skip download
        if target_path.exists() and expected_bytes is not None:
            local_size = target_path.stat().st_size
            if local_size == expected_bytes:
                return (target_path, local_size, True)

        # Atomic streaming write via .tmp
        temp_path = target_path.with_suffix(target_path.suffix + ".tmp")
        downloaded_bytes = 0
        try:
            with open(temp_path, "wb") as f:
                for chunk in response.iter_bytes(chunk_size=chunk_size):
                    f.write(chunk)
                    downloaded_bytes += len(chunk)

            if expected_bytes is not None and downloaded_bytes != expected_bytes:
                raise IOError(
                    f"Byte mismatch: expected {expected_bytes}, received {downloaded_bytes}"
                )

            temp_path.replace(target_path)
            return (target_path, downloaded_bytes, False)
        except Exception:
            temp_path.unlink(missing_ok=True)
            raise


def download_material_via_browser(
    page: Page,
    item: MaterialItem,
    target_dir: Path,
) -> tuple[Path, int, bool]:
    """Use the authenticated document viewer's download button for CSMSDoc files."""
    viewer_page = page.context.new_page()
    try:
        viewer_page.goto(item.url, wait_until="domcontentloaded")
        button = viewer_page.locator('button[aria-label="파일 다운로드"]')
        if not button.count():
            viewer_link = viewer_page.locator('a[href*="/mod/ubfile/viewer.php"]')
            if not viewer_link.count():
                raise ViewOnlyMaterialError("LMS 문서 뷰어의 다운로드 버튼을 찾을 수 없습니다.")
            viewer_url = urljoin(viewer_page.url, viewer_link.first.get_attribute("href"))
            viewer_page.goto(viewer_url, wait_until="domcontentloaded")
            button = viewer_page.locator('button[aria-label="파일 다운로드"]')
        try:
            button.first.wait_for(timeout=15000)
        except PlaywrightTimeoutError as exc:
            raise ViewOnlyMaterialError("LMS 문서 뷰어의 다운로드 버튼을 찾을 수 없습니다.") from exc

        with viewer_page.expect_download(timeout=30000) as download_info:
            button.first.click()
        download = download_info.value
        if failure := download.failure():
            raise IOError(f"LMS 문서 다운로드 실패: {failure}")

        safe_name = sanitize_filename(download.suggested_filename or item.title)
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / safe_name
        temp_path = target_path.with_suffix(target_path.suffix + ".tmp")
        try:
            download.save_as(temp_path)
            downloaded_bytes = temp_path.stat().st_size
            if downloaded_bytes == 0:
                raise IOError("LMS 문서 다운로드 결과가 비어 있습니다.")
            if target_path.exists() and target_path.stat().st_size == downloaded_bytes:
                return target_path, downloaded_bytes, True
            temp_path.replace(target_path)
            return target_path, downloaded_bytes, False
        finally:
            temp_path.unlink(missing_ok=True)
    finally:
        viewer_page.close()
