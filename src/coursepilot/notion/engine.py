"""Notion plan-then-execute synchronization and dry-run write gate."""

from coursepilot.config import Settings, get_settings
from coursepilot.domain.models import SyncTask
from coursepilot.exceptions import NotionIntegrationError
from coursepilot.notion import mapper
from coursepilot.notion.client import NotionClient
from coursepilot.notion.deduplicator import SyncAction, plan_sync
from coursepilot.notion.models import (
    CreateAction,
    ErrorAction,
    SkipAction,
    SyncResult,
    SyncStats,
    UpdateAction,
)


def _safe_error(
    error: Exception,
    *,
    task_id: str | None = None,
    title: str = "",
    page_id: str | None = None,
) -> ErrorAction:
    message = (
        str(error)
        if isinstance(error, NotionIntegrationError)
        else "Notion 작업을 완료하지 못했습니다. 설정과 연결 상태를 확인하세요."
    )
    return ErrorAction(
        task_id=task_id,
        title=title,
        page_id=page_id,
        code=type(error).__name__,
        message=message,
    )


def _result(
    tasks: list[SyncTask],
    actions: list[SyncAction],
    *,
    enabled: bool,
    dry_run: bool,
    target=None,
) -> SyncResult:
    created = [action for action in actions if isinstance(action, CreateAction)]
    updated = [action for action in actions if isinstance(action, UpdateAction)]
    skipped = [action for action in actions if isinstance(action, SkipAction)]
    errors = [action for action in actions if isinstance(action, ErrorAction)]
    return SyncResult(
        enabled=enabled,
        dry_run=dry_run,
        target=target,
        created=created,
        updated=updated,
        skipped=skipped,
        errors=errors,
        stats=SyncStats(
            total=len(tasks),
            created=len(created),
            updated=len(updated),
            skipped=len(skipped),
            errors=len(errors),
        ),
    )


class NotionSyncEngine:
    """Reads and plans first, then dispatches only explicitly allowed writes."""

    def __init__(self, settings: Settings | None = None, client: NotionClient | None = None):
        self.settings = settings or get_settings()
        self.client = client

    def sync(self, tasks: list[SyncTask], *, dry_run: bool = False) -> SyncResult:
        if not self.settings.is_notion_configured:
            actions: list[SyncAction] = [
                SkipAction(task_id=task.id, title=task.title, reason="notion_disabled")
                for task in tasks
            ]
            return _result(tasks, actions, enabled=False, dry_run=dry_run)

        client = self.client or NotionClient(settings=self.settings)
        try:
            target = client.resolve_target()
            client.validate_scheduler_schema(target.data_source_id)
            existing_pages = client.query_existing_pages(target.data_source_id)
            planned = plan_sync(tasks, existing_pages)
        except Exception as error:
            return _result(
                tasks, [_safe_error(error)], enabled=True, dry_run=dry_run
            )

        if dry_run:
            return _result(tasks, planned, enabled=True, dry_run=True, target=target)

        completed: list[SyncAction] = []
        for action in planned:
            if isinstance(action, (SkipAction, ErrorAction)):
                completed.append(action)
                continue
            try:
                if isinstance(action, CreateAction):
                    client.create_page(
                        target.data_source_id, mapper.to_create_properties(action.task)
                    )
                else:
                    client.update_page(action.page_id, action.properties)
                action.executed = True
                completed.append(action)
            except Exception as error:
                completed.append(
                    _safe_error(
                        error,
                        task_id=action.task_id,
                        title=action.title,
                        page_id=getattr(action, "page_id", None),
                    )
                )

        return _result(tasks, completed, enabled=True, dry_run=False, target=target)
