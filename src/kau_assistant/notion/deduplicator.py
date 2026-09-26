"""Pure Scheduler action planning with source identity and legacy-title fallback."""

from collections import Counter, defaultdict
from typing import TypeAlias
import re
from urllib.parse import parse_qs, urlsplit

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


def _source_key(url: str) -> str:
    parts = urlsplit(url)
    module_id = parse_qs(parts.query).get("id", [""])[0]
    return f"{parts.netloc.lower()}{parts.path}?id={module_id}" if module_id and parts.netloc else ""


def _memo_source(memo: str) -> str:
    match = re.search(r"LMS 바로가기:\s*(https?://\S+)", memo)
    return _source_key(match.group(1)) if match else ""


def plan_sync(
    tasks: list[SyncTask], existing_pages: list[ExistingPage]
) -> list[SyncAction]:
    """Plan stable actions in input order, failing closed on ambiguous identity."""
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
    existing_by_source: dict[str, list[ExistingPage]] = defaultdict(list)
    for page in valid_existing:
        existing_by_title[page.title].append(page)
        source = _memo_source(page.memo)
        if source:
            existing_by_source[source].append(page)
    incoming_counts = Counter(task.title for task in tasks)
    incoming_sources = Counter(_source_key(task.source_url) for task in tasks if task.source_url and not task.is_completed)

    for task in tasks:
        if task.is_completed:
            actions.append(SkipAction(task_id=task.id, title=task.title, reason="lms_completed"))
            continue
        source = _source_key(task.source_url)
        if source and incoming_sources[source] > 1:
            actions.append(ErrorAction(task_id=task.id, title=task.title, code="duplicate_incoming_source", message="같은 LMS 활동이 동기화 입력에 중복되어 있습니다."))
            continue
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

        matches = existing_by_source.get(source, []) if source else []
        if not matches:
            matches = existing_by_title.get(task.title, [])
            if any(_memo_source(page.memo) and _memo_source(page.memo) != source for page in matches) and source:
                actions.append(ErrorAction(task_id=task.id, title=task.title, code="source_identity_conflict", message="같은 제목의 Scheduler 항목이 다른 LMS 활동을 가리킵니다."))
                continue
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
