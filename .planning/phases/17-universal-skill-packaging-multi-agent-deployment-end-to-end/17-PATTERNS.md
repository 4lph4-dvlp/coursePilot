# Phase 17 Code Patterns

## File Classification

| Planned file | Role | Closest existing pattern | Execution detail |
|---|---|---|---|
| `skills/coursepilot/SKILL.md` | Natural-language routing and safety | Existing `check`, `sync`, `watch`, `progress` guidance in the same file | Keep neutral frontmatter, repo placeholder, preview-before-write rule; add `notices`/`qna`/`board` and explicit download result handling. |
| `skills/coursepilot/JSON_CONTRACT.md` | Command result contract | Existing `CheckReport` and `SyncReport` tables and examples | Add command-specific sections and model-valid examples; do not force download/board results into `CheckReport`. |
| `tests/test_contract_doc.py` | Documentation assertions | `_collect_model_field_names` and `_extract_json_blocks` | Extend imported models and command dispatch; validate each JSON block against its owning Pydantic model. |
| `src/coursepilot/installer.py` | Safe batch linked deployment | `AGENT_SKILL_PATHS`, `resolve_agent_home`, `install_skill`, `_prepare_replace` | Preflight each home, preserve foreign target guard, verify source resolution and both docs after link. |
| `src/coursepilot/cli.py` | Batch CLI entry | Existing `install-skill --agent` Click command | Add batch mode with per-agent statuses and nonzero exit on partial failure without suppressing remaining agents. |
| `tests/test_installer.py` | Installer behavior | Fake home fixture, `CliRunner`, source placeholder and safe replace tests | Cover five agents, absent home, foreign content, broken source link, and mixed-result batch. |
| `README.md` | Operator instructions | Existing five-agent install table | Document batch link command, skip/partial result semantics, and relink from current checkout. |
| `scripts/verify_phase17_evidence.py` | Evidence completeness gate | `tests/test_contract_doc.py` JSON block parsing and model dispatch | Parse one fenced JSON summary, reject missing/contradictory statuses and private payload fields; keep actual observations for human review. |
| `tests/test_phase17_evidence.py` | Evidence gate tests | `tests/test_contract_doc.py` valid/invalid contract examples | Use compact synthetic ledgers for valid and incomplete/contradictory cases. |
| Phase 17 execution evidence | Privacy-limited UAT record | Phase 08 and 11 SUMMARYs | Counts and statuses only; no full course payloads or transcripts. |

## Data flow

Natural-language request → `SKILL.md` route → Click command → Pydantic result model → `JSON_CONTRACT.md` field interpretation → concise user briefing. Deployment: source skill directory → batch CLI → per-agent `install_skill` → link/readability validation → fresh-session routing evidence. E2E: live CLI and Scheduler read/preview → per-course and per-agent evidence ledger → phase verification.

## Shared Patterns

- `install_skill` uses `_prepare_replace` to reject a foreign target. Preserve this behavior when adding batch operations.
- `tests/test_installer.py` isolates `HOME`, `USERPROFILE`, `LOCALAPPDATA`, and `HERMES_HOME` so test installs do not affect the user's directories.
- `tests/test_contract_doc.py` already parses JSON fenced blocks; expand this validator rather than writing a second parser.
- `ProgressReport.status` and `CourseProgress.status` must guide collection-failure warnings. `BoardReport.errors` has a separate shape. `MaterialStatus.PLANNED` and `saved_path` from dry runs do not prove a file exists.
