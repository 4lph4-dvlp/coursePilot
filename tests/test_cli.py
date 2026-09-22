"""CliRunner coverage for the `check` command's JSON contract, stderr routing, and flags."""

import json
from datetime import datetime, timedelta

import pytest
from click.testing import CliRunner

from kau_assistant.cli import cli
from kau_assistant.domain.models import (
    SyncTask,
    TaskPriority,
    TaskSelect,
    TaskStatus,
    TaskType,
)
from kau_assistant.pipeline import PipelineResult
from kau_assistant.scraper.date_parser import KST

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


def _sample_tasks() -> list[SyncTask]:
    return [
        _task(
            task_id="lec-overdue",
            course_id="course-1",
            course_name="자료구조",
            course_abbr="자구",
            title="[자구] 3주차 강의 시청",
            task_type=TaskType.LECTURE,
            due_date=NOW - timedelta(days=200),
            is_overdue=True,
        ),
        _task(
            task_id="assign-urgent",
            course_id="course-2",
            course_name="공학수학 2",
            course_abbr="공수2",
            title="[공수2] 3주차 과제 제출",
            task_type=TaskType.ASSIGNMENT,
            due_date=NOW + timedelta(hours=3),
            is_urgent=True,
        ),
        _task(
            task_id="lec-later",
            course_id="course-1",
            course_name="자료구조",
            course_abbr="자구",
            title="[자구] 4주차 강의 시청",
            task_type=TaskType.LECTURE,
            due_date=NOW + timedelta(days=10),
        ),
        _task(
            task_id="assign-no-due",
            course_id="course-2",
            course_name="공학수학 2",
            course_abbr="공수2",
            title="[공수2] 자유 게시판 글쓰기",
            task_type=TaskType.FORUM,
            due_date=None,
        ),
    ]


@pytest.fixture
def fake_pipeline(monkeypatch, sample_settings):
    """Patches cli.get_settings/collect_tasks so no real .env or browser is ever touched."""
    monkeypatch.setattr("kau_assistant.cli.get_settings", lambda: sample_settings)

    calls: dict = {}

    def _fake_collect_tasks(settings, *, headed=False, relogin=False, progress=None, now=None):
        calls["settings"] = settings
        calls["headed"] = headed
        calls["relogin"] = relogin
        calls["now"] = now
        if progress is not None:
            progress(1, 2, "자료구조")
        return PipelineResult(course_count=2, tasks=_sample_tasks(), errors=[])

    monkeypatch.setattr("kau_assistant.cli.collect_tasks", _fake_collect_tasks)
    return calls


def test_json_contract_check_envelope(fake_pipeline):
    runner = CliRunner()
    result = runner.invoke(cli, ["check", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert set(payload.keys()) == {
        "schema_version",
        "command",
        "generated_at",
        "summary",
        "items",
        "errors",
    }
    assert payload["schema_version"] == 1
    assert payload["command"] == "check"
    assert set(payload["items"].keys()) == {"overdue", "due_within_24h", "later"}
    assert "[자구] 3주차 강의 시청" in result.stdout


def test_stderr_only_progress(fake_pipeline):
    runner = CliRunner()
    result = runner.invoke(cli, ["check", "--json"])

    assert "[1/2] 자료구조 수집 중" in result.stderr
    assert "[1/2] 자료구조 수집 중" not in result.stdout
    json.loads(result.stdout)


def test_check_passes_headed_and_relogin_flags(fake_pipeline):
    runner = CliRunner()
    result = runner.invoke(cli, ["check", "--json", "--headed", "--relogin"])

    assert result.exit_code == 0, result.output
    assert fake_pipeline["headed"] is True
    assert fake_pipeline["relogin"] is True


def test_check_rejects_unknown_option(fake_pipeline):
    runner = CliRunner()
    result = runner.invoke(cli, ["check", "--course", "자료구조"])

    assert result.exit_code == 2


def test_human_default_renders_sections(fake_pipeline):
    runner = CliRunner()
    result = runner.invoke(cli, ["check"], env={"COLUMNS": "200"})

    assert result.exit_code == 0, result.output
    for heading in ("기한 초과", "24시간 이내", "이후 일정"):
        assert heading in result.stdout
    with pytest.raises(json.JSONDecodeError):
        json.loads(result.stdout)


def test_main_utf8_stdout_under_cp949(monkeypatch, sample_settings):
    import io as io_mod

    from kau_assistant.cli import main

    monkeypatch.setattr("kau_assistant.cli.get_settings", lambda: sample_settings)

    special_task = _task(
        task_id="urgent-special",
        title="[자구] 3주차 과제 제출 ✅",
        due_date=NOW + timedelta(hours=2),
        is_urgent=True,
        memo="완료 표시 ✅",
    )

    def _fake_collect_tasks(settings, *, headed=False, relogin=False, progress=None, now=None):
        return PipelineResult(course_count=1, tasks=[special_task], errors=[])

    monkeypatch.setattr("kau_assistant.cli.collect_tasks", _fake_collect_tasks)

    stdout_buf = io_mod.TextIOWrapper(io_mod.BytesIO(), encoding="cp949")
    stderr_buf = io_mod.TextIOWrapper(io_mod.BytesIO(), encoding="cp949")
    monkeypatch.setattr("sys.stdout", stdout_buf)
    monkeypatch.setattr("sys.stderr", stderr_buf)

    with pytest.raises(SystemExit) as exc:
        main(["check", "--json"])

    assert exc.value.code == 0
    stdout_buf.flush()
    raw_bytes = stdout_buf.buffer.getvalue()
    payload = json.loads(raw_bytes.decode("utf-8"))
    assert "✅" in json.dumps(payload, ensure_ascii=False)
