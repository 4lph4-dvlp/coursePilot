"""Doc/code consistency checks for the JSON contract doc, README agent table, and SKILL.md pointer (D-13, D-20)."""

from __future__ import annotations

import json
import re
import typing
from pathlib import Path

from pydantic import BaseModel

from kau_assistant.installer import AGENT_SKILL_PATHS
from kau_assistant.report_models import CheckReport, SyncReport

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_DOC = REPO_ROOT / "skills" / "kau-lxp" / "JSON_CONTRACT.md"
SKILL_MD = REPO_ROOT / "skills" / "kau-lxp" / "SKILL.md"
README = REPO_ROOT / "README.md"


def _unwrap_annotation(annotation: object) -> list[object]:
    """Flattens a type annotation (Optional/Union/list/...) into its leaf types."""
    args = typing.get_args(annotation)
    if args:
        leaves: list[object] = []
        for arg in args:
            leaves.extend(_unwrap_annotation(arg))
        return leaves
    return [annotation]


def _collect_model_field_names(
    model: type[BaseModel], seen: set[type[BaseModel]] | None = None
) -> set[str]:
    """Recursively collects every field name from `model` and any nested BaseModel fields."""
    if seen is None:
        seen = set()
    if model in seen:
        return set()
    seen.add(model)

    names: set[str] = set()
    for field_name, field in model.model_fields.items():
        names.add(field_name)
        for leaf in _unwrap_annotation(field.annotation):
            if isinstance(leaf, type) and issubclass(leaf, BaseModel):
                names |= _collect_model_field_names(leaf, seen)
    return names


def test_json_contract_doc_lists_every_field() -> None:
    """Every CheckReport/SyncReport field (recursively) appears backtick-wrapped in the doc."""
    content = CONTRACT_DOC.read_text(encoding="utf-8")
    field_names = _collect_model_field_names(CheckReport) | _collect_model_field_names(SyncReport)

    missing = sorted(name for name in field_names if f"`{name}`" not in content)
    assert not missing, f"JSON_CONTRACT.md is missing backtick-wrapped field(s): {missing}"


def _extract_json_blocks(content: str) -> list[str]:
    return re.findall(r"```json\n(.*?)\n```", content, flags=re.DOTALL)


def test_json_contract_doc_examples_validate() -> None:
    """The check example validates as CheckReport; the sync example validates as SyncReport."""
    content = CONTRACT_DOC.read_text(encoding="utf-8")
    blocks = _extract_json_blocks(content)
    assert len(blocks) >= 2, "Expected at least a check example and a sync example json block"

    parsed = [json.loads(block) for block in blocks]
    check_payloads = [p for p in parsed if p.get("command") == "check"]
    sync_payloads = [p for p in parsed if p.get("command") == "sync"]

    assert check_payloads, "No example payload with command == 'check' found"
    assert sync_payloads, "No example payload with command == 'sync' found"

    for payload in check_payloads:
        CheckReport.model_validate(payload)
    for payload in sync_payloads:
        SyncReport.model_validate(payload)


def test_json_contract_readme_lists_every_agent() -> None:
    """README.md's install table lists every AGENT_SKILL_PATHS agent id and its skills_dir path."""
    content = README.read_text(encoding="utf-8")

    missing: list[str] = []
    for agent_id, target in AGENT_SKILL_PATHS.items():
        if agent_id not in content:
            missing.append(f"agent id {agent_id!r}")
        skills_dir_path = "/".join(target.skills_dir)
        if skills_dir_path not in content:
            missing.append(f"skills_dir path {skills_dir_path!r}")

    assert not missing, f"README.md is missing: {missing}"


def test_json_contract_skill_md_points_to_contract() -> None:
    """SKILL.md mentions JSON_CONTRACT.md so agents know where to find the field reference."""
    content = SKILL_MD.read_text(encoding="utf-8")
    assert "JSON_CONTRACT.md" in content
