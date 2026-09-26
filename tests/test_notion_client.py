"""Tests for the guarded notion-client transport boundary."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import httpx
import pytest
from notion_client.errors import APIResponseError

from coursepilot.config import Settings
from coursepilot.exceptions import (
    NotionAuthenticationError,
    NotionSchemaError,
    NotionTargetError,
    NotionTransportError,
)
from coursepilot.notion.client import NotionClient
from coursepilot.scraper.date_parser import KST


def _schema() -> dict:
    return {
        "이름": {"type": "title", "title": {}},
        "선택": {
            "type": "select",
            "select": {"options": [{"name": "루틴"}, {"name": "이벤트"}]},
        },
        "구분": {
            "type": "multi_select",
            "multi_select": {"options": [{"name": "학업"}]},
        },
        "DueDate": {"type": "date", "date": {}},
        "Plan": {"type": "date", "date": {}},
        "우선순위": {
            "type": "select",
            "select": {
                "options": [
                    {"name": name}
                    for name in (
                        "🔴 긴급 (P1)",
                        "🟡 중요 (P2)",
                        "🔵 보통 (P3)",
                        "⚪ 낮음 (P4)",
                    )
                ]
            },
        },
        "상태": {
            "type": "status",
            "status": {
                "options": [
                    {"name": name} for name in ("시작 전", "진행 중", "완료", "폐기")
                ]
            },
        },
        "메모": {"type": "rich_text", "rich_text": {}},
    }


def _api_error(status: int, code: str = "internal_server_error") -> APIResponseError:
    return APIResponseError(
        code=code,
        status=status,
        message="secret-token must never escape",
        headers=httpx.Headers(),
        raw_body_text="secret-token",
        request_id="request-123",
    )


def test_sdk_uses_only_bounded_builtin_429_retry() -> None:
    with patch("coursepilot.notion.client.Client") as client_cls:
        NotionClient(
            settings=Settings(
                notion_token="token", notion_database_id="db-id", _env_file=None
            )
        )

    retry = client_cls.call_args.kwargs["retry"]
    assert retry.max_retries == 3


def test_explicit_database_id_wins_and_resolves_matching_child_data_source() -> None:
    sdk = MagicMock()
    sdk.databases.retrieve.return_value = {
        "title": [{"plain_text": "Scheduler"}],
        "data_sources": [
            {"id": "other", "name": "Archive"},
            {"id": "source-id", "name": "Scheduler"},
        ],
    }
    client = NotionClient(
        settings=Settings(
            notion_token="token",
            notion_database_id="database-id",
            notion_database_name="Scheduler",
            _env_file=None,
        ),
        sdk=sdk,
    )

    target = client.resolve_target()

    assert target.database_id == "database-id"
    assert target.data_source_id == "source-id"
    sdk.databases.retrieve.assert_called_once_with(database_id="database-id")
    sdk.search.assert_not_called()


def test_name_discovery_paginates_and_requires_one_complete_exact_title() -> None:
    sdk = MagicMock()
    sdk.search.side_effect = [
        {
            "results": [
                {
                    "object": "data_source",
                    "id": "partial",
                    "title": [{"plain_text": "Scheduler Archive"}],
                    "parent": {"database_id": "archive-db"},
                }
            ],
            "has_more": True,
            "next_cursor": "cursor-2",
        },
        {
            "results": [
                {
                    "object": "data_source",
                    "id": "source-id",
                    "title": [{"plain_text": "Sched"}, {"plain_text": "uler"}],
                    "parent": {"database_id": "database-id"},
                }
            ],
            "has_more": False,
            "next_cursor": None,
        },
    ]
    client = NotionClient(
        settings=Settings(
            notion_token="token", notion_database_name="Scheduler", _env_file=None
        ),
        sdk=sdk,
    )

    target = client.resolve_target()

    assert target.data_source_id == "source-id"
    assert target.database_id == "database-id"
    assert sdk.search.call_count == 2
    assert sdk.search.call_args_list[0].kwargs == {
        "query": "Scheduler",
        "filter": {"property": "object", "value": "data_source"},
        "page_size": 100,
    }
    assert sdk.search.call_args_list[1].kwargs["start_cursor"] == "cursor-2"


@pytest.mark.parametrize("match_count", [0, 2])
def test_name_discovery_fails_closed_on_absent_or_ambiguous_match(match_count: int) -> None:
    sdk = MagicMock()
    sdk.search.return_value = {
        "results": [
            {
                "object": "data_source",
                "id": f"source-{index}",
                "title": [{"plain_text": "Scheduler"}],
                "parent": {"database_id": f"database-{index}"},
            }
            for index in range(match_count)
        ],
        "has_more": False,
    }
    client = NotionClient(
        settings=Settings(
            notion_token="token", notion_database_name="Scheduler", _env_file=None
        ),
        sdk=sdk,
    )

    with pytest.raises(NotionTargetError):
        client.resolve_target()


def test_schema_validation_is_complete_and_read_only() -> None:
    sdk = MagicMock()
    sdk.data_sources.retrieve.return_value = {"properties": _schema()}
    client = NotionClient(settings=Settings(_env_file=None), sdk=sdk)

    client.validate_scheduler_schema("source-id")

    sdk.data_sources.retrieve.assert_called_once_with(data_source_id="source-id")
    sdk.pages.create.assert_not_called()
    sdk.pages.update.assert_not_called()

    broken = _schema()
    broken["상태"] = {"type": "select", "select": {"options": []}}
    sdk.data_sources.retrieve.return_value = {"properties": broken}
    with pytest.raises(NotionSchemaError, match="상태"):
        client.validate_scheduler_schema("source-id")


def test_client_delegates_schema_and_every_page_to_mapper() -> None:
    sdk = MagicMock()
    sdk.data_sources.retrieve.return_value = {"properties": _schema()}
    raw_pages = [{"id": "one", "properties": {}}, {"id": "two", "properties": {}}]
    sdk.data_sources.query.return_value = {"results": raw_pages, "has_more": False}
    parsed_pages = [MagicMock(page_id="one"), MagicMock(page_id="two")]
    client = NotionClient(settings=Settings(_env_file=None), sdk=sdk)

    with patch("coursepilot.notion.client.mapper.validate_scheduler_schema") as validate:
        client.validate_scheduler_schema("source-id")
        validate.assert_called_once_with(_schema())

    with patch(
        "coursepilot.notion.client.mapper.parse_existing_page", side_effect=parsed_pages
    ) as parse:
        assert client.query_existing_pages(
            "source-id", now=datetime(2026, 9, 22, 12, 0, tzinfo=KST)
        ) == parsed_pages
        assert [call.args[0] for call in parse.call_args_list] == raw_pages


def test_existing_page_query_uses_locked_filter_and_paginates() -> None:
    sdk = MagicMock()
    sdk.data_sources.query.side_effect = [
        {
            "results": [],
            "has_more": True,
            "next_cursor": "cursor-2",
        },
        {
            "results": [
                {
                    "id": "page-id",
                    "properties": {
                        "이름": {"title": [{"plain_text": "[공수2] "}, {"plain_text": "과제"}]},
                        "DueDate": {"date": {"start": "2026-09-27T23:59:00+09:00"}},
                        "우선순위": {"select": {"name": "🔴 긴급 (P1)"}},
                        "상태": {"status": {"name": "진행 중"}},
                        "메모": {"rich_text": [{"plain_text": "memo"}]},
                        "Plan": {"date": None},
                    },
                }
            ],
            "has_more": False,
        },
    ]
    client = NotionClient(settings=Settings(_env_file=None), sdk=sdk)
    now = datetime(2026, 9, 22, 12, 0, tzinfo=KST)

    pages = client.query_existing_pages("source-id", now=now)

    assert pages[0].title == "[공수2] 과제"
    assert pages[0].memo == "memo"
    assert pages[0].due_date == datetime(2026, 9, 27, 23, 59, tzinfo=KST)
    assert sdk.data_sources.query.call_count == 2
    first = sdk.data_sources.query.call_args_list[0].kwargs
    assert first["data_source_id"] == "source-id"
    assert first["page_size"] == 100
    assert first["filter"] == {
        "or": [
            {"property": "DueDate", "date": {"on_or_after": "2026-06-24"}},
            {"property": "상태", "status": {"does_not_equal": "완료"}},
        ]
    }
    assert sdk.data_sources.query.call_args_list[1].kwargs["start_cursor"] == "cursor-2"


def test_read_calls_are_spaced_and_529_retries_are_bounded() -> None:
    sdk = MagicMock()
    sdk.data_sources.retrieve.side_effect = [
        _api_error(529),
        {"properties": _schema()},
    ]
    sleeps: list[float] = []
    clock = [0.0]

    def sleep(seconds: float) -> None:
        sleeps.append(seconds)
        clock[0] += seconds

    client = NotionClient(
        settings=Settings(_env_file=None),
        sdk=sdk,
        sleep_fn=sleep,
        monotonic_fn=lambda: clock[0],
    )

    client.validate_scheduler_schema("source-id")

    assert sdk.data_sources.retrieve.call_count == 2
    assert sleeps == [pytest.approx(0.35)]


def test_configured_transport_errors_are_korean_typed_and_secret_safe() -> None:
    sdk = MagicMock()
    sdk.databases.retrieve.side_effect = _api_error(401, "unauthorized")
    client = NotionClient(
        settings=Settings(
            notion_token="secret-token", notion_database_id="database-id", _env_file=None
        ),
        sdk=sdk,
    )

    with pytest.raises(NotionAuthenticationError) as exc_info:
        client.resolve_target()

    message = str(exc_info.value)
    assert "토큰" in message
    assert "secret-token" not in message

    sdk.databases.retrieve.side_effect = _api_error(529)
    with pytest.raises(NotionTransportError, match="request-123"):
        client.resolve_target()
