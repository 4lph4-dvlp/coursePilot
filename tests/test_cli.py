"""CliRunner coverage for the `check`/`sync` commands' JSON contract, stderr routing, and flags."""

import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from kau_assistant.cli import cli
from kau_assistant.config import Settings
from kau_assistant.domain.models import (
    SyncTask,
    TaskPriority,
    TaskSelect,
    TaskStatus,
    TaskType,
)
from kau_assistant.exceptions import AuthenticationError, ConfigError
from kau_assistant.notion import NotionSyncEngine
from kau_assistant.notion.models import ExistingPage, NotionTarget
from kau_assistant.pipeline import PipelineResult
from kau_assistant.report_models import ErrorItem
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


def test_exit_code_zero_on_success(fake_pipeline):
    runner = CliRunner()
    result = runner.invoke(cli, ["check", "--json"])

    assert result.exit_code == 0, result.output


def test_exit_code_one_on_course_errors(monkeypatch, sample_settings):
    monkeypatch.setattr("kau_assistant.cli.get_settings", lambda: sample_settings)

    course_error = ErrorItem(
        scope="course",
        code="CourseAccessDeniedError",
        message="이 과목 페이지에 접근할 수 없습니다(권한 없음 또는 비공개 과목).",
        course_id="c9",
    )

    def _fake_collect_tasks(settings, **kwargs):
        if kwargs.get("progress") is not None:
            kwargs["progress"](1, 2, "자료구조")
        return PipelineResult(course_count=2, tasks=_sample_tasks(), errors=[course_error])

    monkeypatch.setattr("kau_assistant.cli.collect_tasks", _fake_collect_tasks)

    runner = CliRunner()
    result = runner.invoke(cli, ["check", "--json"])

    assert result.exit_code == 1, result.output
    payload = json.loads(result.stdout)
    assert payload["errors"][0]["scope"] == "course"


def test_exit_code_two_on_config_error(monkeypatch, sample_settings):
    monkeypatch.setattr("kau_assistant.cli.get_settings", lambda: sample_settings)

    def _fake_collect_tasks(settings, **kwargs):
        raise ConfigError("LMS_USERNAME 환경 변수가 설정되지 않았습니다.")

    monkeypatch.setattr("kau_assistant.cli.collect_tasks", _fake_collect_tasks)

    runner = CliRunner()
    result = runner.invoke(cli, ["check", "--json"])

    assert result.exit_code == 2, result.output
    payload = json.loads(result.stdout)
    assert payload["errors"][0]["scope"] == "fatal"
    assert "LMS_USERNAME" in payload["errors"][0]["message"]
    assert payload["summary"]["course_count"] == 0
    assert payload["summary"]["total_count"] == 0
    assert payload["items"]["overdue"] == []
    assert payload["items"]["due_within_24h"] == []
    assert payload["items"]["later"] == []


def test_exit_code_two_on_settings_validation_error(monkeypatch):
    def _raise_settings() -> Settings:
        return Settings(timeout_ms="not-a-number", _env_file=None)

    monkeypatch.setattr("kau_assistant.cli.get_settings", _raise_settings)

    runner = CliRunner()
    result = runner.invoke(cli, ["check", "--json"])

    assert result.exit_code == 2, result.output
    payload = json.loads(result.stdout)
    assert payload["errors"][0]["scope"] == "fatal"
    assert payload["errors"][0]["code"] == "ConfigError"


def test_redaction_fatal_auth_error_json_and_human(monkeypatch, sample_settings):
    monkeypatch.setattr("kau_assistant.cli.get_settings", lambda: sample_settings)

    def _fake_collect_tasks(settings, **kwargs):
        raise AuthenticationError(
            f"로그인 실패: 사용자={sample_settings.lms_username}, 비밀번호={sample_settings.lms_password}"
        )

    monkeypatch.setattr("kau_assistant.cli.collect_tasks", _fake_collect_tasks)

    runner = CliRunner()

    json_result = runner.invoke(cli, ["check", "--json"])
    assert json_result.exit_code == 2, json_result.output
    assert sample_settings.lms_username not in json_result.stdout
    assert sample_settings.lms_password not in json_result.stdout
    assert sample_settings.lms_username not in json_result.stderr
    assert sample_settings.lms_password not in json_result.stderr

    human_result = runner.invoke(cli, ["check"], env={"COLUMNS": "200"})
    assert human_result.exit_code == 2, human_result.output
    assert sample_settings.lms_username not in human_result.stdout
    assert sample_settings.lms_password not in human_result.stdout
    assert sample_settings.lms_username not in human_result.stderr
    assert sample_settings.lms_password not in human_result.stderr


def test_redaction_unexpected_exception(monkeypatch, sample_settings):
    monkeypatch.setattr("kau_assistant.cli.get_settings", lambda: sample_settings)

    def _fake_collect_tasks(settings, **kwargs):
        raise RuntimeError(f"unexpected failure token={sample_settings.notion_token}")

    monkeypatch.setattr("kau_assistant.cli.collect_tasks", _fake_collect_tasks)

    runner = CliRunner()
    result = runner.invoke(cli, ["check", "--json"])

    assert result.exit_code == 2, result.output
    assert sample_settings.notion_token not in result.stdout
    assert sample_settings.notion_token not in result.stderr
    payload = json.loads(result.stdout)
    assert payload["errors"][0]["code"] == "RuntimeError"


def test_redaction_settings_values_never_printed(fake_pipeline, sample_settings):
    runner = CliRunner()

    json_result = runner.invoke(cli, ["check", "--json"])
    human_result = runner.invoke(cli, ["check"], env={"COLUMNS": "200"})

    secrets = (
        sample_settings.lms_username,
        sample_settings.lms_password,
        sample_settings.notion_token,
    )
    for result in (json_result, human_result):
        for secret in secrets:
            assert secret not in result.stdout
            assert secret not in result.stderr


SYNC_OLD_DUE = NOW - timedelta(days=1)
SYNC_NEW_DUE = NOW + timedelta(days=5)
SYNC_UNCHANGED_DUE = NOW + timedelta(days=10)


def _sync_task(
    *,
    task_id: str,
    title: str,
    course_id: str = "course-2",
    course_name: str = "공학수학 2",
    course_abbr: str = "공수2",
    due_date: datetime | None,
    memo: str = "LMS 바로가기: https://lms.kau.ac.kr/course/2",
) -> SyncTask:
    return SyncTask(
        id=task_id,
        course_id=course_id,
        course_name=course_name,
        course_abbr=course_abbr,
        title=title,
        raw_title=title,
        task_type=TaskType.ASSIGNMENT,
        selection=TaskSelect.EVENT,
        due_date=due_date,
        priority=TaskPriority.P2,
        status=TaskStatus.NOT_STARTED,
        memo=memo,
        source_url="https://lms.kau.ac.kr/course/2",
    )


def _sync_sample_tasks() -> list[SyncTask]:
    """One new title, one matching an existing page with a different due date, one unchanged."""
    return [
        _sync_task(task_id="task-new", title="[공수2] 신규 과제 제출", due_date=SYNC_NEW_DUE),
        _sync_task(task_id="task-update", title="[공수2] 3주차 과제 제출", due_date=SYNC_NEW_DUE),
        _sync_task(
            task_id="task-unchanged",
            title="[자구] 4주차 강의 시청",
            course_id="course-1",
            course_name="자료구조",
            course_abbr="자구",
            due_date=SYNC_UNCHANGED_DUE,
            memo="LMS 바로가기: https://lms.kau.ac.kr/course/1",
        ),
    ]


def _fake_notion_client() -> MagicMock:
    """MagicMock Notion client following the tests/test_notion_engine.py fixture pattern."""
    client = MagicMock()
    client.resolve_target.return_value = NotionTarget(
        database_id="database-id", data_source_id="source-id", title="Scheduler"
    )
    client.query_existing_pages.return_value = [
        ExistingPage(
            page_id="page-update",
            title="[공수2] 3주차 과제 제출",
            due_date=SYNC_OLD_DUE,
            priority=TaskPriority.P2,
            memo="LMS 바로가기: https://lms.kau.ac.kr/course/2",
        ),
        ExistingPage(
            page_id="page-unchanged",
            title="[자구] 4주차 강의 시청",
            due_date=SYNC_UNCHANGED_DUE,
            priority=TaskPriority.P2,
            memo="LMS 바로가기: https://lms.kau.ac.kr/course/1",
        ),
    ]
    return client


def test_sync_dry_run_default_never_writes(monkeypatch, sample_settings):
    monkeypatch.setattr("kau_assistant.cli.get_settings", lambda: sample_settings)

    def _fake_collect_tasks(settings, *, headed=False, relogin=False, progress=None, now=None):
        if progress is not None:
            progress(1, 2, "자료구조")
        return PipelineResult(course_count=2, tasks=_sync_sample_tasks(), errors=[])

    monkeypatch.setattr("kau_assistant.cli.collect_tasks", _fake_collect_tasks)

    fake_client = _fake_notion_client()

    def _engine_factory(settings=None, client=None):
        return NotionSyncEngine(settings=settings, client=fake_client)

    monkeypatch.setattr("kau_assistant.cli.NotionSyncEngine", _engine_factory)

    runner = CliRunner()
    result = runner.invoke(cli, ["sync", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert set(payload.keys()) == {
        "schema_version",
        "command",
        "generated_at",
        "summary",
        "sync",
        "errors",
    }
    assert payload["schema_version"] == 1
    assert payload["command"] == "sync"
    assert payload["sync"]["dry_run"] is True
    assert payload["sync"]["applied"] is False
    assert len(payload["sync"]["create"]) == 1
    assert len(payload["sync"]["update"]) == 1
    assert payload["sync"]["update"][0]["changes"][0]["field"] == "DueDate"
    assert "before" in payload["sync"]["update"][0]["changes"][0]
    assert "after" in payload["sync"]["update"][0]["changes"][0]
    assert len(payload["sync"]["skip"]) == 1
    assert payload["sync"]["skip"][0]["reason"] == "unchanged"

    fake_client.create_page.assert_not_called()
    fake_client.update_page.assert_not_called()
