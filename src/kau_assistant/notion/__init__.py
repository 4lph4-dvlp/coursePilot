"""Stable application-facing facade for Notion synchronization."""

from kau_assistant.exceptions import (
    NotionAuthenticationError,
    NotionIntegrationError,
    NotionPermissionError,
    NotionSchemaError,
    NotionTargetError,
    NotionTransportError,
)
from kau_assistant.notion.engine import NotionSyncEngine
from kau_assistant.notion.models import (
    CreateAction,
    ErrorAction,
    SkipAction,
    SyncResult,
    SyncStats,
    UpdateAction,
)

__all__ = [
    "CreateAction",
    "ErrorAction",
    "NotionAuthenticationError",
    "NotionIntegrationError",
    "NotionPermissionError",
    "NotionSchemaError",
    "NotionSyncEngine",
    "NotionTargetError",
    "NotionTransportError",
    "SkipAction",
    "SyncResult",
    "SyncStats",
    "UpdateAction",
]
