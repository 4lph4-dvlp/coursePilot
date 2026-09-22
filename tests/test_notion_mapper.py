"""Pure mapping tests for the user-owned Notion Scheduler schema."""

from datetime import datetime

import pytest

from kau_assistant.domain.models import (
    SyncTask,
    TaskPriority,
    TaskSelect,
    TaskStatus,
    TaskType,
)
from kau_assistant.exceptions import NotionSchemaError
from kau_assistant.notion.mapper import (
    PROTECTED_PROPERTIES,
    SCHEDULER_SCHEMA,
    UPDATEABLE_PROPERTIES,
    parse_existing_page,
    parse_page_title,
    to_create_properties,
    to_update_properties,
    validate_scheduler_schema,
)
from kau_assistant.notion.models import ExistingPage
from kau_assistant.scraper.date_parser import KST


def _schema() -> dict:
    return {
        name: {
            "type": property_type,
            property_type: {"options": [{"name": option} for option in sorted(options)]},
        }
        for name, (property_type, options) in SCHEDULER_SCHEMA.items()
    }


def _task(*, due_date: datetime | None = None, memo: str = "memo") -> SyncTask:
    return SyncTask(
        id="task-1",
        course_id="course-1",
        course_name="공학수학 2",
        course_abbr="공수2",
        title="[공수2] 행렬 과제",
        raw_title="행렬 과제",
        task_type=TaskType.ASSIGNMENT,
        selection=TaskSelect.EVENT,
        category=["학업"],
        due_date=due_date,
        priority=TaskPriority.P1,
        status=TaskStatus.NOT_STARTED,
        memo=memo,
    )


def test_schema_contract_validates_all_eight_properties_and_options() -> None:
    assert set(SCHEDULER_SCHEMA) == {
        "이름",
        "선택",
        "구분",
        "DueDate",
        "Plan",
        "우선순위",
        "상태",
        "메모",
    }
    validate_scheduler_schema(_schema())

    broken = _schema()
    broken["선택"]["select"]["options"] = [{"name": "루틴"}]
    broken["메모"]["type"] = "title"
    with pytest.raises(NotionSchemaError) as exc_info:
        validate_scheduler_schema(broken)
    assert "이벤트" in str(exc_info.value)
    assert "메모" in str(exc_info.value)


def test_parse_existing_page_concatenates_title_and_normalizes_values() -> None:
    raw = {
        "id": "page-id",
        "properties": {
            "이름": {"title": [{"plain_text": "[공수2] "}, {"plain_text": "행렬 과제"}]},
            "DueDate": {"date": {"start": "2026-09-27T23:59:00+09:00"}},
            "Plan": {"date": {"start": "2026-09-25T10:00:00+09:00"}},
            "우선순위": {"select": {"name": "🔴 긴급 (P1)"}},
            "상태": {"status": {"name": "진행 중"}},
            "메모": {"rich_text": [{"plain_text": "memo "}, {"plain_text": "body"}]},
        },
    }

    page = parse_existing_page(raw)

    assert parse_page_title(raw) == "[공수2] 행렬 과제"
    assert page.title == "[공수2] 행렬 과제"
    assert page.due_date == datetime(2026, 9, 27, 23, 59, tzinfo=KST)
    assert page.plan_date == datetime(2026, 9, 25, 10, 0, tzinfo=KST)
    assert page.priority == TaskPriority.P1
    assert page.status == TaskStatus.IN_PROGRESS
    assert page.memo == "memo body"


def test_parse_existing_page_normalizes_date_only_values_to_kst() -> None:
    raw = {
        "id": "page-id",
        "properties": {
            "이름": {"title": [{"plain_text": "[공수2] 행렬 과제"}]},
            "DueDate": {"date": {"start": "2026-09-27"}},
            "Plan": {"date": None},
            "우선순위": {"select": {"name": "🔴 긴급 (P1)"}},
            "상태": {"status": {"name": "진행 중"}},
            "메모": {"rich_text": []},
        },
    }

    page = parse_existing_page(raw)

    assert page.due_date == datetime(2026, 9, 27, 0, 0, tzinfo=KST)


def test_create_properties_are_exact_memo_only_and_kst_serialized() -> None:
    due = datetime(2026, 9, 27, 23, 59, 12, 345000, tzinfo=KST)
    properties = to_create_properties(_task(due_date=due, memo="x" * 1950))

    assert set(properties) == {
        "이름",
        "선택",
        "구분",
        "DueDate",
        "우선순위",
        "상태",
        "메모",
    }
    assert properties["DueDate"] == {"date": {"start": "2026-09-27T23:59:12+09:00"}}
    assert properties["우선순위"] == {"select": {"name": "🔴 긴급 (P1)"}}
    assert properties["메모"]["rich_text"][0]["text"]["content"] == "x" * 1950
    assert "Plan" not in properties
    assert "children" not in properties
    assert "DueDate" not in to_create_properties(_task(due_date=None))


def test_update_properties_use_only_allowlist_and_ignore_protected_values() -> None:
    old_due = datetime(2026, 9, 20, 23, 59, tzinfo=KST)
    new_due = datetime(2026, 9, 27, 23, 59, tzinfo=KST)
    existing = ExistingPage(
        page_id="page-id",
        title="[공수2] 행렬 과제",
        due_date=old_due,
        priority=TaskPriority.P2,
        memo="old memo",
        status=TaskStatus.COMPLETED,
        plan_date=datetime(2026, 9, 25, 10, 0, tzinfo=KST),
    )

    properties, diffs = to_update_properties(
        _task(due_date=new_due, memo="new memo"), existing
    )

    assert UPDATEABLE_PROPERTIES == ("DueDate", "우선순위", "메모")
    assert PROTECTED_PROPERTIES == ("상태", "Plan")
    assert set(properties) == set(UPDATEABLE_PROPERTIES)
    assert properties["우선순위"] == {"select": {"name": "🔴 긴급 (P1)"}}
    assert {diff.property_name for diff in diffs} == set(UPDATEABLE_PROPERTIES)
    assert "상태" not in properties
    assert "Plan" not in properties
