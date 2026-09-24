"""Unit and integration tests for watch runner and CLI watch command."""

import json
from unittest.mock import MagicMock
import pytest
from click.testing import CliRunner

from kau_assistant.cli import cli
from kau_assistant.config import Settings
from kau_assistant.player.models import PlaybackProgress
from kau_assistant.player.runner import (
    WatchResult,
    find_target_course,
    resolve_candidate_vods,
    watch_course_vods,
)
from kau_assistant.player.vod_player import VodPlayer
from kau_assistant.scraper.models import AttendanceStatus, CourseItem, LectureItem


@pytest.fixture
def sample_courses():
    return [
        CourseItem(course_id="1113", clean_name="디지털시스템설계", raw_name="디지털시스템설계(01분반)", url="https://lxp.kau.ac.kr/course/view.php?id=1113"),
        CourseItem(course_id="1103", clean_name="기초전자실험", raw_name="기초전자실험(02분반)", url="https://lxp.kau.ac.kr/course/view.php?id=1103"),
    ]


def test_find_target_course(sample_courses):
    mappings = {"디지털시스템설계": "디시설", "기초전자실험": "기전실"}
    
    # 1. Exact match
    c1 = find_target_course(sample_courses, "기초전자실험", mappings)
    assert c1 is not None and c1.course_id == "1103"

    # 2. Abbr match
    c2 = find_target_course(sample_courses, "디시설", mappings)
    assert c2 is not None and c2.course_id == "1113"

    # 3. Substring match
    c3 = find_target_course(sample_courses, "전자실험", mappings)
    assert c3 is not None and c3.course_id == "1103"

    # 4. Unknown
    c4 = find_target_course(sample_courses, "우주물리학", mappings)
    assert c4 is None


def test_resolve_candidate_vods():
    lectures = [
        LectureItem(course_id="1", week_number=0, clip_number=1, title="OT 안내 영상", full_title="OT", link="https://lxp.kau.ac.kr/mod/vod/view.php?id=1", status=AttendanceStatus.INCOMPLETE),
        LectureItem(course_id="1", week_number=1, clip_number=1, title="1주차 1차시", full_title="1-1", link="https://lxp.kau.ac.kr/mod/vod/view.php?id=2", status=AttendanceStatus.COMPLETED),
        LectureItem(course_id="1", week_number=2, clip_number=1, title="2주차 1차시", full_title="2-1", link="https://lxp.kau.ac.kr/mod/vod/view.php?id=3", status=AttendanceStatus.INCOMPLETE),
        LectureItem(course_id="1", week_number=2, clip_number=2, title="2주차 2차시", full_title="2-2", link="https://lxp.kau.ac.kr/mod/vod/view.php?id=4", status=AttendanceStatus.INCOMPLETE),
        LectureItem(course_id="1", week_number=3, clip_number=1, title="3주차 1차시", full_title="3-1", link="https://lxp.kau.ac.kr/mod/vod/view.php?id=5", status=AttendanceStatus.INCOMPLETE),
    ]

    # "current" week should pick week 2 (earliest incomplete regular week)
    label, vods, skipped = resolve_candidate_vods(lectures, "current")
    assert label == "2주차"
    assert len(vods) == 2
    assert [v.clip_number for v in vods] == [1, 2]

    # specific week "3"
    label3, vods3, skipped3 = resolve_candidate_vods(lectures, "3")
    assert label3 == "3주차"
    assert len(vods3) == 1

    # week "all"
    label_all, vods_all, skipped_all = resolve_candidate_vods(lectures, "all")
    assert label_all == "전체 주차"
    assert len(vods_all) == 3  # weeks 2 (2) + 3 (1)
    assert skipped_all == 1   # week 1 was completed


def test_watch_course_vods_dry_run(monkeypatch, sample_courses):
    settings = Settings(lms_username="test", lms_password="pwd")
    mock_session = MagicMock()
    mock_page = MagicMock()
    mock_session.get_authenticated_page.return_value = mock_page

    monkeypatch.setattr("kau_assistant.player.runner.extract_courses", lambda page, url: sample_courses)
    
    lectures = [
        LectureItem(course_id="1113", week_number=4, clip_number=1, title="4주차 1차시", full_title="[디시설] 4주차 1차시", link="https://lxp.kau.ac.kr/mod/vod/view.php?id=10", status=AttendanceStatus.INCOMPLETE)
    ]
    monkeypatch.setattr("kau_assistant.player.runner.scrape_course", lambda page, course, nav: (lectures, []))

    mock_player = MagicMock()
    result = watch_course_vods(
        settings=settings,
        course_query="디시설",
        week_query="4",
        dry_run=True,
        player=mock_player,
        session_manager=mock_session,
    )

    assert result.dry_run is True
    assert result.course_name == "디지털시스템설계"
    assert result.target_week == "4주차"
    assert result.total_vods == 1
    assert mock_player.play_vod.call_count == 0


def test_watch_course_vods_playback_and_notion_update(monkeypatch, sample_courses):
    settings = Settings(
        lms_username="test",
        lms_password="pwd",
        notion_token="test_token",
        notion_database_id="db_id",
    )
    mock_session = MagicMock()
    mock_page = MagicMock()
    mock_session.get_authenticated_page.return_value = mock_page

    monkeypatch.setattr("kau_assistant.player.runner.extract_courses", lambda page, url: sample_courses)
    
    lectures = [
        LectureItem(course_id="1113", week_number=4, clip_number=1, title="4주차 1차시", full_title="[디시설] 4주차 1차시", link="https://lxp.kau.ac.kr/mod/vod/view.php?id=10", status=AttendanceStatus.INCOMPLETE)
    ]
    monkeypatch.setattr("kau_assistant.player.runner.scrape_course", lambda page, course, nav: (lectures, []))

    mock_player = MagicMock()
    mock_player.play_vod.return_value = PlaybackProgress(
        vod_url="https://lxp.kau.ac.kr/mod/vod/view.php?id=10",
        title="4주차 1차시",
        duration=60.0,
        current_time=60.0,
        progress_percent=100.0,
        is_completed=True,
    )

    mock_notion_client = MagicMock()
    mock_notion_page = MagicMock()
    mock_notion_page.page_id = "page_123"
    
    # Task title: "[디시설] 4주차 1차시 강의 시청"
    mock_notion_client.query_existing_pages.return_value = {
        "[디시설] 4주차 1차시 강의 시청": mock_notion_page
    }
    monkeypatch.setattr("kau_assistant.player.runner.NotionClient", lambda settings: mock_notion_client)

    result = watch_course_vods(
        settings=settings,
        course_query="디시설",
        week_query="4",
        dry_run=False,
        update_notion=True,
        player=mock_player,
        session_manager=mock_session,
    )

    assert result.completed_vods == 1
    assert mock_player.play_vod.call_count == 1
    assert result.notion_updated_count == 1
    mock_notion_client.mark_task_completed.assert_called_once_with("page_123")


def test_cli_watch_command_dry_run_json(monkeypatch, sample_courses):
    monkeypatch.setattr("kau_assistant.player.runner.extract_courses", lambda page, url: sample_courses)
    lectures = [
        LectureItem(course_id="1103", week_number=3, clip_number=1, title="W03 실험 강의", full_title="[기초전자실험] W03 실험 강의", link="https://lxp.kau.ac.kr/mod/vod/view.php?id=20", status=AttendanceStatus.INCOMPLETE)
    ]
    monkeypatch.setattr("kau_assistant.player.runner.scrape_course", lambda page, course, nav: (lectures, []))
    
    mock_session = MagicMock()
    monkeypatch.setattr("kau_assistant.player.runner.SessionManager", lambda *args, **kwargs: mock_session)

    runner = CliRunner()
    res = runner.invoke(cli, ["watch", "--course", "기초전자실험", "--week", "3", "--dry-run", "--json"])
    assert res.exit_code == 0, res.output
    data = json.loads(res.output)
    assert data["course_name"] == "기초전자실험"
    assert data["target_week"] == "3주차"
    assert data["total_vods"] == 1
    assert data["dry_run"] is True
