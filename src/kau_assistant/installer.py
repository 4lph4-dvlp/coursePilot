"""Data-driven agent skill-path table and copy/link installer (D-21, D-22, D-23).

`AGENT_SKILL_PATHS` is the single data table that decides where each supported
agent looks for user-level skills; adding a new agent is a data-only change.
`install_skill()` copies (default) or links (`--link`, added in a later plan
task) the repo's own `skills/kau-lxp/` folder into that location, resolving
the repo path so the installed copy works from any working directory.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from kau_assistant.exceptions import KauAssistantError

SKILL_NAME = "kau-lxp"
REPO_PLACEHOLDER = "{{KAU_LXP_REPO}}"
REPO_ROOT_FILE = "repo-root.txt"


class InstallError(KauAssistantError):
    """Raised when a skill install/link operation cannot proceed safely."""


class AgentTarget(BaseModel):
    """One agent's skill-directory location, relative to the user's home (D-22)."""

    model_config = ConfigDict(frozen=True)

    agent_id: str
    display_name: str
    home_marker: tuple[str, ...]
    skills_dir: tuple[str, ...]


# Evidence levels below come from 05-RESEARCH.md's Assumptions Log (A1-A4).
# All entries are provisional until 05-05's D-27 per-agent manual confirmation;
# a wrong path is a one-line data fix here, never a code change (D-22).
AGENT_SKILL_PATHS: dict[str, AgentTarget] = {
    "claude": AgentTarget(
        agent_id="claude",
        display_name="Claude Code",
        # MEDIUM confidence: official docs + this repo's own .claude/skills/.
        home_marker=(".claude",),
        skills_dir=(".claude", "skills"),
    ),
    "codex": AgentTarget(
        agent_id="codex",
        display_name="Codex",
        # LOW confidence: WebSearch snippets only (A1); .codex/skills/ in this
        # repo is Codex-managed (`.system`), not proof of the user-level path.
        home_marker=(".codex",),
        skills_dir=(".codex", "skills"),
    ),
    "antigravity": AgentTarget(
        agent_id="antigravity",
        display_name="Antigravity",
        # LOW confidence: WebSearch only (A2); no skills/ dir observed yet.
        home_marker=(".gemini", "antigravity"),
        skills_dir=(".gemini", "antigravity", "skills"),
    ),
    "pi": AgentTarget(
        agent_id="pi",
        display_name="Pi",
        # LOW confidence: WebSearch only (A3); no skills/ dir observed yet.
        home_marker=(".pi", "agent"),
        skills_dir=(".pi", "agent", "skills"),
    ),
    "hermes": AgentTarget(
        agent_id="hermes",
        display_name="Hermes",
        # LOW confidence: WebSearch only (A4); no in-repo evidence available.
        home_marker=(".hermes",),
        skills_dir=(".hermes", "skills"),
    ),
}


class InstallResult(BaseModel):
    """Outcome of one `install_skill()` call."""

    model_config = ConfigDict(frozen=True)

    agent: str
    target: Path
    mode: Literal["copy", "link"]
    repo_root: Path
    agent_home_found: bool


def repo_root() -> Path:
    """Resolve this repository's root directory."""
    return Path(__file__).resolve().parents[2]


def skill_source_dir(root: Path | None = None) -> Path:
    """Resolve the repo's own `skills/kau-lxp` directory, validating it exists."""
    base = (root or repo_root()) / "skills" / SKILL_NAME
    if not (base / "SKILL.md").exists():
        raise InstallError(f"스킬 소스 폴더를 찾을 수 없습니다: {base} (SKILL.md 없음)")
    return base


def resolve_install_target(agent: str, *, home: Path | None = None) -> Path:
    """Compute the install target path for `agent`. Pure — no filesystem access."""
    if agent not in AGENT_SKILL_PATHS:
        raise InstallError(f"지원하지 않는 에이전트입니다: {agent}")
    target_agent = AGENT_SKILL_PATHS[agent]
    base = home or Path.home()
    return base.joinpath(*target_agent.skills_dir, SKILL_NAME)


_FILE_ATTRIBUTE_REPARSE_POINT = 0x400


def _is_link_or_junction(path: Path) -> bool:
    """True for a symlink (any OS) or a Windows NTFS junction."""
    if path.is_symlink():
        return True
    if sys.platform != "win32":
        return False
    isjunction = getattr(os.path, "isjunction", None)
    if isjunction is not None:  # Python >= 3.12
        return bool(isjunction(str(path)))
    try:
        attrs = os.lstat(path).st_file_attributes  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        return False
    return bool(attrs & _FILE_ATTRIBUTE_REPARSE_POINT)


def _remove_link(path: Path) -> None:
    """Remove a symlink/junction itself, never the directory it points to."""
    if sys.platform == "win32":
        os.rmdir(path)
    else:
        os.unlink(path)


def _frontmatter_name(skill_md: Path) -> str | None:
    """Read only the `name:` frontmatter value, tolerating any read failure."""
    try:
        content = skill_md.read_text(encoding="utf-8")
    except OSError:
        return None
    lines = content.splitlines()
    if not lines or lines[0] != "---":
        return None
    for line in lines[1:]:
        if line == "---":
            break
        if line.startswith("name:"):
            return line.split(":", 1)[1].strip()
    return None


def _prepare_replace(target: Path) -> None:
    """Safely clear `target` for a fresh install (runs before any write).

    A link/junction is removed as a link only (never touching what it points
    to). A real directory is removed wholesale only when its own SKILL.md
    identifies it as our skill; anything else at the target is refused
    without modification (T-05-15).
    """
    if not target.exists() and not target.is_symlink():
        return

    if _is_link_or_junction(target):
        _remove_link(target)
        return

    if target.is_dir():
        if _frontmatter_name(target / "SKILL.md") == SKILL_NAME:
            shutil.rmtree(target)
            return
        raise InstallError(
            f"설치 대상에 다른 스킬 또는 알 수 없는 내용이 있습니다: {target}. "
            "직접 확인 후 제거하거나 다른 위치를 사용하세요."
        )

    raise InstallError(f"설치 대상이 올바른 스킬 폴더가 아닙니다: {target}")


def _create_link(source: Path, target: Path) -> None:
    """Symlink first; on Windows privilege errors, fall back to an NTFS junction.

    Never falls back to a silent copy (RESEARCH.md Pitfall 4) — if both a
    symlink and a junction fail, this raises InstallError loudly.
    """
    try:
        os.symlink(source, target, target_is_directory=True)
        return
    except OSError as symlink_error:
        if os.name == "nt":
            try:
                subprocess.run(
                    ["cmd", "/c", "mklink", "/J", str(target), str(source)],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                return
            except (OSError, subprocess.CalledProcessError) as junction_error:
                raise InstallError(
                    "심볼릭 링크와 NTFS 접합점(junction) 생성이 모두 실패했습니다. "
                    "--link 없이 다시 실행해 복사 설치를 사용하세요."
                ) from junction_error
        raise InstallError(
            "심볼릭 링크 생성에 실패했습니다. --link 없이 다시 실행해 복사 설치를 사용하세요."
        ) from symlink_error


def _install_copy(source: Path, target: Path) -> None:
    """Copy `source` to `target`, resolving the repo path in the installed SKILL.md."""
    shutil.copytree(
        source,
        target,
        ignore=shutil.ignore_patterns(REPO_ROOT_FILE, "__pycache__"),
    )
    skill_md = target / "SKILL.md"
    content = skill_md.read_text(encoding="utf-8")
    content = content.replace(REPO_PLACEHOLDER, str(repo_root()))
    skill_md.write_text(content, encoding="utf-8")
    (target / REPO_ROOT_FILE).write_text(f"{repo_root()}\n", encoding="utf-8")


def install_skill(
    agent: str,
    *,
    link: bool = False,
    home: Path | None = None,
    source: Path | None = None,
) -> InstallResult:
    """Install (copy by default) the kau-lxp skill for `agent` (D-21..D-23)."""
    if agent not in AGENT_SKILL_PATHS:
        raise InstallError(f"지원하지 않는 에이전트입니다: {agent}")

    target_agent = AGENT_SKILL_PATHS[agent]
    home_dir = home or Path.home()
    src = source or skill_source_dir()
    if not (src / "SKILL.md").exists():
        raise InstallError(f"스킬 소스 폴더를 찾을 수 없습니다: {src} (SKILL.md 없음)")

    target = resolve_install_target(agent, home=home_dir)

    # Containment check (before any filesystem write) — the target must live
    # directly inside the agent's resolved skills directory as SKILL_NAME.
    expected_skills_dir = home_dir.joinpath(*target_agent.skills_dir)
    if target.parent.resolve() != expected_skills_dir.resolve() or target.name != SKILL_NAME:
        raise InstallError(f"설치 대상 경로가 올바르지 않습니다: {target}")

    agent_home_found = home_dir.joinpath(*target_agent.home_marker).exists()

    # Replace handling runs before any write, only on this containment-checked
    # target (T-05-15): a link is removed as a link only, a prior kau-lxp copy
    # is replaced, anything foreign is refused untouched.
    _prepare_replace(target)
    expected_skills_dir.mkdir(parents=True, exist_ok=True)

    if link:
        _create_link(src, target)
        # The linked SKILL.md keeps its placeholder; it resolves the repo via
        # this file instead (written into the source, i.e. the repo's own
        # skills/kau-lxp/ for the common no-source-override case).
        (src / REPO_ROOT_FILE).write_text(f"{repo_root()}\n", encoding="utf-8")
        mode: Literal["copy", "link"] = "link"
    else:
        _install_copy(src, target)
        mode = "copy"

    return InstallResult(
        agent=agent,
        target=target,
        mode=mode,
        repo_root=repo_root(),
        agent_home_found=agent_home_found,
    )
