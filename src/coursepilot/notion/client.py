"""CoursePilot compatibility facade for the independent Scheduler transport."""

from collections.abc import Callable
from datetime import datetime, timedelta
import time
from typing import Any

from notion_scheduler.client import NotionClient as SchedulerClient
from notion_scheduler.schema import (
    AuthenticationError,
    PermissionError as SchedulerPermissionError,
    SchedulerError,
    SchemaError,
    TargetError,
)

from coursepilot.config import Settings, get_settings
from coursepilot.exceptions import (
    NotionAuthenticationError,
    NotionPermissionError,
    NotionSchemaError,
    NotionTargetError,
    NotionTransportError,
)
from coursepilot.notion import mapper
from coursepilot.notion.models import ExistingPage, NotionTarget
from coursepilot.scraper.date_parser import KST


def index_unique_pages_by_title(
    pages: list[ExistingPage],
) -> tuple[dict[str, ExistingPage], set[str]]:
    """Index only unambiguous Scheduler titles for completion updates."""
    indexed: dict[str, ExistingPage] = {}
    ambiguous: set[str] = set()
    for page in pages:
        if not page.title or page.title in ambiguous:
            continue
        if page.title in indexed:
            indexed.pop(page.title)
            ambiguous.add(page.title)
        else:
            indexed[page.title] = page
    return indexed, ambiguous


def _coursepilot_error(error: SchedulerError) -> Exception:
    """Keep CoursePilot's public typed errors and secret-safe Korean messages."""
    request_note = str(error)[str(error).find(" (request ID:"):] if " (request ID:" in str(error) else ""
    if isinstance(error, AuthenticationError):
        return NotionAuthenticationError("Notion 토큰이 유효하지 않습니다. NOTION_TOKEN을 다시 확인하세요." + request_note)
    if isinstance(error, SchedulerPermissionError):
        return NotionPermissionError("Notion 통합에 Scheduler 접근 권한이 없습니다. 연결 권한을 확인하세요." + request_note)
    if isinstance(error, TargetError):
        return NotionTargetError("설정한 Notion Scheduler를 찾거나 하나로 결정할 수 없습니다. ID와 공유 설정을 확인하세요." + request_note)
    if isinstance(error, SchemaError):
        return NotionSchemaError("Scheduler 스키마가 호환되지 않습니다: " + str(error))
    return NotionTransportError("Notion API 요청을 완료하지 못했습니다. 잠시 후 다시 시도하세요." + request_note)


class NotionClient:
    """Preserve the CoursePilot interface while the package owns all SDK calls."""

    def __init__(
        self,
        settings: Settings | None = None,
        sdk: Any | None = None,
        *,
        sleep_fn: Callable[[float], None] = time.sleep,
        monotonic_fn: Callable[[], float] = time.monotonic,
    ):
        self.settings = settings or get_settings()
        self._client = SchedulerClient(
            token=self.settings.effective_notion_token,
            database_id=self.settings.notion_database_id,
            database_name=self.settings.notion_database_name,
            sdk=sdk,
            sleep_fn=sleep_fn,
            monotonic_fn=monotonic_fn,
        )

    def resolve_target(self) -> NotionTarget:
        try:
            target = self._client.resolve_target()
        except SchedulerError as error:
            raise _coursepilot_error(error) from None
        return NotionTarget(database_id=target.database_id, data_source_id=target.data_source_id, title=target.title)

    def validate_scheduler_schema(self, data_source_id: str) -> None:
        try:
            properties = self._client.validate_scheduler_schema(data_source_id)
        except SchedulerError as error:
            raise _coursepilot_error(error) from None
        mapper.validate_scheduler_schema(properties)

    def query_existing_pages(
        self, data_source_id: str, *, now: datetime | None = None
    ) -> list[ExistingPage]:
        current = now or datetime.now(KST)
        cutoff = (current.astimezone(KST) - timedelta(days=90)).date().isoformat()
        predicate = {
            "or": [
                {"property": "DueDate", "date": {"on_or_after": cutoff}},
                {"property": "상태", "status": {"does_not_equal": "완료"}},
            ]
        }
        try:
            pages = self._client.query_pages(data_source_id, filter=predicate)
        except SchedulerError as error:
            raise _coursepilot_error(error) from None
        return [mapper.parse_existing_page(page) for page in pages]

    def create_page(self, data_source_id: str, properties: dict[str, Any]) -> dict[str, Any]:
        try:
            return self._client.create_page(data_source_id, properties)
        except SchedulerError as error:
            raise _coursepilot_error(error) from None

    def update_page(self, page_id: str, properties: dict[str, Any]) -> dict[str, Any]:
        try:
            return self._client.update_page(page_id, properties)
        except SchedulerError as error:
            raise _coursepilot_error(error) from None

    def mark_task_completed(self, page_id: str) -> dict[str, Any]:
        """Explicit VOD completion may change status to 완료."""
        return self.update_page(page_id, {"상태": {"status": {"name": "완료"}}})
