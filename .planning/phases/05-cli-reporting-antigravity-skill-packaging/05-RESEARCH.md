# Phase 5: CLI Reporting & Universal Agent Skill Packaging - Research

**Researched:** 2026-09-23
**Domain:** Python CLI (click + rich) end-to-end orchestration, Pydantic JSON contracts, and cross-agent SKILL.md packaging (Claude Code, Codex, Antigravity, Pi, Hermes)
**Confidence:** MEDIUM — core CLI/reporting stack is HIGH confidence (existing code + official docs); cross-agent install paths are MEDIUM/LOW confidence (web search only, no official cross-agent spec exists) and are flagged for user confirmation.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

1. **Briefing layout (브리핑 구성)**
   - D-01: Top-level grouping is by urgency: 기한 초과 → 24시간 이내 → 이후 일정. Inside each section, items are grouped by course.
   - D-02: Two-level detail. Tables show course, task name, due date, and time remaining. Only urgent items (overdue + within 24h) and errors get an extra detail block with description and LMS link.
   - D-03: A summary header shows the total course count and the counts for overdue / within 24h / later.
   - D-04: Never truncate. Both the terminal and the agent chat show every incomplete item.
   - D-05: The "기한 초과" section includes every item the LMS still reports as incomplete, however old. No N-day cutoff.

2. **Command safety (명령 안전성)**
   - D-06: `sync` is a dry-run by default. It writes to Notion only when `--apply` is passed. This reuses the Phase 4 real-read / blocked-write dry-run path. — Reversibility: costly.
   - D-07: `check` runs LMS login, scraping, normalization, and the briefing. It never touches Notion.
   - D-08: Configuration or login failures abort immediately. Failures for a single course or item do not stop the run: processing continues, errors are collected and shown, exit non-zero.
   - D-09: Human output uses Rich by default. `--json` emits the same result for agents and automation.

3. **CLI options, progress, exit codes, and JSON contract**
   - D-10: Options stay minimal. Shared: `--json`, `--headed`, `--relogin`. `sync` only: `--apply`. No course filter or other convenience flags.
   - D-11: Progress is shown per course (e.g. `[3/7] 자료구조 수집 중`) with a Rich spinner or status line. All progress and log output goes to stderr; stdout carries only the report or pure JSON.
   - D-12: Exit codes: `0` = full success, `1` = partial failure, `2` = fatal (missing config or login failure; aborted). — Reversibility: costly.
   - D-13: JSON contract is versioned and documented, not a raw dump. Top-level shape: `{schema_version, command, generated_at, summary, items | sync, errors}`. Documented in the skill's support docs. Any breaking change bumps `schema_version`. — Reversibility: one-way.
   - D-14: No output (Rich, JSON, or error text) may contain student ID, password, Notion token, or session cookies. Item LMS links and Notion page URLs are included. Apply the existing `_safe_error` masking approach to CLI error output as well.

4. **Skill invocation experience (스킬 호출 경험)**
   - D-15: Skill folder lives at `skills/kau-lxp/` in the repo (`SKILL.md` + support docs such as JSON schema reference).
   - D-16: For requests like "노션에 올려줘", the agent runs `sync` (dry-run) first, shows create/update/skip lists, and runs `sync --apply` only after user approval in conversation.
   - D-17: In chat, the agent parses `--json` and rebuilds the briefing as markdown tables following D-01–D-04. It does not paste the Rich/ANSI output.
   - D-18: On first run, the agent diagnoses the environment and installs dependencies itself (`uv sync`, `playwright install chromium`). For secrets, it only tells the user to put them in `.env`. The agent never asks for secrets in conversation.

5. **Universal agent skill packaging (범용 에이전트 스킬)**
   - D-19: `SKILL.md` uses only fields common to the Agent Skills format (`name`, `description`) plus agent-neutral body instructions. No agent-specific tool names or frontmatter extensions. — Reversibility: costly.
   - D-20: README includes per-agent install guidance for Claude Code, Codex, Antigravity, and Pi/Hermes.
   - D-21: Install command is `python -m kau_assistant install-skill --agent {claude|codex|antigravity|pi|hermes}`. One Python implementation for every OS, testable.
   - D-22: Supported install targets from day one: Claude Code, Codex, Antigravity, Pi, Hermes. Agent → skill-path mappings kept as data. Exact paths confirmed in research (see `## Skill Install Path Matrix` below).
   - D-23: Install copies the folder by default. `--link` creates a symlink or junction for development. The installed SKILL.md must resolve the repo/CLI location so it works from any working directory.
   - D-24: Update ROADMAP.md, REQUIREMENTS.md (SKIL-03), and PROJECT.md to say "universal Agent Skill (SKILL.md)" instead of "Antigravity Skill".

6. **Verification (E2E 검증)**
   - D-25: Automated tests cover CLI commands, reporter (sections, grouping, no truncation), JSON contract, exit codes, secret redaction, and install-skill path generation, using fixtures and mocks.
   - D-26: Live evidence: one real `check` run and one real dry-run `sync`, recorded like `04-02-LIVE-DRY-RUN-EVIDENCE.md`. Live `sync --apply` only with explicit user approval, not mandatory.
   - D-27: Manual skill-invocation check in every supported agent (Claude Code, Codex, Antigravity, Pi, Hermes): install with `install-skill`, ask "과제 확인해줘", confirm the skill triggers and follows D-16/D-17.

### Claude's Discretion
- CLI framework wiring (`click` is already a dependency), module layout (`cli.py`, `reporter.py`, `pipeline.py`, etc.).
- Exact Rich styling (colors, borders), time-remaining format ("3시간 12분" vs "D-1").
- Exact JSON field names below the top level, as long as they are documented and versioned.
- Whether `install-skill` also supports a project-level target in addition to user-level.

### Deferred Ideas (OUT OF SCOPE)
- None remaining. Per-agent install adapters and compatibility checks were deferred in the earlier Codex session and are now in scope (D-21, D-22, D-27).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SKIL-01 | Rich 콘솔 브리핑 리포트로 미완료 강의/과제/마감일을 직관적으로 표시 | `## Architecture Patterns` (reporter design, urgency grouping), `## Code Examples` (Table/Console patterns), existing `SyncTask`/`calculate_priority` fields already carry `is_overdue`/`is_urgent`/`due_date` needed for D-01–D-05 grouping |
| SKIL-02 | `check`/`sync` CLI 명령어 제공 | `## Architecture Patterns` (pipeline + click group design), `## Code Examples` (click group/exit code/stderr routing), existing `NotionSyncEngine.sync(dry_run=...)` and `exceptions.py` hierarchy map directly to D-06/D-08/D-12 |
| SKIL-03 | 범용 SKILL.md 패키징 및 에이전트별 설치 명령 | `## Skill Install Path Matrix`, `## Don't Hand-Roll` (symlink/junction), `## Common Pitfalls` (agent-specific frontmatter leakage) |
</phase_requirements>

## Summary

Phase 5 has no new external package needs — `click` (installed 8.1.8), `rich` (installed 14.3.3), and `pydantic` (installed 2.13.4) are already dependencies and are sufficient for the whole phase. The real engineering work is (1) writing the first end-to-end orchestrator (`pipeline.py`) that chains the already-built, well-tested pieces from Phases 1–4 (`SessionManager` → `extract_courses` → per-course scrape → `transform_to_sync_tasks` → `NotionSyncEngine`), since **no such orchestrator exists yet**; (2) a pure, testable `reporter.py` that turns a list of `SyncTask` (and a `SyncResult` for `sync`) into both a Rich console layout and a versioned Pydantic JSON envelope, honoring D-01–D-05, D-11, D-14; and (3) an `install-skill` command whose only genuinely novel technical risk is cross-platform directory linking (D-23) on Windows, where `os.symlink` requires Developer Mode/admin and NTFS junctions are the standard admin-free alternative.

The cross-agent SKILL.md packaging goal (D-19–D-22) is achievable with a single small `SKILL.md` (frontmatter: `name` + `description` only) because that is the entire *portable* surface of the Agent Skills format — every agent-specific extension (Claude Code's `allowed-tools`, Antigravity's tool bindings, etc.) is additive and ignored by agents that don't recognize it, so omitting them is what makes the file agent-neutral. This is empirically confirmed by a skill folder **already present in this exact repository** (`.claude/skills/inherit-legacy-style/SKILL.md`, `.agents/skills/inherit-legacy-style/`, `.pi/skills/inherit-legacy-style/`) which uses exactly this shape. Per-agent install *paths*, however, could not be verified from any single authoritative cross-agent spec — they were gathered per-agent from each vendor's own docs/blog posts (MEDIUM confidence for Claude Code's own docs, LOW confidence for Codex/Antigravity/Pi/Hermes since no official page was fetched for the latter three within this session beyond search snippets) and one path family (`.agents/skills/`) is independently corroborated by the in-repo evidence above.

**Primary recommendation:** Build `pipeline.py` (orchestrator) → `reporter.py` (pure function, Rich + JSON) → `cli.py` (click group calling both) → `skills/kau-lxp/SKILL.md` + `installer.py` (data-driven agent→path table, copy-by-default/`--link`-optional). Keep the agent→path table isolated in one module so `install-skill` unit tests can assert path generation without touching the filesystem for every agent.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| LMS login/scrape orchestration | Backend/CLI process (local) | — | `pipeline.py` runs in the same local Python process as the CLI; no client/server split in this project (local-only agent skill, per PROJECT.md out-of-scope: no SaaS hosting) |
| Domain normalization (`SyncTask`) | Backend/CLI process | — | Already implemented in `domain/transformer.py`; reused unchanged |
| Notion sync (dry-run/apply) | Backend/CLI process | External API (Notion) | `NotionSyncEngine` already owns this; CLI only calls `.sync(tasks, dry_run=...)` |
| Console report rendering | CLI presentation layer | — | Pure function of `list[SyncTask]` / `SyncResult` → Rich renderables; must not perform I/O itself (testability, D-25) |
| JSON contract | CLI presentation layer | Agent chat layer (Claude/Codex/etc. parse this) | Same data as the console report, serialized via Pydantic models; the "agent chat" tier is external and out of this repo's control — only the contract crosses that boundary |
| SKILL.md content | Agent-loaded instruction tier | — | Loaded by each agent's own runtime (Claude Code, Codex, Antigravity, Pi, Hermes); this repo only authors and installs the file, it does not control how each agent parses it |
| install-skill filesystem copy/link | CLI / local filesystem | OS (symlink vs junction) | Cross-platform file operation; Windows requires the junction fallback described in `## Don't Hand-Roll` |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `click` | 8.1.8 installed (8.5.0 latest on PyPI) [VERIFIED: pip index versions click, run this session] | CLI command group, options, exit codes | Already a project dependency (`pyproject.toml`); de facto standard for composable Python CLIs; supports `python -m kau_assistant` entry via `__main__.py` |
| `rich` | 14.3.3 installed (15.0.0 latest on PyPI) [VERIFIED: pip index versions rich, run this session] | Console tables, spinners/status, colored output | Already a project dependency; explicitly required by D-01/D-09/D-11 ("Rich 기반 콘솔 브리핑") |
| `pydantic` | 2.13.4 installed (2.13.5 latest on PyPI) [VERIFIED: pip index versions pydantic, run this session] | JSON contract DTOs (`schema_version`-tagged envelope) | Already used for every DTO in the codebase (`SyncTask`, `SyncResult`, etc.); D-13 requires "explicit Pydantic output models, not raw dumps" per 05-CONTEXT.md code_context |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `json` (stdlib) | n/a | Serialize the Pydantic JSON envelope to stdout | `--json` flag output; use `model_dump(mode="json")` + `json.dumps(..., ensure_ascii=False)` so Korean text isn't escaped |
| `pathlib` (stdlib) | n/a | Cross-platform path handling for `install-skill` targets | All agent skill-path table entries should be `Path.home() / ...` expressions, never hardcoded POSIX/Windows separators |
| `subprocess` (stdlib) | n/a | Windows junction creation fallback (`mklink /J`) | Only on Windows, only when `os.symlink` raises `OSError`/`PermissionError` for `--link` (see Don't Hand-Roll) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `click` | `argparse` (stdlib) | `argparse` needs far more boilerplate for subcommands (`check`/`sync`/`install-skill`) and has no built-in `CliRunner`-style testing helper; `click` is already installed and used nowhere else yet, so no migration cost |
| Manual junction via `ctypes`/`_winapi` | Third-party `ntfslink-python` package | Adds a new dependency for one platform-specific edge case (dev `--link` convenience flag, not required for core functionality); `subprocess` + `mklink /J` avoids a new package entirely and is sufficient — recommend NOT adding a new package for this |
| Two `Console` instances (stdout/stderr) | Rich's `Console(stderr=True)` shortcut | Either works; `Console(file=sys.stderr)` is the documented pattern and makes the stderr routing explicit at the call site, which is easier to unit test by injecting a `StringIO` |

**Installation:**
No new packages required. Existing `pyproject.toml` dependencies (`click>=8.1.0`, `rich>=13.7.0`, `pydantic>=2.6.0`) already cover this phase.

**Version verification:** Verified via `pip index versions click|rich|pydantic` run in this session against the project's actual environment (see table above) — all three show an `INSTALLED` version already satisfying `pyproject.toml`'s floor. No `uv add` / `pip install` action is needed for Phase 5.

## Package Legitimacy Audit

**Not applicable — this phase installs no new external packages.** All CLI/reporting/JSON functionality is built from `click`, `rich`, `pydantic`, and the Python standard library (`json`, `pathlib`, `subprocess`), all already present in `pyproject.toml` and already installed in the project's environment (see Standard Stack table, versions verified via `pip index versions` this session). If a plan later decides to add a convenience package (e.g. a junction-creation library), it MUST be run through `gsd_run query package-legitimacy check` before being added to `pyproject.toml`, and the resulting verdict recorded here.

**Packages removed due to [SLOP] verdict:** none (no packages checked — none proposed)
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
                         ┌─────────────────────────────────────────┐
                         │   python -m kau_assistant <cmd> [opts]   │
                         │        (cli.py — click.group)            │
                         └───────────────┬───────────────────────────┘
                                         │
                  ┌──────────────────────┼───────────────────────┐
                  │                       │                       │
                  ▼                       ▼                       ▼
            check           sync (--apply?)              install-skill (--agent, --link)
                  │                       │                       │
                  ▼                       ▼                       ▼
        ┌─────────────────┐    ┌─────────────────┐    ┌───────────────────────┐
        │   pipeline.py    │    │   pipeline.py    │    │  installer.py          │
        │  run_pipeline()  │    │  run_pipeline()   │    │  AGENT_SKILL_PATHS    │
        └────────┬─────────┘    └────────┬──────────┘    │  (data table)          │
                 │                       │                │  copy_tree() / link() │
   ┌─────────────┼───────────┐          │                └───────────┬────────────┘
   │             │           │          │                            │
   ▼             ▼           ▼          ▼                            ▼
SessionManager  extract_  per-course:   NotionSyncEngine     skills/kau-lxp/*
(login/session) courses   navigate_*,   .sync(tasks,         copied/symlinked to
                          parse_*       dry_run=not apply)   the agent's skill dir
   │             │           │          │
   └─────────────┴───────────┴──────────┘
                 │  (per-course try/except → ErrorAction/collected errors, D-08)
                 ▼
       transform_to_sync_tasks()  →  list[SyncTask]
                 │
                 ▼
          reporter.py (pure function)
        build_report(tasks, sync_result=None) -> BriefingReport (pydantic)
                 │
        ┌────────┴─────────┐
        ▼                  ▼
  render_rich(report)  report.model_dump() → json.dumps()
  → Console(stdout)      → stdout (--json)
  progress/logs →
  Console(stderr)
```

A reader can trace `check`: `cli.py` → `pipeline.run_pipeline()` → scrape/transform → `reporter.build_report()` → Rich table on stdout (or JSON if `--json`), with all progress/log lines on stderr throughout. `sync` follows the same path but additionally calls `NotionSyncEngine.sync()` and folds its `SyncResult` into the same report shape (`items | sync` per D-13). `install-skill` is a separate, filesystem-only path that never touches the scraper.

### Recommended Project Structure
```
src/kau_assistant/
├── __main__.py          # `python -m kau_assistant` entry -> cli.cli()
├── cli.py                # click.group() with check/sync/install-skill subcommands
├── pipeline.py            # NEW: orchestrates SessionManager -> scraper -> transformer -> (NotionSyncEngine)
├── reporter.py            # NEW: pure functions, SyncTask/SyncResult -> BriefingReport (pydantic) -> Rich or JSON
├── report_models.py        # NEW (or inline in reporter.py): versioned Pydantic JSON contract DTOs (schema_version=1)
├── installer.py           # NEW: AGENT_SKILL_PATHS table + copy/link logic for install-skill
├── ... (existing Phase 1-4 modules unchanged)
skills/
└── kau-lxp/
    ├── SKILL.md            # NEW: name + description only, agent-neutral body (D-19)
    ├── JSON_CONTRACT.md     # NEW: documents schema_version 1 fields (D-13, referenced by SKILL.md)
    └── README.md            # NEW: per-agent install table (D-20)
```

### Pattern 1: Pure reporter function (testable without a browser)
**What:** `reporter.build_report(tasks: list[SyncTask], *, sync_result: SyncResult | None, errors: list[...], now: datetime | None) -> BriefingReport` — a pure function with no I/O.
**When to use:** Always — this is what makes D-25's fixture-based automated tests possible without mocking Playwright for reporter tests.
**Example:**
```python
# Pattern derived from the project's existing pure-function style
# (see domain/transformer.py: transform_to_sync_tasks(courses, ..., now=None))
def build_report(
    tasks: list[SyncTask],
    *,
    sync_result: SyncResult | None = None,
    course_errors: list[ErrorItem] | None = None,
    now: datetime | None = None,
) -> BriefingReport:
    current = now or get_current_kst_time()
    overdue = [t for t in tasks if t.is_overdue]          # D-01 section 1, D-05: no cutoff
    urgent = [t for t in tasks if t.is_urgent and not t.is_overdue]  # D-01 section 2
    later = [t for t in tasks if not t.is_overdue and not t.is_urgent]  # D-01 section 3
    return BriefingReport(
        schema_version=1,
        summary=Summary(
            course_count=len({t.course_id for t in tasks}),
            overdue_count=len(overdue),
            urgent_count=len(urgent),
            later_count=len(later),
        ),
        overdue=_group_by_course(overdue),
        urgent=_group_by_course(urgent),
        later=_group_by_course(later),
        errors=course_errors or [],
        sync=sync_result,
    )
```

### Pattern 2: click group with stderr-only logging and explicit exit codes
**What:** A single `click.group()` in `cli.py`; every subcommand builds its own `rich.console.Console(file=sys.stderr)` for progress and a plain `Console(file=sys.stdout)` (or `print`/`sys.stdout.write`) for the final report/JSON, then calls `sys.exit(code)` per D-12.
**When to use:** All three subcommands (`check`, `sync`, `install-skill`).
**Example:**
```python
# Source: click.palletsprojects.com/en/stable/quickstart + testing docs (Context7)
import sys
import click
from rich.console import Console

@click.group()
def cli() -> None:
    """KAU LXP Assistant CLI."""

@cli.command()
@click.option("--json", "as_json", is_flag=True)
@click.option("--headed", is_flag=True)
@click.option("--relogin", is_flag=True)
def check(as_json: bool, headed: bool, relogin: bool) -> None:
    err_console = Console(file=sys.stderr)
    err_console.print("[1/7] 자료구조 수집 중...")   # D-11: progress -> stderr
    result = run_pipeline(headed=headed, relogin=relogin)  # per-course try/except inside (D-08)
    report = build_report(result.tasks, course_errors=result.errors)
    if as_json:
        sys.stdout.write(report.model_dump_json())
    else:
        Console(file=sys.stdout).print(render_rich(report))
    sys.exit(0 if not result.errors else 1)   # D-12: 0 success, 1 partial failure

if __name__ == "__main__":
    cli()
```

### Pattern 3: Data-driven agent skill-path table (D-22)
**What:** A single dict/table mapping agent id → list of candidate install locations, so adding an agent is a data change, not new install logic.
**When to use:** `install-skill` implementation and its tests (path-generation tests don't need to touch the filesystem).
**Example:**
```python
# Paths per ## Skill Install Path Matrix below.
# In-repo confirmed by .claude/skills/, .agents/skills/, .pi/skills/ already present in this project.
from pathlib import Path

AGENT_SKILL_PATHS: dict[str, dict[str, Path]] = {
    "claude": {
        "user": Path.home() / ".claude" / "skills",
        "project": Path.cwd() / ".claude" / "skills",
    },
    "codex": {
        "user": Path.home() / ".codex" / "skills",
        "project": Path.cwd() / ".codex" / "skills",
    },
    "antigravity": {
        "user": Path.home() / ".gemini" / "antigravity" / "skills",
        "project": Path.cwd() / ".agents" / "skills",
    },
    "pi": {
        "user": Path.home() / ".pi" / "agent" / "skills",
        "project": Path.cwd() / ".pi" / "skills",
    },
    "hermes": {
        "user": Path.home() / ".hermes" / "skills",
        "project": Path.cwd() / "skills",
    },
}
```

### Anti-Patterns to Avoid
- **Embedding agent-specific frontmatter in `SKILL.md`:** The in-repo `inherit-legacy-style` skill demonstrates the temptation — it adds `metadata.origin` and `allowed-tools` (Claude Code-specific) fields. D-19 explicitly forbids this for `skills/kau-lxp/SKILL.md`: only `name` and `description` are guaranteed portable across Claude Code, Codex, Antigravity, Pi, and Hermes. Extra fields don't break agents that ignore unknown YAML keys, but they invite exactly the "Antigravity-only" scope creep the user already rejected once (see CONTEXT.md `<specifics>`).
- **Rendering the Rich table directly to a string and pasting it into chat:** D-17 explicitly requires the agent to rebuild markdown tables from `--json`, not paste ANSI. The reporter must therefore expose data (Pydantic model), not a pre-rendered Rich string, as the thing that crosses into the JSON contract.
- **Doing I/O inside the reporter:** Any `reporter.py` function that calls Playwright, Notion, or the filesystem cannot be tested with fixtures alone (violates D-25's "using fixtures and mocks" testability goal).
- **Hardcoding one OS's path separator in `AGENT_SKILL_PATHS`:** always build with `pathlib.Path`, never string concatenation, since the CLI must run correctly on the Windows dev machine (`win32`, confirmed by this session's environment) as well as macOS/Linux where the other agents commonly run.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Directory symlink/junction on Windows without admin | A custom ctypes `DeviceIoControl` reparse-point writer | `os.symlink(target, link, target_is_directory=True)` first (works unprivileged on POSIX, and on Windows if Developer Mode/admin is available); on `OSError`/`PermissionError` on Windows, fall back to `subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], check=True)` for a junction | Junctions need no special privilege on Windows and are the documented workaround for exactly this admin/Developer-Mode restriction [CITED: search results — Python Discourse "Add os.junction", GeeksforGeeks "Creating Junction Points"]; writing raw reparse points is a well-known source of subtle bugs (wrong tag, wrong buffer size) that `mklink` already handles correctly |
| Secret redaction in CLI error text | A new regex-based secret scrubber | Reuse `notion/engine.py`'s `_safe_error` pattern (already returns a generic message for any non-`NotionIntegrationError`, and only surfaces the exception's own message for the app's own typed errors) — extend the same *shape* (typed-error allowlist, not string scrubbing) to `pipeline.py`/`cli.py` errors, per D-14's explicit instruction | The codebase already has one masking convention; a second, different masking strategy (e.g. regex over `str(error)`) risks both under- and over-redacting compared to the existing, already-reviewed approach (Phase 4 verification confirmed no secret leakage using this pattern) |
| JSON schema versioning / envelope shape | A hand-rolled `dict` returned from `cli.py` | Explicit Pydantic models (`BriefingReport`, `Summary`, etc.) with a literal `schema_version: int = 1` field, serialized via `model_dump_json()` | Matches the codebase's established pattern (every DTO in `domain/models.py` and `notion/models.py` is already Pydantic); guarantees the "not a raw model dump" requirement in D-13 by construction, and makes future `schema_version` bumps a type-checked, diffable change |
| Per-agent skill installation logic duplicated per agent | Five near-identical `install_for_claude()`, `install_for_codex()`, ... functions | One `AGENT_SKILL_PATHS` data table + one generic `install(agent, target, link)` function (Pattern 3 above) | D-22 explicitly requires "Agent → skill-path mappings are kept as data ... so adding an agent is a data change" |

**Key insight:** Nothing in this phase requires new infrastructure-grade libraries. The risk is entirely in *wiring discipline* (keeping the reporter pure, keeping progress on stderr, keeping the skill-path table as data) and in the *one* platform-specific edge case (Windows junctions for `--link`) that has no single-call stdlib solution.

## Common Pitfalls

### Pitfall 1: Mixing progress/log output with report/JSON on stdout
**What goes wrong:** A `print()` or default `rich.print()` call inside the pipeline (e.g. a stray debug line, or `Console()` without `file=sys.stderr`) leaks into stdout, corrupting the `--json` output that an agent parses.
**Why it happens:** Rich's default `Console()` writes to stdout; it's easy to instantiate one without thinking about which stream matters for a given call site.
**How to avoid:** Instantiate exactly two `Console` objects at the top of `cli.py` (`out = Console(file=sys.stdout)`, `err = Console(file=sys.stderr)`) and pass `err` explicitly into any function that logs progress (`pipeline.run_pipeline(..., console=err)`); never call a bare `Console()` or `print()` inside `pipeline.py`/`reporter.py`.
**Warning signs:** `--json` output fails to `json.loads()` in a test; a manual test shows spinner text intermixed with table borders when piping stdout to a file.

### Pitfall 2: Treating "existing Notion `_safe_error` masking" as covering the whole CLI
**What goes wrong:** D-14 requires no LMS credentials, Notion token, or session cookies leak through *any* CLI output — but `_safe_error` in `notion/engine.py` only masks `NotionIntegrationError`-family exceptions. A raw `AuthenticationError` or Playwright exception (which can embed the LMS URL with query params, or even echo back input) could leak `lms_username`/`lms_password` if printed via `str(error)` unfiltered.
**Why it happens:** Reusing one module's error-safety pattern without auditing every exception type that can reach the CLI boundary (auth failures, navigation timeouts, config errors all originate outside `notion/`).
**How to avoid:** Build a single top-level `_safe_cli_error()` in `cli.py`/`pipeline.py` that applies the same typed-allowlist approach across *all* of `kau_assistant.exceptions`, not just the Notion subtree; add a fixture-based test that raises each exception type with a fake secret in the message and asserts the secret does not appear in captured stdout/stderr (this operationalizes D-14 and D-25 together).
**Warning signs:** A test only checks Notion-path errors for redaction; LMS-path errors (bad login, `NavigationTimeoutError` messages that might embed a URL with credentials in some LMS configurations) are untested.

### Pitfall 3: `--json` output escaping Korean text
**What goes wrong:** `json.dumps(data)` defaults to `ensure_ascii=True`, turning every Korean course/task name into `\uXXXX` escapes, which is technically valid JSON but makes D-17's "rebuild markdown tables" step harder to eyeball/debug and bloats the payload.
**Why it happens:** `ensure_ascii=True` is `json.dumps`'s default; Pydantic's `model_dump_json()` does NOT escape non-ASCII by default (it uses a different serializer), so mixing `json.dumps(model.model_dump())` and `model.model_dump_json()` inconsistently produces different-looking output.
**How to avoid:** Standardize on `model.model_dump_json()` (Pydantic v2's own serializer) for the `--json` path everywhere, and never round-trip through stdlib `json.dumps` with default settings.
**Warning signs:** JSON output in a live evidence file (D-26) shows `자료구조` instead of `자료구조`.

### Pitfall 4: `install-skill --link` silently copying instead of linking on Windows
**What goes wrong:** If the fallback to `mklink /J` is missing or the `OSError` from `os.symlink` is swallowed too broadly, `--link` silently degrades to a full copy on a Windows dev machine without Developer Mode enabled, and repo edits stop showing up in the installed skill — defeating the entire purpose of D-23's `--link` flag.
**Why it happens:** `os.symlink(..., target_is_directory=True)` raises `OSError: [WinError 1314] A required privilege is not held by the client` rather than a more specific/catchable error; a broad `except Exception: copy_tree()` fallback hides this distinction from the user.
**How to avoid:** Catch the specific privilege error on Windows, attempt the `mklink /J` fallback explicitly, and only fall back to a plain copy (with a visible warning printed to stderr) if *both* fail; add a test asserting that on a platform where symlinks are unavailable, the installer either produces a working junction or an explicit warning — never a silent copy.
**Warning signs:** A developer edits `skills/kau-lxp/SKILL.md` in the repo and the agent-installed copy doesn't change.

## Code Examples

### Rich Table + stderr status pattern
```python
# Source: rich.readthedocs.io/en/stable (Context7: /websites/rich_readthedocs_io_en_stable)
from rich.console import Console
from rich.table import Table

table = Table(title="기한 초과")
table.add_column("과목", style="cyan")
table.add_column("작업", style="white")
table.add_column("마감일", justify="right")
table.add_column("남은 시간", justify="right", style="red")
table.add_row("자료구조", "3주차 강의 시청", "2026-09-20 23:59", "-3일 2시간")

out_console = Console()          # stdout — report only
out_console.print(table)

err_console = Console(file=__import__("sys").stderr)
with err_console.status("[3/7] 자료구조 수집 중..."):
    ...  # scraping work
```

### Click group + CliRunner test pattern
```python
# Source: click.palletsprojects.com/en/stable/testing (Context7: /websites/click_palletsprojects_en_stable)
from click.testing import CliRunner
from kau_assistant.cli import cli

def test_check_json_is_valid_json(monkeypatch):
    runner = CliRunner()
    result = runner.invoke(cli, ["check", "--json"])
    assert result.exit_code in (0, 1)   # D-12: 0 or 1 depending on fixture errors
    import json
    payload = json.loads(result.output)
    assert payload["schema_version"] == 1
```

### SKILL.md minimal agent-neutral shape (D-19)
```markdown
<!-- Source: platform.claude.com/docs/en/agents-and-tools/agent-skills/overview (Context7)
     Cross-checked against the in-repo .claude/skills/inherit-legacy-style/SKILL.md,
     which is read this session: name/description present; extra fields
     (metadata.origin, allowed-tools) are Claude-Code-specific and are the
     pattern D-19 says NOT to copy for skills/kau-lxp/SKILL.md. -->
---
name: kau-lxp
description: Checks KAU LMS for incomplete lectures/assignments and can sync deadlines to the user's Notion Scheduler. Use when the user asks to check LMS status, list assignments/lectures, or sync/upload deadlines to Notion (e.g. "과제 확인해줘", "노션에 올려줘").
---

# KAU LXP Assistant

## When to activate
...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| No CLI entry point; each Phase 1-4 module tested/used in isolation | Phase 5 introduces the first `__main__.py`/`cli.py` chaining every prior module | This phase | First point where a full login→scrape→sync run can fail end-to-end; increases the value of D-08's per-course error isolation |
| Ad hoc `print()`/`logger` calls throughout scraper/session modules (existing `logging.getLogger(...)` calls in `session_manager.py`, `navigator.py`, `auth.py`) | CLI-level stderr/stdout separation (D-11) sits *on top of* existing logging — existing `logger.info(...)` calls already go to Python's logging (typically stderr by default `basicConfig`), so no rework of Phase 1-4 modules is strictly required, only confirming the CLI's own root logger config sends to stderr | This phase | Plans should configure `logging.basicConfig(stream=sys.stderr, ...)` once in `cli.py` rather than reworking existing `logger.info` calls in scraper modules |

**Deprecated/outdated:** Nothing in this phase deprecates prior-phase code; Phase 5 is purely additive (new `pipeline.py`, `reporter.py`, `cli.py`, `installer.py`, `skills/kau-lxp/`).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Codex CLI reads project/user skills from `.codex/skills/` and `~/.codex/skills/` respectively | Skill Install Path Matrix | `install-skill --agent codex` would write to a path Codex never scans; skill install would silently no-op for Codex users. Only found via WebSearch snippets (LOW confidence), no official page fetched in full this session. |
| A2 | Antigravity user-level path is `~/.gemini/antigravity/skills/` and project-level is `<workspace>/.agents/skills/` | Skill Install Path Matrix | Same risk as A1 for Antigravity users. The `.agents/skills/` project path is partially corroborated by this repo's own `.agents/skills/inherit-legacy-style/` folder (in-repo, read this session), but the *user-level* Antigravity path is WebSearch-only. |
| A3 | Pi reads from `~/.pi/agent/skills/` (user) and `.pi/skills/` (project) | Skill Install Path Matrix | Same class of risk. `.pi/skills/inherit-legacy-style/` exists in this repo (in-repo, read this session) confirming the project-level path; the user-level `~/.pi/agent/skills/` path is WebSearch-only. |
| A4 | Hermes reads from `~/.hermes/skills/` (default) or a project `skills/` directory | Skill Install Path Matrix | If Hermes's actual default differs (e.g. requires explicit config pointing at a directory), `install-skill --agent hermes` could install to a location Hermes never auto-loads. WebSearch-only; no in-repo `.hermes/` evidence exists in this project to cross-check. |
| A5 | No Python stdlib function creates an NTFS junction directly (as of this session's search); `mklink /J` via `subprocess` is the standard workaround | Don't Hand-Roll (junction pitfall) | If a stdlib/`_winapi` junction API does exist in the Python version this project targets (>=3.11) that this search missed, the `subprocess`-based fallback is a slightly heavier-than-necessary but still-correct implementation — low risk either way. |
| A6 | Existing Python `logging` calls in `session_manager.py`/`navigator.py`/`auth.py` already default to stderr (no explicit `basicConfig` was found configuring a stream) | State of the Art table | If some other part of the codebase (not found in this session's read of `config.py`, `session_manager.py`, `auth.py`, `navigator.py`) configures `logging` to stdout, D-11's stderr-only guarantee could be violated by pre-existing log lines rather than new Phase 5 code. |

**If this table is empty:** N/A — see rows above. The Standard Stack (click/rich/pydantic versions), the in-repo `SyncTask`/`SyncResult`/`_safe_error` code (all read this session), and the Agent Skills `name`/`description` frontmatter spec (Context7, official Claude docs) are the only claims that reach `[VERIFIED]`/`[CITED]`; every cross-agent (Codex/Antigravity/Pi/Hermes) install path is `[ASSUMED]` per the rows above and needs user confirmation before being locked into `installer.py`'s data table — recommend a `checkpoint:human-verify` or a "verify by installing once per agent" task in the plan, which D-27 already requires as a manual E2E step per agent.

## Open Questions

1. **Are the Codex/Antigravity/Pi/Hermes skill paths still current?**
   - What we know: Claude Code's paths are corroborated both by its own docs and by this repo's existing `.claude/skills/inherit-legacy-style/`. Pi's and Antigravity's *project-level* paths are corroborated by this repo's existing `.pi/skills/` and `.agents/skills/` folders respectively.
   - What's unclear: The *user-level* paths for Codex, Antigravity, and Hermes, and Codex's project-level path, rest on WebSearch snippets only (LOW confidence, no official page fully fetched).
   - Recommendation: D-27's manual per-agent install-and-invoke checkpoint is the natural place to falsify or confirm each path; the plan should treat `AGENT_SKILL_PATHS` as provisional until that checkpoint passes for each agent, and should NOT hardcode these paths as unverified "facts" in `SKILL.md`'s own body (only in `installer.py` and the README table, both easy to correct later per D-22's "data change" design).

2. **Does `python -m kau_assistant install-skill` need to support installing to a *running* agent's already-open session, or is a static file copy always sufficient?**
   - What we know: All five agents auto-discover skills either at startup or by scanning a directory (per the research above); none of the search results indicated a "live reload" API.
   - What's unclear: Whether Claude Code (or others) require a session restart to pick up a newly installed skill, which matters for the D-27 manual verification script's exact steps.
   - Recommendation: Document "restart the agent session after install" as a note in the installed README; this is a low-risk assumption to state explicitly rather than silently omit.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >=8.0.0 (installed; see `pyproject.toml` `[project.optional-dependencies].dev`) + `pytest-mock`, `pytest-asyncio` |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` — `testpaths = ["tests"]`, `pythonpath = ["src"]` |
| Quick run command | `uv run pytest -q tests/test_cli.py tests/test_reporter.py tests/test_pipeline.py tests/test_installer.py -x` |
| Full suite command | `uv run pytest` (108 passed as of Phase 4 per `04-VERIFICATION.md`; Phase 5 adds new test files, no existing ones should regress) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SKIL-01 | Reporter groups tasks into 기한 초과/24h/이후, never truncates, includes detail block only for urgent+errors (D-01–D-05) | unit | `uv run pytest tests/test_reporter.py -k "grouping or truncat or detail" -x` | ❌ Wave 0 |
| SKIL-01 | JSON contract is versioned Pydantic output, not a raw dump; Korean text not escaped | unit | `uv run pytest tests/test_reporter.py -k "json_contract" -x` | ❌ Wave 0 |
| SKIL-02 | `check` never calls Notion; `sync` defaults to dry-run and only writes with `--apply` (D-06, D-07) | unit/behavioral | `uv run pytest tests/test_cli.py -k "dry_run or apply or no_notion" -x` | ❌ Wave 0 |
| SKIL-02 | Config/login failure aborts (exit 2); per-course failure continues and collects errors (exit 1) (D-08, D-12) | behavioral | `uv run pytest tests/test_cli.py -k "exit_code" -x` | ❌ Wave 0 |
| SKIL-02 | All progress/log output goes to stderr; stdout carries only report/JSON (D-11) | behavioral | `uv run pytest tests/test_cli.py -k "stderr" -x` | ❌ Wave 0 |
| SKIL-02 | No secret (LMS password, Notion token, session cookie) appears in any output (D-14) | unit | `uv run pytest tests/test_cli.py -k "redaction" -x` | ❌ Wave 0 |
| SKIL-03 | `install-skill --agent X` generates the correct path per the data table, without touching the filesystem (path-generation only) | unit | `uv run pytest tests/test_installer.py -k "path" -x` | ❌ Wave 0 |
| SKIL-03 | `install-skill --link` produces a working link/junction and falls back safely (not silently) if unsupported | unit (mocked FS) | `uv run pytest tests/test_installer.py -k "link" -x` | ❌ Wave 0 |
| SKIL-03 | Installed `SKILL.md` resolves the repo/CLI location regardless of the agent's working directory (D-23) | unit | `uv run pytest tests/test_installer.py -k "resolve_path" -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest -q tests/test_<touched_module>.py -x`
- **Per wave merge:** `uv run pytest` (full suite)
- **Phase gate:** Full suite green before `/gsd-verify-work`, plus the D-26 live-evidence checkpoint (one real `check`, one real dry-run `sync`) and the D-27 manual per-agent skill-invocation checkpoint (both require human execution/approval, same as Phase 4's `04-02-LIVE-DRY-RUN-EVIDENCE.md` precedent).

### Wave 0 Gaps
- [ ] `tests/test_reporter.py` — covers SKIL-01 (grouping, no-truncation, JSON contract, redaction-safe fields)
- [ ] `tests/test_cli.py` — covers SKIL-02 (dry-run default, exit codes, stderr routing, secret redaction) using `click.testing.CliRunner` and mocked `pipeline.run_pipeline`
- [ ] `tests/test_pipeline.py` — covers the new orchestrator's per-course error isolation (D-08) with mocked `SessionManager`/scraper functions
- [ ] `tests/test_installer.py` — covers SKIL-03 path-generation and link/copy behavior with a mocked or `tmp_path`-based filesystem
- [ ] No new framework install needed — pytest, pytest-mock, pytest-asyncio already present in `[project.optional-dependencies].dev`

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | No (new) | LMS credentials already handled by Phase 1 `config.py`/`session_manager.py`; Phase 5 only *consumes* an authenticated `Page`, does not add new auth surface |
| V3 Session Management | No (new) | Session caching (`session.json`) unchanged from Phase 1; `--relogin` only ignores the cache, doesn't change how it's created |
| V4 Access Control | N/A | Single-user local CLI tool; no multi-user access control surface (explicitly out of scope per PROJECT.md: "다중 사용자 호스팅 SaaS 서버 구축") |
| V5 Input Validation | Yes | Pydantic models (`BriefingReport`, `AgentInstallRequest`-style click options) validate all CLI-boundary data; `--agent` should be a `click.Choice(["claude","codex","antigravity","pi","hermes"])` so invalid agent names fail fast with click's own error, not a KeyError deep in `installer.py` |
| V6 Cryptography | No (new) | No new cryptographic operations in this phase |
| V7 Error Handling & Logging (ASVS 7.x, ties to D-14) | Yes | Typed-error allowlist pattern (`_safe_error`/`_safe_cli_error`), same approach already verified safe in Phase 4 — never log/print raw exception `args` for untyped exceptions that might embed request URLs or credentials |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|-----------------------|
| Secret leakage via exception messages (LMS password/Notion token appearing in a stack trace or `str(error)`) | Information Disclosure | Extend `_safe_error`'s typed-allowlist pattern (D-14); test with fixtures that inject known secret strings into mocked exceptions and assert absence in captured output |
| Path traversal / unintended overwrite via `--agent`/`--link` writing outside the intended skill directory | Tampering | `installer.py` should resolve all target paths through `Path(...).resolve()` and assert the resolved path's parent matches the expected `AGENT_SKILL_PATHS` entry before any write; reject unexpected `..` components |
| Symlink/junction misuse (linking to an unintended or attacker-controlled directory) | Tampering / Elevation of Privilege | `--link` always targets the *repo's own* `skills/kau-lxp/` directory as source (never a user-supplied path — D-10 confirms no extra CLI flags beyond the documented ones), so there is no user-controlled link target to sanitize; still validate the source path exists and is inside the repo root before linking |
| JSON injection / malformed `--json` output breaking an agent's parser | Tampering (of the agent-CLI contract) | Always serialize through the versioned Pydantic model (`model_dump_json()`), never string-concatenate JSON; add a fixture test that round-trips `json.loads(cli_output)` for every `--json` code path |

## Sources

### Primary (HIGH confidence)
- In-repo source files read this session: `src/kau_assistant/notion/engine.py`, `notion/models.py`, `notion/__init__.py`, `domain/models.py`, `domain/transformer.py`, `domain/priority.py`, `domain/naming.py`, `session_manager.py`, `config.py`, `exceptions.py`, `scraper/course_list.py`, `scraper/navigator.py`, `scraper/models.py`, `scraper/assessment_parser.py`, `scraper/lecture_parser.py`, `auth.py`, `tests/conftest.py`, `pyproject.toml` — used for every claim about existing code shape, reuse points, and the integration gap (no orchestrator yet)
- `.claude/skills/inherit-legacy-style/SKILL.md` (read this session, lines 1-15 quoted above) — direct in-repo evidence of the Agent Skills frontmatter shape and of what NOT to copy (agent-specific extensions)
- `.agents/skills/inherit-legacy-style/`, `.pi/skills/inherit-legacy-style/`, `.claude/skills/inherit-legacy-style/` directory existence (confirmed via `find` this session) — in-repo evidence for the project-level path segment of Claude Code, Antigravity(`.agents`), and Pi
- Context7 `/websites/platform_claude_en_agents-and-tools_agent-skills` — official Claude Agent Skills frontmatter spec (`name`/`description` required fields, validation rules, three-level loading model)
- Context7 `/websites/rich_readthedocs_io_en_stable` — official Rich docs (Table, Console, Status/spinner)
- Context7 `/websites/click_palletsprojects_en_stable` — official Click docs (testing/CliRunner, entry points, exit code retrieval)
- `pip index versions click|rich|pydantic` run this session against the project's actual environment — confirms installed versions

### Secondary (MEDIUM confidence)
- WebSearch: "Claude Code Agent Skills SKILL.md format directory" — code.claude.com/docs/en/skills, platform.claude.com/docs/en/agents-and-tools/agent-skills/overview (official Anthropic docs, cross-checked against in-repo evidence)

### Tertiary (LOW confidence — flagged in Assumptions Log, need D-27 confirmation)
- WebSearch: "OpenAI Codex CLI Agent Skills SKILL.md support skills directory" — developers.openai.com/codex/skills, agentskillshub.dev (official-looking but not independently cross-checked against in-repo evidence)
- WebSearch: "Google Antigravity agent SKILL.md skills directory install" — antigravity.google/docs/skills/, codelabs.developers.google.com (user-level path only WebSearch-sourced; project-level path cross-checked in-repo)
- WebSearch: "Pi coding agent SKILL.md agent skills format directory" — pi.dev/docs/latest/skills, github.com/earendil-works/pi (user-level path only WebSearch-sourced; project-level path cross-checked in-repo)
- WebSearch: "Hermes AI coding agent SKILL.md agent skills directory install" — hermes-agent.nousresearch.com/docs/guides/work-with-skills (WebSearch-only, no in-repo cross-check available)
- WebSearch: "python create directory junction windows without admin" — discuss.python.org, GeeksforGeeks (community sources, not an official Microsoft/Python doc page fetched in full)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; versions verified against the live environment this session
- Architecture (pipeline/reporter/cli wiring): HIGH — derived directly from reading every relevant existing module's actual signatures this session
- Cross-agent skill install paths: LOW/MEDIUM — mixed; Claude Code is MEDIUM (official docs + in-repo cross-check), Codex/Antigravity(user-level)/Pi(user-level)/Hermes are LOW (WebSearch snippets only); flagged in Assumptions Log and mitigated by D-27's mandatory per-agent manual verification
- Pitfalls: HIGH for stdout/stderr and secret-redaction pitfalls (derived from reading the actual `_safe_error` implementation and D-11/D-14 text); MEDIUM for the Windows junction pitfall (based on community sources, not a live falsification test run in this session)

**Research date:** 2026-09-23
**Valid until:** 30 days for the click/rich/pydantic/Python-stdlib findings (stable ecosystem); 7-14 days for the cross-agent SKILL.md install-path findings (these tools — Codex CLI, Antigravity, Pi, Hermes — are new/fast-moving as of this session and their install conventions may still be in flux)
