"""Pure title-only planning tests for Notion smart upsert."""

from datetime import datetime

from coursepilot.domain.models import (
    SyncTask,
    TaskPriority,
    TaskSelect,
    TaskStatus,
    TaskType,
)
from coursepilot.notion.deduplicator import plan_sync
from coursepilot.notion.models import (
    CreateAction,
    ErrorAction,
    ExistingPage,
    SkipAction,
    UpdateAction,
)
from coursepilot.scraper.date_parser import KST


def _task(
    task_id: str,
    title: str,
    *,
    due_date: datetime | None = None,
    memo: str = "memo",
) -> SyncTask:
    return SyncTask(
        id=task_id,
        course_id="course",
        course_name="course",
        course_abbr="C",
        title=title,
        raw_title=title,
        task_type=TaskType.ASSIGNMENT,
        selection=TaskSelect.EVENT,
        due_date=due_date,
        priority=TaskPriority.P1,
        status=TaskStatus.NOT_STARTED,
        memo=memo,
    )


def test_title_only_deadline_change_plans_one_update_without_reading_dedup_key(
    monkeypatch,
) -> None:
    old_due = datetime(2026, 9, 20, 23, 59, tzinfo=KST)
    new_due = datetime(2026, 9, 27, 23, 59, tzinfo=KST)
    task = _task("one", "[C] same title", due_date=new_due)
    existing = ExistingPage(
        page_id="page-one",
        title=task.title,
        due_date=old_due,
        priority=task.priority,
        memo=task.memo,
        status=TaskStatus.COMPLETED,
        plan_date=datetime(2026, 9, 25, 9, 0, tzinfo=KST),
    )
    monkeypatch.setattr(
        SyncTask,
        "dedup_key",
        property(lambda self: (_ for _ in ()).throw(AssertionError("dedup_key read"))),
    )

    actions = plan_sync([task], [existing])

    assert len(actions) == 1
    assert isinstance(actions[0], UpdateAction)
    assert set(actions[0].properties) == {"DueDate"}
    assert "상태" not in actions[0].properties
    assert "Plan" not in actions[0].properties


def test_planner_preserves_input_order_for_create_skip_and_update() -> None:
    due = datetime(2026, 9, 27, 23, 59, tzinfo=KST)
    tasks = [
        _task("create", "new", due_date=due),
        _task("skip", "same", due_date=due),
        _task("update", "changed", due_date=due, memo="new"),
    ]
    existing = [
        ExistingPage(
            page_id="same-page",
            title="same",
            due_date=due,
            priority=TaskPriority.P1,
            memo="memo",
        ),
        ExistingPage(
            page_id="changed-page",
            title="changed",
            due_date=due,
            priority=TaskPriority.P1,
            memo="old",
        ),
    ]

    actions = plan_sync(tasks, existing)

    assert [type(action) for action in actions] == [CreateAction, SkipAction, UpdateAction]
    assert actions[1].reason == "unchanged"


def test_duplicate_incoming_and_existing_titles_fail_closed() -> None:
    incoming = [_task("one", "duplicate"), _task("two", "duplicate")]
    incoming_actions = plan_sync(incoming, [])
    assert all(isinstance(action, ErrorAction) for action in incoming_actions)
    assert all(action.code == "duplicate_incoming_title" for action in incoming_actions)

    existing = [
        ExistingPage(page_id="page-1", title="duplicate"),
        ExistingPage(page_id="page-2", title="duplicate"),
    ]
    existing_actions = plan_sync([_task("one", "duplicate")], existing)
    assert len(existing_actions) == 1
    assert isinstance(existing_actions[0], ErrorAction)
    assert existing_actions[0].code == "duplicate_existing_title"


def test_malformed_existing_page_becomes_error_without_a_write_action() -> None:
    actions = plan_sync([], [ExistingPage(page_id="page-1", title="")])

    assert len(actions) == 1
    assert isinstance(actions[0], ErrorAction)
    assert actions[0].code == "malformed_existing_page"

