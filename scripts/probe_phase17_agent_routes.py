"""Run privacy-limited, fresh-session CoursePilot skill routing probes.

Only small, classified observations are printed. Agent streams and LMS responses
live in a temporary directory for the duration of one probe and are then removed.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
import os
import re
import shutil
import signal
import subprocess
import tempfile
import time
from pathlib import Path

PROMPTS = {"진도율": "progress", "공지": "notices", "Q&A": "qna"}
SKILL_TARGETS = {
    "claude": Path.home() / ".claude/skills/coursepilot",
    "codex": Path.home() / ".codex/skills/coursepilot",
    "pi": Path.home() / ".pi/agent/skills/coursepilot",
    "hermes": Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local"))) / "hermes/skills/coursepilot",
    "antigravity": Path.home() / ".gemini/antigravity-cli/skills/coursepilot",
}
COURSEPILOT_COMMAND = re.compile(
    r"^\s*(?:&\s*)?(?:(?:\S*[/\\])?uv(?:\.exe)?\s+(?:--directory\s+(?:\"[^\"]+\"|'[^']+'|\S+)\s+)?run\s+)?"
    r"(?:(?:\S*[/\\])?python(?:\.exe)?\s+-m\s+)?coursepilot\s+(progress|notices|qna)\b", re.I
)
SKILL_READ = re.compile(r"(?:coursepilot[/\\]SKILL\.md|/coursepilot\b|\\coursepilot\b)", re.I)
ERROR_PATTERNS = (
    ("quota", re.compile(r"rate.?limit|usage.?limit|quota|resource_exhausted|(?:http(?: status)?|status(?:_code)?)[\s\":=]+429\b", re.I)),
    ("sandbox_setup", re.compile(r"helper_unknown_error: setup refresh had errors", re.I)),
    ("browser_missing", re.compile(r"executable.*(?:doesn't exist|not found|missing)|browser.*missing", re.I)),
    ("authentication", re.compile(r"unauthorized|unauthenticated|login required|not logged in|invalid api key", re.I)),
    ("permission", re.compile(r"permission denied|access is denied|sandbox denied", re.I)),
    ("provider", re.compile(r"provider error|model error|api error", re.I)),
    ("command_unavailable", re.compile(r"not recognized as the name of a cmdlet|command not found|failed to spawn", re.I)),
    ("dependency", re.compile(r"modulenotfounderror|importerror|no module named", re.I)),
)
MAX_STREAM_BYTES = 4 * 1024 * 1024


def launcher(agent: str) -> str | None:
    """Prefer the known working Hermes shim without changing user PATH."""
    if agent == "hermes":
        current = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local"))) / "hermes/bin/hermes.cmd"
        if current.is_file():
            return str(current)
    if agent == "antigravity":
        return shutil.which("agy")
    return shutil.which(agent)


def launch_prefix(agent: str) -> list[str] | None:
    """Bypass Windows cmd shims so a bare Q&A remains one literal argument."""
    executable = launcher(agent)
    if not executable:
        return None
    if agent == "pi" and Path(executable).suffix.lower() == ".cmd":
        script = Path(executable).parent / "node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js"
        node = shutil.which("node")
        return [node, str(script)] if node and script.is_file() else None
    if agent == "codex" and Path(executable).suffix.lower() == ".cmd":
        script = Path(executable).parent / "node_modules/@openai/codex/bin/codex.js"
        node = shutil.which("node")
        return [node, str(script)] if node and script.is_file() else None
    if agent == "hermes" and Path(executable).suffix.lower() == ".cmd":
        match = re.search(r'^"([^"\r\n]+python\.exe)"\s+-I\s+-c\s+"([^"\r\n]+)"\s+%\*',
                          Path(executable).read_text(encoding="utf-8", errors="replace"), re.M | re.I)
        return [match.group(1), "-I", "-c", match.group(2)] if match and Path(match.group(1)).is_file() else None
    return [executable]


def browser_visible() -> bool:
    root = browser_root()
    return root.is_dir() and any(root.glob("chromium_headless_shell-*/chrome-headless-shell-win64/chrome-headless-shell.exe"))


def browser_root() -> Path:
    return Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH") or Path(os.environ.get("LOCALAPPDATA", "")) / "ms-playwright")


def preflight(agent: str) -> dict:
    target = SKILL_TARGETS[agent]
    prefix = launch_prefix(agent)
    docs = all((target / name).is_file() for name in ("SKILL.md", "JSON_CONTRACT.md"))
    result = {"agent": agent, "launcher_found": bool(prefix), "skill_docs_readable": docs,
              "browser_visible_on_host": browser_visible() if agent == "codex" else None}
    if agent == "hermes":
        hermes_home = Path(os.environ.get("HERMES_HOME") or Path(os.environ.get("LOCALAPPDATA", "")) / "hermes")
        config = hermes_home / "config.yaml"
        try:
            config_text = config.read_text(encoding="utf-8")
        except OSError:
            config_text = ""
        result["skill_autoloaded"] = bool(re.search(r"(?m)^\s+auto_load:\s*\n\s*-\s*coursepilot\s*$", config_text))
    if prefix:
        try:
            check = subprocess.run([*prefix, "--version"], cwd=tempfile.gettempdir(),
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=12, check=False)
            result["launcher_ready"] = check.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            result["launcher_ready"] = False
    else:
        result["launcher_ready"] = False
    if prefix and result["launcher_ready"]:
        auth_args = {"claude": ["auth", "status"], "codex": ["login", "status"],
                     "pi": ["auth", "check", "--provider", "freellmapi", "--no-refresh"],
                     "hermes": None, "antigravity": None}[agent]
        if auth_args is None:
            result["auth_preflight_ready"] = None
            return result
        try:
            auth = subprocess.run([*prefix, *auth_args], cwd=tempfile.gettempdir(),
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                  timeout=12, check=False)
            result["auth_preflight_ready"] = auth.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            result["auth_preflight_ready"] = False
    else:
        result["auth_preflight_ready"] = False
    return result


def command_for(agent: str, prompt: str, neutral: Path) -> list[str]:
    prefix = launch_prefix(agent)
    if not prefix:
        raise ValueError("launcher missing")
    if agent == "claude":
        return [*prefix, "-p", prompt, "--verbose", "--output-format", "stream-json", "--no-session-persistence",
                "--allowedTools", "Bash(uv *),PowerShell(uv *)",
                "--add-dir", str(Path(__file__).resolve().parent.parent), str(Path.home() / ".coursepilot")]
    if agent == "codex":
        sandbox = os.environ.get("COURSEPILOT_CODEX_SANDBOX", "workspace-write")
        if sandbox not in ("workspace-write", "danger-full-access"):
            raise ValueError("unsupported Codex sandbox")
        browser_allowance = ["--add-dir", str(browser_root())] if sandbox == "workspace-write" else []
        return [*prefix, "exec", "--ephemeral", "--json", "--skip-git-repo-check", "--sandbox", sandbox,
                *browser_allowance, "-C", str(neutral), prompt]
    if agent == "pi":
        return [*prefix, "--print", "--mode", "json", "--no-session", prompt]
    if agent == "hermes":
        return [*prefix, "chat", "-q", prompt, "--format", "stream-json", "--in", str(neutral)]
    if agent == "antigravity":
        return [*prefix, "--print", prompt, "--output-format", "stream-json",
                "--print-timeout", "180s", "--add-dir", str(Path(__file__).resolve().parent.parent)]
    raise ValueError("unsupported agent")


def _category(text: str) -> str | None:
    for name, pattern in ERROR_PATTERNS:
        if pattern.search(text):
            return name
    return None


def _selected_command(argument: str) -> str | None:
    """Recognize an invoked CLI, excluding searches and quoted documentation."""
    for segment in re.split(r"[\r\n;]|&&", argument):
        match = COURSEPILOT_COMMAND.match(segment)
        if match:
            return match.group(1).lower()
        # Codex on Windows wraps the actual uv invocation in PowerShell -Command.
        # Only unwrap an executed shell prefix; search/documentation commands stay excluded.
        if re.match(r"^\s*(?:rg|grep|findstr|Get-Content|Select-String)\b", segment, re.I):
            continue
        wrapper = re.search(r"\b(?:powershell|pwsh)(?:\.exe)?\b[^\r\n]*?\s-Command\s+(.+)$", segment, re.I)
        if wrapper:
            inner = wrapper.group(1).strip().strip('"\'')
            match = COURSEPILOT_COMMAND.match(inner)
            if match:
                return match.group(1).lower()
    return None


def _json_objects(value: str, depth: int = 0):
    """Yield JSON objects, including stdout embedded in a terminal tool envelope."""
    if depth > 2:
        return
    decoder = json.JSONDecoder()
    seen: set[int] = set()
    try:
        top = json.loads(value)
    except ValueError:
        top = None
    if isinstance(top, str):
        yield from _json_objects(top, depth + 1)
    elif isinstance(top, dict):
        yield top
        seen.add(value.find("{"))
        for key in ("stdout", "output", "content", "result"):
            child = top.get(key)
            if isinstance(child, str):
                yield from _json_objects(child, depth + 1)
    # PowerShell notices may precede the report or tool envelope.
    for match in re.finditer(r"\{", value):
        if match.start() in seen:
            continue
        try:
            parsed, _ = decoder.raw_decode(value[match.start():])
        except ValueError:
            continue
        if isinstance(parsed, dict):
            yield parsed
            for key in ("stdout", "output", "content", "result"):
                child = parsed.get(key)
                if isinstance(child, str):
                    yield from _json_objects(child, depth + 1)


def _json_report(value: str, selected: str | None) -> bool:
    if not selected:
        return False
    return any(report.get("schema_version") == 1 and report.get("command") == selected
               and not report.get("errors") and report.get("status") not in ("error", "partial_success")
               for report in _json_objects(value))


def _report_exit_code(value: str, selected: str) -> int | None:
    """Derive CoursePilot's exit from a complete successful report when a tool omits it."""
    if not _json_report(value, selected):
        return None
    if selected in ("notices", "qna"):
        return 0  # cli.py: _handle_board_command exits 0 when report.errors is empty.
    for report in _json_objects(value):
        if (isinstance(report, dict) and report.get("schema_version") == 1
                and report.get("command") == "progress" and not report.get("errors")
                and report.get("status") not in ("error", "partial_success")):
            summary = report.get("summary")
            count = summary.get("missed_past_count") if isinstance(summary, dict) else None
            if type(count) is int and count >= 0:
                return 1 if count else 0
    return None


def _tool_arguments(event: dict) -> list[str]:
    """Extract executed tool arguments, never assistant prose or skill examples."""
    found: list[str] = []
    item = event.get("item")
    if isinstance(item, dict) and item.get("type") in ("command_execution", "function_call"):
        for key in ("command", "arguments"):
            value = item.get(key)
            if isinstance(value, str):
                found.append(value)
    message = event.get("message")
    if isinstance(message, dict):
        for block in message.get("content", []):
            if isinstance(block, dict) and block.get("type") == "tool_use":
                args = block.get("input", {})
                if isinstance(args, dict):
                    found.extend(str(args[key]) for key in ("command", "cmd", "file_path") if key in args)
    if event.get("type") in ("tool_call", "tool_call_start", "tool_execution_start"):
        args = event.get("arguments") or event.get("args") or {}
        if isinstance(args, dict):
            found.extend(str(args[key]) for key in ("command", "cmd", "path") if key in args)
    if event.get("type") == "tool_use" and isinstance(event.get("input"), dict):
        found.extend(str(event["input"][key]) for key in ("command", "cmd", "path") if key in event["input"])
    return found


def _tool_results(event: dict) -> list[tuple[str, int | None, str | None]]:
    found: list[tuple[str, int | None, str | None]] = []
    item = event.get("item")
    if isinstance(item, dict) and item.get("type") == "command_execution" and event.get("type") == "item.completed":
        found.append((str(item.get("aggregated_output", "")), item.get("exit_code"), str(item.get("id")) if item.get("id") else None))
    if event.get("type") in ("tool_result", "tool_execution_end"):
        content = event.get("content") or event.get("result") or event.get("output") or ""
        code = event.get("exit_code")
        if isinstance(content, str):
            try:
                envelope = json.loads(content)
            except ValueError:
                envelope = None
            if isinstance(envelope, dict) and code is None:
                code = envelope.get("exit_code", envelope.get("exitCode"))
        if isinstance(content, dict):
            details = content.get("details") or {}
            if isinstance(details, dict) and code is None:
                code = details.get("exitCode", details.get("exit_code"))
            structured = content.get("structuredContent") or {}
            if isinstance(structured, dict) and code is None:
                code = structured.get("exitCode", structured.get("exit_code"))
            structured_output = structured.get("output") if isinstance(structured, dict) else None
            code = content.get("exitCode", content.get("exit_code", code))
            content = structured_output if isinstance(structured_output, str) else content.get("content") or content.get("output") or ""
        if isinstance(content, list):
            content = "\n".join(str(block.get("text", "")) for block in content if isinstance(block, dict))
        result_id = event.get("toolCallId") or event.get("tool_use_id") or event.get("id")
        found.append((str(content), code, str(result_id) if result_id else None))
    message = event.get("message")
    if isinstance(message, dict):
        for block in message.get("content", []):
            if isinstance(block, dict) and block.get("type") == "tool_result":
                content = block.get("content", "")
                if isinstance(content, list):
                    content = "\n".join(str(x.get("text", "")) for x in content if isinstance(x, dict))
                found.append((str(content), None, str(block.get("tool_use_id")) if block.get("tool_use_id") else None))
    return found


def parse_probe(agent: str, prompt: str, stdout: str, stderr: str, exit_code: int | None,
                timed_out: bool = False, skill_autoloaded: bool = False) -> dict:
    """Return only bounded proof fields; never include source streams or payloads."""
    expected = PROMPTS[prompt]
    selected: str | None = None
    triggered = agent == "hermes" and skill_autoloaded
    result_valid = False
    schema_seen = False
    cli_exit: int | None = None
    cli_exit_source: str | None = None
    final = False
    category = _category(stderr)
    pending_tool_ids: dict[str, str] = {}
    hermes_pending_command: str | None = None
    event_types: Counter[str] = Counter()
    stop_reasons: set[str] = set()
    error_codes: set[str] = set()
    result_shapes: list[dict[str, object]] = []
    cli_output_categories: set[str] = set()
    antigravity_shapes: list[dict[str, object]] = []
    antigravity_cli_events: list[dict[str, object]] = []
    claude_tool_names: Counter[str] = Counter()
    claude_command_tags: Counter[str] = Counter()
    claude_result_shapes: list[dict[str, object]] = []
    hermes_shapes: list[dict[str, object]] = []
    hermes_cli_events: list[dict[str, object]] = []
    codex_error_shapes: list[dict[str, object]] = []
    codex_command_events: list[dict[str, object]] = []
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        if agent == "hermes" and event.get("type") in ("tool_use", "tool_result") and len(hermes_shapes) < 8:
            hermes_shapes.append({"type": event["type"], "keys": sorted(event),
                                  "name": event.get("name") if isinstance(event.get("name"), str) and re.fullmatch(r"[A-Za-z_]{1,40}", event["name"]) else None,
                                  "arguments_keys": sorted(event["arguments"]) if isinstance(event.get("arguments"), dict) else [],
                                  "input_keys": sorted(event["input"]) if isinstance(event.get("input"), dict) else []})
        if agent == "codex" and isinstance(event.get("item"), dict) and event["item"].get("type") == "command_execution" and len(codex_command_events) < 10:
            item = event["item"]
            command = item.get("command") if isinstance(item.get("command"), str) else ""
            output = item.get("aggregated_output") if isinstance(item.get("aggregated_output"), str) else ""
            allowed_tokens = {"uv", "uv.exe", "run", "python", "python.exe", "-m", "coursepilot", "notices", "qna", "progress", "--json", "--directory", "powershell", "pwsh", "cmd", "-command", "-noprofile", "set-location", "cd", "&", ";", "|", "rg", "get-content"}
            skeleton = [token if token.lower() in allowed_tokens else "*" for token in re.findall(r"--?[A-Za-z0-9_.-]+|[A-Za-z0-9_.-]+|[;&|]", command)[:35]]
            codex_command_events.append({"event": event.get("type"), "command_len": len(command),
                                         "coursepilot_named": "coursepilot" in command.lower(),
                                         "uv_named": bool(re.search(r"\buv\b", command, re.I)),
                                         "json_flag": "--json" in command,
                                         "selected": _selected_command(command),
                                         "skeleton": skeleton if "uv" in command.lower() and "--json" in command else [],
                                         "output_len": len(output), "schema_seen": "schema_version" in output,
                                         "exit_code": item.get("exit_code") if type(item.get("exit_code")) is int else None})
        if agent == "antigravity":
            kind = event.get("event")
            nested = event.get(kind) if isinstance(kind, str) else None
            if isinstance(nested, dict):
                event = {"type": kind, **nested}
            if len(antigravity_shapes) < 6:
                antigravity_shapes.append({"type": kind if isinstance(kind, str) and re.fullmatch(r"[A-Za-z_.]{1,40}", kind) else None,
                                           "keys": sorted(nested) if isinstance(nested, dict) else []})
            info = event.get("tool_info")
            if isinstance(info, dict):
                params = info.get("parameters") or {}
                tool_name = info.get("name")
                if isinstance(params, dict):
                    path = params.get("AbsolutePath")
                    if isinstance(path, str) and SKILL_READ.search(path) and path.lower().endswith("skill.md"):
                        triggered = True
                    command = params.get("CommandLine")
                    invoked = _selected_command(command) if tool_name == "run_command" and isinstance(command, str) else None
                    if invoked:
                        selected = invoked
                        result_valid = False
                        cli_exit = None
                        cli_exit_source = None
                        output = info.get("output")
                        if not isinstance(output, str):
                            output = ""
                        if len(antigravity_cli_events) < 6:
                            antigravity_cli_events.append({"command": invoked, "json_flag": "--json" in command,
                                                           "state": event.get("state") if event.get("state") in ("started", "running", "completed", "failed") else None,
                                                           "info_keys": sorted(info), "output_len": len(output),
                                                           "schema_seen": "schema_version" in output})
                        result_valid = _json_report(output, invoked)
                        schema_seen = result_valid
                        match = re.search(r"(?:exit\s*code|exited\s*with\s*code)\s*[:=]?\s*(-?\d+)", output, re.I)
                        if match:
                            cli_exit = int(match.group(1))
                            cli_exit_source = "tool_output"
                        elif result_valid and "error" not in info:
                            cli_exit = _report_exit_code(output, invoked)
                            if cli_exit is not None:
                                cli_exit_source = "cli_report_contract"
                        if not result_valid:
                            category = category or _category(output)
                if isinstance(info.get("error"), str):
                    category = category or _category(info["error"]) or "tool_error"
            if event.get("type") == "result":
                final = event.get("status") == "SUCCESS"
        event_type = event.get("type")
        if isinstance(event_type, str) and re.fullmatch(r"[a-z_\.]{1,40}", event_type):
            event_types[event_type] += 1
        message_value = event.get("message")
        if isinstance(message_value, dict):
            stop = message_value.get("stopReason") or message_value.get("stop_reason")
            if isinstance(stop, str) and re.fullmatch(r"[a-z_]{1,40}", stop):
                stop_reasons.add(stop)
            for block in message_value.get("content", []):
                if agent == "claude" and isinstance(block, dict) and block.get("type") == "tool_result" and len(claude_result_shapes) < 12:
                    content = block.get("content")
                    claude_result_shapes.append({"content_type": type(content).__name__,
                                                 "content_len": len(content) if isinstance(content, (str, list)) else None,
                                                 "content_block_types": [part.get("type") for part in content if isinstance(part, dict) and part.get("type") in ("text", "image", "error")][:3] if isinstance(content, list) else [],
                                                 "is_error": block.get("is_error") is True,
                                                 "matches_cli": str(block.get("tool_use_id")) in pending_tool_ids})
                if agent == "claude" and isinstance(block, dict) and block.get("type") == "tool_use":
                    name = block.get("name")
                    if isinstance(name, str) and re.fullmatch(r"[A-Za-z_]{1,32}", name):
                        claude_tool_names[name] += 1
                    tool_input = block.get("input") or {}
                    command_text = tool_input.get("command") if isinstance(tool_input, dict) else None
                    if isinstance(command_text, str):
                        for tag, pattern in (("uv_sync", r"\buv\s+sync\b"),
                                             ("playwright_install", r"\bplaywright\s+install\b"),
                                             ("coursepilot_cli", r"\bcoursepilot\s+(?:progress|notices|qna)\b")):
                            if re.search(pattern, command_text, re.I):
                                claude_command_tags[tag] += 1
                if (isinstance(block, dict) and block.get("type") == "tool_use"
                        and str(block.get("name", "")).lower() == "skill"):
                    skill_input = block.get("input") or {}
                    if isinstance(skill_input, dict) and skill_input.get("skill") == "coursepilot":
                        triggered = True
        error_value = event.get("error")
        if isinstance(error_value, dict):
            code = error_value.get("code") or error_value.get("type")
            if isinstance(code, str) and re.fullmatch(r"[A-Za-z_0-9-]{1,40}", code):
                error_codes.add(code)
        if event.get("type") in ("error", "turn.failed"):
            category = category or _category(str(error_value)) or "agent_error"
            if agent == "codex" and len(codex_error_shapes) < 4:
                compact_error = str(error_value or event.get("message") or "")
                codex_error_shapes.append({"event_keys": sorted(event),
                                           "error_type": type(error_value).__name__,
                                           "message_len": len(compact_error),
                                           "indicators": [name for name, pattern in ERROR_PATTERNS if pattern.search(compact_error)]})
        arguments = _tool_arguments(event)
        event_command = None
        for argument in arguments:
            if SKILL_READ.search(argument) and "SKILL.md" in argument:
                triggered = True
            invoked = _selected_command(argument)
            if invoked:
                selected = invoked
                event_command = selected
                result_valid = False
                schema_seen = False
                cli_exit = None
                cli_exit_source = None
                if agent == "hermes" and event.get("type") == "tool_use":
                    hermes_pending_command = selected
                tool_id = (event.get("item") or {}).get("id") or event.get("toolCallId") or event.get("id")
                if tool_id:
                    pending_tool_ids[str(tool_id)] = selected
                message = message_value if isinstance(message_value, dict) else {}
                for block in message.get("content", []):
                    if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("id"):
                        pending_tool_ids[str(block["id"])] = selected
        for output, code, result_tool_id in _tool_results(event):
            result_command = event_command or (pending_tool_ids.pop(result_tool_id, None) if result_tool_id else None)
            if agent == "hermes" and event.get("type") == "tool_result":
                result_command = result_command or hermes_pending_command
                hermes_pending_command = None
            matched_result = result_command is not None
            if agent == "hermes" and event.get("type") == "tool_result" and matched_result and len(hermes_cli_events) < 4:
                report_command = None
                report_error_count = None
                for match in re.finditer(r"\{", output):
                    try:
                        parsed, _ = json.JSONDecoder().raw_decode(output[match.start():])
                    except ValueError:
                        continue
                    if isinstance(parsed, dict) and parsed.get("schema_version") == 1:
                        report_command = parsed.get("command") if parsed.get("command") in PROMPTS.values() else "other"
                        report_error_count = len(parsed["errors"]) if isinstance(parsed.get("errors"), list) else None
                        break
                hermes_cli_events.append({"output_len": len(output), "tool_error": event.get("is_error") is True,
                                          "schema_seen": "schema_version" in output,
                                          "escaped_schema": '\\"schema_version\\"' in output,
                                          "report_command": report_command, "report_error_count": report_error_count})
            if matched_result and len(result_shapes) < 4:
                raw_result = event.get("result")
                details = raw_result.get("details") if isinstance(raw_result, dict) else None
                structured = raw_result.get("structuredContent") if isinstance(raw_result, dict) else None
                structured_output = structured.get("output") if isinstance(structured, dict) else None
                result_shapes.append({"event": event_type, "result_keys": sorted(raw_result) if isinstance(raw_result, dict) else [],
                                      "detail_keys": sorted(details) if isinstance(details, dict) else [],
                                      "structured_keys": sorted(structured) if isinstance(structured, dict) else [],
                                      "structured_output_len": len(structured_output) if isinstance(structured_output, str) else None,
                                      "structured_schema_seen": "schema_version" in structured_output if isinstance(structured_output, str) else False,
                                      "truncated": structured.get("truncated") if isinstance(structured, dict) and type(structured.get("truncated")) is bool else None,
                                      "exit_type": type(code).__name__})
            report_valid = matched_result and _json_report(output, result_command)
            if matched_result and not report_valid:
                for name, pattern in ERROR_PATTERNS:
                    if pattern.search(output):
                        cli_output_categories.add(name)
            if code is None:
                code_match = re.search(r"(?:exit code|exited with code)\s*[:=]?\s*(\d+)", output, re.I)
                if code_match:
                    code = int(code_match.group(1))
            if matched_result and "schema_version" in output:
                schema_seen = True
            if report_valid:
                result_valid = True
                cli_exit = code if isinstance(code, int) else None
                if cli_exit is not None:
                    cli_exit_source = "tool_result"
                elif agent in ("claude", "hermes"):
                    cli_exit = _report_exit_code(output, result_command)
                    if cli_exit is not None:
                        cli_exit_source = "cli_report_contract"
            elif matched_result and selected and isinstance(code, int):
                cli_exit = code
                cli_exit_source = "tool_result"
                category = category or _category(output)
        if event.get("type") in ("result", "turn.completed", "agent_end") and agent != "antigravity":
            final = not bool(event.get("is_error") or event.get("error"))
    if timed_out:
        category = "timeout"
    elif category is None and exit_code not in (0, None):
        category = "agent_exit"
    if selected and selected != expected:
        category = "wrong_route"
    elif not selected and category is None:
        category = "no_command"
    elif selected and not result_valid and category is None:
        category = "cli_unverified"
    outcome = ("pass" if selected == expected and triggered and result_valid and type(cli_exit) is int
               and cli_exit in (0, 1) and final
               and exit_code == 0 and category is None else "fail")
    if agent == "hermes" and not event_types and not timed_out:
        outcome = "unverified"
        category = "unstructured_output"
    return {"agent": agent, "prompt": prompt, "triggered": triggered,
            "selected_command": selected, "cli_exit": cli_exit, "cli_exit_source": cli_exit_source,
            "trigger_source": "configured_auto_load" if agent == "hermes" and skill_autoloaded else None,
            "cli_json_valid": result_valid,
            "cli_schema_seen": schema_seen,
            "final_response": final, "agent_exit": exit_code, "outcome": outcome,
            "error_category": category, "reason": "verified" if outcome == "pass" else category or "incomplete",
            "diagnostic": {"events": dict(event_types), "stop_reasons": sorted(stop_reasons),
                           "error_codes": sorted(error_codes), "result_shapes": result_shapes,
                           "cli_output_categories": sorted(cli_output_categories),
                           "antigravity_shapes": antigravity_shapes if agent == "antigravity" else [],
                           "antigravity_cli_events": antigravity_cli_events if agent == "antigravity" else [],
                           "claude_tool_names": dict(claude_tool_names) if agent == "claude" else {},
                           "claude_command_tags": dict(claude_command_tags) if agent == "claude" else {},
                           "claude_result_shapes": claude_result_shapes if agent == "claude" else [],
                           "hermes_shapes": hermes_shapes if agent == "hermes" else [],
                           "hermes_cli_events": hermes_cli_events if agent == "hermes" else [],
                           "codex_error_shapes": codex_error_shapes if agent == "codex" else [],
                           "codex_command_events": codex_command_events if agent == "codex" else []}}


def _stop_process_tree(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10, check=False)
    else:
        os.killpg(process.pid, signal.SIGKILL)
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


def _clean_probe_temp(neutral: Path) -> None:
    """Discard raw streams even when a child-owned cache blocks directory removal."""
    for name in ("stdout", "stderr"):
        try:
            (neutral / name).unlink(missing_ok=True)
        except OSError:
            pass
    if neutral.resolve().parent != Path(tempfile.gettempdir()).resolve() or not neutral.name.startswith("coursepilot-route-"):
        return
    try:
        shutil.rmtree(neutral)
    except OSError:
        pass


def run_probe(agent: str, prompt: str, timeout: int = 150, context_control: bool = False) -> dict:
    ready = preflight(agent)
    if not ready["launcher_ready"] or not ready["skill_docs_readable"]:
        return {"agent": agent, "prompt": prompt, "outcome": "unverified", "triggered": False,
                "selected_command": None, "cli_exit": None, "cli_json_valid": False,
                "final_response": False, "agent_exit": None, "error_category": "preflight",
                "reason": "launcher or skill docs unavailable", "preflight": ready}
    neutral = Path(tempfile.mkdtemp(prefix="coursepilot-route-"))
    process: subprocess.Popen | None = None
    try:
        actual_prompt = f"CoursePilot에서 {prompt} 확인해줘" if context_control else prompt
        command = command_for(agent, actual_prompt, neutral)
        with (neutral / "stdout").open("wb") as output, (neutral / "stderr").open("wb") as errors:
            process = subprocess.Popen(command, cwd=neutral, stdin=subprocess.DEVNULL,
                                       stdout=output, stderr=errors,
                                       creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
                                       start_new_session=os.name != "nt")
            start = time.monotonic()
            timed_out = False
            while process.poll() is None:
                if (time.monotonic() - start > timeout
                        or (neutral / "stdout").stat().st_size > MAX_STREAM_BYTES
                        or (neutral / "stderr").stat().st_size > MAX_STREAM_BYTES):
                    timed_out = True
                    _stop_process_tree(process)
                    break
                time.sleep(0.2)
        stdout = (neutral / "stdout").read_text(encoding="utf-8", errors="replace")[:MAX_STREAM_BYTES]
        stderr = (neutral / "stderr").read_text(encoding="utf-8", errors="replace")[:MAX_STREAM_BYTES]
        result = parse_probe(agent, prompt, stdout, stderr, process.returncode, timed_out,
                             skill_autoloaded=ready.get("skill_autoloaded") is True)
        result["stream_shape"] = {"stdout_bytes": len(stdout.encode("utf-8")),
                                  "stderr_bytes": len(stderr.encode("utf-8")),
                                  "stdout_json_lines": sum(isinstance(_parse_json_line(line), dict) for line in stdout.splitlines())}
        result["preflight"] = ready
        result["context_control"] = context_control
        return result
    finally:
        if process is not None:
            _stop_process_tree(process)
        _clean_probe_temp(neutral)


def _parse_json_line(line: str) -> object | None:
    try:
        return json.loads(line)
    except ValueError:
        return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", choices=tuple(SKILL_TARGETS), required=True)
    parser.add_argument("--prompt", choices=tuple(PROMPTS), required=True)
    parser.add_argument("--timeout", type=int, default=150)
    parser.add_argument("--context-control", action="store_true", help="Diagnostic only; never counts as an exact-prompt pass")
    args = parser.parse_args()
    result = run_probe(args.agent, args.prompt, args.timeout, args.context_control)
    if args.context_control:
        result["outcome"] = "control"
    print(json.dumps(result, ensure_ascii=True))
    return 0 if result["outcome"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
