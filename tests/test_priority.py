"""Unit tests for 24-hour urgency and priority decision ladder."""

from datetime import datetime, timedelta
import pytest

from coursepilot.domain.models import TaskPriority, TaskSelect, TaskType
from coursepilot.domain.priority import calculate_priority, get_task_selection
from coursepilot.scraper.date_parser import KST


def test_urgent_24h_boundary():
    """DOMN-02: Verify 24-hour urgency promotion and exact boundary values."""
    now = datetime(2026, 9, 21, 12, 0, 0, tzinfo=KST)

    # 1. 10 hours remaining -> P1, urgent
    due_10h = now + timedelta(hours=10)
    pri, urgent, overdue = calculate_priority(TaskType.ASSIGNMENT, due_10h, now=now)
    assert pri == TaskPriority.P1
    assert urgent is True
    assert overdue is False

    # 2. Lecture with 5 hours remaining -> P1 (promoted from P3)
    due_5h = now + timedelta(hours=5)
    pri, urgent, overdue = calculate_priority(TaskType.LECTURE, due_5h, now=now)
    assert pri == TaskPriority.P1
    assert urgent is True
    assert overdue is False

    # 3. Exactly 24 hours remaining -> P1, urgent
    due_24h = now + timedelta(hours=24)
    pri, urgent, overdue = calculate_priority(TaskType.ASSIGNMENT, due_24h, now=now)
    assert pri == TaskPriority.P1
    assert urgent is True
    assert overdue is False

    # 4. 24 hours + 1 second remaining -> P2 (Normal assignment, not urgent)
    due_24h1s = now + timedelta(hours=24, seconds=1)
    pri, urgent, overdue = calculate_priority(TaskType.ASSIGNMENT, due_24h1s, now=now)
    assert pri == TaskPriority.P2
    assert urgent is False
    assert overdue is False

    # 5. Lecture 24 hours + 1 minute remaining -> P3 (Normal lecture, not urgent)
    due_24h1m = now + timedelta(hours=24, minutes=1)
    pri, urgent, overdue = calculate_priority(TaskType.LECTURE, due_24h1m, now=now)
    assert pri == TaskPriority.P3
    assert urgent is False
    assert overdue is False


def test_overdue_and_completed_priorities():
    """D-06, D-10: Verify overdue and completed tasks are downgraded to P4 and not falsely urgent."""
    now = datetime(2026, 9, 21, 12, 0, 0, tzinfo=KST)

    # 1. Overdue assignment (1 second ago) -> P4, overdue=True, urgent=False
    past_1s = now - timedelta(seconds=1)
    pri, urgent, overdue = calculate_priority(TaskType.ASSIGNMENT, past_1s, now=now)
    assert pri == TaskPriority.P4
    assert overdue is True
    assert urgent is False

    # 2. Overdue lecture (2 days ago) -> P4, overdue=True, urgent=False
    past_2d = now - timedelta(days=2)
    pri, urgent, overdue = calculate_priority(TaskType.LECTURE, past_2d, now=now)
    assert pri == TaskPriority.P4
    assert overdue is True
    assert urgent is False

    # 3. Completed task due in 2 hours -> P4, overdue=False, urgent=False
    due_soon = now + timedelta(hours=2)
    pri, urgent, overdue = calculate_priority(
        TaskType.ASSIGNMENT, due_soon, is_completed=True, now=now
    )
    assert pri == TaskPriority.P4
    assert overdue is False
    assert urgent is False

    # 4. Completed overdue task -> P4, overdue=False, urgent=False
    pri, urgent, overdue = calculate_priority(
        TaskType.ASSIGNMENT, past_2d, is_completed=True, now=now
    )
    assert pri == TaskPriority.P4
    assert overdue is False
    assert urgent is False


def test_no_due_date_priorities():
    """Verify tasks without due date receive default priorities."""
    # Lecture without due date -> P3
    pri, urgent, overdue = calculate_priority(TaskType.LECTURE, None)
    assert pri == TaskPriority.P3
    assert urgent is False
    assert overdue is False

    # Assignment without due date -> P2
    pri, urgent, overdue = calculate_priority(TaskType.ASSIGNMENT, None)
    assert pri == TaskPriority.P2
    assert urgent is False
    assert overdue is False

    # Quiz without due date -> P2
    pri, urgent, overdue = calculate_priority(TaskType.QUIZ, None)
    assert pri == TaskPriority.P2
    assert urgent is False
    assert overdue is False


def test_selection_mapping():
    """D-05: Verify Notion '선택' property mapping (루틴 vs 이벤트)."""
    assert get_task_selection(TaskType.LECTURE) == TaskSelect.ROUTINE
    assert get_task_selection(TaskType.ASSIGNMENT) == TaskSelect.EVENT
    assert get_task_selection(TaskType.QUIZ) == TaskSelect.EVENT
    assert get_task_selection(TaskType.FORUM) == TaskSelect.EVENT
    assert get_task_selection(TaskType.OTHER) == TaskSelect.EVENT
