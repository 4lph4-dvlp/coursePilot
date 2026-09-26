"""Unit tests for materials downloader module."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import httpx
import pytest

from coursepilot.config import Settings
from coursepilot.materials.downloader import (
    download_material_file,
    get_authenticated_httpx_client,
    mark_material_viewed,
)
from coursepilot.materials.models import MaterialItem


@pytest.fixture
def sample_item() -> MaterialItem:
    return MaterialItem(
        course_id="101",
        course_name="자료구조",
        week_number=1,
        module_id="8001",
        title="1주차 강의자료.pdf",
        url="https://lxp.kau.ac.kr/mod/ubfile/view.php?id=8001",
    )


def test_mark_material_viewed_success(sample_item):
    mock_client = MagicMock(spec=httpx.Client)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_client.get.return_value = mock_resp

    result = mark_material_viewed(mock_client, sample_item)
    assert result is True
    mock_client.get.assert_called_once_with(sample_item.url)


def test_mark_material_viewed_failure(sample_item):
    mock_client = MagicMock(spec=httpx.Client)
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_client.get.return_value = mock_resp

    result = mark_material_viewed(mock_client, sample_item)
    assert result is False


def test_download_material_file_direct_binary(tmp_path: Path, sample_item):
    mock_client = MagicMock(spec=httpx.Client)
    mock_response = MagicMock()
    mock_response.url = "https://lxp.kau.ac.kr/pluginfile.php/123/mod_ubfile/content/1/lecture.pdf"
    mock_response.headers = {
        "content-type": "application/pdf",
        "content-disposition": 'attachment; filename="lecture.pdf"',
        "content-length": "12",
    }
    mock_response.iter_bytes.return_value = [b"hello ", b"world!"]
    mock_response.raise_for_status.return_value = None

    # Context manager for client.stream
    mock_client.stream.return_value.__enter__.return_value = mock_response

    target_dir = tmp_path / "자료구조" / "W1"
    saved_path, size, is_skipped = download_material_file(mock_client, sample_item, target_dir)

    assert saved_path == target_dir / "lecture.pdf"
    assert saved_path.exists()
    assert saved_path.read_bytes() == b"hello world!"
    assert size == 12
    assert is_skipped is False


def test_download_material_file_skip_duplicate(tmp_path: Path, sample_item):
    mock_client = MagicMock(spec=httpx.Client)
    target_dir = tmp_path / "자료구조" / "W1"
    target_dir.mkdir(parents=True, exist_ok=True)
    existing_file = target_dir / "lecture.pdf"
    existing_file.write_bytes(b"1234567890")

    mock_response = MagicMock()
    mock_response.url = "https://lxp.kau.ac.kr/pluginfile.php/123/mod_ubfile/content/1/lecture.pdf"
    mock_response.headers = {
        "content-type": "application/pdf",
        "content-disposition": 'attachment; filename="lecture.pdf"',
        "content-length": "10",
    }
    mock_response.raise_for_status.return_value = None
    mock_client.stream.return_value.__enter__.return_value = mock_response

    saved_path, size, is_skipped = download_material_file(mock_client, sample_item, target_dir)

    assert saved_path == existing_file
    assert size == 10
    assert is_skipped is True
    # iter_bytes should not be called when skipped
    mock_response.iter_bytes.assert_not_called()


def test_download_material_file_overwrite_different_size(tmp_path: Path, sample_item):
    mock_client = MagicMock(spec=httpx.Client)
    target_dir = tmp_path / "자료구조" / "W1"
    target_dir.mkdir(parents=True, exist_ok=True)
    existing_file = target_dir / "lecture.pdf"
    existing_file.write_bytes(b"old")  # length 3 != 10

    mock_response = MagicMock()
    mock_response.url = "https://lxp.kau.ac.kr/pluginfile.php/123/mod_ubfile/content/1/lecture.pdf"
    mock_response.headers = {
        "content-type": "application/pdf",
        "content-disposition": 'attachment; filename="lecture.pdf"',
        "content-length": "10",
    }
    mock_response.iter_bytes.return_value = [b"0123456789"]
    mock_response.raise_for_status.return_value = None
    mock_client.stream.return_value.__enter__.return_value = mock_response

    saved_path, size, is_skipped = download_material_file(mock_client, sample_item, target_dir)

    assert saved_path == existing_file
    assert size == 10
    assert is_skipped is False
    assert saved_path.read_bytes() == b"0123456789"


def test_download_material_file_embedded_html_viewer(tmp_path: Path, sample_item):
    mock_client = MagicMock(spec=httpx.Client)

    # First call: HTML page with iframe
    html_content = '<iframe src="https://lxp.kau.ac.kr/pluginfile.php/456/slides.pdf"></iframe>'
    resp_html = MagicMock()
    resp_html.url = "https://lxp.kau.ac.kr/mod/ubfile/view.php?id=8001"
    resp_html.headers = {"content-type": "text/html; charset=utf-8"}
    resp_html.read.return_value = html_content.encode("utf-8")
    resp_html.raise_for_status.return_value = None

    # Second call: Binary stream
    resp_bin = MagicMock()
    resp_bin.url = "https://lxp.kau.ac.kr/pluginfile.php/456/slides.pdf"
    resp_bin.headers = {
        "content-type": "application/pdf",
        "content-disposition": 'attachment; filename="slides.pdf"',
        "content-length": "6",
    }
    resp_bin.iter_bytes.return_value = [b"slides"]
    resp_bin.raise_for_status.return_value = None

    cm_html = MagicMock()
    cm_html.__enter__.return_value = resp_html
    cm_bin = MagicMock()
    cm_bin.__enter__.return_value = resp_bin

    mock_client.stream.side_effect = [cm_html, cm_bin]

    target_dir = tmp_path / "자료구조" / "W1"
    saved_path, size, is_skipped = download_material_file(mock_client, sample_item, target_dir)

    assert saved_path.name == "slides.pdf"
    assert is_skipped is False
    assert mock_client.stream.call_count == 2


def test_download_material_file_cleanup_on_error(tmp_path: Path, sample_item):
    mock_client = MagicMock(spec=httpx.Client)
    mock_response = MagicMock()
    mock_response.url = "https://lxp.kau.ac.kr/pluginfile.php/123/mod_ubfile/content/1/lecture.pdf"
    mock_response.headers = {
        "content-type": "application/pdf",
        "content-disposition": 'attachment; filename="lecture.pdf"',
        "content-length": "100",
    }
    mock_response.iter_bytes.side_effect = IOError("Network drop")
    mock_response.raise_for_status.return_value = None
    mock_client.stream.return_value.__enter__.return_value = mock_response

    target_dir = tmp_path / "자료구조" / "W1"
    with pytest.raises(IOError, match="Network drop"):
        download_material_file(mock_client, sample_item, target_dir)

    # .tmp file must be cleaned up
    tmp_files = list(target_dir.glob("*.tmp"))
    assert len(tmp_files) == 0


def test_get_authenticated_httpx_client(tmp_path: Path):
    cache_file = tmp_path / "session.json"
    cache_file.write_text(
        json.dumps({
            "cookies": [
                {"name": "MoodleSession", "value": "test_moodle_session_val"},
                {"name": "OTHER", "value": "xyz"},
            ]
        }),
        encoding="utf-8",
    )

    settings = Settings(session_cache_path=cache_file, lms_url="https://lxp.kau.ac.kr")
    client = get_authenticated_httpx_client(settings)

    assert client.cookies.get("MoodleSession") == "test_moodle_session_val"
    assert client.headers["referer"] == "https://lxp.kau.ac.kr"
