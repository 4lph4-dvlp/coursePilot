"""Completeness and privacy checks for the Phase 17 evidence ledger."""

from __future__ import annotations

from copy import deepcopy

import pytest

from scripts.verify_phase17_evidence import AGENTS, PROMPTS, EvidenceError, validate_ledger


@pytest.fixture
def valid_ledger() -> dict:
    return {
        "offline": {"full_suite_passed": True, "test_count": 448},
        "deployment": [
            {"agent": agent, "status": "success", "target": f"/fake/{agent}/coursepilot", "reason": "linked docs readable", "docs_readable": True, "link_source": "/fake/source"}
            for agent in AGENTS
        ],
        "optional_scheduler": [{"agent": agent, "readable": False} for agent in AGENTS],
        "lxp": {"enrolled_count": 2, "commands": {name: {"success_count": 2, "failure_count": 0, "observed": True} for name in ("check", "progress", "notices", "qna")}},
        "downloads": {kind: {"status": "downloaded", "created_by_smoke": True, "saved_path_present": True, "file_existed": True, "size_bytes": 100, "cleaned": True} for kind in ("material", "vod")},
        "watch": {"dry_run_observed": True, "dry_run_at": "2026-10-04T11:59:00Z", "started_at": "2026-10-04T12:00:00Z", "status_at": "2026-10-04T12:01:00Z", "stopped_at": "2026-10-04T12:02:00Z"},
        "scheduler": {"read_observed": True, "sync_preview_observed": True, "watch_preview_observed": True, "create_calls": 0, "update_calls": 0},
        "agents": [
            {"agent": agent, "prompt": prompt, "triggered": True, "selected_command": command, "outcome": "pass", "reason": "observed"}
            for agent in AGENTS for prompt, command in PROMPTS.items()
        ],
        "criteria": [{"id": n, "verdict": "passed", "reason": "observed"} for n in range(1, 5)],
    }


def test_valid_ledger_passes_all_sections(valid_ledger: dict) -> None:
    for section in (None, "deployment", "live", "agents"):
        assert validate_ledger(valid_ledger, section) == []


@pytest.mark.parametrize("mutator", [
    lambda d: d["deployment"].pop(),
    lambda d: d["lxp"]["commands"]["qna"].update(success_count=1),
    lambda d: d["scheduler"].update(create_calls=1),
    lambda d: d["agents"][0].update(selected_command="check"),
    lambda d: d.update(raw_json={"private": "value"}),
    lambda d: d["agents"][0].update(full_transcript="private"),
    lambda d: d["watch"].update(status_at="2026-10-04T11:58:00Z"),
])
def test_invalid_or_private_ledger_rejected(valid_ledger: dict, mutator) -> None:
    case = deepcopy(valid_ledger)
    mutator(case)
    with pytest.raises(EvidenceError):
        validate_ledger(case)


def test_unverified_cannot_be_claimed_passed(valid_ledger: dict) -> None:
    case = deepcopy(valid_ledger)
    case["deployment"][0].update(status="skip", docs_readable=False, link_source=None, reason="home missing")
    with pytest.raises(EvidenceError):
        validate_ledger(case)
    case["criteria"][1]["verdict"] = "unverified"
    assert "deployment:claude" in validate_ledger(case)


def test_wrong_known_route_is_recorded_as_failure(valid_ledger: dict) -> None:
    case = deepcopy(valid_ledger)
    row = next(r for r in case["agents"] if r["agent"] == "claude" and r["prompt"] == "공지")
    row.update(selected_command="progress", outcome="fail", reason="selected progress for notice prompt")
    case["criteria"][1]["verdict"] = "unverified"
    assert "agent:claude:공지" in validate_ledger(case)


def test_unknown_enrollment_stays_incomplete(valid_ledger: dict) -> None:
    case = deepcopy(valid_ledger)
    case["lxp"]["enrolled_count"] = None
    for command in case["lxp"]["commands"].values():
        command.update(success_count=0, failure_count=0, observed=False)
    case["criteria"][2]["verdict"] = "unverified"
    assert "lxp:enrollment" in validate_ledger(case)
