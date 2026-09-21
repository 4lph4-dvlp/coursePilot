"""Configuration module using Pydantic Settings."""

from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LMS Settings
    lms_url: str = Field(default="https://lms.kau.ac.kr", description="KAU LMS URL")
    lms_username: str = Field(default="", description="학번/아이디")
    lms_password: str = Field(default="", description="비밀번호")

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
            f"session_cache_path={self.session_cache_path!r}, course_mappings_path={self.course_mappings_path!r})"
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
