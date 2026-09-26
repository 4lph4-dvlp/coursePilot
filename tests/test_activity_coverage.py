"""Regression inventory for the user's 18 activities and current Coursemos markup."""

from datetime import datetime
import json
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from coursepilot.cli import cli
from coursepilot.domain.scope import scope_tasks
from coursepilot.domain.transformer import transform_to_sync_tasks
from coursepilot.errors import safe_cli_error
from coursepilot.exceptions import ActivityCollectionError, ConfigError
from coursepilot.notion.deduplicator import plan_sync
from coursepilot.notion.models import CreateAction, ExistingPage, SkipAction, SyncResult, UpdateAction
from coursepilot.pipeline import PipelineResult
from coursepilot.scraper.assessment_parser import merge_section_assessments
from coursepilot.scraper.course_sections import needs_section_view, sections_url, validate_activity_coverage
from coursepilot.scraper.date_parser import KST
from coursepilot.scraper.lecture_parser import UblogsActivityStatus, merge_ublogs_completion, parse_lectures_from_course_sections
from coursepilot.scraper.material_parser import parse_materials_from_course_sections
from coursepilot.scraper.models import AttendanceStatus, CourseItem
from coursepilot.scraper.navigator import CourseNavigator
from coursepilot.progress.runner import _collect_single_course_progress

NOW = datetime(2026, 9, 27, 1, 0, tzinfo=KST)
# Source module IDs and section weeks from the read-only LMS diagnosis.
# These are representative HTML fixtures, not stored authenticated pages.
BASELINE = {
    "1125": ("공학수학II", [
        (4, "2850", "vod", "Fourier analysis 2 문제풀이", False, "2026-09-28 23:59:00"),
        (4, "2847", "ubfile", "Fourier analysis 2 문제풀이", True, ""),
        (4, "9763", "quiz", "4주차 퀴즈", False, "2026-09-28 15:20:00"),
    ]),
    "1113": ("디지털시스템설계", [
        (5, "2143", "vod", "Verilog HDL for Circuit Synthesis 3", False, ""),
    ]),
    "1101": ("자료구조및실습", [
        (5, "9473", "vod", "5주차: 스택", False, "2026-09-29 14:59:00"),
        (5, "9476", "ubfile", "5주차 강의자료", False, ""),
    ]),
    "1097": ("확률및랜덤변수", [
        (4, "8482", "vod", "Ch4. Continuous Random Variables", False, "2026-09-28 23:59:00"),
        (4, "8483", "ubfile", "Ch4. Continuous Random Variables", False, ""),
        (5, "9767", "vod", "Ch5. Multiple Random Variables", False, "2026-10-01 23:59:00"),
        (5, "9766", "ubfile", "Ch5. Multiple Random Variables", False, ""),
    ]),
    "1103": ("기초전자실험", [
        (5, "8684", "ubfile", "W04 래치및플립플롭", False, ""),
        (5, "8686", "vod", "W04_래치및플립플롭", False, "2026-10-05 23:59:59"),
        (5, "8725", "quiz", "W04 퀴즈", False, "2026-10-02 09:00:00"),
        (5, "8690", "assign", "W04 예비보고서 제출함", False, "2026-10-02 09:00:00"),
        (5, "8691", "assign", "W04 결과보고서 제출함", False, "2026-10-09 09:00:00"),
    ]),
    "1478": ("항공우주산업개론", [
        (4, "3348", "vod", "항산개_4주차_3_1", False, "2026-09-28 23:59:00"),
        (4, "3349", "vod", "항산개_4주차_3_2", False, "2026-09-28 23:59:00"),
        (4, "3351", "vod", "항산개_4주차_3_3", False, "2026-09-28 23:59:00"),
    ]),
}


def section_html(rows):
    sections = {}
    for week, mid, kind, title, done, due in rows:
        status = "completed" if done else "incomplete"
        dates = f'<div class="activity-dates"><span class="timeopen">2026-09-01 00:00:00</span> ~ <span class="timeclose">{due}</span></div>' if due else ""
        sections.setdefault(week, []).append(
            f'<li class="activity modtype_{kind} activity-{status}" id="module-{mid}">'
            f'<a class="activity-container" href="/mod/{kind}/view.php?id={mid}">'
            f'<div class="sr-only">활동 {title} 선택</div><div class="activityname">{title}</div>{dates}'
            f'<span class="displayoptions">01:23:45</span><div class="csms-chips-dot">{"완료" if done else "미완료"}</div></a></li>'
        )
    return '<ul class="weeks">' + "".join(
        f'<li class="section" id="section-{week}"><h3 class="sectionname">{week}주차</h3><ul>{"".join(activities)}</ul></li>'
        for week, activities in sections.items()
    ) + "</ul>"


def inventory(include_completed=True):
    courses, lectures, assessments, materials = [], {}, {}, {}
    for cid, (name, rows) in BASELINE.items():
        course = CourseItem(course_id=cid, raw_name=name, clean_name=name, url=f"https://lxp.kau.ac.kr/course/view.php?id={cid}")
        courses.append(course)
        html = section_html(rows)
        validate_activity_coverage(html, course)
        lectures[cid] = parse_lectures_from_course_sections(html, course)
        assessments[cid] = merge_section_assessments([], html, course)
        materials[cid] = parse_materials_from_course_sections(html, course)
    return transform_to_sync_tasks(courses, lectures, assessments, include_completed=include_completed, mappings={}, now=NOW, materials_by_course=materials)


def test_baseline_all_18_source_identities_and_17_incomplete():
    tasks = inventory()
    expected = {mid for _, rows in BASELINE.values() for _, mid, *_ in rows}
    assert {task.source_url.split("id=")[-1] for task in tasks} == expected
    assert len(tasks) == 18
    assert len(inventory(False)) == 17
    assert sum(t.task_type.value == "material" for t in tasks) == 5
    assert [t.source_url.split("id=")[-1] for t in tasks if t.is_completed] == ["2847"]
    assert all("선택" not in t.raw_title and "01:23:45" not in t.raw_title and "미완료" not in t.raw_title for t in tasks)


def test_actual_section_week_and_separate_preparation_date():
    tasks = inventory()
    target = datetime(2026, 10, 2, 23, 59, 59, tzinfo=KST)
    scoped = scope_tasks(tasks, course_weeks=("기초전자실험:5",), prepare_by=target)
    assert len(scoped) == 5
    assert all(t.week_number == 5 and t.preparation_date == target for t in scoped)
    report = next(t for t in scoped if "결과보고서" in t.raw_title)
    assert report.due_date == datetime(2026, 10, 9, 9, 0, tzinfo=KST)
    assert report.plan_date is None
    assert "수업 준비 목표" in report.memo
    assert all(t.preparation_date is None for t in tasks)


def test_scopes_exclude_other_undated_weeks_and_reject_unknown_course():
    tasks = inventory()
    original = next(t for t in tasks if t.course_id == "1113")
    later = original.model_copy(update={"id": "later", "week_number": 10})
    selected = scope_tasks(tasks + [later], course_weeks=("디지털시스템설계:5",))
    assert selected == [original]
    with pytest.raises(ConfigError):
        scope_tasks(tasks, course_weeks=("없는과목:5",))
    due = datetime(2026, 10, 2, 23, 59, 59, tzinfo=KST)
    union = scope_tasks(tasks, course_weeks=("기초전자실험:5",), due_before=due)
    assert any(t.due_date and t.due_date > due for t in union)
    assert any(t.course_id == "1478" for t in union)
    assert all(t.id != "later" for t in union)


def test_course_scope_with_no_incomplete_tasks_is_an_empty_success():
    course = CourseItem(course_id="123", raw_name="완료 과목", clean_name="완료 과목", url="https://lxp.kau.ac.kr/course/view.php?id=123")
    assert scope_tasks([], course_weeks=("완료 과목:4",), courses=[course]) == []


def test_dashboard_navigation_and_unknown_layout_are_not_silent(sample_settings):
    cid = "1101"
    course = CourseItem(course_id=cid, raw_name="자료구조", clean_name="자료구조", url=f"https://lxp.kau.ac.kr/course/view.php?id={cid}")
    dashboard = '<div class="current-activity"><a href="/mod/vod/view.php?id=9473">5주차: 스택</a></div>'
    assert needs_section_view(dashboard)
    assert sections_url(course.url + "&expandsection=4") == course.url + "&mode=sections"
    page = MagicMock()
    page.goto.return_value.status = 200
    page.content.side_effect = [dashboard, section_html(BASELINE[cid][1])]
    page.wait_for_selector.side_effect = RuntimeError("no error box")
    navigator = CourseNavigator(sample_settings, min_delay=0, max_delay=0)
    html = navigator.navigate_to_course(page, course)
    assert len(parse_lectures_from_course_sections(html, course)) == 1
    assert page.goto.call_args_list[-1].args[0].endswith("&mode=sections")
    with pytest.raises(ActivityCollectionError, match="해석"):
        validate_activity_coverage(dashboard, course)


def test_current_completion_is_not_overridden_by_same_name_material_record():
    cid = "1125"
    course = CourseItem(course_id=cid, raw_name="공수2", clean_name="공수2", url=f"https://lxp.kau.ac.kr/course/view.php?id={cid}")
    lectures = parse_lectures_from_course_sections(section_html(BASELINE[cid][1]), course)
    records = [UblogsActivityStatus(week_number=4, activity_title=lectures[0].title, status="완료", is_completed=True)]
    merged = merge_ublogs_completion(lectures, records, now=NOW)
    assert merged[0].status == AttendanceStatus.INCOMPLETE


def test_future_unlinked_activities_are_inventoried_but_not_available():
    course = CourseItem(course_id="future", raw_name="미래 과목", clean_name="미래 과목", url="https://lxp.kau.ac.kr/course/view.php?id=123")
    html = '<li class="section" id="section-8"><h3 class="sectionname">8주차</h3><ul><li class="activity modtype_ubfile activity-incomplete" id="module-99"><div class="activityname">예정 자료</div><span class="timeopen">2026-10-15 09:00:00</span></li></ul></li>'
    validate_activity_coverage(html, course)
    material = parse_materials_from_course_sections(html, course)[0]
    assert material.module_id == "99" and material.week_number == 8
    assert material.start_date == datetime(2026, 10, 15, 9, 0, tzinfo=KST)
    assert material.due_date is None and not material.is_available
    with pytest.raises(ActivityCollectionError):
        validate_activity_coverage(html.replace('<div class="activityname">예정 자료</div>', ''), course)


def test_progress_http_uses_sections_and_preserves_all_module_identities(sample_settings):
    cid = "1103"
    course = CourseItem(course_id=cid, raw_name="기초전자실험", clean_name="기초전자실험", url=f"https://lxp.kau.ac.kr/course/view.php?id={cid}")
    client = MagicMock()
    def response(url):
        resp = MagicMock(status_code=200)
        resp.text = section_html(BASELINE[cid][1]) if "mode=sections" in url else '<div class="current-activity"></div>' if url == course.url else ""
        return resp
    client.get.side_effect = response
    result = _collect_single_course_progress(client, course, sample_settings, now=NOW)
    assert {item.module_id for item in result.all_items} == {row[1] for row in BASELINE[cid][1]}
    assert all(item.week_number == 5 for item in result.all_items)
    urls = [call.args[0] for call in client.get.call_args_list]
    assert course.url + "&mode=sections" in urls
    assert any("/report/ublogs/completion.php?" in url for url in urls)


def test_collection_error_is_actionable_and_secret_safe():
    error = safe_cli_error(ActivityCollectionError("sensitive-cookie-value"), scope="course")
    assert error.code == "ActivityCollectionError"
    assert "해석" in error.message and "sensitive-cookie-value" not in error.message


def test_source_identity_conflicts_and_duplicates_fail_closed():
    task = inventory(False)[0]
    other_source = task.model_copy(update={"source_url": "https://lxp.kau.ac.kr/mod/vod/view.php?id=99999"})
    existing = ExistingPage(page_id="other", title=task.title, memo=other_source.memo + "\n", priority=task.priority)
    existing.memo = "LMS 바로가기: " + other_source.source_url
    assert plan_sync([task], [existing])[0].code == "source_identity_conflict"
    duplicate = task.model_copy(update={"id": "duplicate", "title": "another title"})
    assert all(action.code == "duplicate_incoming_source" for action in plan_sync([task, duplicate], []))


def test_inventory_completed_item_is_skipped_and_source_survives_title_change():
    tasks = inventory()
    done = next(t for t in tasks if t.is_completed)
    assert isinstance(plan_sync([done], [])[0], SkipAction)
    task = next(t for t in tasks if t.course_id == "1103" and "결과보고서" in t.raw_title)
    existing = ExistingPage(page_id="old-page", title="old display title", memo=task.memo, priority=task.priority, due_date=task.due_date)
    actions = plan_sync([task], [existing])
    assert len(actions) == 1 and not isinstance(actions[0], CreateAction)
    if isinstance(actions[0], UpdateAction):
        assert "Plan" not in actions[0].properties and "상태" not in actions[0].properties


@pytest.mark.parametrize("command,extra", [("check", []), ("sync", []), ("sync", ["--apply"])])
def test_cli_supported_scope_is_applied_before_reporting_and_sync(monkeypatch, sample_settings, command, extra):
    monkeypatch.setattr("coursepilot.cli.get_settings", lambda: sample_settings)
    monkeypatch.setattr("coursepilot.cli.get_current_kst_time", lambda: NOW)
    monkeypatch.setattr("coursepilot.cli.collect_tasks", lambda *a, **kw: PipelineResult(course_count=6, tasks=inventory(kw.get("include_completed", False))))
    engine = MagicMock()
    engine.sync.return_value = SyncResult(enabled=False, dry_run=True)
    monkeypatch.setattr("coursepilot.cli.NotionSyncEngine", lambda **kw: engine)
    result = CliRunner().invoke(cli, [command, "--json", "--course-week", "기초전자실험:5", "--prepare-by", "2026-10-02", *extra])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["summary"]["total_count"] == 5
    if command == "sync":
        args, kwargs = engine.sync.call_args
        assert len(args[0]) == 5 and all(t.week_number == 5 for t in args[0])
        assert kwargs["dry_run"] is (not bool(extra))
    else:
        items = [t for groups in payload["items"].values() for group in groups for t in group["items"]]
        assert all(t["preparation_date"].startswith("2026-10-02") for t in items)
