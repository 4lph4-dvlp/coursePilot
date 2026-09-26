"""Unit tests for materials runner module."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import httpx
import pytest

from coursepilot.config import Settings
from coursepilot.materials.models import MaterialItem, MaterialStatus
from coursepilot.materials.runner import (
    process_course_materials,
    resolve_candidate_materials,
    run_materials_pipeline,
)
from coursepilot.scraper.models import CourseItem


@pytest.fixture
def sample_course() -> CourseItem:
    return CourseItem(
        course_id="101",
        raw_name="자료구조 (001)",
        clean_name="자료구조",
        url="https://lxp.kau.ac.kr/course/view.php?id=101",
    )


@pytest.fixture
def sample_materials() -> list[MaterialItem]:
    return [
        MaterialItem(
            course_id="101",
            course_name="자료구조",
            week_number=1,
            module_id="8001",
            title="1주차 자료1.pdf",
            url="https://lxp.kau.ac.kr/mod/ubfile/view.php?id=8001",
            is_completed=True,
        ),
        MaterialItem(
            course_id="101",
            course_name="자료구조",
            week_number=1,
            module_id="8002",
            title="1주차 자료2.zip",
            url="https://lxp.kau.ac.kr/mod/resource/view.php?id=8002",
            is_completed=False,
        ),
        MaterialItem(
            course_id="101",
            course_name="자료구조",
            week_number=2,
            module_id="8003",
            title="2주차 자료1.hwp",
            url="https://lxp.kau.ac.kr/mod/ubfile/view.php?id=8003",
            is_completed=False,
        ),
    ]


def test_resolve_candidate_materials_empty():
    label, items = resolve_candidate_materials([])
    assert label == "none"
    assert items == []


def test_resolve_candidate_materials_all(sample_materials):
    label, items = resolve_candidate_materials(sample_materials, week_query="all")
    assert label == "전체 주차"
    assert len(items) == 3


def test_resolve_candidate_materials_specific_week(sample_materials):
    label, items = resolve_candidate_materials(sample_materials, week_query="2")
    assert label == "2주차"
    assert len(items) == 1
    assert items[0].module_id == "8003"


def test_resolve_candidate_materials_current_incomplete(sample_materials):
    label, items = resolve_candidate_materials(sample_materials, week_query="current")
    # Earliest incomplete week is week 1 (8002 is incomplete)
    assert label == "1주차"
    assert len(items) == 2


def test_resolve_candidate_materials_current_all_completed(sample_materials):
    for m in sample_materials:
        m.is_completed = True
    label, items = resolve_candidate_materials(sample_materials, week_query="current")
    assert label == "2주차 (완료)"
    assert len(items) == 1
    assert items[0].module_id == "8003"


@patch("coursepilot.materials.runner.download_material_file")
@patch("coursepilot.materials.runner.mark_material_viewed")
def test_process_course_materials_normal(
    mock_mark_viewed,
    mock_download,
    tmp_path: Path,
    sample_course,
    sample_materials,
):
    mock_mark_viewed.return_value = True
    mock_download.return_value = (tmp_path / "saved.pdf", 1024, False)
    mock_client = MagicMock(spec=httpx.Client)

    res = process_course_materials(
        course=sample_course,
        materials=sample_materials,
        target_week="1주차",
        output_root=tmp_path,
        client=mock_client,
        dry_run=False,
        no_download=False,
    )

    assert res.course_id == "101"
    assert res.course_name == "자료구조"
    assert len(res.items) == 3
    # First item is already completed, mark_material_viewed not called for it
    # Second and third are uncompleted, mark_material_viewed called
    assert mock_mark_viewed.call_count == 2
    # download called for all 3
    assert mock_download.call_count == 3
    assert res.items[0].status == MaterialStatus.DOWNLOADED


@patch("coursepilot.materials.runner.download_material_file")
@patch("coursepilot.materials.runner.mark_material_viewed")
def test_process_course_materials_no_download(
    mock_mark_viewed,
    mock_download,
    tmp_path: Path,
    sample_course,
    sample_materials,
):
    mock_mark_viewed.return_value = True
    mock_client = MagicMock(spec=httpx.Client)

    res = process_course_materials(
        course=sample_course,
        materials=sample_materials,
        target_week="1주차",
        output_root=tmp_path,
        client=mock_client,
        dry_run=False,
        no_download=True,
    )

    assert len(res.items) == 3
    for it in res.items:
        assert it.status == MaterialStatus.VIEWED_ONLY
    mock_download.assert_not_called()


def test_process_course_materials_dry_run(tmp_path: Path, sample_course, sample_materials):
    res = process_course_materials(
        course=sample_course,
        materials=sample_materials,
        target_week="1주차",
        output_root=tmp_path,
        client=None,
        dry_run=True,
        no_download=False,
    )

    assert len(res.items) == 3
    assert res.items[0].status == MaterialStatus.DOWNLOADED
    assert "downloads" not in res.items[0].saved_path or str(tmp_path) in res.items[0].saved_path


@patch("coursepilot.materials.runner.download_material_file")
@patch("coursepilot.materials.runner.mark_material_viewed")
def test_process_course_materials_error_isolation(
    mock_mark_viewed,
    mock_download,
    tmp_path: Path,
    sample_course,
    sample_materials,
):
    mock_mark_viewed.return_value = True
    # First download raises error, second succeeds
    mock_download.side_effect = [
        IOError("Network error"),
        (tmp_path / "item2.zip", 2048, False),
        (tmp_path / "item3.hwp", 4096, False),
    ]
    mock_client = MagicMock(spec=httpx.Client)

    res = process_course_materials(
        course=sample_course,
        materials=sample_materials,
        target_week="1주차",
        output_root=tmp_path,
        client=mock_client,
    )

    assert res.items[0].status == MaterialStatus.FAILED
    assert res.items[0].error_message == "Network error"
    assert res.items[1].status == MaterialStatus.DOWNLOADED
    assert res.items[2].status == MaterialStatus.DOWNLOADED


@patch("coursepilot.materials.runner.SessionManager")
@patch("coursepilot.materials.runner.CourseNavigator")
@patch("coursepilot.materials.runner.extract_courses")
@patch("coursepilot.materials.runner.parse_materials_from_course_sections")
def test_run_materials_pipeline_dry_run(
    mock_parse_materials,
    mock_extract_courses,
    mock_navigator_cls,
    mock_session_mgr_cls,
    tmp_path: Path,
    sample_course,
    sample_materials,
):
    mock_sm = MagicMock()
    mock_session_mgr_cls.return_value.__enter__.return_value = mock_sm
    mock_page = MagicMock()
    mock_sm.get_authenticated_page.return_value = mock_page

    mock_extract_courses.return_value = [sample_course]
    mock_parse_materials.return_value = sample_materials

    result = run_materials_pipeline(
        course_query="자료구조",
        week_query="1",
        output_dir=tmp_path,
        dry_run=True,
    )

    assert result.total_courses == 1
    assert result.total_materials == 2
    assert result.dry_run is True
    assert len(result.courses) == 1
    assert result.courses[0].course_name == "자료구조"
