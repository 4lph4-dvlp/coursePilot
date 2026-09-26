"""Calculation engine for activity progress, week detection, and KPI metrics."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict

from kau_assistant.progress.models import (
    ActivityBreakdown,
    ActivityCount,
    ActivityItem,
    ActivityType,
    CourseProgress,
    DashboardSummary,
)
from kau_assistant.scraper.date_parser import KST, get_current_kst_time


class SectionMeta(BaseModel):
    """Metadata for an LXP course section/week."""

    model_config = ConfigDict(extra="forbid")

    week_number: int
    title: str = ""
    start_date: datetime | None = None
    end_date: datetime | None = None
    is_current: bool = False


def _due_date_sort_key(item: ActivityItem) -> datetime:
    """Helper sort key: sorts items with due dates ascending, None due dates last."""
    if item.due_date is None:
        return datetime.max.replace(tzinfo=KST)
    if item.due_date.tzinfo is None:
        return item.due_date.replace(tzinfo=KST)
    return item.due_date


def detect_current_week(sections: list[SectionMeta], now: datetime | None = None) -> int:
    """Detects current week number using hybrid date-range and .current class matching.

    Resolution precedence (D-16-02):
    1. Date range match: Section where start_date <= now <= end_date.
    2. LMS indicator match: Section marked with is_current (from .current class).
    3. Fallback: Minimum positive week number in sections, or 1.
    """
    current_time = now or get_current_kst_time()
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=KST)

    # Step 1: Date range
    for sec in sections:
        if sec.week_number <= 0:
            continue
        start = sec.start_date
        end = sec.end_date
        if start and start.tzinfo is None:
            start = start.replace(tzinfo=KST)
        if end and end.tzinfo is None:
            end = end.replace(tzinfo=KST)

        if start and end and start <= current_time <= end:
            return sec.week_number

    # Step 2: LXP .current class
    for sec in sections:
        if sec.is_current and sec.week_number > 0:
            return sec.week_number

    # Step 3: Fallback
    positive_weeks = [s.week_number for s in sections if s.week_number > 0]
    return min(positive_weeks, default=1)


def compute_breakdown(items: list[ActivityItem]) -> ActivityBreakdown:
    """Computes completed/total counts and percentage rates for each of 4 activity types."""
    counts: dict[ActivityType, tuple[int, int]] = {
        ActivityType.VOD: (0, 0),
        ActivityType.ASSIGNMENT: (0, 0),
        ActivityType.QUIZ: (0, 0),
        ActivityType.MATERIAL: (0, 0),
    }

    for item in items:
        completed, total = counts.get(item.activity_type, (0, 0))
        counts[item.activity_type] = (
            completed + (1 if item.is_completed else 0),
            total + 1,
        )

    def _make_count(act_type: ActivityType) -> ActivityCount:
        c, t = counts[act_type]
        rate = round(c / t * 100.0, 1) if t > 0 else 100.0
        return ActivityCount(completed=c, total=t, rate=rate)

    return ActivityBreakdown(
        vod=_make_count(ActivityType.VOD),
        assignment=_make_count(ActivityType.ASSIGNMENT),
        quiz=_make_count(ActivityType.QUIZ),
        material=_make_count(ActivityType.MATERIAL),
    )


def calculate_course_progress(
    course_id: str,
    course_name: str,
    course_abbr: str,
    current_week: int,
    activities: list[ActivityItem],
    now: datetime | None = None,
) -> CourseProgress:
    """Calculates multi-tier progress rates, missed past activities, and prioritized To-Do items."""
    past_activities = [a for a in activities if a.week_number < current_week]
    current_week_activities = [a for a in activities if a.week_number == current_week]
    open_activities = [a for a in activities if a.week_number <= current_week]
    all_activities = list(activities)

    # Metric 1: Current Open Rate (D-16-04, main metric)
    open_total = len(open_activities)
    open_completed = sum(1 for a in open_activities if a.is_completed)
    open_rate = round(open_completed / open_total * 100.0, 1) if open_total > 0 else 100.0

    # Metric 2: Past Weeks Cumulative Rate & Missed Items (D-16-03, strict past accounting)
    if current_week <= 1:
        # Week 1 boundary: no past weeks exist
        past_total = 0
        past_completed = 0
        past_rate = 100.0
        missed_past: list[ActivityItem] = []
    else:
        past_total = len(past_activities)
        past_completed = sum(1 for a in past_activities if a.is_completed)
        past_rate = round(past_completed / past_total * 100.0, 1) if past_total > 0 else 100.0
        missed_past = [a for a in past_activities if not a.is_completed]

    # Metric 3: Semester Overall Rate (D-16-04, auxiliary metric)
    semester_total = len(all_activities)
    semester_completed = sum(1 for a in all_activities if a.is_completed)
    semester_rate = round(semester_completed / semester_total * 100.0, 1) if semester_total > 0 else 100.0

    # Action Items: This Week To-Do Prioritization (D-16-07)
    todo_items = [a for a in current_week_activities if not a.is_completed]
    todo_items.sort(key=_due_date_sort_key)
    done_items = [a for a in current_week_activities if a.is_completed]
    current_week_items = todo_items + done_items

    # Activity Breakdown: computed on open_activities (D-16-01)
    activity_breakdown = compute_breakdown(open_activities)

    return CourseProgress(
        course_id=course_id,
        course_name=course_name,
        course_abbr=course_abbr,
        current_week=current_week,
        current_open_rate=open_rate,
        current_open_completed=open_completed,
        current_open_total=open_total,
        past_weeks_rate=past_rate,
        past_weeks_completed=past_completed,
        past_weeks_total=past_total,
        semester_overall_rate=semester_rate,
        semester_completed=semester_completed,
        semester_total=semester_total,
        activity_breakdown=activity_breakdown,
        current_week_items=current_week_items,
        missed_past_items=missed_past,
        all_items=all_activities,
        status="ok",
    )


def aggregate_dashboard_summary(courses: list[CourseProgress]) -> DashboardSummary:
    """Aggregates multi-course progress indicators into a high-level KPI dashboard summary."""
    valid_courses = [c for c in courses if c.status == "ok"]

    total_courses = len(courses)
    open_comp = sum(c.current_open_completed for c in valid_courses)
    open_tot = sum(c.current_open_total for c in valid_courses)
    open_rate = round(open_comp / open_tot * 100.0, 1) if open_tot > 0 else 100.0

    past_comp = sum(c.past_weeks_completed for c in valid_courses)
    past_tot = sum(c.past_weeks_total for c in valid_courses)
    past_rate = round(past_comp / past_tot * 100.0, 1) if past_tot > 0 else 100.0

    sem_comp = sum(c.semester_completed for c in valid_courses)
    sem_tot = sum(c.semester_total for c in valid_courses)
    sem_rate = round(sem_comp / sem_tot * 100.0, 1) if sem_tot > 0 else 100.0

    missed_count = sum(len(c.missed_past_items) for c in valid_courses)
    todo_count = sum(sum(1 for a in c.current_week_items if not a.is_completed) for c in valid_courses)

    # Activity totals: aggregate counts across open activities of valid courses
    vod_c = sum(c.activity_breakdown.vod.completed for c in valid_courses)
    vod_t = sum(c.activity_breakdown.vod.total for c in valid_courses)
    asg_c = sum(c.activity_breakdown.assignment.completed for c in valid_courses)
    asg_t = sum(c.activity_breakdown.assignment.total for c in valid_courses)
    quiz_c = sum(c.activity_breakdown.quiz.completed for c in valid_courses)
    quiz_t = sum(c.activity_breakdown.quiz.total for c in valid_courses)
    mat_c = sum(c.activity_breakdown.material.completed for c in valid_courses)
    mat_t = sum(c.activity_breakdown.material.total for c in valid_courses)

    activity_totals = ActivityBreakdown(
        vod=ActivityCount(completed=vod_c, total=vod_t, rate=round(vod_c / vod_t * 100.0, 1) if vod_t > 0 else 100.0),
        assignment=ActivityCount(completed=asg_c, total=asg_t, rate=round(asg_c / asg_t * 100.0, 1) if asg_t > 0 else 100.0),
        quiz=ActivityCount(completed=quiz_c, total=quiz_t, rate=round(quiz_c / quiz_t * 100.0, 1) if quiz_t > 0 else 100.0),
        material=ActivityCount(completed=mat_c, total=mat_t, rate=round(mat_c / mat_t * 100.0, 1) if mat_t > 0 else 100.0),
    )

    return DashboardSummary(
        total_courses=total_courses,
        current_open_rate=open_rate,
        current_open_completed=open_comp,
        current_open_total=open_tot,
        past_weeks_rate=past_rate,
        past_weeks_completed=past_comp,
        past_weeks_total=past_tot,
        semester_overall_rate=sem_rate,
        semester_completed=sem_comp,
        semester_total=sem_tot,
        missed_past_count=missed_count,
        current_week_todo_count=todo_count,
        activity_totals=activity_totals,
    )
