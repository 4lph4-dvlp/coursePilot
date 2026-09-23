"""Data-driven agent skill-path table and copy/link installer (D-21, D-22, D-23).

`AGENT_SKILL_PATHS` is the single data table that decides where each supported
agent looks for user-level skills; adding a new agent is a data-only change.
`install_skill()` copies (default) or links (`--link`, added in a later plan
task) the repo's own `skills/kau-lxp/` folder into that location, resolving
the repo path so the installed copy works from any working directory.
"""

from __future__ import annotations

import shutil
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
    target = resolve_install_target(agent, home=home_dir)

    # Containment check (before any filesystem write) — the target must live
    # directly inside the agent's resolved skills directory as SKILL_NAME.
    expected_skills_dir = home_dir.joinpath(*target_agent.skills_dir)
    if target.parent.resolve() != expected_skills_dir.resolve() or target.name != SKILL_NAME:
        raise InstallError(f"설치 대상 경로가 올바르지 않습니다: {target}")

    agent_home_found = home_dir.joinpath(*target_agent.home_marker).exists()

    if link:
        raise InstallError(
            "--link은 이 단계에서 아직 지원되지 않습니다. --link 없이 다시 실행해 복사 설치를 사용하세요."
        )

    expected_skills_dir.mkdir(parents=True, exist_ok=True)
    _install_copy(src, target)

    return InstallResult(
        agent=agent,
        target=target,
        mode="copy",
        repo_root=repo_root(),
        agent_home_found=agent_home_found,
    )
