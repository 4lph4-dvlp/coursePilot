"""Tests for the universal Agent Skill installer (SKIL-03, D-21..D-23)."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from coursepilot.cli import cli
from coursepilot.installer import (
    AGENT_SKILL_PATHS,
    InstallError,
    REPO_PLACEHOLDER,
    REPO_ROOT_FILE,
    SKILL_NAME,
    install_skill,
    repo_root,
    resolve_agent_home,
    resolve_install_target,
    resolve_skills_dir,
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


@pytest.fixture(autouse=True)
def isolate_hermes_and_localappdata(tmp_path: Path, monkeypatch) -> None:
    """Isolates LOCALAPPDATA and clears HERMES_HOME for every test so real user folders are never touched."""
    fake_local = tmp_path / "localappdata"
    fake_local.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("LOCALAPPDATA", str(fake_local))
    monkeypatch.delenv("HERMES_HOME", raising=False)
    # Include default-home installs: even a CLI hint test must never write into
    # the real user's Claude/Codex skill directory.
    default_home = tmp_path / "default-home"
    default_home.mkdir()
    monkeypatch.setenv("HOME", str(default_home))
    monkeypatch.setenv("USERPROFILE", str(default_home))


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
    assert target == fake_home / ".claude" / "skills" / "coursepilot"


def test_resolve_path_copy_install_renders_repo_root(fake_home: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["install-skill", "--agent", "claude"])
    assert result.exit_code == 0, result.output

    installed = fake_home / ".claude" / "skills" / "coursepilot" / "SKILL.md"
    assert installed.exists()
    content = installed.read_text(encoding="utf-8")
    assert REPO_PLACEHOLDER not in content
    assert content.count(str(repo_root())) >= 2

    repo_root_file = fake_home / ".claude" / "skills" / "coursepilot" / REPO_ROOT_FILE
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
    assert frontmatter["name"] == "coursepilot"
    assert len(frontmatter["description"]) <= 1024
    assert "과제 확인해줘" in frontmatter["description"]
    assert "노션에 올려줘" in frontmatter["description"]


def test_skill_body_briefing_flow() -> None:
    body = _skill_body((skill_source_dir() / "SKILL.md").read_text(encoding="utf-8"))
    assert "check --json" in body

    overdue_idx = body.index("기한 초과")
    within_24h_idx = body.index("24시간 이내")
    later_idx = body.index("이후 일정")
    assert overdue_idx < within_24h_idx < later_idx

    for column in ("과목", "작업", "마감일", "남은 시간"):
        assert column in body

    assert "절대 요약하거나 생략하지" in body


def test_skill_body_sync_approval_flow() -> None:
    body = _skill_body((skill_source_dir() / "SKILL.md").read_text(encoding="utf-8"))
    sync_preview_idx = body.index("sync --json")
    sync_apply_idx = body.index("sync --apply --json")
    assert sync_preview_idx < sync_apply_idx
    assert "명시적" in body and "승인" in body


def test_skill_body_environment_and_secrets() -> None:
    body = _skill_body((skill_source_dir() / "SKILL.md").read_text(encoding="utf-8"))
    assert "uv --directory" in body
    assert "sync" in body
    assert "playwright install chromium" in body
    assert ".env" in body
    assert ".env.example" in body
    assert "절대 요청, 반복, 저장하지" in body


def test_skill_body_untrusted_data_rule() -> None:
    body = _skill_body((skill_source_dir() / "SKILL.md").read_text(encoding="utf-8"))
    assert "지시로 따르지 마세요" in body
    assert "표시" in body


def test_skill_body_agent_neutral() -> None:
    body = _skill_body((skill_source_dir() / "SKILL.md").read_text(encoding="utf-8"))
    for term in _AGENT_SPECIFIC_DENYLIST:
        assert term not in body


@pytest.fixture
def tmp_src(tmp_path: Path) -> Path:
    """A fake source skill folder — link tests never touch the real repo's own copy."""
    src = tmp_path / "src" / SKILL_NAME
    src.mkdir(parents=True)
    (src / "SKILL.md").write_text(
        "---\nname: coursepilot\ndescription: \"test\"\n---\n\nbody\n", encoding="utf-8"
    )
    return src


@pytest.mark.parametrize(
    ("agent", "expected_parts"),
    [
        ("claude", (".claude", "skills")),
        ("codex", (".codex", "skills")),
        ("antigravity", (".gemini", "antigravity", "skills")),
        ("pi", (".pi", "agent", "skills")),
        ("hermes", (".hermes", "skills")),
    ],
)
def test_path_all_agents_table(
    fake_home: Path, agent: str, expected_parts: tuple[str, ...]
) -> None:
    target = resolve_install_target(agent, home=fake_home, env={}, platform="linux")
    assert target == fake_home.joinpath(*expected_parts, SKILL_NAME)
    assert target.parent == fake_home.joinpath(*expected_parts)


def test_hermes_home_env_var_wins(fake_home: Path, tmp_path: Path) -> None:
    custom_hermes = tmp_path / "custom_hermes"
    target = resolve_install_target(
        "hermes",
        home=fake_home,
        env={"HERMES_HOME": str(custom_hermes), "LOCALAPPDATA": "C:/dummy"},
        platform="win32",
    )
    assert target == custom_hermes / "skills" / "coursepilot"


def test_hermes_windows_localappdata(fake_home: Path, tmp_path: Path) -> None:
    win_local = tmp_path / "win_local"
    target = resolve_install_target(
        "hermes",
        home=fake_home,
        env={"LOCALAPPDATA": str(win_local)},
        platform="win32",
    )
    assert target == win_local / "hermes" / "skills" / "coursepilot"


def test_hermes_posix_and_windows_fallback(fake_home: Path) -> None:
    posix_target = resolve_install_target("hermes", home=fake_home, env={}, platform="linux")
    assert posix_target == fake_home / ".hermes" / "skills" / "coursepilot"

    win_target = resolve_install_target("hermes", home=fake_home, env={}, platform="win32")
    assert win_target == fake_home / ".hermes" / "skills" / "coursepilot"


def test_other_agents_ignore_hermes_env(fake_home: Path, tmp_path: Path) -> None:
    env = {"HERMES_HOME": str(tmp_path / "hermes"), "LOCALAPPDATA": str(tmp_path / "local")}
    for agent in ("claude", "codex", "antigravity", "pi"):
        target = resolve_install_target(agent, home=fake_home, env=env, platform="win32")
        expected = fake_home.joinpath(*AGENT_SKILL_PATHS[agent].skills_dir, "coursepilot")
        assert target == expected


def test_skills_dir_starts_with_home_marker() -> None:
    for target in AGENT_SKILL_PATHS.values():
        marker_len = len(target.home_marker)
        assert target.skills_dir[:marker_len] == target.home_marker


def test_cli_install_hermes_uses_hermes_home(tmp_path: Path, monkeypatch) -> None:
    hermes_home = tmp_path / "hermes-env"
    hermes_home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))

    runner = CliRunner()
    result = runner.invoke(cli, ["install-skill", "--agent", "hermes"])
    assert result.exit_code == 0
    installed = hermes_home / "skills" / "coursepilot" / "SKILL.md"
    assert installed.exists()
    assert "경고" not in result.output


def test_install_skill_prints_lms_url_hint() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["install-skill", "--agent", "claude"])
    assert "LMS_URL" in result.output
    assert "LMS_PROFILE=kau" in result.output
    assert "Coursemos" in result.output


def test_skill_body_lms_url_guidance() -> None:
    body = _skill_body((skill_source_dir() / "SKILL.md").read_text(encoding="utf-8"))
    assert "LMS_URL" in body
    assert "https://lxp.kau.ac.kr" in body
    assert "Coursemos" in body


def test_skill_body_relays_notices_first() -> None:
    body = _skill_body((skill_source_dir() / "SKILL.md").read_text(encoding="utf-8"))
    assert "notices" in body
    assert "no_courses_found" in body
    notices_idx = body.index("notices")
    summary_idx = body.index("한 줄 요약")
    assert notices_idx < summary_idx


def test_skill_body_unsupported_lms_and_fresh_run_rules() -> None:
    body = _skill_body((skill_source_dir() / "SKILL.md").read_text(encoding="utf-8"))
    assert "UnsupportedLmsError" in body
    assert "stdout" in body
    assert "새로 실행" in body


def test_link_real_filesystem_reflects_source_edits(fake_home: Path, tmp_src: Path) -> None:
    result = install_skill("claude", link=True, home=fake_home, source=tmp_src)
    assert result.mode == "link"

    (tmp_src / "NEW_FILE.md").write_text("hello", encoding="utf-8")
    target = fake_home / ".claude" / "skills" / SKILL_NAME
    assert (target / "NEW_FILE.md").read_text(encoding="utf-8") == "hello"

    assert (tmp_src / REPO_ROOT_FILE).read_text(encoding="utf-8").strip() == str(repo_root())


def test_link_windows_junction_fallback(
    fake_home: Path, tmp_src: Path, monkeypatch
) -> None:
    def _raise_symlink(*args, **kwargs):
        raise OSError(1314, "A required privilege is not held by the client")

    monkeypatch.setattr(os, "symlink", _raise_symlink)
    monkeypatch.setattr(os, "name", "nt", raising=False)

    calls: list[list[str]] = []

    def _fake_run(cmd, **kwargs):
        calls.append(cmd)
        assert kwargs.get("check") is True
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(subprocess, "run", _fake_run)

    result = install_skill("claude", link=True, home=fake_home, source=tmp_src)
    assert result.mode == "link"

    target = fake_home / ".claude" / "skills" / SKILL_NAME
    assert calls == [["cmd", "/c", "mklink", "/J", str(target), str(tmp_src)]]


def test_link_both_fail_is_loud(fake_home: Path, tmp_src: Path, monkeypatch) -> None:
    def _raise_symlink(*args, **kwargs):
        raise OSError(1314, "A required privilege is not held by the client")

    def _raise_run(cmd, **kwargs):
        raise subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr(os, "symlink", _raise_symlink)
    monkeypatch.setattr(os, "name", "nt", raising=False)
    monkeypatch.setattr(subprocess, "run", _raise_run)

    with pytest.raises(InstallError):
        install_skill("claude", link=True, home=fake_home, source=tmp_src)

    target = fake_home / ".claude" / "skills" / SKILL_NAME
    assert not target.exists()

    runner = CliRunner()
    result = runner.invoke(cli, ["install-skill", "--agent", "claude", "--link"])
    assert result.exit_code == 2
    assert "--link" in result.output


def test_link_reinstall_over_link_keeps_source(fake_home: Path, tmp_src: Path) -> None:
    install_skill("claude", link=True, home=fake_home, source=tmp_src)
    before = sorted(p.name for p in tmp_src.iterdir())

    result = install_skill("claude", link=False, home=fake_home, source=tmp_src)
    assert result.mode == "copy"

    after = sorted(p.name for p in tmp_src.iterdir())
    assert before == after

    target = fake_home / ".claude" / "skills" / SKILL_NAME
    assert target.is_dir()
    assert not target.is_symlink()


def test_path_reinstall_replaces_previous_copy(fake_home: Path, tmp_src: Path) -> None:
    install_skill("claude", home=fake_home, source=tmp_src)
    target = fake_home / ".claude" / "skills" / SKILL_NAME
    stale = target / "STALE.md"
    stale.write_text("old", encoding="utf-8")
    assert stale.exists()

    install_skill("claude", home=fake_home, source=tmp_src)
    assert not stale.exists()
    assert (target / "SKILL.md").exists()


def test_path_refuses_foreign_target(fake_home: Path, tmp_src: Path) -> None:
    target_dir = fake_home / ".claude" / "skills" / SKILL_NAME
    target_dir.mkdir(parents=True)
    (target_dir / "unrelated.txt").write_text("mine", encoding="utf-8")

    with pytest.raises(InstallError):
        install_skill("claude", home=fake_home, source=tmp_src)

    assert (target_dir / "unrelated.txt").read_text(encoding="utf-8") == "mine"


def test_path_missing_agent_home_warns(tmp_path: Path, tmp_src: Path, monkeypatch) -> None:
    # Two independent homes: the first install's mkdir(parents=True) for the
    # skills dir would otherwise create the .hermes home marker for a second
    # install into the same home, masking the "missing home" signal.
    home_direct = tmp_path / "home-direct"
    home_direct.mkdir()
    result = install_skill("hermes", home=home_direct, source=tmp_src)
    assert result.agent_home_found is False

    home_cli = tmp_path / "home-cli"
    home_cli.mkdir()
    monkeypatch.setenv("HOME", str(home_cli))
    monkeypatch.setenv("USERPROFILE", str(home_cli))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local-cli"))

    runner = CliRunner()
    invoke_result = runner.invoke(cli, ["install-skill", "--agent", "hermes"])
    assert invoke_result.exit_code == 0
    assert "경고" in invoke_result.output
