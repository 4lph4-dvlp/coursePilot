"""Integration-style tests for the Notion synchronization orchestrator."""

from datetime import datetime
from unittest.mock import MagicMock

from kau_assistant.config import Settings
from kau_assistant.domain.models import (
    SyncTask,
    TaskPriority,
    TaskSelect,
    TaskStatus,
    TaskType,
)
from kau_assistant.notion.engine import NotionSyncEngine
from kau_assistant.notion.models import ExistingPage, NotionTarget
from kau_assistant.scraper.date_parser import KST


def _task(*, due_date: datetime | None = None) -> SyncTask:
    return SyncTask(
        id="task-1",
        course_id="course-1",
        course_name="공학수학 2",
        course_abbr="공수2",
        title="[공수2] 3주차 행렬 연산 과제 제출",
        raw_title="3주차 행렬 연산 과제 제출",
        task_type=TaskType.ASSIGNMENT,
        selection=TaskSelect.EVENT,
        due_date=due_date,
        priority=TaskPriority.P1,
        status=TaskStatus.NOT_STARTED,
        memo="LMS에서 과제 내용을 확인하세요.",
    )


def test_configured_dry_run_reads_before_planning_and_never_writes() -> None:
    calls: list[str] = []
    target = NotionTarget(
        database_id="database-id",
        data_source_id="data-source-id",
        title="Scheduler",
    )
    old_due = datetime(2026, 9, 20, 23, 59, tzinfo=KST)
    new_due = datetime(2026, 9, 27, 23, 59, tzinfo=KST)
    existing = ExistingPage(
        page_id="page-1",
        title="[공수2] 3주차 행렬 연산 과제 제출",
        due_date=old_due,
        priority=TaskPriority.P1,
        memo="LMS에서 과제 내용을 확인하세요.",
        status=TaskStatus.IN_PROGRESS,
    )

    client = MagicMock()
    client.resolve_target.side_effect = lambda: (calls.append("resolve"), target)[1]
    client.validate_scheduler_schema.side_effect = lambda data_source_id: calls.append(
        f"schema:{data_source_id}"
    )
    client.query_existing_pages.side_effect = lambda data_source_id: (
        calls.append(f"query:{data_source_id}"),
        [existing],
    )[1]
    settings = Settings(
        notion_api_key="secret-token",
        notion_database_id="database-id",
        _env_file=None,
    )

    result = NotionSyncEngine(settings=settings, client=client).sync(
        [_task(due_date=new_due)], dry_run=True
    )

    assert calls == ["resolve", "schema:data-source-id", "query:data-source-id"]
    assert result.enabled is True
    assert result.dry_run is True
    assert result.target == target
    assert result.stats.total == 1
    assert result.stats.updated == 1
    assert result.updated[0].page_id == "page-1"
    assert result.updated[0].executed is False
    assert result.updated[0].properties["DueDate"]["date"]["start"] == new_due.isoformat()
    client.create_page.assert_not_called()
    client.update_page.assert_not_called()


def test_missing_notion_configuration_returns_successful_disabled_result() -> None:
    client = MagicMock()
    settings = Settings(
        notion_api_key="",
        notion_database_id="",
        _env_file=None,
    )

    result = NotionSyncEngine(settings=settings, client=client).sync([_task()], dry_run=True)

    assert result.enabled is False
    assert result.dry_run is True
    assert result.stats.total == 1
    assert result.stats.skipped == 1
    assert result.skipped[0].reason == "notion_disabled"
    client.resolve_target.assert_not_called()
