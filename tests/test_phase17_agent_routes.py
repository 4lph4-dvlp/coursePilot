"""Synthetic agent streams never imply a successful route from process exit alone."""

from __future__ import annotations

import json
from scripts.probe_phase17_agent_routes import _clean_probe_temp, _json_report, _report_exit_code, _selected_command, command_for, parse_probe, _stop_process_tree


def codex_events(command: str, report_command: str, exit_code: int = 0) -> str:
    events = [
        {"type": "item.completed", "item": {"type": "command_execution", "command": "Get-Content C:/Users/a/.codex/skills/coursepilot/SKILL.md", "exit_code": 0}},
        {"type": "item.completed", "item": {"type": "command_execution", "command": f"uv run python -m coursepilot {command} --json", "exit_code": exit_code,
                                          "aggregated_output": json.dumps({"schema_version": 1, "command": report_command, "errors": []})}},
        {"type": "turn.completed"},
    ]
    return "\n".join(json.dumps(event) for event in events)


def test_correct_command_and_valid_json_pass() -> None:
    row = parse_probe("codex", "공지", codex_events("notices", "notices"), "", 0)
    assert row["outcome"] == "pass"
    assert row["cli_json_valid"] is True
    assert row["final_response"] is True


def test_successful_cli_json_number_does_not_claim_quota() -> None:
    events = [json.loads(line) for line in codex_events("notices", "notices").splitlines()]
    events[1]["item"]["aggregated_output"] = json.dumps({"schema_version": 1, "command": "notices", "errors": [], "item_id": 429})
    stream = "\n".join(json.dumps(event) for event in events)
    row = parse_probe("codex", "공지", stream, "", 0)
    assert row["outcome"] == "pass"
    assert "quota" not in row["diagnostic"]["cli_output_categories"]


def test_profile_notice_before_cli_json_is_accepted() -> None:
    output = "PowerShell profile notice\n" + json.dumps({"schema_version": 1, "command": "notices", "errors": []})
    assert _json_report(output, "notices")
    assert not _json_report(output, "qna")


def test_pi_tool_result_is_matched_by_tool_call_id() -> None:
    events = [
        {"type": "tool_execution_start", "toolCallId": "read1", "toolName": "read", "args": {"path": "/skills/coursepilot/SKILL.md"}},
        {"type": "tool_execution_start", "toolCallId": "bash1", "toolName": "bash", "args": {"command": "uv run python -m coursepilot qna --json"}},
        {"type": "tool_execution_end", "toolCallId": "bash1", "result": {"content": [{"type": "text", "text": json.dumps({"schema_version": 1, "command": "qna", "errors": []})}], "details": {"exitCode": 0}}},
        {"type": "agent_end"},
    ]
    row = parse_probe("pi", "Q&A", "\n".join(json.dumps(event) for event in events), "", 0)
    assert row["outcome"] == "pass"


def test_pi_structured_result_contains_cli_exit() -> None:
    events = [
        {"type": "tool_execution_start", "toolCallId": "bash1", "toolName": "bash", "args": {"command": "uv run python -m coursepilot qna --json"}},
        {"type": "tool_execution_end", "toolCallId": "bash1", "result": {
            "content": [{"type": "text", "text": json.dumps({"schema_version": 1, "command": "qna", "errors": []})}],
            "structuredContent": {"exit_code": 0, "output": "private"}}},
        {"type": "agent_end"},
    ]
    row = parse_probe("pi", "Q&A", "\n".join(json.dumps(event) for event in events), "", 0)
    assert row["cli_exit"] == 0
    assert row["outcome"] == "fail"  # skill discovery is a separate proof field
    assert "private" not in json.dumps(row)


def test_pi_and_hermes_pass_bare_qna_as_one_process_argument(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("scripts.probe_phase17_agent_routes.launch_prefix", lambda agent: ["node.exe", "cli.js"] if agent == "pi" else ["python.exe", "-I", "-c", "bootstrap"])
    for agent in ("pi", "hermes"):
        args = command_for(agent, "Q&A", tmp_path)
        assert "Q&A" in args
        assert args.count("Q&A") == 1
        assert not any(arg.lower().endswith(".cmd") for arg in args)


def test_codex_node_entry_preserves_bare_ampersand_argument(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("scripts.probe_phase17_agent_routes.launch_prefix", lambda _agent: ["node.exe", "codex.js"])
    args = command_for("codex", "Q&A", tmp_path)
    assert args[-1] == "Q&A"
    assert args.count("Q&A") == 1
    assert not any(arg.lower().endswith(".cmd") for arg in args)


def test_codex_diagnostic_sandbox_mode_is_explicit(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("scripts.probe_phase17_agent_routes.launch_prefix", lambda _agent: ["codex.exe"])
    monkeypatch.setenv("COURSEPILOT_CODEX_SANDBOX", "danger-full-access")
    command = command_for("codex", "공지", tmp_path)
    assert command[command.index("--sandbox") + 1] == "danger-full-access"
    assert "--add-dir" not in command


def test_claude_allows_only_uv_shell_calls_in_print_mode(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("scripts.probe_phase17_agent_routes.launch_prefix", lambda _agent: ["claude.exe"])
    command = command_for("claude", "공지", tmp_path)
    assert command[command.index("-p") + 1] == "공지"
    assert command[command.index("--allowedTools") + 1] == "Bash(uv *),PowerShell(uv *)"
    assert command[-3] == "--add-dir"


def test_wrong_route_fails_even_if_cli_and_agent_exit_zero() -> None:
    row = parse_probe("codex", "공지", codex_events("progress", "progress"), "", 0)
    assert row["selected_command"] == "progress"
    assert row["outcome"] == "fail"
    assert row["error_category"] == "wrong_route"


def test_missing_cli_does_not_parse_prose_as_tool_call() -> None:
    stream = json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "Use coursepilot notices --json"}})
    row = parse_probe("codex", "공지", stream, "", 0)
    assert row["selected_command"] is None
    assert row["outcome"] == "fail"


def test_search_command_mentioning_coursepilot_is_not_a_cli_route() -> None:
    assert _selected_command("rg -n 'coursepilot notices' SKILL.md") is None
    assert _selected_command("Get-Content SKILL.md | Select-String 'coursepilot qna'") is None
    assert _selected_command('uv --directory "D:/dev/coursePilot" run python -m coursepilot notices --json') == "notices"
    assert _selected_command('C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -NoProfile -Command "uv --directory D:/dev/coursePilot run python -m coursepilot notices --json"') == "notices"
    assert _selected_command('rg -n "PowerShell -Command uv run python -m coursepilot notices --json" SKILL.md') is None


def test_cli_failure_and_timeout_are_bounded() -> None:
    failed = parse_probe("codex", "공지", codex_events("notices", "notices", 2), "", 0)
    assert failed["outcome"] == "fail"
    timed = parse_probe("codex", "공지", codex_events("notices", "notices"), "", None, timed_out=True)
    assert timed["outcome"] == "fail"
    assert timed["error_category"] == "timeout"


def test_later_cli_retry_without_result_cannot_inherit_earlier_json() -> None:
    events = [
        {"type": "item.completed", "item": {"type": "command_execution", "command": "Get-Content C:/Users/a/.codex/skills/coursepilot/SKILL.md", "exit_code": 0}},
        {"type": "item.completed", "item": {"type": "command_execution", "command": "coursepilot notices --json", "exit_code": 0,
                                            "aggregated_output": json.dumps({"schema_version": 1, "command": "notices", "errors": []})}},
        {"type": "item.started", "item": {"type": "command_execution", "command": "coursepilot notices --json", "id": "retry"}},
        {"type": "turn.completed"},
    ]
    row = parse_probe("codex", "공지", "\n".join(json.dumps(event) for event in events), "", 0)
    assert row["outcome"] == "fail"
    assert row["cli_json_valid"] is False
    assert row["cli_exit"] is None


def test_private_stream_text_never_enters_row() -> None:
    marker = "SECRET_CANARY_4477"
    row = parse_probe("pi", "Q&A", json.dumps({"type": "error", "error": marker}), marker, 1)
    assert marker not in json.dumps(row)


def test_codex_sandbox_setup_failure_is_classified_without_raw_error() -> None:
    diagnostic = "Failed to create unified exec process: helper_unknown_error: setup refresh had errors"
    row = parse_probe("codex", "공지", "", diagnostic, 1)
    assert row["outcome"] == "fail"
    assert row["error_category"] == "sandbox_setup"
    assert diagnostic not in json.dumps(row)


def test_claude_skill_tool_counts_as_activation() -> None:
    stream = json.dumps({"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "skill1", "name": "Skill", "input": {"skill": "coursepilot"}}
    ]}})
    row = parse_probe("claude", "공지", stream, "", 0)
    assert row["triggered"] is True
    assert row["outcome"] == "fail"


def test_claude_board_exit_can_be_derived_when_tool_omits_it() -> None:
    events = [
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "skill", "name": "Skill", "input": {"skill": "coursepilot"}},
            {"type": "tool_use", "id": "cli", "name": "Bash", "input": {"command": "uv run python -m coursepilot notices --json"}},
        ]}},
        {"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "cli", "is_error": False,
             "content": json.dumps({"schema_version": 1, "command": "notices", "errors": []})},
        ]}},
        {"type": "result", "is_error": False},
    ]
    row = parse_probe("claude", "공지", "\n".join(json.dumps(event) for event in events), "", 0)
    assert row["outcome"] == "pass"
    assert row["cli_exit"] == 0
    assert row["cli_exit_source"] == "cli_report_contract"


def test_plain_hermes_output_cannot_prove_tool_route() -> None:
    row = parse_probe("hermes", "공지", "Assistant reply without tool events", "", 0)
    assert row["outcome"] == "unverified"
    assert row["error_category"] == "unstructured_output"


def test_hermes_autoloaded_skill_and_terminal_result_are_distinct_proof() -> None:
    events = [
        {"type": "tool_use", "name": "terminal", "input": {"command": "uv run python -m coursepilot notices --json"}},
        {"type": "tool_result", "name": "terminal", "output": json.dumps({"schema_version": 1, "command": "notices", "errors": []}), "is_error": False},
        {"type": "result", "is_error": False},
    ]
    stream = "\n".join(json.dumps(event) for event in events)
    without_autoload = parse_probe("hermes", "공지", stream, "", 0)
    assert without_autoload["outcome"] == "fail"
    row = parse_probe("hermes", "공지", stream, "", 0, skill_autoloaded=True)
    assert row["outcome"] == "pass"
    assert row["trigger_source"] == "configured_auto_load"
    assert row["cli_exit_source"] == "cli_report_contract"


def test_hermes_terminal_json_envelope_keeps_actual_exit_and_report() -> None:
    report = json.dumps({"schema_version": 1, "command": "notices", "errors": []})
    envelope = json.dumps({"stdout": report, "stderr": "private", "exit_code": 0})
    events = [
        {"type": "tool_use", "name": "terminal", "input": {"command": "uv run python -m coursepilot notices --json"}},
        {"type": "tool_result", "name": "terminal", "output": envelope, "is_error": False},
        {"type": "result", "is_error": False},
    ]
    row = parse_probe("hermes", "공지", "\n".join(json.dumps(event) for event in events), "", 0, skill_autoloaded=True)
    assert row["outcome"] == "pass"
    assert row["cli_exit"] == 0
    assert row["cli_exit_source"] == "tool_result"
    assert "private" not in json.dumps(row)


def test_antigravity_step_updates_require_skill_command_result_and_final() -> None:
    events = [
        {"type": "step_update", "tool_info": {"name": "view_file", "parameters": {"AbsolutePath": "C:/Users/a/.gemini/antigravity-cli/skills/coursepilot/SKILL.md"}, "output": "private"}},
        {"type": "step_update", "tool_info": {"name": "run_command", "parameters": {"CommandLine": "uv run python -m coursepilot notices --json"},
                                        "output": "Exit code: 0\n" + json.dumps({"schema_version": 1, "command": "notices", "errors": []})}},
        {"type": "result", "status": "SUCCESS", "response": "private"},
    ]
    row = parse_probe("antigravity", "공지", "\n".join(json.dumps(event) for event in events), "", 0)
    assert row["outcome"] == "pass"
    assert row["cli_exit"] == 0
    assert "private" not in json.dumps(row)

    wrapped = [{"event": event["type"], event["type"]: {key: value for key, value in event.items() if key != "type"}} for event in events]
    wrapped_row = parse_probe("antigravity", "공지", "\n".join(json.dumps(event) for event in wrapped), "", 0)
    assert wrapped_row["outcome"] == "pass"


def test_antigravity_board_exit_is_derived_from_verified_report() -> None:
    events = [
        {"type": "step_update", "tool_info": {"name": "view_file", "parameters": {"AbsolutePath": "/coursepilot/SKILL.md"}}},
        {"type": "step_update", "tool_info": {"name": "run_command", "parameters": {"CommandLine": "coursepilot qna --json"},
                                        "output": json.dumps({"schema_version": 1, "command": "qna", "errors": []})}},
        {"type": "result", "status": "SUCCESS"},
    ]
    row = parse_probe("antigravity", "Q&A", "\n".join(json.dumps(event) for event in events), "", 0)
    assert row["outcome"] == "pass"
    assert row["cli_exit"] == 0
    assert row["cli_exit_source"] == "cli_report_contract"


def test_progress_exit_derivation_requires_missed_count() -> None:
    base = {"schema_version": 1, "command": "progress", "status": "success", "errors": []}
    assert _report_exit_code(json.dumps(base), "progress") is None
    base["summary"] = {"missed_past_count": 3}
    assert _report_exit_code(json.dumps(base), "progress") == 1
    base["summary"] = {"missed_past_count": 0}
    assert _report_exit_code(json.dumps(base), "progress") == 0


def test_stop_process_tree_only_stops_child() -> None:
    import subprocess
    import sys

    process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"],
                               creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
                               start_new_session=sys.platform != "win32")
    _stop_process_tree(process)
    assert process.poll() is not None


def test_raw_streams_removed_when_child_cache_denies_directory_cleanup(monkeypatch) -> None:
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory(prefix="coursepilot-route-") as directory:
        neutral = Path(directory)
        for name in ("stdout", "stderr"):
            (neutral / name).write_text("private", encoding="utf-8")
        with monkeypatch.context() as patch:
            patch.setattr("scripts.probe_phase17_agent_routes.shutil.rmtree", lambda *_args: (_ for _ in ()).throw(PermissionError("child cache")))
            _clean_probe_temp(neutral)
        assert not (neutral / "stdout").exists()
        assert not (neutral / "stderr").exists()
