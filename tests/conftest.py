"""Shared Pytest fixtures for KAU LXP Assistant tests."""

import pytest
from pathlib import Path
from kau_assistant.config import Settings, get_settings


@pytest.fixture
def clean_env(monkeypatch):
    """Ensure sensitive environment variables are isolated during tests."""
    for key in [
        "LMS_URL",
        "LMS_USERNAME",
        "LMS_PASSWORD",
        "NOTION_TOKEN",
        "NOTION_API_KEY",
        "NOTION_DATABASE_ID",
        "NOTION_DATABASE_NAME",
        "HEADLESS",
        "TIMEOUT_MS",
    ]:
        monkeypatch.delenv(key, raising=False)
    # Clear singleton cache
    get_settings(reload=True)
    yield monkeypatch
    get_settings(reload=True)


@pytest.fixture
def sample_settings(tmp_path: Path) -> Settings:
    """Fixture providing a predictable Settings instance."""
    return Settings(
        lms_url="https://lms.kau.ac.kr",
        lms_username="2020123456",
        lms_password="supersecretpassword",
        headless=True,
        timeout_ms=30000,
        notion_token="secret_notion_key_abc123",
        notion_database_id="21d53280-64be-80ec-af4e-000b679f03bb",
        session_cache_path=tmp_path / "session.json",
        course_mappings_path=tmp_path / "course_mappings.json",
    )
