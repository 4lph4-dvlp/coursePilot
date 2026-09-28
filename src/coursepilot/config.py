"""Configuration module using Pydantic Settings."""

from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_LMS_URL = ""
LMS_PROFILES = {"kau": "https://lxp.kau.ac.kr"}


def resolve_data_root(home: Path | None = None) -> Path:
    """Keep private CoursePilot data under the user's home on every install type."""
    return (home or Path.home()) / ".coursepilot"


DATA_ROOT = resolve_data_root()
# Backward-compatible internal name for callers that import PROJECT_ROOT.
PROJECT_ROOT = DATA_ROOT


def resolve_output_dir(output_dir: Path | str | None, default_dir: Path) -> Path:
    """Keep relative explicit output paths under the user data root."""
    if output_dir is None:
        return default_dir
    return resolve_data_path(Path(output_dir))


def resolve_data_path(requested: Path) -> Path:
    """Resolve a user path, refusing relative traversal outside ~/.coursepilot."""
    if requested.is_absolute():
        return requested
    resolved = (DATA_ROOT / requested).resolve()
    if not resolved.is_relative_to(DATA_ROOT.resolve()):
        raise ValueError("상대 경로는 ~/.coursepilot 안에 있어야 합니다.")
    return resolved


class Settings(BaseSettings):
    """Application configuration loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=DATA_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LMS Settings
    lms_url: str = Field(
        default=DEFAULT_LMS_URL,
        description="학교 LMS 주소 (명시적으로 지정하거나 LMS_PROFILE 선택)",
    )
    lms_profile: Literal["", "kau"] = Field(default="", description="선택적 학교 프로필")
    lms_username: str = Field(default="", description="학번/아이디")
    lms_password: str = Field(default="", description="비밀번호")

    @model_validator(mode="after")
    def resolve_lms_profile(self):
        """An explicit URL wins; school profiles are opt-in, never a default."""
        self.lms_url = self.lms_url.strip()
        if not self.lms_url and self.lms_profile:
            self.lms_url = LMS_PROFILES[self.lms_profile]
        # Relative overrides are relative to private CoursePilot data, never the caller's CWD.
        for field_name in ("session_cache_path", "course_mappings_path", "download_dir"):
            path = getattr(self, field_name)
            setattr(self, field_name, resolve_data_path(path))
        return self

    # Execution Options
    headless: bool = Field(default=True, description="헤드리스 브라우저 구동 여부")
    timeout_ms: int = Field(default=30000, description="페이지 네비게이션 타임아웃(ms)")

    # Notion Settings
    notion_token: str = Field(default="", description="Preferred Notion integration token")
    notion_api_key: str = Field(
        default="", description="Legacy Notion integration token input"
    )
    notion_database_id: str = Field(
        default="",
        description="Notion Scheduler Database ID",
    )
    notion_database_name: str = Field(
        default="", description="Notion Scheduler name used for exact discovery"
    )

    @property
    def effective_notion_token(self) -> str:
        """Return the preferred token, falling back to the legacy input."""
        return self.notion_token.strip() or self.notion_api_key.strip()

    @property
    def is_notion_configured(self) -> bool:
        """Whether both a credential and an explicit or discoverable target exist."""
        has_target = bool(self.notion_database_id.strip() or self.notion_database_name.strip())
        return bool(self.effective_notion_token and has_target)

    # Paths
    session_cache_path: Path = Field(
        default=Path(".cache/session.json"),
        description="세션 스토리지 파일 경로",
    )
    course_mappings_path: Path = Field(
        default=Path("config/course_mappings.json"),
        description="과목명 약칭 매핑 파일 경로",
    )
    download_dir: Path = Field(
        default=Path("downloads"),
        description="강의 자료 기본 다운로드 저장 디렉터리 경로",
    )

    def __repr__(self) -> str:
        masked_pw = "***" if self.lms_password else ""
        masked_token = "***" if self.notion_token else ""
        masked_key = "***" if self.notion_api_key else ""
        return (
            f"Settings(lms_url='{self.lms_url}', lms_username='{self.lms_username}', "
            f"lms_password='{masked_pw}', headless={self.headless}, timeout_ms={self.timeout_ms}, "
            f"notion_token='{masked_token}', notion_api_key='{masked_key}', "
            f"notion_database_id='{self.notion_database_id}', "
            f"notion_database_name='{self.notion_database_name}', "
            f"session_cache_path={self.session_cache_path!r}, course_mappings_path={self.course_mappings_path!r}, "
            f"download_dir={self.download_dir!r})"
        )

    def __str__(self) -> str:
        return self.__repr__()


_settings_instance: Settings | None = None


def get_settings(reload: bool = False) -> Settings:
    """Retrieve the cached singleton Settings instance, optionally reloading it."""
    global _settings_instance
    if _settings_instance is None or reload:
        _settings_instance = Settings()
    return _settings_instance
