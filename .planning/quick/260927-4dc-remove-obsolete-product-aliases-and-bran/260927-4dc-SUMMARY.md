---
quick_id: 260927-4dc
status: complete
completed: 2026-09-27
execution: inline-codex-adapter
---

# CoursePilot single-identity cleanup complete

The user's explicit breaking-change request supersedes the preceding compatibility strategy. Only `coursepilot` is available as the distribution, Python package, module command, console entry and source agent skill; the public base exception is `CoursePilotError`.

## Delivered

- Deleted the former package shim, routing skill and exception/console aliases. Removed the obsolete ignore entry and generated shim bytecode without touching application caches or downloads. Removed files remain recoverable in Git history.
- Replaced compatibility regressions with positive canonical-module, sole console-entry, manifest and source/skill inventory contracts. School selection and activity/cache identity checks remain covered.
- Renamed provider-labelled fixture/debug file names to generic LMS names and updated their references.
- Normalized former product identifiers across all tracked text, including dated planning records. Corrected current PROJECT/README compatibility claims. Prior rebrand plan/summary/verification carry explicit supersession notices; historical commit IDs, counts and outcomes remain intact.
- README instructs other devices to pull, run `uv sync`, reinstall canonical skill links and start a fresh agent session.

## Commits

- `066dce7` — runtime, packaging, source skill removal, fixture renames/references and regression tests.
- `5d2cb53` — README and tracked planning terminology/current policy, including historical debug rename.

Dependent fixture renames and their test references were committed with runtime changes so that the implementation commit is independently testable. Current task artifacts and STATE are recorded in the final lifecycle commit.

## Verification

- Baseline full suite: **419 passed** in 19.15 seconds.
- Targeted rebranding/installer/config tests: **51 passed** in 5.41 seconds.
- Final full suite: **419 passed** in 17.85 seconds. Removed compatibility cases were replaced by canonical contracts; counts are not claimed to represent new platform support.
- Canonical skill validator passed with ephemeral PyYAML and UTF-8 mode; no project dependency was added.
- Reinstalled editable package metadata with `uv sync --extra dev`; only the canonical console launcher remains.
- Built wheel passed isolated installation outside the repository: exactly one package and its dist-info, one console entry, canonical module/console help, bundled skill/contract lookup and copy installation into a temporary agent home. No private repo-root marker is packaged.
- Case-insensitive tracked former-product content audit: **0 matches**. Tracked former-label file-name audit: **0 matches**. README local links: **0 broken**. Whitespace check passed.
- alpha-AOS plan/status inspection immediately after manifest setup and after verification: BROWNFIELD_INIT deployment **CURRENT**. No pack approval/sync or harness artifact edits were performed.

## Safety and handoff

No credentials, actual LMS URLs/profile IDs, application caches/downloads or activity identities were changed. No LMS/Notion writes, publication, remote change, Git-history rewrite, active workspace-root rename or external skill-directory mutation occurred. The cleanup guarantee covers the Git-tracked working tree, not old commits or user-managed external installations.

Existing installations are intentionally incompatible and require `git pull`, `uv sync`, then `uv run coursepilot install-skill --agent <id> --link` (omit `--link` for copies). Remove unused external skill connections manually and start a fresh agent session. No per-agent rediscovery or new LMS adapter is claimed. Phase 17 remains at its context-gathered boundary.
