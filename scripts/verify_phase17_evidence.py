"""Validate the privacy-limited Phase 17 deployment and live evidence ledger."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

EVIDENCE = Path(__file__).resolve().parents[1] / ".planning" / "phases" / "17-universal-skill-packaging-multi-agent-deployment-end-to-end" / "17-E2E-EVIDENCE.md"
AGENTS = ("claude", "codex", "antigravity", "pi", "hermes")
PROMPTS = {"진도율": "progress", "공지": "notices", "Q&A": "qna"}
COMMANDS = ("check", "progress", "notices", "qna")
PRIVATE_KEYS = {"payload", "course_payload", "raw_json", "raw_response", "raw_stdout", "raw_stderr",
                "stdout", "stderr", "tool_output", "transcript", "full_transcript", "credentials",
                "password", "token", "session_cookie", "course_title", "course_titles", "course_name", "course_names"}


class EvidenceError(ValueError):
    """An evidence claim is malformed or contradicts its observations."""


def read_ledger(path: Path = EVIDENCE) -> dict:
    text = path.read_text(encoding="utf-8")
    blocks = re.findall(r"```json\s*\n(.*?)\n```", text, flags=re.DOTALL)
    if len(blocks) != 1:
        raise EvidenceError("evidence must contain exactly one fenced JSON ledger")
    result = json.loads(blocks[0])
    if not isinstance(result, dict):
        raise EvidenceError("ledger must be an object")
    return result


def _reject_private(value: object) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in PRIVATE_KEYS:
                raise EvidenceError(f"private/raw field forbidden: {key}")
            _reject_private(child)
    elif isinstance(value, list):
        for child in value:
            _reject_private(child)


def validate_ledger(data: dict, section: str | None = None) -> list[str]:
    """Return unmet observations; raise for missing/contradictory claims."""
    if section not in (None, "deployment", "live", "agents"):
        raise EvidenceError(f"unknown section: {section}")
    _reject_private(data)
    unmet: list[str] = []
    offline = data.get("offline", {})
    if not isinstance(offline.get("full_suite_passed"), bool) or not isinstance(offline.get("test_count"), int):
        raise EvidenceError("offline full-suite status and test count required")
    if not offline["full_suite_passed"] or offline["test_count"] <= 0:
        unmet.append("offline")
    if section in (None, "deployment"):
        rows = data.get("deployment")
        if not isinstance(rows, list) or len(rows) != 5 or {r.get("agent") for r in rows} != set(AGENTS):
            raise EvidenceError("deployment needs exactly five distinct agent rows")
        for row in rows:
            if row.get("status") not in ("success", "skip", "failure"):
                raise EvidenceError("invalid deployment status")
            if not row.get("target") or not row.get("reason") or not isinstance(row.get("docs_readable"), bool):
                raise EvidenceError("deployment row lacks target, reason, or docs_readable")
            if row["status"] != "success" and row["docs_readable"]:
                raise EvidenceError("skipped/failed target claimed readable")
            if row["status"] == "success" and (not row["docs_readable"] or not row.get("link_source")):
                raise EvidenceError("successful target lacks readable link proof")
            if row["status"] != "success":
                unmet.append(f"deployment:{row['agent']}")
        optional = data.get("optional_scheduler")
        if not isinstance(optional, list) or len(optional) != 5:
            raise EvidenceError("optional Scheduler status needs five rows")

    if section in (None, "live"):
        lxp = data.get("lxp")
        if not isinstance(lxp, dict):
            raise EvidenceError("live LXP section missing")
        enrolled = lxp.get("enrolled_count")
        if enrolled is not None and (not isinstance(enrolled, int) or enrolled < 0):
            raise EvidenceError("invalid live enrolled_count")
        if enrolled is None:
            unmet.append("lxp:enrollment")
        reports = lxp.get("commands", {})
        for name in COMMANDS:
            result = reports.get(name)
            if not isinstance(result, dict):
                raise EvidenceError(f"missing live {name} result")
            success, failure = result.get("success_count"), result.get("failure_count")
            if not isinstance(success, int) or not isinstance(failure, int) or success < 0 or failure < 0:
                raise EvidenceError(f"invalid {name} counts")
            if enrolled is not None and success + failure != enrolled:
                raise EvidenceError(f"{name} counts do not cover enrolled courses")
            if enrolled is None and (success or failure or result.get("observed")):
                raise EvidenceError(f"{name} claims observations without enrolled baseline")
            if failure or not result.get("observed"):
                unmet.append(f"lxp:{name}")
        downloads = data.get("downloads", {})
        for kind in ("material", "vod"):
            item = downloads.get(kind, {})
            if item.get("status") != "downloaded" or not all(item.get(key) for key in ("created_by_smoke", "saved_path_present", "file_existed", "cleaned")) or not isinstance(item.get("size_bytes"), int) or item["size_bytes"] <= 0:
                unmet.append(f"download:{kind}")
        watch = data.get("watch", {})
        stamp_keys = ("dry_run_at", "started_at", "status_at", "stopped_at")
        if not watch.get("dry_run_observed") or not all(watch.get(key) for key in stamp_keys):
            unmet.append("watch")
        else:
            try:
                stamps = [datetime.fromisoformat(watch[key].replace("Z", "+00:00")) for key in stamp_keys]
            except (ValueError, AttributeError) as error:
                raise EvidenceError("invalid watch timestamp") from error
            if stamps != sorted(stamps) or len(set(stamps)) != len(stamps):
                raise EvidenceError("watch sequence is not dry-run, start, status, stop")
        scheduler = data.get("scheduler", {})
        if scheduler.get("create_calls") != 0 or scheduler.get("update_calls") != 0:
            raise EvidenceError("Scheduler preview recorded Notion writes")
        if not all(scheduler.get(key) for key in ("read_observed", "sync_preview_observed", "watch_preview_observed")):
            unmet.append("scheduler")

    if section in (None, "agents"):
        rows = data.get("agents")
        if not isinstance(rows, list) or len(rows) != 15:
            raise EvidenceError("agents need 15 fresh-session prompt rows")
        seen = set()
        for row in rows:
            pair = (row.get("agent"), row.get("prompt"))
            if pair in seen or pair[0] not in AGENTS or pair[1] not in PROMPTS:
                raise EvidenceError("duplicate or invalid agent prompt")
            seen.add(pair)
            if row.get("selected_command") not in (*PROMPTS.values(), None):
                raise EvidenceError("unknown selected command for prompt")
            if row.get("outcome") not in ("pass", "fail", "unverified") or not isinstance(row.get("triggered"), bool):
                raise EvidenceError("invalid agent outcome")
            if row["outcome"] == "pass" and (
                not row["triggered"] or row["selected_command"] != PROMPTS[pair[1]]
                or row.get("cli_json_valid") is not True
                or row.get("cli_exit") not in (0, 1)
                or row.get("final_response") is not True
            ):
                raise EvidenceError("route pass lacks observed skill, correct command, valid CLI JSON, or final response")
            if row.get("cli_json_valid") is True and row.get("selected_command") is None:
                raise EvidenceError("CLI JSON proof without selected command")
            if not row.get("reason"):
                raise EvidenceError("agent route needs reason")
            if row["outcome"] != "pass":
                unmet.append(f"agent:{pair[0]}:{pair[1]}")
        criteria = data.get("criteria")
        if not isinstance(criteria, list) or len(criteria) != 4 or {r.get("id") for r in criteria} != {1, 2, 3, 4}:
            raise EvidenceError("criteria need four roadmap verdicts")
        for row in criteria:
            if row.get("verdict") not in ("passed", "failed", "unverified") or not row.get("reason"):
                raise EvidenceError("invalid roadmap verdict")
            if row["verdict"] == "passed":
                if row["id"] == 1 and "offline" in unmet:
                    raise EvidenceError("documentation criterion passed without regression proof")
                if row["id"] == 2 and any(r.get("status") != "success" for r in data.get("deployment", [])):
                    raise EvidenceError("deployment criterion passed with skipped/failed target")
                if row["id"] == 2 and validate_ledger(data, "deployment"):
                    raise EvidenceError("deployment criterion passed without complete link proof")
                if row["id"] == 3 and any(key.startswith(("lxp:", "download:", "watch")) for key in validate_ledger(data, "live")):
                    raise EvidenceError("live criterion passed with unverified prerequisite")
                if row["id"] == 4 and "scheduler" in validate_ledger(data, "live"):
                    raise EvidenceError("Scheduler criterion passed without preview proof")
                if row["id"] == 2 and any(r.get("outcome") != "pass" for r in rows):
                    raise EvidenceError("deployment criterion passed without fresh-session routes")
            else:
                unmet.append(f"criterion:{row['id']}")
    return unmet


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--section", choices=("deployment", "live", "agents"))
    parser.add_argument("--path", type=Path, default=EVIDENCE)
    args = parser.parse_args()
    try:
        unmet = validate_ledger(read_ledger(args.path), args.section)
    except (EvidenceError, OSError, json.JSONDecodeError) as error:
        print(f"INVALID: {error}")
        return 2
    print(f"{'INCOMPLETE' if unmet else 'PASS'}: {args.section or 'all'}; unmet={len(unmet)}")
    for item in unmet:
        print(f"- {item}")
    return 1 if unmet else 0


if __name__ == "__main__":
    raise SystemExit(main())
