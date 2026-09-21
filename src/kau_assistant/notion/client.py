"""Synchronous Notion SDK boundary for Scheduler reads and writes."""

from collections.abc import Callable
from datetime import datetime, timedelta
import time
from typing import Any

from notion_client import Client, RetryOptions
from notion_client.errors import APIResponseError

from kau_assistant.config import Settings, get_settings
from kau_assistant.domain.models import TaskPriority, TaskStatus
from kau_assistant.exceptions import (
    NotionAuthenticationError,
    NotionPermissionError,
    NotionSchemaError,
    NotionTargetError,
    NotionTransportError,
)
from kau_assistant.notion.models import ExistingPage, NotionTarget
from kau_assistant.scraper.date_parser import KST


REQUEST_INTERVAL_SECONDS = 0.35
READ_529_RETRIES = 2
REQUIRED_SCHEMA: dict[str, tuple[str, set[str]]] = {
    "이름": ("title", set()),
    "선택": ("select", {"루틴", "이벤트"}),
    "구분": ("multi_select", {"학업"}),
    "DueDate": ("date", set()),
    "Plan": ("date", set()),
    "우선순위": ("select", {"P1", "P2", "P3", "P4"}),
    "상태": ("status", {"시작 전", "진행 중", "완료", "폐기"}),
    "메모": ("rich_text", set()),
}


def _plain_text(parts: list[dict[str, Any]] | None) -> str:
    return "".join(str(part.get("plain_text", "")) for part in parts or [])


class NotionClient:
    """Owns all notion-client SDK calls used by the synchronization engine."""

    def __init__(
        self,
        settings: Settings | None = None,
        sdk: Any | None = None,
        *,
        sleep_fn: Callable[[float], None] = time.sleep,
        monotonic_fn: Callable[[], float] = time.monotonic,
    ):
        self.settings = settings or get_settings()
        token = self.settings.effective_notion_token
        self._sdk = sdk or Client(auth=token, retry=RetryOptions(max_retries=3))
        self._sleep = sleep_fn
        self._monotonic = monotonic_fn
        self._last_request_at: float | None = None

    def _throttle(self) -> None:
        now = self._monotonic()
        if self._last_request_at is not None:
            wait = REQUEST_INTERVAL_SECONDS - (now - self._last_request_at)
            if wait > 0:
                self._sleep(wait)
                now = self._monotonic()
        self._last_request_at = now

    @staticmethod
    def _translate_error(error: APIResponseError) -> Exception:
        request_id = getattr(error, "request_id", None)
        suffix = f" (요청 ID: {request_id})" if request_id else ""
        status = getattr(error, "status", None)
        if status == 401:
            return NotionAuthenticationError(
                "Notion 토큰이 유효하지 않습니다. NOTION_TOKEN을 다시 확인하세요." + suffix
            )
        if status == 403:
            return NotionPermissionError(
                "Notion 통합에 Scheduler 접근 권한이 없습니다. 연결 권한을 확인하세요." + suffix
            )
        if status == 404:
            return NotionTargetError(
                "설정한 Notion Scheduler를 찾을 수 없습니다. ID와 공유 설정을 확인하세요." + suffix
            )
        return NotionTransportError(
            "Notion API 요청을 완료하지 못했습니다. 잠시 후 다시 시도하세요." + suffix
        )

    def _read(self, operation: Callable[..., Any], **kwargs: Any) -> Any:
        for attempt in range(READ_529_RETRIES + 1):
            self._throttle()
            try:
                return operation(**kwargs)
            except APIResponseError as error:
                if getattr(error, "status", None) == 529 and attempt < READ_529_RETRIES:
                    continue
                raise self._translate_error(error) from error
        raise AssertionError("unreachable")

    def _write(self, operation: Callable[..., Any], **kwargs: Any) -> Any:
        self._throttle()
        try:
            return operation(**kwargs)
        except APIResponseError as error:
            raise self._translate_error(error) from error

    def resolve_target(self) -> NotionTarget:
        """Resolve an explicit container or one exact discovered data source."""
        database_id = self.settings.notion_database_id.strip()
        configured_name = self.settings.notion_database_name.strip()
        if database_id:
            database = self._read(self._sdk.databases.retrieve, database_id=database_id)
            data_sources = database.get("data_sources", [])
            if len(data_sources) == 1:
                child = data_sources[0]
            else:
                matching = [
                    item for item in data_sources if str(item.get("name", "")) == configured_name
                ]
                if len(matching) != 1:
                    raise NotionTargetError(
                        "설정한 데이터베이스의 데이터 소스를 하나로 결정할 수 없습니다. "
                        "NOTION_DATABASE_NAME을 정확히 지정하세요."
                    )
                child = matching[0]
            title = _plain_text(database.get("title")) or str(child.get("name", ""))
            return NotionTarget(
                database_id=database_id,
                data_source_id=str(child["id"]),
                title=title,
            )

        if not configured_name:
            raise NotionTargetError("Notion Scheduler ID 또는 이름이 필요합니다.")
        matches: list[dict[str, Any]] = []
        cursor: str | None = None
        while True:
            kwargs: dict[str, Any] = {
                "query": configured_name,
                "filter": {"property": "object", "value": "data_source"},
                "page_size": 100,
            }
            if cursor:
                kwargs["start_cursor"] = cursor
            response = self._read(self._sdk.search, **kwargs)
            for item in response.get("results", []):
                title = _plain_text(item.get("title")) or str(item.get("name", ""))
                if item.get("object") == "data_source" and title == configured_name:
                    matches.append(item)
            if not response.get("has_more"):
                break
            cursor = response.get("next_cursor")
            if not cursor:
                break
        if len(matches) != 1:
            raise NotionTargetError(
                f"'{configured_name}'와 정확히 일치하는 Notion 데이터 소스를 하나로 결정할 수 없습니다."
            )
        match = matches[0]
        parent = match.get("parent", {})
        parent_database_id = parent.get("database_id")
        if not parent_database_id:
            raise NotionTargetError("검색된 데이터 소스의 상위 데이터베이스 ID가 없습니다.")
        return NotionTarget(
            database_id=str(parent_database_id),
            data_source_id=str(match["id"]),
            title=configured_name,
        )

    def validate_scheduler_schema(self, data_source_id: str) -> None:
        """Compare all required Scheduler fields without mutating the schema."""
        data_source = self._read(
            self._sdk.data_sources.retrieve, data_source_id=data_source_id
        )
        properties = data_source.get("properties", {})
        errors: list[str] = []
        for name, (expected_type, required_options) in REQUIRED_SCHEMA.items():
            actual = properties.get(name)
            if actual is None:
                errors.append(f"{name}: 누락")
                continue
            actual_type = actual.get("type")
            if actual_type != expected_type:
                errors.append(f"{name}: {actual_type!r} (필요: {expected_type!r})")
                continue
            if required_options:
                option_names = {
                    str(item.get("name", ""))
                    for item in actual.get(expected_type, {}).get("options", [])
                }
                missing = required_options - option_names
                if missing:
                    errors.append(f"{name}: 옵션 누락 {sorted(missing)}")
        if errors:
            raise NotionSchemaError("Scheduler 스키마가 호환되지 않습니다: " + "; ".join(errors))

    def query_existing_pages(
        self, data_source_id: str, *, now: datetime | None = None
    ) -> list[ExistingPage]:
        """Query every recent-or-incomplete page and normalize its protected fields."""
        current = now or datetime.now(KST)
        cutoff = (current.astimezone(KST) - timedelta(days=90)).date().isoformat()
        pages: list[ExistingPage] = []
        cursor: str | None = None
        while True:
            kwargs: dict[str, Any] = {
                "data_source_id": data_source_id,
                "page_size": 100,
                "filter": {
                    "or": [
                        {"property": "DueDate", "date": {"on_or_after": cutoff}},
                        {"property": "상태", "status": {"does_not_equal": "완료"}},
                    ]
                },
            }
            if cursor:
                kwargs["start_cursor"] = cursor
            response = self._read(self._sdk.data_sources.query, **kwargs)
            for page in response.get("results", []):
                properties = page.get("properties", {})
                title = _plain_text(properties.get("이름", {}).get("title"))
                due_raw = (properties.get("DueDate", {}).get("date") or {}).get("start")
                plan_raw = (properties.get("Plan", {}).get("date") or {}).get("start")
                priority_raw = (properties.get("우선순위", {}).get("select") or {}).get("name")
                status_raw = (properties.get("상태", {}).get("status") or {}).get("name")
                memo = _plain_text(properties.get("메모", {}).get("rich_text"))
                pages.append(
                    ExistingPage(
                        page_id=str(page["id"]),
                        title=title,
                        due_date=datetime.fromisoformat(due_raw) if due_raw else None,
                        priority=TaskPriority(priority_raw) if priority_raw else None,
                        memo=memo,
                        status=TaskStatus(status_raw) if status_raw else None,
                        plan_date=datetime.fromisoformat(plan_raw) if plan_raw else None,
                    )
                )
            if not response.get("has_more"):
                break
            cursor = response.get("next_cursor")
            if not cursor:
                break
        return pages

    def create_page(self, data_source_id: str, properties: dict[str, Any]) -> dict[str, Any]:
        """Create one data-source child page."""
        return self._write(
            self._sdk.pages.create,
            parent={"type": "data_source_id", "data_source_id": data_source_id},
            properties=properties,
        )

    def update_page(self, page_id: str, properties: dict[str, Any]) -> dict[str, Any]:
        """Apply an allowlisted partial property update."""
        return self._write(self._sdk.pages.update, page_id=page_id, properties=properties)
