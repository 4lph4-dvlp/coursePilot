"""Notion synchronization orchestration and dry-run write gate."""

from typing import Iterable

from kau_assistant.config import Settings, get_settings
from kau_assistant.domain.models import SyncTask
from kau_assistant.notion.client import NotionClient
from kau_assistant.notion.models import (
    CreateAction,
    ExistingPage,
    FieldDiff,
    SkipAction,
    SyncResult,
    SyncStats,
    UpdateAction,
)


def _date_property(task: SyncTask) -> dict:
    return {"date": {"start": task.due_date.isoformat() if task.due_date else None}}


def _build_update(task: SyncTask, existing: ExistingPage) -> tuple[dict, list[FieldDiff]]:
    properties: dict = {}
    diffs: list[FieldDiff] = []
    if task.due_date != existing.due_date:
        properties["DueDate"] = _date_property(task)
        diffs.append(FieldDiff(property_name="DueDate", before=existing.due_date, after=task.due_date))
    if task.priority != existing.priority:
        properties["우선순위"] = {"select": {"name": task.priority.value}}
        diffs.append(FieldDiff(property_name="우선순위", before=existing.priority, after=task.priority))
    if task.memo != existing.memo:
        properties["메모"] = {"rich_text": [{"text": {"content": task.memo}}]}
        diffs.append(FieldDiff(property_name="메모", before=existing.memo, after=task.memo))
    return properties, diffs


def _create_properties(task: SyncTask) -> dict:
    properties = {
        "이름": {"title": [{"text": {"content": task.title}}]},
        "선택": {"select": {"name": task.selection.value}},
        "구분": {"multi_select": [{"name": item} for item in task.category]},
        "우선순위": {"select": {"name": task.priority.value}},
        "상태": {"status": {"name": task.status.value}},
        "메모": {"rich_text": [{"text": {"content": task.memo}}]},
    }
    if task.due_date is not None:
        properties["DueDate"] = _date_property(task)
    return properties


class NotionSyncEngine:
    """Reads the live Scheduler, plans by exact title, and gates all writes."""

    def __init__(self, settings: Settings | None = None, client: NotionClient | None = None):
        self.settings = settings or get_settings()
        self.client = client

    def _configured(self) -> bool:
        configured = getattr(self.settings, "is_notion_configured", None)
        if configured is not None:
            return bool(configured() if callable(configured) else configured)
        token = self.settings.notion_api_key.strip()
        name = getattr(self.settings, "notion_database_name", "").strip()
        return bool(token and (self.settings.notion_database_id.strip() or name))

    def sync(self, tasks: list[SyncTask], *, dry_run: bool = False) -> SyncResult:
        if not self._configured():
            skipped = [
                SkipAction(task_id=task.id, title=task.title, reason="notion_disabled")
                for task in tasks
            ]
            return SyncResult(
                enabled=False,
                dry_run=dry_run,
                skipped=skipped,
                stats=SyncStats(total=len(tasks), skipped=len(skipped)),
            )

        client = self.client or NotionClient(settings=self.settings)
        target = client.resolve_target()
        client.validate_scheduler_schema(target.data_source_id)
        existing_pages = client.query_existing_pages(target.data_source_id)
        existing_by_title = {page.title: page for page in existing_pages}

        creates: list[CreateAction] = []
        updates: list[UpdateAction] = []
        skips: list[SkipAction] = []
        for task in tasks:
            existing = existing_by_title.get(task.title)
            if existing is None:
                creates.append(CreateAction(task_id=task.id, title=task.title, task=task))
                continue
            properties, diffs = _build_update(task, existing)
            if properties:
                updates.append(
                    UpdateAction(
                        task_id=task.id,
                        title=task.title,
                        page_id=existing.page_id,
                        properties=properties,
                        diffs=diffs,
                    )
                )
            else:
                skips.append(
                    SkipAction(
                        task_id=task.id,
                        title=task.title,
                        page_id=existing.page_id,
                        reason="unchanged",
                    )
                )

        if not dry_run:
            for action in creates:
                client.create_page(target.data_source_id, _create_properties(action.task))
                action.executed = True
            for action in updates:
                client.update_page(action.page_id, action.properties)
                action.executed = True

        return SyncResult(
            enabled=True,
            dry_run=dry_run,
            target=target,
            created=creates,
            updated=updates,
            skipped=skips,
            stats=SyncStats(
                total=len(tasks),
                created=len(creates),
                updated=len(updates),
                skipped=len(skips),
            ),
        )
