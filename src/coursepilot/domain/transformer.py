"""Scraper DTO to domain SyncTask transformer with memo building and deadline rescue (D-09 ~ D-15)."""

from datetime import datetime
import re

from coursepilot.course_mapping import load_course_mappings
from coursepilot.domain.models import (
    Course,
    SyncTask,
    TaskPriority,
    TaskSelect,
    TaskStatus,
    TaskType,
)
from coursepilot.domain.naming import format_task_title
from coursepilot.domain.priority import calculate_priority, get_task_selection
from coursepilot.scraper.date_parser import KST, parse_lms_date
from coursepilot.scraper.models import (
    AssessmentItem,
    AssessmentType,
    AttendanceStatus,
    CourseItem,
    LectureItem,
    SubmissionStatus,
)
from coursepilot.materials.models import MaterialItem


def extract_deadline_from_description(text: str) -> datetime | None:
    """Rescues deadline from assignment description when LMS has no formal due date (D-11)."""
    if not text:
        return None

    patterns = [
        r"(?:제출\s*기한|마감\s*일시|마감\s*기한|제출\s*마감)[:\s]*([0-9년월일\s\(\)\-./:~]+)",
        r"([0-9]{1,2}\s*월\s*[0-9]{1,2}\s*일[\s\(\)월화수목금토일]*\s*(?:자정|24시|23:59|[0-9]{1,2}:[0-9]{1,2}))\s*까지",
        r"([0-9]{4}[-./][0-9]{1,2}[-./][0-9]{1,2}\s+[0-9]{1,2}:[0-9]{1,2})\s*까지",
    ]

    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            date_snippet = m.group(1).strip()
            date_snippet = re.sub(r"(?:자정|24시)", "23:59:59", date_snippet)
            parsed_dt, _ = parse_lms_date(date_snippet)
            if parsed_dt:
                return parsed_dt

    return None


def format_memo(
    task_type: TaskType,
    url: str = "",
    cutoff_date: datetime | None = None,
    attachments: list | None = None,
    description_text: str = "",
) -> str:
    """Builds structured Notion memo payload with 1500-char safe truncation (D-12 ~ D-14)."""
    # Lecture: concise single line (D-12)
    if task_type == TaskType.LECTURE:
        return f"LMS 바로가기: {url}" if url else ""

    sections: list[str] = []

    # 1. LMS Link
    if url:
        sections.append(f"LMS 바로가기: {url}")

    # 2. Cutoff Date
    if cutoff_date:
        cutoff_str = cutoff_date.strftime("%Y-%m-%d %H:%M:%S (KST)")
        sections.append(f"지각 제출 마감: {cutoff_str}")

    # 3. Attachments
    if attachments:
        att_lines = ["첨부파일:"]
        for att in attachments:
            size_str = f" ({att.filesize})" if getattr(att, "filesize", "") else ""
            att_lines.append(f"- {att.filename}{size_str}: {att.url}")
        sections.append("\n".join(att_lines))

    # 4. Description with safe 1500-char truncation (D-14)
    if description_text:
        cleaned_desc = description_text.strip()
        if len(cleaned_desc) > 1500:
            cleaned_desc = (
                cleaned_desc[:1500] + "\n... [이하 생략 - 전체 내용은 LMS 페이지 참조]"
            )
        sections.append(f"과제 안내:\n{cleaned_desc}")

    memo_text = "\n\n".join(sections).strip()
    # Hard safety cap under Notion 2000-char limit
    if len(memo_text) > 1950:
        memo_text = memo_text[:1900] + "\n... [내용 초과 절삭]"
    return memo_text


def transform_lecture_to_task(
    course: CourseItem,
    lecture: LectureItem,
    mappings: dict[str, str],
    now: datetime | None = None,
) -> SyncTask | None:
    """Transforms LectureItem to SyncTask. Retains incomplete lectures even if without explicit due date, excluding OT/open lectures (D-11)."""
    if lecture.due_date is None:
        title_norm = (lecture.title + " " + lecture.full_title).lower()
        is_ot = lecture.week_number == 0 or bool(
            re.search(r"\b(ot|orientation)\b|오리엔테이션|강의\s*개요|과목\s*소개", title_norm, re.I)
        )
        if is_ot:
            return None

    is_completed = lecture.status == AttendanceStatus.COMPLETED
    priority, is_urgent, is_overdue = calculate_priority(
        task_type=TaskType.LECTURE,
        due_date=lecture.due_date,
        is_completed=is_completed,
        now=now,
    )

    title = format_task_title(
        course_name=course.clean_name,
        raw_title=lecture.title,
        task_type=TaskType.LECTURE,
        week_number=lecture.week_number,
        clip_number=lecture.clip_number,
        course_mappings=mappings,
    )

    memo = format_memo(TaskType.LECTURE, url=lecture.link)

    return SyncTask(
        id=f"lec_{course.course_id}_{lecture.week_number}_{lecture.clip_number}",
        course_id=course.course_id,
        course_name=course.clean_name,
        course_abbr=mappings.get(course.clean_name, course.clean_name),
        title=title,
        raw_title=lecture.title,
        task_type=TaskType.LECTURE,
        selection=TaskSelect.ROUTINE,
        category=["학업"],
        due_date=lecture.due_date,
        priority=priority,
        status=TaskStatus.COMPLETED if is_completed else TaskStatus.NOT_STARTED,
        memo=memo,
        is_completed=is_completed,
        is_overdue=is_overdue,
        is_urgent=is_urgent,
        source_url=lecture.link,
        week_number=lecture.week_number,
        clip_number=lecture.clip_number,
        start_date=lecture.start_date,
        is_available=lecture.is_available,
    )


def transform_assessment_to_task(
    course: CourseItem,
    assessment: AssessmentItem,
    mappings: dict[str, str],
    now: datetime | None = None,
) -> SyncTask | None:
    """Transforms AssessmentItem to SyncTask with deadline rescue (D-11)."""
    due_date = assessment.due_date
    if due_date is None:
        due_date = extract_deadline_from_description(assessment.description_text)

    type_map = {
        AssessmentType.ASSIGNMENT: TaskType.ASSIGNMENT,
        AssessmentType.QUIZ: TaskType.QUIZ,
        AssessmentType.FORUM: TaskType.FORUM,
    }
    task_type = type_map.get(assessment.item_type, TaskType.ASSIGNMENT)

    is_completed = assessment.status in (
        SubmissionStatus.SUBMITTED,
        SubmissionStatus.GRADED,
    )
    priority, is_urgent, is_overdue = calculate_priority(
        task_type=task_type,
        due_date=due_date,
        is_completed=is_completed,
        now=now,
    )

    title = format_task_title(
        course_name=course.clean_name,
        raw_title=assessment.title,
        task_type=task_type,
        course_mappings=mappings,
    )

    memo = format_memo(
        task_type=task_type,
        url=assessment.url,
        cutoff_date=assessment.cutoff_date,
        attachments=assessment.attachments,
        description_text=assessment.description_text,
    )

    return SyncTask(
        id=f"assess_{course.course_id}_{assessment.item_id}",
        course_id=course.course_id,
        course_name=course.clean_name,
        course_abbr=mappings.get(course.clean_name, course.clean_name),
        title=title,
        raw_title=assessment.title,
        task_type=task_type,
        selection=get_task_selection(task_type),
        category=["학업"],
        due_date=due_date,
        priority=priority,
        status=TaskStatus.COMPLETED if is_completed else TaskStatus.NOT_STARTED,
        memo=memo,
        is_completed=is_completed,
        is_overdue=is_overdue,
        is_urgent=is_urgent,
        source_url=assessment.url,
        week_number=assessment.week_number,
        start_date=assessment.start_date,
        is_available=assessment.is_available,
    )


def transform_material_to_task(
    course: CourseItem, material: MaterialItem, mappings: dict[str, str], now: datetime | None = None,
) -> SyncTask:
    """Schedule the material activity without marking it viewed or downloading it."""
    priority, urgent, overdue = calculate_priority(TaskType.MATERIAL, material.due_date, material.is_completed, now)
    return SyncTask(
        id=f"mat_{course.course_id}_{material.module_id}",
        course_id=course.course_id, course_name=course.clean_name,
        course_abbr=mappings.get(course.clean_name, course.clean_name),
        title=format_task_title(course.clean_name, material.title, TaskType.MATERIAL, week_number=material.week_number, course_mappings=mappings),
        raw_title=material.title, task_type=TaskType.MATERIAL,
        selection=TaskSelect.ROUTINE, category=["학업"],
        due_date=material.due_date, priority=priority,
        status=TaskStatus.COMPLETED if material.is_completed else TaskStatus.NOT_STARTED,
        is_completed=material.is_completed, is_urgent=urgent, is_overdue=overdue,
        memo=format_memo(TaskType.MATERIAL, url=material.url), source_url=material.url,
        week_number=material.week_number, start_date=material.start_date, is_available=material.is_available,
    )


def transform_to_sync_tasks(
    courses: list[CourseItem],
    lectures_by_course: dict[str, list[LectureItem]],
    assessments_by_course: dict[str, list[AssessmentItem]],
    include_completed: bool = False,
    mappings: dict[str, str] | None = None,
    now: datetime | None = None,
    materials_by_course: dict[str, list[MaterialItem]] | None = None,
) -> list[SyncTask]:
    """Transforms all collected course activities into normalized SyncTasks (D-09).

    Sorts resulting tasks by due_date (earliest first, None last).
    """
    active_mappings = mappings if mappings is not None else load_course_mappings()
    tasks: list[SyncTask] = []

    for course in courses:
        cid = course.course_id

        for lec in lectures_by_course.get(cid, []):
            task = transform_lecture_to_task(course, lec, active_mappings, now=now)
            if task is not None:
                if include_completed or not task.is_completed:
                    tasks.append(task)

        for assess in assessments_by_course.get(cid, []):
            task = transform_assessment_to_task(
                course, assess, active_mappings, now=now
            )
            if task is not None:
                if include_completed or not task.is_completed:
                    tasks.append(task)

        for material in (materials_by_course or {}).get(cid, []):
            task = transform_material_to_task(course, material, active_mappings, now=now)
            if include_completed or not task.is_completed:
                tasks.append(task)

    # Sort: earliest deadline first, tasks without deadline last
    tasks.sort(
        key=lambda t: (
            t.due_date is None,
            t.due_date or datetime.max.replace(tzinfo=KST),
        )
    )
    return tasks
