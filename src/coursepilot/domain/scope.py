"""Explicit task selection and preparation targets without changing LMS deadlines."""

from datetime import datetime
import re

from coursepilot.domain.models import SyncTask
from coursepilot.exceptions import ConfigError
from coursepilot.scraper.models import CourseItem


def _course_term(value: str) -> str:
    value = value.lower().replace("Ⅱ", "2").replace("ii", "2")
    return re.sub(r"[\s_()/\-]+", "", value)


def scope_tasks(
    tasks: list[SyncTask], *, weeks: tuple[int, ...] = (),
    course_weeks: tuple[str, ...] = (), due_before: datetime | None = None,
    prepare_by: datetime | None = None,
    courses: list[CourseItem] | None = None,
) -> list[SyncTask]:
    """Date and week selectors form a union; course-week selectors match uniquely."""
    selected_course_weeks: set[tuple[str, int]] = set()
    course_names = {(t.course_id, t.course_name, t.course_abbr) for t in tasks}
    course_names.update((c.course_id, c.clean_name, "") for c in courses or [])
    for selector in course_weeks:
        course_query, separator, week_text = selector.rpartition(":")
        if not separator or not week_text.isdigit() or int(week_text) < 1:
            raise ConfigError("--course-week는 '과목명:주차' 형식이어야 합니다 (예: '자료구조:5').")
        query = _course_term(course_query)
        matches = {cid for cid, name, abbr in course_names if query and (
            query in {_course_term(cid), _course_term(name), _course_term(abbr)}
            or query in _course_term(name)
        )}
        if len(matches) != 1:
            raise ConfigError(f"--course-week 과목 '{course_query}'을 하나로 식별하지 못했습니다. 과목 ID나 전체 이름을 사용하세요.")
        selected_course_weeks.add((next(iter(matches)), int(week_text)))

    filtered = bool(weeks or course_weeks or due_before)
    result: list[SyncTask] = []
    for task in tasks:
        if filtered and not (
            task.week_number in weeks
            or (task.course_id, task.week_number) in selected_course_weeks
            or (due_before is not None and task.due_date is not None and task.due_date <= due_before)
        ):
            continue
        if prepare_by is not None:
            memo = task.memo + ("\n\n" if task.memo else "") + f"수업 준비 목표: {prepare_by.strftime('%Y-%m-%d %H:%M (KST)')} (LMS 공식 마감과 별도)"
            task = task.model_copy(update={"preparation_date": prepare_by, "memo": memo})
        result.append(task)
    return result
