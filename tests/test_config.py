"""Tests for configuration loader (CONF-01)."""

from pathlib import Path
from kau_assistant.config import Settings, get_settings


def test_default_values(clean_env):
    """Verify default values are properly initialized."""
    settings = Settings(_env_file=None)
    assert settings.lms_url == "https://lms.kau.ac.kr"
    assert settings.lms_username == ""
    assert settings.lms_password == ""
    assert settings.headless is True
    assert settings.timeout_ms == 30000
    assert settings.notion_database_id == "21d53280-64be-80ec-af4e-000b679f03bb"
    assert settings.notion_api_key == ""
    assert settings.session_cache_path == Path(".cache/session.json")
    assert settings.course_mappings_path == Path("config/course_mappings.json")


def test_env_loading(tmp_path: Path, clean_env):
    """Verify settings load correctly from a custom .env file."""
    env_file = tmp_path / ".env"
    env_file.write_text(
        "LMS_URL=https://custom-lms.kau.ac.kr\n"
        "LMS_USERNAME=2021123456\n"
        "LMS_PASSWORD=mypassword123!\n"
        "NOTION_API_KEY=secret_notion_key\n"
        "NOTION_DATABASE_ID=custom-db-id\n"
        "HEADLESS=false\n"
        "TIMEOUT_MS=45000\n",
        encoding="utf-8",
    )

    settings = Settings(_env_file=str(env_file))
    assert settings.lms_url == "https://custom-lms.kau.ac.kr"
    assert settings.lms_username == "2021123456"
    assert settings.lms_password == "mypassword123!"
    assert settings.notion_api_key == "secret_notion_key"
    assert settings.notion_database_id == "custom-db-id"
    assert settings.headless is False
    assert settings.timeout_ms == 45000


def test_env_var_precedence(tmp_path: Path, monkeypatch, clean_env):
    """Verify environment variables take precedence over .env file."""
    env_file = tmp_path / ".env"
    env_file.write_text(
        "LMS_USERNAME=from_file\n"
        "LMS_PASSWORD=password_from_file\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("LMS_USERNAME", "from_environment")
    settings = Settings(_env_file=str(env_file))
    assert settings.lms_username == "from_environment"
    assert settings.lms_password == "password_from_file"


def test_sensitive_info_masking():
    """Verify sensitive fields are masked in __repr__ and __str__."""
    settings = Settings(
        lms_password="supersecretpassword",
        notion_api_key="secret_token_123",
        _env_file=None,
    )
    repr_str = repr(settings)
    str_str = str(settings)

    assert "supersecretpassword" not in repr_str
    assert "secret_token_123" not in repr_str
    assert "***" in repr_str

    assert "supersecretpassword" not in str_str
    assert "secret_token_123" not in str_str
    assert "***" in str_str


def test_get_settings_singleton(clean_env):
    """Verify get_settings returns the same instance unless reloaded."""
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2

    s3 = get_settings(reload=True)
    assert s3 is not s1
