# Phase 17 end-to-end evidence

Observed on 2026-10-04 and 2026-10-05. This ledger keeps counts and outcomes only. It excludes course titles, full CLI payloads, credentials, and agent transcripts. An `unverified` row remains open until a direct observation supports it.

```json
{
  "offline": {"full_suite_passed": true, "test_count": 455},
  "deployment": [
    {"agent": "claude", "status": "success", "target": "C:/Users/alpha/.claude/skills/coursepilot", "reason": "linked docs readable", "docs_readable": true, "link_source": "D:/dev/coursePilot/skills/coursepilot"},
    {"agent": "codex", "status": "success", "target": "C:/Users/alpha/.codex/skills/coursepilot", "reason": "linked docs readable", "docs_readable": true, "link_source": "D:/dev/coursePilot/skills/coursepilot"},
    {"agent": "antigravity", "status": "success", "target": "C:/Users/alpha/.gemini/antigravity/skills/coursepilot", "reason": "linked docs readable", "docs_readable": true, "link_source": "D:/dev/coursePilot/skills/coursepilot"},
    {"agent": "pi", "status": "success", "target": "C:/Users/alpha/.pi/agent/skills/coursepilot", "reason": "linked docs readable", "docs_readable": true, "link_source": "D:/dev/coursePilot/skills/coursepilot"},
    {"agent": "hermes", "status": "success", "target": "C:/Users/alpha/AppData/Local/hermes/skills/coursepilot", "reason": "linked docs readable", "docs_readable": true, "link_source": "D:/dev/coursePilot/skills/coursepilot"}
  ],
  "optional_scheduler": [
    {"agent": "claude", "readable": false},
    {"agent": "codex", "readable": true},
    {"agent": "antigravity", "readable": false},
    {"agent": "pi", "readable": false},
    {"agent": "hermes", "readable": false}
  ],
  "lxp": {"enrolled_count": 7, "reason": "live check baseline reconciled with progress, notices, and qna on 2026-10-05", "commands": {
    "check": {"success_count": 7, "failure_count": 0, "observed": true},
    "progress": {"success_count": 7, "failure_count": 0, "observed": true},
    "notices": {"success_count": 7, "failure_count": 0, "observed": true},
    "qna": {"success_count": 7, "failure_count": 0, "observed": true}
  }},
  "downloads": {
    "material": {"status": "downloaded", "created_by_smoke": true, "saved_path_present": true, "file_existed": true, "size_bytes": 311255, "cleaned": true, "reason": "one requested week-six CSMSDoc PDF downloaded through the authenticated viewer button; CLI reported downloaded, saved_path and file stat matched, then unique smoke directory was removed"},
    "vod": {"status": "downloaded", "created_by_smoke": true, "saved_path_present": true, "file_existed": true, "size_bytes": 216275200, "cleaned": true, "reason": "one VOD saved under a unique smoke directory, stat verified, then smoke directory removed"}
  },
  "watch": {"dry_run_observed": true, "dry_run_at": "2026-10-04T18:12:20+00:00", "started_at": "2026-10-04T18:12:44+00:00", "status_at": "2026-10-04T18:13:09+00:00", "stopped_at": "2026-10-04T18:13:11.6081826Z", "reason": "live PID confirmed active; watch stop returned stopped=true with exit 0 and final status stopped; stopped_at is watch state file modification time"},
  "scheduler": {"read_observed": true, "sync_preview_observed": true, "watch_preview_observed": true, "create_calls": 0, "update_calls": 0, "reason": "independent Scheduler list, academic sync preview, and watch completion dry-run succeeded without apply flags"},
  "agents": [
    {"agent": "claude", "prompt": "진도율", "triggered": true, "selected_command": "progress", "outcome": "fail", "reason": "fresh session selected CoursePilot skill and progress CLI but ended with error_max_turns before a final answer"},
    {"agent": "claude", "prompt": "공지", "triggered": false, "selected_command": null, "outcome": "fail", "reason": "fresh session with explicit Korean skill description still searched files and ended with error_max_turns without CLI selection"},
    {"agent": "claude", "prompt": "Q&A", "triggered": false, "selected_command": null, "outcome": "fail", "reason": "fresh session with explicit Korean skill description searched files and ended with error_max_turns without CLI selection"},
    {"agent": "codex", "prompt": "진도율", "triggered": false, "selected_command": null, "outcome": "fail", "reason": "fresh codex exec completed after 159 seconds with no CoursePilot CLI selection"},
    {"agent": "codex", "prompt": "공지", "triggered": false, "selected_command": null, "outcome": "fail", "reason": "fresh codex exec completed after 59 seconds with no CoursePilot CLI selection"},
    {"agent": "codex", "prompt": "Q&A", "triggered": false, "selected_command": null, "outcome": "fail", "reason": "fresh codex exec exited 1 before any command execution"},
    {"agent": "antigravity", "prompt": "진도율", "triggered": false, "selected_command": null, "outcome": "unverified", "reason": "Antigravity IDE installed, but its CLI has editor commands only and no headless agent prompt; no active GUI session"},
    {"agent": "antigravity", "prompt": "공지", "triggered": false, "selected_command": null, "outcome": "unverified", "reason": "Antigravity IDE installed, but its CLI has editor commands only and no headless agent prompt; no active GUI session"},
    {"agent": "antigravity", "prompt": "Q&A", "triggered": false, "selected_command": null, "outcome": "unverified", "reason": "Antigravity IDE installed, but its CLI has editor commands only and no headless agent prompt; no active GUI session"},
    {"agent": "pi", "prompt": "진도율", "triggered": true, "selected_command": "progress", "outcome": "pass", "reason": "fresh Pi session read CoursePilot skill, executed progress CLI, observed bash results, and exited 0"},
    {"agent": "pi", "prompt": "공지", "triggered": true, "selected_command": "notices", "outcome": "pass", "reason": "fresh Pi session read CoursePilot skill, executed notices CLI, observed bash result, and exited 0"},
    {"agent": "pi", "prompt": "Q&A", "triggered": false, "selected_command": null, "outcome": "fail", "reason": "two fresh Pi sessions exited 1 before any CoursePilot tool call"},
    {"agent": "hermes", "prompt": "진도율", "triggered": false, "selected_command": null, "outcome": "unverified", "reason": "Hermes CLI exits 1 without output for help/version; session launch unavailable"},
    {"agent": "hermes", "prompt": "공지", "triggered": false, "selected_command": null, "outcome": "unverified", "reason": "Hermes CLI exits 1 without output for help/version; session launch unavailable"},
    {"agent": "hermes", "prompt": "Q&A", "triggered": false, "selected_command": null, "outcome": "unverified", "reason": "Hermes CLI exits 1 without output for help/version; session launch unavailable"}
  ],
  "criteria": [
    {"id": 1, "verdict": "passed", "reason": "skill and contract tests passed with the full 455-test suite"},
    {"id": 2, "verdict": "unverified", "reason": "five links verified; fresh-session routing pending"},
    {"id": 3, "verdict": "passed", "reason": "seven-course live reads, material and VOD files, and bounded watch stop were observed"},
    {"id": 4, "verdict": "passed", "reason": "independent Scheduler read and both CoursePilot previews succeeded with zero create/update calls"}
  ]
}
```

## Observations

- Full regression: 455 tests passed after the VOD session constructor, Windows watch PID, and CSMSDoc browser download fixes.
- Batch command: `install-skill --all` exited 0 with five success rows. Independent target inspection found five source links and both docs readable at each target.
- After the Korean trigger description update, SHA-256 hashes of `SKILL.md` and `JSON_CONTRACT.md` read through each of the five targets still matched this checkout's source files.
- Initial live `check --json` exited 2 with safe `ConfigError`; after the user set the three LMS values locally, `check --json` exited 0 with 7 enrolled courses and 0 errors. `progress --refresh --json` covered 7 courses, all `ok`, with 0 collection errors and JSON status `success`; its process exit 1 is the CLI's overdue-item signal. `notices --json` and `qna --json` each returned 7 course groups and 0 errors. Raw course data and credential values were neither retained nor printed.
- Optional `notion-scheduler` Agent Skill is readable for Codex and absent in the other four target directories. Its absence did not change the CoursePilot install result.
- Independent Scheduler `list --limit 1` with the local CoursePilot environment exited 0 and reported 404 matching tasks, without retaining task data. `watch sync-notion --dry-run --json` exited 0 with `planned_count: 0` and `synced_count: 0`. After LMS configuration, academic `sync --json` exited 0 with 0 errors. No command included an apply flag; observed Notion create/update calls: 0.
- Source inspection confirms `sync --json` passes `dry_run=True` to `NotionSyncEngine.sync`; its dry-run branch returns after read and planning, before the `create_page` / `update_page` dispatch loop. This supports the zero-write observation for the academic preview.
- Materials preview found 55 planned items. Eleven earlier live single-item attempts, including one from each of five distinct courses, returned `viewed_only` because the HTTP downloader could not extract the CSMSDoc viewer's browser button. The user identified a downloadable week-six PDF. A Playwright probe found its `aria-label="파일 다운로드"` button and observed a 311,255-byte `.pdf` download event. After adding the authenticated browser fallback, a fresh `materials --course <alias> --week 6 --output-dir <unique smoke dir> --json` run exited 0, returned one `downloaded` item and zero failures, and produced a file inside the smoke directory whose actual size equaled the reported 311,255 bytes. That smoke directory was removed after verification. VOD preview found 105 candidates; one selected VOD returned `downloaded`, with a verified 216,275,200-byte file under its unique smoke directory, removed afterward. The initial VOD preview exposed an unsupported `SessionManager(relogin=...)` argument; the call was fixed before retry.
- `watch --dry-run --json` found one target before a live watch process was launched. The supervisor did not record a valid ordered `running` observation and its stop attempt interrupted the supervisor. A later direct status read found a stale `running` state with PID 7716; that PID was absent, `watch stop --json` reset the state, and a final status read returned `stopped`. This is partial watch evidence only; no Scheduler update flag was used. Playback may have left partial LXP progress.
- A later isolated-console watch probe observed `running` at 17:34:20 UTC after a fresh dry-run and start. `watch stop --json` exited 0 four seconds later but returned `stopped: false`; final state was `stopped`. That attempt did not prove active-process stop.
- Investigation found Windows `os.kill(pid, 0)` returned `OSError` for an active child here, so the existing `watch stop` liveness check treated active playback as absent. After replacing it with a Windows process-handle check, a fresh dry-run/start/status/stop sequence observed a live PID at 18:13:09 UTC, `watch stop --json` exited 0 with `stopped: true`, and final status was `stopped`. The live playback was brief and may leave partial LMS progress; no Notion update flag was used.
- Fresh-session probes used separate `진도율`, `공지`, and `Q&A` prompts. After the user configured LMS and the skill description included Korean triggers, Claude Code selected the skill and `progress` for `진도율` but ended with `error_max_turns`; its `공지` and `Q&A` sessions still made no CLI selection. Codex `진도율` and `공지` finished after 159 and 59 seconds without CLI selection; `Q&A` exited 1 before a command. Pi `진도율` and `공지` independently read the skill, ran the exact `progress` and `notices` CLI commands, and exited 0 with tool results. Pi `Q&A` exited 1 before any tool call in two fresh sessions. Antigravity IDE is installed, but its CLI exposes editor management rather than a headless agent prompt and no GUI instance was active; Hermes CLI help/version exited 1 without output. No incomplete route counts as a pass.
