"""Urgency, priority determination, and Notion property mapper (D-05 ~ D-08, DOMN-02)."""

from datetime import datetime

from kau_assistant.domain.models import TaskPriority, TaskSelect, TaskType
from kau_assistant.scraper.date_parser import KST, get_current_kst_time


def calculate_priority(
    task_type: TaskType,
    due_date: datetime | None,
    is_completed: bool = False,
    now: datetime | None = None,
) -> tuple[TaskPriority, bool, bool]:
    """Calculates task priority and status flags (D-06, DOMN-02).

    Evaluation Order (Crucial):
      1. Completed -> P4, is_urgent=False, is_overdue=False
      2. No due date -> P3 (Lecture) or P2 (Assessment), is_urgent=False, is_overdue=False
      3. Past deadline (due_date < now) -> P4, is_urgent=False, is_overdue=True
      4. Imminent deadline (0 <= remaining <= 24h) -> P1, is_urgent=True, is_overdue=False
      5. Normal pending (> 24h) -> P3 (Lecture) or P2 (Assessment), is_urgent=False, is_overdue=False

    Returns:
        (priority, is_urgent, is_overdue)
    """
    # 1. Completed tasks are downgraded to P4
    if is_completed:
        return TaskPriority.P4, False, False

    # 2. No deadline -> default priority
    if due_date is None:
        default_priority = (
            TaskPriority.P3 if task_type == TaskType.LECTURE else TaskPriority.P2
        )
        return default_priority, False, False

    current_time = now if now is not None else get_current_kst_time()
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=KST)
    else:
        current_time = current_time.astimezone(KST)

    if due_date.tzinfo is None:
        due_date = due_date.replace(tzinfo=KST)
    else:
        due_date = due_date.astimezone(KST)

    # 3. Overdue: past deadline -> P4 (D-06, D-10)
    if due_date < current_time:
        return TaskPriority.P4, False, True

    # 4. Imminent: <= 24 hours -> P1 (DOMN-02, D-06)
    remaining_seconds = (due_date - current_time).total_seconds()
    if 0 <= remaining_seconds <= 24 * 3600:
        return TaskPriority.P1, True, False

    # 5. Normal pending tasks (> 24h) (D-06)
    if task_type == TaskType.LECTURE:
        return TaskPriority.P3, False, False
    else:
        return TaskPriority.P2, False, False


def get_task_selection(task_type: TaskType) -> TaskSelect:
    """Maps activity type to Notion '선택' property (D-05)."""
    if task_type == TaskType.LECTURE:
        return TaskSelect.ROUTINE
    return TaskSelect.EVENT
