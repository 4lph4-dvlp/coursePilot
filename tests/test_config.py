"""Tests for configuration loader (CONF-01)."""

from pathlib import Path
from kau_assistant.config import Settings, get_settings


def test_default_values(clean_env):
    """Verify default values are properly initialized."""
    settings = Settings(_env_file=None)
    assert settings.lms_url == "https://lxp.kau.ac.kr"
    assert settings.lms_username == ""
    assert settings.lms_password == ""
    assert settings.headless is True
    assert settings.timeout_ms == 30000
    assert settings.notion_database_id == ""
    assert settings.notion_database_name == ""
    assert settings.notion_token == ""
    assert settings.notion_api_key == ""
    assert settings.effective_notion_token == ""
    assert settings.is_notion_configured is False
    assert settings.session_cache_path == Path(".cache/session.json")
    assert settings.course_mappings_path == Path("config/course_mappings.json")


def test_default_lms_url_is_kau_lxp():
    from kau_assistant.config import DEFAULT_LMS_URL
    assert DEFAULT_LMS_URL == "https://lxp.kau.ac.kr"
    assert Settings.model_fields["lms_url"].default == DEFAULT_LMS_URL


def test_env_loading(tmp_path: Path, clean_env):
    """Verify settings load correctly from a custom .env file."""
    env_file = tmp_path / ".env"
    env_file.write_text(
        "LMS_URL=https://custom-lms.kau.ac.kr\n"
        "LMS_USERNAME=2021123456\n"
        "LMS_PASSWORD=mypassword123!\n"
        "NOTION_TOKEN=preferred_notion_token\n"
        "NOTION_API_KEY=legacy_notion_key\n"
        "NOTION_DATABASE_ID=custom-db-id\n"
        "HEADLESS=false\n"
        "TIMEOUT_MS=45000\n",
        encoding="utf-8",
    )

    settings = Settings(_env_file=str(env_file))
    assert settings.lms_url == "https://custom-lms.kau.ac.kr"
    assert settings.lms_username == "2021123456"
    assert settings.lms_password == "mypassword123!"
    assert settings.notion_token == "preferred_notion_token"
    assert settings.notion_api_key == "legacy_notion_key"
    assert settings.effective_notion_token == "preferred_notion_token"
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
        notion_token="preferred_secret_123",
        notion_api_key="legacy_secret_456",
        _env_file=None,
    )
    repr_str = repr(settings)
    str_str = str(settings)

    assert "supersecretpassword" not in repr_str
    assert "preferred_secret_123" not in repr_str
    assert "legacy_secret_456" not in repr_str
    assert "***" in repr_str

    assert "supersecretpassword" not in str_str
    assert "preferred_secret_123" not in str_str
    assert "legacy_secret_456" not in str_str
    assert "***" in str_str


def test_notion_credential_precedence_and_legacy_compatibility():
    preferred = Settings(
        notion_token="preferred",
        notion_api_key="legacy",
        notion_database_id="db-id",
        _env_file=None,
    )
    legacy = Settings(
        notion_api_key="legacy-only",
        notion_database_name="Scheduler",
        _env_file=None,
    )

    assert preferred.effective_notion_token == "preferred"
    assert preferred.is_notion_configured is True
    assert legacy.effective_notion_token == "legacy-only"
    assert legacy.is_notion_configured is True


def test_notion_configuration_requires_credential_and_one_target():
    assert Settings(notion_token="token", notion_database_id="db", _env_file=None).is_notion_configured
    assert Settings(
        notion_token="token", notion_database_name="Scheduler", _env_file=None
    ).is_notion_configured
    assert not Settings(notion_token="token", _env_file=None).is_notion_configured
    assert not Settings(notion_database_id="db", _env_file=None).is_notion_configured


def test_get_settings_singleton(clean_env):
    """Verify get_settings returns the same instance unless reloaded."""
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2

    s3 = get_settings(reload=True)
    assert s3 is not s1
