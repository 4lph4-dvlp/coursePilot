"""Allowlist and exit-code unit coverage for safe_cli_error / exit_code_for (D-12, D-14)."""

from pydantic import ValidationError

from kau_assistant.config import Settings
from kau_assistant.errors import EXIT_FATAL, EXIT_OK, EXIT_PARTIAL, exit_code_for, safe_cli_error
from kau_assistant.exceptions import (
    AuthenticationError,
    ConfigError,
    CourseAccessDeniedError,
    KauAssistantError,
    NavigationTimeoutError,
    NotionAuthenticationError,
)
from kau_assistant.report_models import ErrorItem

SECRET_PW = "supersecretpassword"


def test_redaction_allowlist_messages():
    config_err = ConfigError("LMS_USERNAME 환경 변수가 설정되지 않았습니다.")
    notion_err = NotionAuthenticationError("Notion 토큰이 유효하지 않습니다: 대상 데이터베이스를 찾을 수 없습니다.")
    auth_err = AuthenticationError(f"로그인 실패: 비밀번호={SECRET_PW}")
    nav_err = NavigationTimeoutError(f"페이지 이동 실패 (token={SECRET_PW})")
    denied_err = CourseAccessDeniedError(f"접근 거부: {SECRET_PW}")
    bare_err = KauAssistantError(f"알 수 없는 내부 오류: {SECRET_PW}")
    runtime_err = RuntimeError(f"예상치 못한 오류: {SECRET_PW}")

    config_item = safe_cli_error(config_err, scope="fatal")
    notion_item = safe_cli_error(notion_err, scope="notion", course_id="c1")
    auth_item = safe_cli_error(auth_err, scope="fatal")
    nav_item = safe_cli_error(nav_err, scope="course", course_id="c2", course_name="공학수학 2")
    denied_item = safe_cli_error(denied_err, scope="course", course_id="c3", task_title="3주차 과제")
    bare_item = safe_cli_error(bare_err, scope="fatal")
    runtime_item = safe_cli_error(runtime_err, scope="fatal")

    # ConfigError / NotionIntegrationError surface their own message verbatim.
    assert config_item.message == str(config_err)
    assert notion_item.message == str(notion_err)
    assert notion_item.course_id == "c1"

    for item, err in (
        (auth_item, auth_err),
        (nav_item, nav_err),
        (denied_item, denied_err),
        (bare_item, bare_err),
        (runtime_item, runtime_err),
    ):
        assert SECRET_PW not in item.message
        assert item.message != str(err)
        assert item.code == type(err).__name__

    assert nav_item.course_name == "공학수학 2"
    assert denied_item.task_title == "3주차 과제"


def test_redaction_validation_error_lists_field_names_only():
    try:
        Settings(timeout_ms="not-a-number", _env_file=None)
        raise AssertionError("expected ValidationError")
    except ValidationError as error:
        item = safe_cli_error(error, scope="fatal")

    assert item.code == "ConfigError"
    assert "TIMEOUT_MS" in item.message
    assert "not-a-number" not in item.message


def test_exit_code_for_mapping():
    course_error = ErrorItem(scope="course", code="X", message="m")
    notion_error = ErrorItem(scope="notion", code="Y", message="m")
    fatal_error = ErrorItem(scope="fatal", code="Z", message="m")

    assert exit_code_for([]) == EXIT_OK
    assert exit_code_for([course_error]) == EXIT_PARTIAL
    assert exit_code_for([notion_error]) == EXIT_PARTIAL
    assert exit_code_for([fatal_error]) == EXIT_FATAL
    assert exit_code_for([course_error, fatal_error]) == EXIT_FATAL


def test_unsupported_lms_error_static_message():
    from kau_assistant.config import DEFAULT_LMS_URL
    from kau_assistant.exceptions import UnsupportedLmsError

    err = UnsupportedLmsError(f"Leaked secret: {SECRET_PW}")
    item = safe_cli_error(err, scope="fatal")

    assert item.code == "UnsupportedLmsError"
    assert "LMS_URL" in item.message
    assert "Coursemos" in item.message
    assert DEFAULT_LMS_URL in item.message
    assert SECRET_PW not in item.message
    assert str(err) not in item.message
    assert exit_code_for([item]) == EXIT_FATAL


def test_auth_message_mentions_lms_url():
    auth_err = AuthenticationError("auth failed")
    item = safe_cli_error(auth_err, scope="fatal")
    assert item.message.startswith("LMS 로그인에 실패했습니다")
    assert "LMS_URL" in item.message

