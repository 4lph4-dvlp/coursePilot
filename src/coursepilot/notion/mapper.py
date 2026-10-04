"""Pure Scheduler schema validation and Notion property transformations."""

from datetime import datetime
from typing import Any

from notion_scheduler.schema import (
    SCHEDULER_SCHEMA as BASE_SCHEDULER_SCHEMA,
    SchemaError,
    parse_page,
    plain_text,
    serialize_fields,
    validate_scheduler_schema as validate_base_schema,
)

from coursepilot.domain.models import SyncTask, TaskPriority, TaskStatus
from coursepilot.exceptions import NotionSchemaError
from coursepilot.notion.models import ExistingPage, FieldDiff
from coursepilot.scraper.date_parser import KST


PRIORITY_LABELS: dict[TaskPriority, str] = {
    TaskPriority.P1: "🔴 긴급 (P1)",
    TaskPriority.P2: "🟡 중요 (P2)",
    TaskPriority.P3: "🔵 보통 (P3)",
    TaskPriority.P4: "⚪ 낮음 (P4)",
}
NOTION_LABEL_PRIORITIES = {label: priority for priority, label in PRIORITY_LABELS.items()}

SCHEDULER_SCHEMA: dict[str, tuple[str, set[str]]] = {
    name: (kind, set(options) | ({"학업"} if name == "구분" else set()))
    for name, (kind, options) in BASE_SCHEDULER_SCHEMA.items()
}
UPDATEABLE_PROPERTIES = ("DueDate", "우선순위", "메모")
PROTECTED_PROPERTIES = ("상태", "Plan")


def _parse_date(value: dict[str, Any] | None) -> datetime | None:
    start = (value or {}).get("start")
    if not start:
        return None
    parsed = datetime.fromisoformat(start)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=KST)
    return parsed.astimezone(KST)


def _date_value(value: datetime | None) -> str | None:
    return value.astimezone(KST).isoformat(timespec="seconds") if value else None


def _serialization_schema() -> dict[str, Any]:
    """CoursePilot's fixed academic options for shared property serialization."""
    return {
        name: {kind: {"options": [{"name": option} for option in options]}}
        for name, (kind, options) in SCHEDULER_SCHEMA.items()
    }


def _parse_priority(value: str | None) -> TaskPriority | None:
    if not value:
        return None
    if value in NOTION_LABEL_PRIORITIES:
        return NOTION_LABEL_PRIORITIES[value]
    return TaskPriority(value)


def validate_scheduler_schema(properties: dict[str, Any]) -> None:
    """Validate the shared Scheduler schema and CoursePilot's 학업 category."""
    try:
        validate_base_schema(properties)
    except SchemaError as error:
        raise NotionSchemaError("Scheduler 스키마가 호환되지 않습니다: " + str(error)) from None
    categories = {item.get("name") for item in properties["구분"]["multi_select"].get("options", [])}
    if "학업" not in categories:
        raise NotionSchemaError("Scheduler 스키마가 호환되지 않습니다: 구분: 학업 옵션 누락")


def parse_page_title(page: dict[str, Any]) -> str:
    """Return the complete Scheduler title across every rich-text segment."""
    properties = page.get("properties", {})
    return plain_text(properties.get("이름", {}).get("title"))


def parse_existing_page(page: dict[str, Any]) -> ExistingPage:
    """Normalize one raw Notion page into the stable existing-page DTO."""
    neutral = parse_page(page)
    return ExistingPage(
        page_id=neutral.page_id,
        title=neutral.title,
        due_date=_parse_date({"start": neutral.due_date} if neutral.due_date else None),
        priority=_parse_priority(neutral.priority),
        memo=neutral.memo,
        status=TaskStatus(neutral.status) if neutral.status else None,
        plan_date=_parse_date({"start": neutral.plan_date} if neutral.plan_date else None),
    )


def to_create_properties(task: SyncTask) -> dict[str, Any]:
    """Serialize a task without Plan or page children (D-08)."""
    fields: dict[str, Any] = {
        "title": task.title,
        "category": task.category,
        "priority": PRIORITY_LABELS[task.priority],
        "status": task.status.value,
        "memo": task.memo,
    }
    if task.due_date is not None:
        fields["due_date"] = _date_value(task.due_date)
    return serialize_fields(fields, _serialization_schema())


def to_update_properties(
    task: SyncTask, existing: ExistingPage, *, update_title: bool = False
) -> tuple[dict[str, Any], list[FieldDiff]]:
    """Build an explicit D-01 allowlisted payload and exact field diffs."""
    properties: dict[str, Any] = {}
    diffs: list[FieldDiff] = []
    if update_title and task.title != existing.title:
        properties.update(serialize_fields({"title": task.title}, _serialization_schema()))
        diffs.append(FieldDiff(property_name="이름", before=existing.title, after=task.title))
    if task.due_date != existing.due_date:
        properties.update(serialize_fields({"due_date": _date_value(task.due_date)}, _serialization_schema()))
        diffs.append(
            FieldDiff(property_name="DueDate", before=existing.due_date, after=task.due_date)
        )
    if task.priority != existing.priority:
        properties.update(serialize_fields({"priority": PRIORITY_LABELS[task.priority]}, _serialization_schema()))
        diffs.append(
            FieldDiff(property_name="우선순위", before=existing.priority, after=task.priority)
        )
    if task.memo != existing.memo:
        properties.update(serialize_fields({"memo": task.memo}, _serialization_schema()))
        diffs.append(FieldDiff(property_name="메모", before=existing.memo, after=task.memo))
    return properties, diffs
