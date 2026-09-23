"""Tests for the universal Agent Skill installer (SKIL-03, D-21..D-23)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from click.testing import CliRunner

from kau_assistant.cli import cli
from kau_assistant.installer import (
    REPO_PLACEHOLDER,
    REPO_ROOT_FILE,
    resolve_install_target,
    repo_root,
    skill_source_dir,
)

# Agent-specific tool/runtime identifiers the SKILL.md body must never mention
# (kept here, not in production code, per Task 2's action text).
_AGENT_SPECIFIC_DENYLIST = (
    "Bash(",
    "allowed-tools",
    "run_shell_command",
    "claude_code",
    "codex exec",
)


def _parse_frontmatter(content: str) -> dict[str, str]:
    """Minimal parser for this file's fixed two-key frontmatter shape."""
    lines = content.splitlines()
    assert lines[0] == "---"
    end = lines[1:].index("---") + 1
    frontmatter_lines = lines[1:end]
    parsed: dict[str, str] = {}
    for line in frontmatter_lines:
        match = re.match(r"^(\w+):\s*(.*)$", line)
        assert match, f"Unparseable frontmatter line: {line!r}"
        key, value = match.group(1), match.group(2)
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        parsed[key] = value
    return parsed


def _skill_body(content: str) -> str:
    """Return the SKILL.md content after the closing frontmatter `---`."""
    lines = content.splitlines()
    assert lines[0] == "---"
    end = lines[1:].index("---") + 1
    return "\n".join(lines[end + 1 :])


@pytest.fixture
def fake_home(tmp_path: Path, monkeypatch) -> Path:
    """Make `Path.home()` resolve into `tmp_path` on every OS (Windows & POSIX)."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    return home


def test_path_claude_user_target(fake_home: Path) -> None:
    target = resolve_install_target("claude", home=fake_home)
    assert target == fake_home / ".claude" / "skills" / "kau-lxp"


def test_resolve_path_copy_install_renders_repo_root(fake_home: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["install-skill", "--agent", "claude"])
    assert result.exit_code == 0, result.output

    installed = fake_home / ".claude" / "skills" / "kau-lxp" / "SKILL.md"
    assert installed.exists()
    content = installed.read_text(encoding="utf-8")
    assert REPO_PLACEHOLDER not in content
    assert content.count(str(repo_root())) >= 2

    repo_root_file = fake_home / ".claude" / "skills" / "kau-lxp" / REPO_ROOT_FILE
    assert repo_root_file.read_text(encoding="utf-8").strip() == str(repo_root())

    # The repo's own copy must still carry the placeholder.
    own = skill_source_dir() / "SKILL.md"
    assert REPO_PLACEHOLDER in own.read_text(encoding="utf-8")


def test_path_unknown_agent_rejected() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["install-skill", "--agent", "foo"])
    assert result.exit_code == 2


def test_skill_frontmatter_agent_neutral() -> None:
    content = (skill_source_dir() / "SKILL.md").read_text(encoding="utf-8")
    frontmatter = _parse_frontmatter(content)
    assert set(frontmatter.keys()) == {"name", "description"}
    assert frontmatter["name"] == "kau-lxp"
    assert len(frontmatter["description"]) <= 1024
    assert "과제 확인해줘" in frontmatter["description"]
    assert "노션에 올려줘" in frontmatter["description"]
