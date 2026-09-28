"""Tests for materials domain models and configuration."""

import json
from pathlib import Path
from coursepilot.config import PROJECT_ROOT, Settings
from coursepilot.materials.models import (
    CourseMaterialsResult,
    MaterialDownloadResult,
    MaterialItem,
    MaterialsRunResult,
    MaterialStatus,
)


def test_material_status_enum():
    assert MaterialStatus.DOWNLOADED == "downloaded"
    assert MaterialStatus.SKIPPED == "skipped"
    assert MaterialStatus.VIEWED_ONLY == "viewed_only"
    assert MaterialStatus.FAILED == "failed"
    assert MaterialStatus.PLANNED == "planned"
    assert len(MaterialStatus) == 5


def test_material_item_defaults():
    item = MaterialItem(
        course_id="12345",
        course_name="자료구조",
        week_number=1,
        module_id="8001",
        title="1주차 강의자료.pdf",
        url="https://lxp.kau.ac.kr/mod/ubfile/view.php?id=8001",
    )
    assert item.course_id == "12345"
    assert item.week_number == 1
    assert item.is_completed is False
    assert item.download_url == ""
    assert item.suggested_filename == ""


def test_material_download_result_defaults():
    item = MaterialItem(
        course_id="12345",
        course_name="자료구조",
        week_number=1,
        module_id="8001",
        title="1주차 강의자료.pdf",
        url="https://lxp.kau.ac.kr/mod/ubfile/view.php?id=8001",
    )
    res = MaterialDownloadResult(item=item, status=MaterialStatus.DOWNLOADED)
    assert res.status == MaterialStatus.DOWNLOADED
    assert res.filename == ""
    assert res.saved_path == ""
    assert res.filesize == 0
    assert res.view_success is False
    assert res.error_message is None


def test_materials_run_result_json_serialization():
    item = MaterialItem(
        course_id="12345",
        course_name="자료구조",
        week_number=1,
        module_id="8001",
        title="1주차 강의자료.pdf",
        url="https://lxp.kau.ac.kr/mod/ubfile/view.php?id=8001",
        is_completed=True,
    )
    download_res = MaterialDownloadResult(
        item=item,
        status=MaterialStatus.DOWNLOADED,
        filename="1주차_강의자료.pdf",
        saved_path="downloads/자료구조/W1/1주차_강의자료.pdf",
        filesize=1024,
        view_success=True,
    )
    course_res = CourseMaterialsResult(
        course_id="12345",
        course_name="자료구조",
        target_week="1주차",
        items=[download_res],
    )
    run_res = MaterialsRunResult(
        total_courses=1,
        total_materials=1,
        downloaded_count=1,
        courses=[course_res],
    )

    json_str = run_res.model_dump_json()
    data = json.loads(json_str)
    assert data["total_courses"] == 1
    assert data["downloaded_count"] == 1
    assert len(data["courses"]) == 1
    assert data["courses"][0]["items"][0]["filename"] == "1주차_강의자료.pdf"
    assert data["courses"][0]["items"][0]["status"] == "downloaded"


def test_settings_download_dir():
    settings = Settings(_env_file=None)
    assert settings.download_dir == PROJECT_ROOT / "downloads"
    custom_settings = Settings(download_dir=Path("custom/path"), _env_file=None)
    assert custom_settings.download_dir == PROJECT_ROOT / "custom/path"
    assert "download_dir=WindowsPath('custom/path')" in repr(custom_settings) or "custom/path" in repr(custom_settings)
