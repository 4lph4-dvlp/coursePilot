"""Stable application-facing facade for Notion synchronization."""

from coursepilot.exceptions import (
    NotionAuthenticationError,
    NotionIntegrationError,
    NotionPermissionError,
    NotionSchemaError,
    NotionTargetError,
    NotionTransportError,
)
from coursepilot.notion.engine import NotionSyncEngine
from coursepilot.notion.models import (
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
