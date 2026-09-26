"""Unit tests for progress domain models and schema_version: 1 JSON contract."""

from datetime import datetime
import json
import pytest
from pydantic import ValidationError

from kau_assistant.progress.models import (
    SCHEMA_VERSION,
    ActivityBreakdown,
    ActivityCount,
    ActivityItem,
    ActivityType,
    CourseProgress,
    DashboardSummary,
    ProgressReport,
)
from kau_assistant.scraper.date_parser import KST


def test_activity_type_enum():
    assert ActivityType.VOD == "vod"
    assert ActivityType.ASSIGNMENT == "assignment"
    assert ActivityType.QUIZ == "quiz"
    assert ActivityType.MATERIAL == "material"


def test_activity_item_validation():
    now = datetime(2026, 9, 26, 12, 0, 0, tzinfo=KST)
    item = ActivityItem(
        course_id="10101",
        activity_type=ActivityType.VOD,
        week_number=3,
        title="3주차 1차시 강의",
        is_completed=True,
        due_date=now,
        raw_due_date="2026-09-26 12:00",
        is_overdue=False,
        is_urgent=False,
        url="https://canvas.kau.ac.kr/mod/vod/view.php?id=99",
        module_id="mod_1",
        clip_number=1,
    )
    assert item.course_id == "10101"
    assert item.activity_type == ActivityType.VOD
    assert item.is_completed is True

    # Extra fields forbidden
    with pytest.raises(ValidationError):
        ActivityItem(
            course_id="10101",
            activity_type=ActivityType.VOD,
            week_number=1,
            title="테스트",
            is_completed=False,
            unknown_field="invalid",
        )


def test_activity_breakdown_defaults():
    breakdown = ActivityBreakdown()
    assert breakdown.vod.completed == 0
    assert breakdown.vod.total == 0
    assert breakdown.vod.rate == 0.0
    assert breakdown.assignment.completed == 0
    assert breakdown.quiz.completed == 0
    assert breakdown.material.completed == 0


def test_progress_report_json_contract():
    now = datetime(2026, 9, 26, 12, 0, 0, tzinfo=KST)
    item = ActivityItem(
        course_id="10101",
        activity_type=ActivityType.ASSIGNMENT,
        week_number=3,
        title="과제 3",
        is_completed=False,
        due_date=now,
        raw_due_date="2026-09-26 23:59",
        is_overdue=False,
        is_urgent=True,
    )
    course = CourseProgress(
        course_id="10101",
        course_name="자료구조(01분반)",
        course_abbr="자료구조",
        current_week=3,
        current_open_rate=80.0,
        current_open_completed=8,
        current_open_total=10,
        past_weeks_rate=100.0,
        past_weeks_completed=6,
        past_weeks_total=6,
        semester_overall_rate=25.0,
        semester_completed=8,
        semester_total=32,
        activity_breakdown=ActivityBreakdown(
            vod=ActivityCount(completed=5, total=5, rate=100.0),
            assignment=ActivityCount(completed=1, total=2, rate=50.0),
            quiz=ActivityCount(completed=1, total=1, rate=100.0),
            material=ActivityCount(completed=1, total=2, rate=50.0),
        ),
        current_week_items=[item],
        missed_past_items=[],
        all_items=[item],
        status="ok",
    )
    summary = DashboardSummary(
        total_courses=1,
        current_open_rate=80.0,
        current_open_completed=8,
        current_open_total=10,
        past_weeks_rate=100.0,
        past_weeks_completed=6,
        past_weeks_total=6,
        semester_overall_rate=25.0,
        semester_completed=8,
        semester_total=32,
        missed_past_count=0,
        current_week_todo_count=1,
        activity_totals=course.activity_breakdown,
    )
    report = ProgressReport(
        schema_version=SCHEMA_VERSION,
        command="progress",
        status="success",
        generated_at=now,
        is_cached=False,
        summary=summary,
        courses=[course],
    )

    json_str = report.model_dump_json()
    data = json.loads(json_str)

    assert data["schema_version"] == 1
    assert data["command"] == "progress"
    assert data["status"] == "success"
    assert data["summary"]["total_courses"] == 1
    assert data["summary"]["current_open_rate"] == 80.0
    assert len(data["courses"]) == 1
    assert data["courses"][0]["current_open_rate"] == 80.0
    assert data["courses"][0]["activity_breakdown"]["vod"]["rate"] == 100.0

    # Round trip validation
    parsed_report = ProgressReport.model_validate(data)
    assert parsed_report.schema_version == 1
    assert parsed_report.command == "progress"
    assert parsed_report.courses[0].course_abbr == "자료구조"
