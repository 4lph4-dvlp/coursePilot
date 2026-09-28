"""Typed-allowlist secret-safe error conversion and exit-code mapping (D-12, D-14).

Extends the shape of `notion/engine.py`'s `_safe_error` (type checks, never regex
scrubbing) across the full `coursepilot.exceptions` hierarchy plus pydantic's
`ValidationError`, so no LMS/Notion secret can escape through any CLI output path.
"""

from collections.abc import Sequence
from typing import Literal

from pydantic import ValidationError

from coursepilot.exceptions import (
    ActivityCollectionError,
    AuthenticationError,
    ConfigError,
    CourseAccessDeniedError,
    CoursePilotError,
    NavigationTimeoutError,
    NotionIntegrationError,
    UnsupportedLmsError,
)
from coursepilot.report_models import ErrorItem

EXIT_OK = 0
EXIT_PARTIAL = 1
EXIT_FATAL = 2

_AUTH_MESSAGE = (
    "LMS 로그인에 실패했습니다. ~/.coursepilot/.env의 LMS 계정 정보를 직접 확인하거나 "
    "--relogin 또는 --headed로 다시 시도하세요. "
    "로그인 화면을 찾지 못한 경우 ~/.coursepilot/.env의 LMS_URL 또는 LMS_PROFILE이 학교의 Coursemos LMS를 선택하는지 확인하세요."
)
_UNSUPPORTED_LMS_MESSAGE = (
    "LMS_URL에 설정된 사이트에서 Coursemos(Moodle) 강의 목록 구조를 찾지 못했습니다. "
    "~/.coursepilot/.env의 LMS_URL 또는 LMS_PROFILE이 학교의 Coursemos LMS를 선택하는지 확인하세요. "
    "Canvas, Blackboard 등 다른 LMS 플랫폼은 지원하지 않습니다."
)
_NAV_TIMEOUT_MESSAGE = "LMS 페이지 응답이 지연되어 불러오지 못했습니다. 잠시 후 다시 시도하세요."
_COURSE_ACCESS_MESSAGE = "이 과목 페이지에 접근할 수 없습니다(권한 없음 또는 비공개 과목)."
_GENERIC_KNOWN_MESSAGE = "작업을 완료하지 못했습니다."
_GENERIC_UNKNOWN_MESSAGE = "예기치 않은 오류가 발생했습니다."
_VALIDATION_SUFFIX = "~/.coursepilot/.env 파일을 직접 확인하세요."


def _validation_error_message(error: ValidationError) -> str:
    field_names = sorted(
        {str(loc).upper() for err in error.errors() for loc in err.get("loc", ())}
    )
    fields = ", ".join(field_names) if field_names else "설정 값"
    return f"{fields} 값이 올바르지 않습니다. {_VALIDATION_SUFFIX}"


def safe_cli_error(
    error: Exception,
    *,
    scope: Literal["fatal", "course", "notion"],
    course_id: str | None = None,
    course_name: str | None = None,
    task_title: str | None = None,
) -> ErrorItem:
    """Converts any exception into a redacted ErrorItem via a typed allowlist.

    Never includes `str(error)`, `error.args`, `repr`, or a traceback for any
    exception type outside the allowlist below.
    """
    if isinstance(error, ValidationError):
        code = "ConfigError"
        message = _validation_error_message(error)
    elif isinstance(error, (ConfigError, NotionIntegrationError)):
        # These raise sites in this repo build messages from key names or
        # target metadata only, so their own message is already safe to show.
        code = type(error).__name__
        message = str(error)
    elif isinstance(error, AuthenticationError):
        code = type(error).__name__
        message = _AUTH_MESSAGE
    elif isinstance(error, NavigationTimeoutError):
        code = type(error).__name__
        message = _NAV_TIMEOUT_MESSAGE
    elif isinstance(error, CourseAccessDeniedError):
        code = type(error).__name__
        message = _COURSE_ACCESS_MESSAGE
    elif isinstance(error, ActivityCollectionError):
        code = type(error).__name__
        message = "학습활동 목록을 빠짐없이 해석하지 못했습니다. 강의실 화면 형식과 주차별 목록을 확인하세요."
    elif isinstance(error, UnsupportedLmsError):
        code = type(error).__name__
        message = _UNSUPPORTED_LMS_MESSAGE
    elif isinstance(error, CoursePilotError):
        code = type(error).__name__
        message = _GENERIC_KNOWN_MESSAGE
    else:
        code = type(error).__name__
        message = _GENERIC_UNKNOWN_MESSAGE

    return ErrorItem(
        scope=scope,
        code=code,
        message=message,
        course_id=course_id,
        course_name=course_name,
        task_title=task_title,
    )


def exit_code_for(errors: Sequence[ErrorItem]) -> int:
    """Maps collected errors to a process exit code: fatal wins over partial (D-12)."""
    if any(error.scope == "fatal" for error in errors):
        return EXIT_FATAL
    if errors:
        return EXIT_PARTIAL
    return EXIT_OK
