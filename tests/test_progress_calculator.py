"""Unit tests for progress calculation engine, hybrid week detection, and KPI aggregation."""

from datetime import datetime
import pytest

from kau_assistant.progress.calculator import (
    SectionMeta,
    aggregate_dashboard_summary,
    calculate_course_progress,
    compute_breakdown,
    detect_current_week,
)
from kau_assistant.progress.models import (
    ActivityItem,
    ActivityType,
    CourseProgress,
)
from kau_assistant.scraper.date_parser import KST


def test_detect_current_week_by_date():
    sections = [
        SectionMeta(
            week_number=1,
            title="1주차",
            start_date=datetime(2026, 9, 1, 0, 0, tzinfo=KST),
            end_date=datetime(2026, 9, 7, 23, 59, tzinfo=KST),
            is_current=False,
        ),
        SectionMeta(
            week_number=2,
            title="2주차",
            start_date=datetime(2026, 9, 8, 0, 0, tzinfo=KST),
            end_date=datetime(2026, 9, 14, 23, 59, tzinfo=KST),
            is_current=False,
        ),
        SectionMeta(
            week_number=3,
            title="3주차",
            start_date=datetime(2026, 9, 15, 0, 0, tzinfo=KST),
            end_date=datetime(2026, 9, 21, 23, 59, tzinfo=KST),
            is_current=True,
        ),
    ]

    test_date = datetime(2026, 9, 10, 15, 30, tzinfo=KST)
    detected = detect_current_week(sections, now=test_date)
    assert detected == 2


def test_detect_current_week_by_is_current_fallback():
    sections = [
        SectionMeta(week_number=1, title="1주차", is_current=False),
        SectionMeta(week_number=2, title="2주차", is_current=False),
        SectionMeta(week_number=3, title="3주차", is_current=True),
    ]

    test_date = datetime(2026, 12, 1, 0, 0, tzinfo=KST)
    detected = detect_current_week(sections, now=test_date)
    assert detected == 3


def test_detect_current_week_fallback_to_min_week():
    sections = [
        SectionMeta(week_number=0, title="오리엔테이션"),  # ignored (<= 0)
        SectionMeta(week_number=2, title="2주차"),
        SectionMeta(week_number=3, title="3주차"),
    ]

    test_date = datetime(2026, 12, 1, 0, 0, tzinfo=KST)
    detected = detect_current_week(sections, now=test_date)
    assert detected == 2


def test_compute_breakdown_all_types():
    items = [
        ActivityItem(course_id="c1", activity_type=ActivityType.VOD, week_number=1, title="V1", is_completed=True),
        ActivityItem(course_id="c1", activity_type=ActivityType.VOD, week_number=1, title="V2", is_completed=False),
        ActivityItem(course_id="c1", activity_type=ActivityType.ASSIGNMENT, week_number=1, title="A1", is_completed=True),
        ActivityItem(course_id="c1", activity_type=ActivityType.QUIZ, week_number=1, title="Q1", is_completed=False),
        ActivityItem(course_id="c1", activity_type=ActivityType.MATERIAL, week_number=1, title="M1", is_completed=True),
    ]

    breakdown = compute_breakdown(items)
    assert breakdown.vod.completed == 1
    assert breakdown.vod.total == 2
    assert breakdown.vod.rate == 50.0

    assert breakdown.assignment.completed == 1
    assert breakdown.assignment.total == 1
    assert breakdown.assignment.rate == 100.0

    assert breakdown.quiz.completed == 0
    assert breakdown.quiz.total == 1
    assert breakdown.quiz.rate == 0.0

    assert breakdown.material.completed == 1
    assert breakdown.material.total == 1
    assert breakdown.material.rate == 100.0


def test_calculate_course_progress_metrics():
    # 4 activities in total:
    # Week 1: VOD1 (completed), Asg1 (not completed) -> past missed = 1
    # Week 2 (Current): VOD2 (completed), Quiz1 (not completed)
    # Week 3 (Future): VOD3 (not completed)
    activities = [
        ActivityItem(course_id="c1", activity_type=ActivityType.VOD, week_number=1, title="W1-VOD", is_completed=True),
        ActivityItem(course_id="c1", activity_type=ActivityType.ASSIGNMENT, week_number=1, title="W1-Asg", is_completed=False),
        ActivityItem(course_id="c1", activity_type=ActivityType.VOD, week_number=2, title="W2-VOD", is_completed=True),
        ActivityItem(course_id="c1", activity_type=ActivityType.QUIZ, week_number=2, title="W2-Quiz", is_completed=False),
        ActivityItem(course_id="c1", activity_type=ActivityType.VOD, week_number=3, title="W3-VOD", is_completed=False),
    ]

    progress = calculate_course_progress(
        course_id="c1",
        course_name="알고리즘",
        course_abbr="알고리즘",
        current_week=2,
        activities=activities,
    )

    # Open activities are Week 1 & Week 2 (4 items, 2 completed) -> 50.0%
    assert progress.current_open_total == 4
    assert progress.current_open_completed == 2
    assert progress.current_open_rate == 50.0

    # Past activities is Week 1 (2 items, 1 completed) -> 50.0%
    assert progress.past_weeks_total == 2
    assert progress.past_weeks_completed == 1
    assert progress.past_weeks_rate == 50.0
    assert len(progress.missed_past_items) == 1
    assert progress.missed_past_items[0].title == "W1-Asg"

    # Semester activities (5 items, 2 completed) -> 40.0%
    assert progress.semester_total == 5
    assert progress.semester_completed == 2
    assert progress.semester_overall_rate == 40.0


def test_week_1_boundary_past_weeks_all_clear():
    # Week 1 boundary: past weeks do not exist -> 100% past rate, 0 missed items (Pitfall 1)
    activities = [
        ActivityItem(course_id="c1", activity_type=ActivityType.VOD, week_number=1, title="W1-VOD", is_completed=False),
    ]

    progress = calculate_course_progress(
        course_id="c1",
        course_name="자료구조",
        course_abbr="자료구조",
        current_week=1,
        activities=activities,
    )

    assert progress.past_weeks_total == 0
    assert progress.past_weeks_completed == 0
    assert progress.past_weeks_rate == 100.0
    assert len(progress.missed_past_items) == 0

    assert progress.current_open_total == 1
    assert progress.current_open_completed == 0
    assert progress.current_open_rate == 0.0


def test_future_activities_separation():
    # Future weeks activities should not drag down current open rate (Pitfall 2 & D-16-04)
    activities = [
        # Current week (Week 2): all completed
        ActivityItem(course_id="c1", activity_type=ActivityType.VOD, week_number=2, title="W2-VOD", is_completed=True),
        ActivityItem(course_id="c1", activity_type=ActivityType.ASSIGNMENT, week_number=2, title="W2-Asg", is_completed=True),
        # Future week (Week 10): uncompleted
        ActivityItem(course_id="c1", activity_type=ActivityType.VOD, week_number=10, title="W10-VOD", is_completed=False),
    ]

    progress = calculate_course_progress(
        course_id="c1",
        course_name="운영체제",
        course_abbr="운영체제",
        current_week=2,
        activities=activities,
    )

    # Current open rate should be 100% (2/2)
    assert progress.current_open_rate == 100.0
    assert progress.current_open_completed == 2
    assert progress.current_open_total == 2

    # Semester rate reflects the future uncompleted item (2/3 = 66.7%)
    assert progress.semester_overall_rate == 66.7
    assert progress.semester_total == 3


def test_current_week_todo_sorting():
    # Incomplete items first, sorted by due date ascending, completed items last (D-16-07)
    due_earlier = datetime(2026, 9, 20, 12, 0, tzinfo=KST)
    due_later = datetime(2026, 9, 25, 23, 59, tzinfo=KST)

    activities = [
        ActivityItem(course_id="c1", activity_type=ActivityType.VOD, week_number=2, title="Done VOD", is_completed=True),
        ActivityItem(course_id="c1", activity_type=ActivityType.ASSIGNMENT, week_number=2, title="Later Due Asg", is_completed=False, due_date=due_later),
        ActivityItem(course_id="c1", activity_type=ActivityType.QUIZ, week_number=2, title="Early Due Quiz", is_completed=False, due_date=due_earlier),
        ActivityItem(course_id="c1", activity_type=ActivityType.MATERIAL, week_number=2, title="No Due Material", is_completed=False, due_date=None),
    ]

    progress = calculate_course_progress(
        course_id="c1",
        course_name="컴퓨터네트워크",
        course_abbr="네트워크",
        current_week=2,
        activities=activities,
    )

    items = progress.current_week_items
    assert len(items) == 4
    # Incomplete first: Early Due Quiz -> Later Due Asg -> No Due Material
    assert items[0].title == "Early Due Quiz"
    assert items[1].title == "Later Due Asg"
    assert items[2].title == "No Due Material"
    # Completed last
    assert items[3].title == "Done VOD"
    assert items[3].is_completed is True


def test_aggregate_dashboard_summary():
    course1 = CourseProgress(
        course_id="c1",
        course_name="과목 1",
        course_abbr="과목1",
        current_week=3,
        current_open_rate=100.0,
        current_open_completed=10,
        current_open_total=10,
        past_weeks_rate=100.0,
        past_weeks_completed=8,
        past_weeks_total=8,
        semester_overall_rate=50.0,
        semester_completed=10,
        semester_total=20,
        activity_breakdown=compute_breakdown([
            ActivityItem(course_id="c1", activity_type=ActivityType.VOD, week_number=1, title="V1", is_completed=True),
        ]),
        current_week_items=[],
        missed_past_items=[],
        status="ok",
    )
    course2 = CourseProgress(
        course_id="c2",
        course_name="과목 2",
        course_abbr="과목2",
        current_week=3,
        current_open_rate=50.0,
        current_open_completed=5,
        current_open_total=10,
        past_weeks_rate=75.0,
        past_weeks_completed=3,
        past_weeks_total=4,
        semester_overall_rate=25.0,
        semester_completed=5,
        semester_total=20,
        activity_breakdown=compute_breakdown([
            ActivityItem(course_id="c2", activity_type=ActivityType.VOD, week_number=1, title="V2", is_completed=False),
        ]),
        current_week_items=[
            ActivityItem(course_id="c2", activity_type=ActivityType.ASSIGNMENT, week_number=3, title="To-Do Asg", is_completed=False),
        ],
        missed_past_items=[
            ActivityItem(course_id="c2", activity_type=ActivityType.VOD, week_number=1, title="Missed VOD", is_completed=False),
        ],
        status="ok",
    )
    # Errored course
    course3 = CourseProgress(
        course_id="c3",
        course_name="과목 3",
        course_abbr="과목3",
        current_week=1,
        current_open_rate=0.0,
        current_open_completed=0,
        current_open_total=0,
        past_weeks_rate=0.0,
        past_weeks_completed=0,
        past_weeks_total=0,
        semester_overall_rate=0.0,
        semester_completed=0,
        semester_total=0,
        activity_breakdown=compute_breakdown([]),
        status="error",
        error_message="Network timeout",
    )

    summary = aggregate_dashboard_summary([course1, course2, course3])
    assert summary.total_courses == 3
    # open: (10 + 5) / (10 + 10) = 15/20 = 75.0%
    assert summary.current_open_completed == 15
    assert summary.current_open_total == 20
    assert summary.current_open_rate == 75.0

    # past: (8 + 3) / (8 + 4) = 11/12 = 91.7%
    assert summary.past_weeks_completed == 11
    assert summary.past_weeks_total == 12
    assert summary.past_weeks_rate == 91.7

    # missed past items = 1
    assert summary.missed_past_count == 1
    # current week todo = 1
    assert summary.current_week_todo_count == 1
