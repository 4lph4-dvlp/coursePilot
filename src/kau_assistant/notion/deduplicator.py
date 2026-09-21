"""Pure, deterministic exact-title action planning for Scheduler sync."""

from collections import Counter, defaultdict
from typing import TypeAlias

from kau_assistant.domain.models import SyncTask
from kau_assistant.notion import mapper
from kau_assistant.notion.models import (
    CreateAction,
    ErrorAction,
    ExistingPage,
    SkipAction,
    UpdateAction,
)


SyncAction: TypeAlias = CreateAction | UpdateAction | SkipAction | ErrorAction


def plan_sync(
    tasks: list[SyncTask], existing_pages: list[ExistingPage]
) -> list[SyncAction]:
    """Plan stable actions in input order, matching solely on exact title."""
    actions: list[SyncAction] = []
    valid_existing: list[ExistingPage] = []
    for page in existing_pages:
        if not page.page_id or not page.title:
            actions.append(
                ErrorAction(
                    title=page.title,
                    page_id=page.page_id or None,
                    code="malformed_existing_page",
                    message="기존 Notion 페이지의 ID 또는 제목이 비어 있습니다.",
                )
            )
        else:
            valid_existing.append(page)

    existing_by_title: dict[str, list[ExistingPage]] = defaultdict(list)
    for page in valid_existing:
        existing_by_title[page.title].append(page)
    incoming_counts = Counter(task.title for task in tasks)

    for task in tasks:
        if incoming_counts[task.title] > 1:
            actions.append(
                ErrorAction(
                    task_id=task.id,
                    title=task.title,
                    code="duplicate_incoming_title",
                    message="동기화 입력에 같은 제목이 둘 이상 있어 안전하게 건너뜁니다.",
                )
            )
            continue

        matches = existing_by_title.get(task.title, [])
        if len(matches) > 1:
            actions.append(
                ErrorAction(
                    task_id=task.id,
                    title=task.title,
                    code="duplicate_existing_title",
                    message="Scheduler에 같은 제목의 페이지가 둘 이상 있어 안전하게 건너뜁니다.",
                )
            )
            continue
        if not matches:
            actions.append(CreateAction(task_id=task.id, title=task.title, task=task))
            continue

        existing = matches[0]
        properties, diffs = mapper.to_update_properties(task, existing)
        if properties:
            actions.append(
                UpdateAction(
                    task_id=task.id,
                    title=task.title,
                    page_id=existing.page_id,
                    properties=properties,
                    diffs=diffs,
                )
            )
        else:
            actions.append(
                SkipAction(
                    task_id=task.id,
                    title=task.title,
                    page_id=existing.page_id,
                    reason="unchanged",
                )
            )
    return actions

