"""Pure reporter coverage: grouping, detail blocks, no truncation, JSON encoding (D-01..D-05, D-09)."""

import io
import json
from datetime import datetime, timedelta

from rich.console import Console

from coursepilot.domain.models import (
    SyncTask,
    TaskPriority,
    TaskSelect,
    TaskStatus,
    TaskType,
)
from coursepilot.notion.models import (
    CreateAction,
    FieldDiff,
    NotionTarget,
    SkipAction,
    SyncResult,
    SyncStats,
    UpdateAction,
)
from coursepilot.report_models import ErrorItem
from coursepilot.reporter import (
    build_check_report,
    build_sync_report,
    format_remaining,
    render_check_report,
    render_sync_report,
    to_json,
)
from coursepilot.scraper.date_parser import KST

NOW = datetime(2026, 9, 23, 12, 0, tzinfo=KST)


def _task(
    *,
    task_id: str,
    course_id: str = "course-1",
    course_name: str = "자료구조",
    course_abbr: str = "자구",
    title: str = "[자구] 3주차 강의 시청",
    task_type: TaskType = TaskType.LECTURE,
    due_date: datetime | None = None,
    is_overdue: bool = False,
    is_urgent: bool = False,
    memo: str = "LMS 바로가기: https://lms.kau.ac.kr/course/1",
    source_url: str = "https://lms.kau.ac.kr/course/1",
) -> SyncTask:
    return SyncTask(
        id=task_id,
        course_id=course_id,
        course_name=course_name,
        course_abbr=course_abbr,
        title=title,
        raw_title=title,
        task_type=task_type,
        selection=TaskSelect.ROUTINE if task_type == TaskType.LECTURE else TaskSelect.EVENT,
        due_date=due_date,
        priority=TaskPriority.P2,
        status=TaskStatus.NOT_STARTED,
        memo=memo,
        is_overdue=is_overdue,
        is_urgent=is_urgent,
        source_url=source_url,
    )


def _render(report, *, width: int = 200) -> str:
    buf = io.StringIO()
    console = Console(file=buf, width=width, color_system=None)
    render_check_report(report, console)
    return buf.getvalue()


def test_grouping_sections_by_urgency_then_course():
    tasks = [
        _task(
            task_id="overdue-1",
            course_id="c1",
            course_name="자료구조",
            course_abbr="자구",
            due_date=NOW - timedelta(days=1),
            is_overdue=True,
        ),
        _task(
            task_id="urgent-1",
            course_id="c2",
            course_name="공학수학 2",
            course_abbr="공수2",
            due_date=NOW + timedelta(hours=1),
            is_urgent=True,
        ),
        _task(
            task_id="later-1",
            course_id="c1",
            course_name="자료구조",
            course_abbr="자구",
            due_date=NOW + timedelta(days=5),
        ),
        _task(
            task_id="later-2",
            course_id="c2",
            course_name="공학수학 2",
            course_abbr="공수2",
            due_date=NOW + timedelta(days=6),
        ),
        _task(
            task_id="later-3",
            course_id="c1",
            course_name="자료구조",
            course_abbr="자구",
            due_date=NOW + timedelta(days=7),
        ),
    ]
    report = build_check_report(tasks, course_count=2, now=NOW)

    assert [g.course_id for g in report.items.overdue] == ["c1"]
    assert [g.course_id for g in report.items.due_within_24h] == ["c2"]
    assert [g.course_id for g in report.items.later] == ["c1", "c2"]
    assert [i.task_id for i in report.items.later[0].items] == ["later-1", "later-3"]


def test_grouping_includes_very_old_overdue():
    tasks = [_task(task_id="ancient", due_date=NOW - timedelta(days=200), is_overdue=True)]
    report = build_check_report(tasks, course_count=1, now=NOW)

    assert report.summary.overdue_count == 1
    ids = [i.task_id for group in report.items.overdue for i in group.items]
    assert "ancient" in ids


def test_grouping_summary_counts():
    tasks = [
        _task(task_id="overdue-1", due_date=NOW - timedelta(days=1), is_overdue=True),
        _task(task_id="urgent-1", due_date=NOW + timedelta(hours=1), is_urgent=True),
        _task(task_id="later-1", due_date=NOW + timedelta(days=1)),
    ]
    report = build_check_report(tasks, course_count=3, now=NOW)

    assert report.summary.course_count == 3
    assert report.summary.overdue_count == 1
    assert report.summary.due_within_24h_count == 1
    assert report.summary.later_count == 1
    assert report.summary.total_count == 3
    assert report.summary.error_count == 0


def test_detail_only_for_urgent_and_overdue():
    tasks = [
        _task(task_id="overdue-1", due_date=NOW - timedelta(days=1), is_overdue=True, memo="과거 메모"),
        _task(
            task_id="urgent-1",
            due_date=NOW + timedelta(hours=1),
            is_urgent=True,
            memo="긴급 메모",
            source_url="https://lms.kau.ac.kr/urgent",
        ),
        _task(task_id="later-1", due_date=NOW + timedelta(days=5), memo="나중 메모"),
    ]
    report = build_check_report(tasks, course_count=1, now=NOW)

    overdue_item = report.items.overdue[0].items[0]
    urgent_item = report.items.due_within_24h[0].items[0]
    later_item = report.items.later[0].items[0]

    assert overdue_item.detail == "과거 메모"
    assert urgent_item.detail == "긴급 메모"
    assert later_item.detail is None

    output = _render(report)
    assert "긴급 메모" in output
    assert "https://lms.kau.ac.kr/urgent" in output
    assert "나중 메모" not in output


def test_detail_errors_section_rendered():
    errors = [
        ErrorItem(
            scope="course",
            code="CourseAccessDeniedError",
            message="이 과목 페이지에 접근할 수 없습니다(권한 없음 또는 비공개 과목).",
            course_name="네트워크",
        ),
        ErrorItem(
            scope="fatal",
            code="AuthenticationError",
            message="LMS 로그인에 실패했습니다. .env의 LMS 계정 정보를 직접 확인하거나 --relogin 또는 --headed로 다시 시도하세요.",
        ),
    ]
    report = build_check_report([], course_count=0, errors=errors, now=NOW)
    output = _render(report)

    assert "CourseAccessDeniedError" in output
    assert "네트워크" in output
    assert "치명적 오류" in output
    assert "LMS 로그인에 실패했습니다" in output


def test_no_truncation_sixty_items_json_and_rich():
    tasks = [
        _task(
            task_id=f"lec-{i}",
            course_id=f"c{i}",
            course_name=f"과목{i}",
            course_abbr=f"과{i}",
            title=f"[과{i}] {i}주차 강의 시청 - 이것은 매우 긴 제목입니다 테스트를 위한 긴 텍스트",
            due_date=NOW + timedelta(days=30),
        )
        for i in range(60)
    ]
    report = build_check_report(tasks, course_count=60, now=NOW)

    json_output = to_json(report)
    rich_output = _render(report, width=200)

    for i in range(60):
        title = f"[과{i}] {i}주차 강의 시청 - 이것은 매우 긴 제목입니다 테스트를 위한 긴 텍스트"
        assert title in json_output
        assert title in rich_output


def test_no_truncation_narrow_console_no_ellipsis():
    tasks = [
        _task(
            task_id="urgent-long",
            due_date=NOW + timedelta(hours=2),
            is_urgent=True,
            title="[자구] 매우 매우 매우 매우 긴 강의 제목이 여기 들어갑니다 정말로 깁니다",
            memo="매우 매우 매우 매우 긴 메모 내용이 여기 들어갑니다 정말로 깁니다",
        )
    ]
    report = build_check_report(tasks, course_count=1, now=NOW)
    output = _render(report, width=40)

    assert "…" not in output


def test_detail_bracketed_titles_render_literally():
    tasks = [
        _task(
            task_id="bracket-1",
            course_id="c1",
            title="[공수2] 3주차",
            due_date=NOW + timedelta(hours=1),
            is_urgent=True,
            memo="[b]x[/b] 굵게 표시되지 않아야 함",
        )
    ]
    report = build_check_report(tasks, course_count=1, now=NOW)
    output = _render(report)

    assert "[공수2] 3주차" in output
    assert "[b]x[/b]" in output


def test_json_contract_korean_unescaped():
    tasks = [_task(task_id="kr-1", course_name="자료구조", due_date=NOW + timedelta(days=1))]
    report = build_check_report(tasks, course_count=1, now=NOW)

    output = to_json(report)
    assert "자료구조" in output
    assert "\\u" not in output


def test_format_remaining_cases():
    now = datetime(2026, 9, 23, 12, 0, tzinfo=KST)
    assert format_remaining(now + timedelta(hours=3, minutes=12), now) == "3시간 12분 남음"
    assert format_remaining(now + timedelta(days=1, hours=4), now) == "1일 4시간 남음"
    assert format_remaining(now + timedelta(minutes=45), now) == "45분 남음"
    assert format_remaining(now - timedelta(days=2, hours=3), now) == "2일 3시간 지남"
    assert format_remaining(None, now) == "마감일 없음"


def _render_sync(report, *, width: int = 200) -> str:
    buf = io.StringIO()
    console = Console(file=buf, width=width, color_system=None)
    render_sync_report(report, console)
    return buf.getvalue()


def _sync_result_sample(*, dry_run: bool = True) -> SyncResult:
    new_task = _task(task_id="t1", title="[공수2] 신규 과제 제출", due_date=NOW + timedelta(days=1))
    target = NotionTarget(database_id="db-id", data_source_id="ds-id", title="Scheduler")
    created = [CreateAction(task_id="t1", title=new_task.title, task=new_task)]
    updated = [
        UpdateAction(
            task_id="t2",
            title="[공수2] 3주차 과제 제출",
            page_id="page-1",
            diffs=[
                FieldDiff(
                    property_name="DueDate",
                    before=NOW - timedelta(days=1),
                    after=NOW + timedelta(days=2),
                )
            ],
        )
    ]
    skipped = [SkipAction(task_id="t3", title="[자구] 4주차 강의 시청", page_id="page-2", reason="unchanged")]
    return SyncResult(
        enabled=True,
        dry_run=dry_run,
        target=target,
        created=created,
        updated=updated,
        skipped=skipped,
        errors=[],
        stats=SyncStats(total=3, created=1, updated=1, skipped=1, errors=0),
    )


def test_json_contract_sync_envelope_keys():
    sync_result = _sync_result_sample()
    report = build_sync_report([], sync_result, course_count=2, now=NOW)

    payload = json.loads(to_json(report))
    assert set(payload["sync"].keys()) == {
        "enabled",
        "dry_run",
        "applied",
        "target_title",
        "notice",
        "create",
        "update",
        "skip",
        "counts",
    }


def test_detail_sync_render_sections():
    dry_run_report = build_sync_report([], _sync_result_sample(dry_run=True), course_count=2, now=NOW)
    dry_run_output = _render_sync(dry_run_report)

    assert "미리보기" in dry_run_output
    assert "--apply" in dry_run_output
    assert "DueDate" in dry_run_output
    assert "->" in dry_run_output
    assert "변경 없음" in dry_run_output

    apply_report = build_sync_report([], _sync_result_sample(dry_run=False), course_count=2, now=NOW)
    apply_output = _render_sync(apply_report)
    assert "적용 완료" in apply_output

    errors_report = build_sync_report(
        [],
        None,
        course_count=0,
        errors=[
            ErrorItem(
                scope="notion",
                code="NotionAuthenticationError",
                message="Notion 토큰이 유효하지 않습니다.",
            )
        ],
        now=NOW,
    )
    errors_output = _render_sync(errors_report)
    assert "NotionAuthenticationError" in errors_output


def test_detail_sync_no_truncation():
    created = [
        CreateAction(
            task_id=f"t{i}",
            title=f"[과{i}] {i}주차 신규 과제 제출 - 매우 긴 제목입니다 테스트용 텍스트",
            task=_task(
                task_id=f"t{i}",
                title=f"[과{i}] {i}주차 신규 과제 제출 - 매우 긴 제목입니다 테스트용 텍스트",
                due_date=NOW + timedelta(days=i),
            ),
        )
        for i in range(40)
    ]
    sync_result = SyncResult(
        enabled=True,
        dry_run=True,
        target=None,
        created=created,
        updated=[],
        skipped=[],
        errors=[],
        stats=SyncStats(total=40, created=40, updated=0, skipped=0, errors=0),
    )
    report = build_sync_report([], sync_result, course_count=40, now=NOW)

    wide_output = _render_sync(report, width=200)
    for i in range(40):
        title = f"[과{i}] {i}주차 신규 과제 제출 - 매우 긴 제목입니다 테스트용 텍스트"
        assert title in wide_output

    narrow_output = _render_sync(report, width=40)
    assert "…" not in narrow_output


def test_render_check_report_shows_notice_before_sections():
    report = build_check_report([], course_count=0, now=NOW)
    assert len(report.notices) == 1
    assert report.notices[0].code == "no_courses_found"

    output = _render(report)
    assert "안내" in output
    assert " ".join(report.notices[0].message.split()) in " ".join(output.split())
    notice_idx = output.find("안내")
    overdue_section_idx = output.rfind("기한 초과")
    assert notice_idx < overdue_section_idx


def test_render_sync_report_shows_notice():
    report = build_sync_report([], None, course_count=0, now=NOW)
    assert len(report.notices) == 1
    assert report.notices[0].code == "no_courses_found"

    output = _render_sync(report)
    assert "안내" in output
    assert " ".join(report.notices[0].message.split()) in " ".join(output.split())


def test_render_without_notices_has_no_notice_heading():
    tasks = [_task(task_id="t1", due_date=NOW + timedelta(days=1))]
    check_report = build_check_report(tasks, course_count=1, now=NOW)
    assert check_report.notices == []
    check_output = _render(check_report)
    assert "안내" not in check_output

    sync_report = build_sync_report(tasks, None, course_count=1, now=NOW)
    assert sync_report.notices == []
    sync_output = _render_sync(sync_report)
    assert "안내" not in sync_output


def test_no_courses_notice_names_explicit_school_selection():
    from coursepilot.reporter import NO_COURSES_NOTICE_MESSAGE

    assert "LMS_URL" in NO_COURSES_NOTICE_MESSAGE
    assert "LMS_PROFILE" in NO_COURSES_NOTICE_MESSAGE
