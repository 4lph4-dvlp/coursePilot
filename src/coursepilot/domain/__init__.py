"""CoursePilot domain modeling and task normalization package (D-15)."""

from coursepilot.domain.models import (
    Course,
    SyncTask,
    TaskPriority,
    TaskSelect,
    TaskStatus,
    TaskType,
)
from coursepilot.domain.naming import (
    clean_task_title,
    extract_week_and_title,
    format_task_title,
)
from coursepilot.domain.priority import (
    calculate_priority,
    get_task_selection,
)
from coursepilot.domain.transformer import (
    extract_deadline_from_description,
    format_memo,
    transform_assessment_to_task,
    transform_lecture_to_task,
    transform_to_sync_tasks,
)

__all__ = [
    "Course",
    "SyncTask",
    "TaskPriority",
    "TaskSelect",
    "TaskStatus",
    "TaskType",
    "calculate_priority",
    "clean_task_title",
    "extract_deadline_from_description",
    "extract_week_and_title",
    "format_memo",
    "format_task_title",
    "get_task_selection",
    "transform_assessment_to_task",
    "transform_lecture_to_task",
    "transform_to_sync_tasks",
]
