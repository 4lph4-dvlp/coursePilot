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


def test_unique_source_match_previews_shorter_title_and_preserves_user_fields():
    source = "https://lxp.kau.ac.kr/mod/ubfile/view.php?id=2847"
    task = _task("mat_1125_2847", "[공수2] 4주차 문제풀이 확인 및 다운로드")
    task.source_url = source
    task.memo = f"LMS 바로가기: {source}"
    existing = ExistingPage(
        page_id="page-2847", title="[공학수학II] 4주차 문제풀이 확인 및 다운로드",
        priority=task.priority, memo=task.memo, status=TaskStatus.COMPLETED,
    )
    actions = plan_sync([task], [existing])
    assert isinstance(actions[0], UpdateAction)
    assert set(actions[0].properties) == {"이름"}
    assert [(d.property_name, d.before, d.after) for d in actions[0].diffs] == [
        ("이름", existing.title, task.title)
    ]


def test_source_matched_title_change_fails_when_another_page_uses_target_title():
    source = "https://lxp.kau.ac.kr/mod/assign/view.php?id=2222"
    task = _task("task", "[항산개] 4주차 보고서 제출")
    task.source_url = source
    pages = [
        ExistingPage(page_id="source", title="[항공우주산업개론] 4주차 보고서 제출", memo=f"LMS 바로가기: {source}"),
        ExistingPage(page_id="other", title=task.title),
    ]
    actions = plan_sync([task], pages)
    assert isinstance(actions[0], ErrorAction)
    assert actions[0].code == "title_collision"
