"""Behavioral regressions for the single CoursePilot product identity."""

import importlib.metadata
import os
from pathlib import Path
import subprocess
import sys
import tomllib

import pytest

from coursepilot.config import LMS_PROFILES, Settings
from coursepilot.exceptions import ConfigError
from coursepilot.installer import skill_source_dir
from coursepilot.pipeline import collect_tasks

ROOT = Path(__file__).resolve().parents[1]


def child_python(tmp_path, *args):
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
    return subprocess.run([sys.executable, *args], cwd=tmp_path, env=env, capture_output=True, text=True, encoding="utf-8", timeout=30)


def test_canonical_imports_preserve_module_identity(tmp_path):
    script = '''
import importlib
for suffix in ("config", "domain.models", "scraper.models", "exceptions", "cli", "notion.engine"):
    a = importlib.import_module("coursepilot." + suffix)
    b = importlib.import_module("coursepilot." + suffix)
    assert a is b, suffix
    assert a.__name__.startswith("coursepilot."), a.__name__
    assert a.__spec__.name.startswith("coursepilot."), a.__spec__.name
from coursepilot.config import get_settings
assert get_settings() is get_settings()
'''
    result = child_python(tmp_path, "-c", script)
    assert result.returncode == 0, result.stderr


def test_module_entry_point_works_outside_repository(tmp_path):
    result = child_python(tmp_path, "-m", "coursepilot", "--help")
    assert result.returncode == 0, result.stderr
    assert "CoursePilot" in result.stdout
    assert "check" in result.stdout and "install-skill" in result.stdout


def test_distribution_console_entry_points():
    entries = {entry.name: entry.value for entry in importlib.metadata.distribution("coursepilot").entry_points if entry.group == "console_scripts"}
    assert entries == {"coursepilot": "coursepilot.cli:main"}


def test_manifest_exposes_only_canonical_package_and_command():
    manifest = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert manifest["project"]["name"] == "coursepilot"
    assert manifest["project"]["scripts"] == {"coursepilot": "coursepilot.cli:main"}
    assert manifest["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"] == ["src/coursepilot"]


def test_repository_has_only_canonical_package_and_skill():
    for directory in (ROOT / "src", ROOT / "skills"):
        assert {path.name for path in directory.iterdir() if path.is_dir() and not path.name.startswith(".") and path.name != "__pycache__"} == {"coursepilot"}


def test_school_selection_is_explicit_and_url_overrides_profile(clean_env):
    assert Settings(_env_file=None).lms_url == ""
    assert Settings(lms_profile="kau", _env_file=None).lms_url == LMS_PROFILES["kau"]
    assert Settings(lms_profile="kau", lms_url="https://lms.example.edu", _env_file=None).lms_url == "https://lms.example.edu"
    with pytest.raises(ConfigError, match="LMS_URL"):
        collect_tasks(Settings(lms_username="student", lms_password="secret", _env_file=None), session_factory=lambda **kw: pytest.fail("Browser must not start without a school"))


def test_profile_loads_from_environment(monkeypatch, clean_env):
    monkeypatch.setenv("LMS_PROFILE", "kau")
    assert Settings(_env_file=None).lms_url == LMS_PROFILES["kau"]
    monkeypatch.setenv("LMS_URL", "https://other.example.edu")
    assert Settings(_env_file=None).lms_url == "https://other.example.edu"


def test_all_browser_workflows_require_a_school_before_launch(monkeypatch, clean_env):
    from coursepilot.session_manager import SessionManager
    monkeypatch.setattr("coursepilot.session_manager.sync_playwright", lambda: pytest.fail("No browser may start without a school"))
    with pytest.raises(ConfigError, match="LMS_URL"):
        with SessionManager(settings=Settings(_env_file=None)):
            pytest.fail("Unconfigured session must not open")


def test_source_activity_identity_and_local_paths_are_unchanged(sample_settings):
    from coursepilot.domain.models import SyncTask, TaskPriority, TaskSelect, TaskType
    task = SyncTask(id="mat_1125_2847", course_id="1125", course_name="Example", course_abbr="Ex", title="Material", raw_title="Material", task_type=TaskType.MATERIAL, selection=TaskSelect.ROUTINE, priority=TaskPriority.P3, source_url="https://lxp.kau.ac.kr/mod/ubfile/view.php?id=2847")
    restored = SyncTask.model_validate_json(task.model_dump_json())
    assert restored.id == task.id and restored.source_url == task.source_url
    assert Settings(_env_file=None).session_cache_path == Path(".cache/session.json")
    assert Settings(_env_file=None).download_dir == Path("downloads")


def test_bundled_skill_fallback_and_explicit_missing_root(tmp_path, monkeypatch):
    from coursepilot import installer
    package = tmp_path / "site-packages" / "coursepilot"
    resources = package / "skill"
    resources.mkdir(parents=True)
    (resources / "SKILL.md").write_text("---\nname: coursepilot\ndescription: Test fixture\n---\n", encoding="utf-8")
    monkeypatch.setattr(installer, "__file__", str(package / "installer.py"))
    monkeypatch.setattr(installer, "repo_root", lambda: tmp_path / "workspace")
    assert skill_source_dir() == resources
    with pytest.raises(installer.InstallError):
        skill_source_dir(root=tmp_path / "missing-repo")
