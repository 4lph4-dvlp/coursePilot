"""Synchronous Notion SDK boundary for Scheduler reads and writes."""

from datetime import datetime
from typing import Any

from notion_client import Client, RetryOptions

from kau_assistant.config import Settings, get_settings
from kau_assistant.notion.models import ExistingPage, NotionTarget


def _plain_text(parts: list[dict[str, Any]] | None) -> str:
    return "".join(str(part.get("plain_text", "")) for part in parts or [])


class NotionClient:
    """Owns all notion-client SDK calls used by the synchronization engine."""

    def __init__(self, settings: Settings | None = None, sdk: Any | None = None):
        self.settings = settings or get_settings()
        token = getattr(self.settings, "effective_notion_token", None)
        if callable(token):
            token = token()
        token = token or self.settings.notion_api_key
        self._sdk = sdk or Client(auth=token, retry=RetryOptions(max_retries=3))

    def resolve_target(self) -> NotionTarget:
        """Resolve an explicit database container to its child data source."""
        database_id = self.settings.notion_database_id.strip()
        if not database_id:
            raise ValueError("Notion database ID is required for explicit target resolution")
        database = self._sdk.databases.retrieve(database_id=database_id)
        data_sources = database.get("data_sources", [])
        if len(data_sources) != 1:
            raise ValueError("Notion database must expose exactly one data source")
        child = data_sources[0]
        title = _plain_text(database.get("title")) or str(child.get("name", ""))
        return NotionTarget(
            database_id=database_id,
            data_source_id=str(child["id"]),
            title=title,
        )

    def validate_scheduler_schema(self, data_source_id: str) -> None:
        """Perform a read-only schema retrieval before any query or write."""
        self._sdk.data_sources.retrieve(data_source_id=data_source_id)

    def query_existing_pages(
        self, data_source_id: str, *, now: datetime | None = None
    ) -> list[ExistingPage]:
        """Query and minimally normalize existing Scheduler pages."""
        response = self._sdk.data_sources.query(data_source_id=data_source_id, page_size=100)
        pages: list[ExistingPage] = []
        for page in response.get("results", []):
            properties = page.get("properties", {})
            title = _plain_text(properties.get("이름", {}).get("title"))
            pages.append(ExistingPage(page_id=str(page["id"]), title=title))
        return pages

    def create_page(self, data_source_id: str, properties: dict[str, Any]) -> dict[str, Any]:
        """Create one data-source child page."""
        return self._sdk.pages.create(
            parent={"type": "data_source_id", "data_source_id": data_source_id},
            properties=properties,
        )

    def update_page(self, page_id: str, properties: dict[str, Any]) -> dict[str, Any]:
        """Apply an allowlisted partial property update."""
        return self._sdk.pages.update(page_id=page_id, properties=properties)

