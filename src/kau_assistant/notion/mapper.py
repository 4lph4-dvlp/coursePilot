"""Pure Scheduler schema validation and Notion property transformations."""

from datetime import datetime
from typing import Any

from kau_assistant.domain.models import SyncTask, TaskPriority, TaskStatus
from kau_assistant.exceptions import NotionSchemaError
from kau_assistant.notion.models import ExistingPage, FieldDiff
from kau_assistant.scraper.date_parser import KST


PRIORITY_LABELS: dict[TaskPriority, str] = {
    TaskPriority.P1: "🔴 긴급 (P1)",
    TaskPriority.P2: "🟡 중요 (P2)",
    TaskPriority.P3: "🔵 보통 (P3)",
    TaskPriority.P4: "⚪ 낮음 (P4)",
}
NOTION_LABEL_PRIORITIES = {label: priority for priority, label in PRIORITY_LABELS.items()}

SCHEDULER_SCHEMA: dict[str, tuple[str, set[str]]] = {
    "이름": ("title", set()),
    "선택": ("select", {"루틴", "이벤트"}),
    "구분": ("multi_select", {"학업"}),
    "DueDate": ("date", set()),
    "Plan": ("date", set()),
    "우선순위": ("select", set(PRIORITY_LABELS.values())),
    "상태": ("status", {"시작 전", "진행 중", "완료", "폐기"}),
    "메모": ("rich_text", set()),
}
UPDATEABLE_PROPERTIES = ("DueDate", "우선순위", "메모")
PROTECTED_PROPERTIES = ("상태", "Plan")


def _plain_text(parts: list[dict[str, Any]] | None) -> str:
    return "".join(str(part.get("plain_text", "")) for part in parts or [])


def _parse_date(value: dict[str, Any] | None) -> datetime | None:
    start = (value or {}).get("start")
    return datetime.fromisoformat(start) if start else None


def _encode_date(value: datetime | None) -> dict[str, Any]:
    if value is None:
        return {"date": None}
    return {"date": {"start": value.astimezone(KST).isoformat(timespec="seconds")}}


def _parse_priority(value: str | None) -> TaskPriority | None:
    if not value:
        return None
    if value in NOTION_LABEL_PRIORITIES:
        return NOTION_LABEL_PRIORITIES[value]
    return TaskPriority(value)


def validate_scheduler_schema(properties: dict[str, Any]) -> None:
    """Validate the eight-field Scheduler contract without any mutation path."""
    errors: list[str] = []
    for name, (expected_type, required_options) in SCHEDULER_SCHEMA.items():
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


def parse_page_title(page: dict[str, Any]) -> str:
    """Return the complete Scheduler title across every rich-text segment."""
    properties = page.get("properties", {})
    return _plain_text(properties.get("이름", {}).get("title"))


def parse_existing_page(page: dict[str, Any]) -> ExistingPage:
    """Normalize one raw Notion page into the stable existing-page DTO."""
    properties = page.get("properties", {})
    priority_name = (properties.get("우선순위", {}).get("select") or {}).get("name")
    status_name = (properties.get("상태", {}).get("status") or {}).get("name")
    return ExistingPage(
        page_id=str(page["id"]),
        title=parse_page_title(page),
        due_date=_parse_date(properties.get("DueDate", {}).get("date")),
        priority=_parse_priority(priority_name),
        memo=_plain_text(properties.get("메모", {}).get("rich_text")),
        status=TaskStatus(status_name) if status_name else None,
        plan_date=_parse_date(properties.get("Plan", {}).get("date")),
    )


def to_create_properties(task: SyncTask) -> dict[str, Any]:
    """Serialize a task without Plan or page children (D-08)."""
    properties: dict[str, Any] = {
        "이름": {"title": [{"text": {"content": task.title}}]},
        "선택": {"select": {"name": task.selection.value}},
        "구분": {"multi_select": [{"name": item} for item in task.category]},
        "우선순위": {"select": {"name": PRIORITY_LABELS[task.priority]}},
        "상태": {"status": {"name": task.status.value}},
        "메모": {"rich_text": [{"text": {"content": task.memo}}]},
    }
    if task.due_date is not None:
        properties["DueDate"] = _encode_date(task.due_date)
    return properties


def to_update_properties(
    task: SyncTask, existing: ExistingPage
) -> tuple[dict[str, Any], list[FieldDiff]]:
    """Build an explicit D-01 allowlisted payload and exact field diffs."""
    properties: dict[str, Any] = {}
    diffs: list[FieldDiff] = []
    if task.due_date != existing.due_date:
        properties["DueDate"] = _encode_date(task.due_date)
        diffs.append(
            FieldDiff(property_name="DueDate", before=existing.due_date, after=task.due_date)
        )
    if task.priority != existing.priority:
        properties["우선순위"] = {"select": {"name": PRIORITY_LABELS[task.priority]}}
        diffs.append(
            FieldDiff(property_name="우선순위", before=existing.priority, after=task.priority)
        )
    if task.memo != existing.memo:
        properties["메모"] = {"rich_text": [{"text": {"content": task.memo}}]}
        diffs.append(FieldDiff(property_name="메모", before=existing.memo, after=task.memo))
    return properties, diffs
