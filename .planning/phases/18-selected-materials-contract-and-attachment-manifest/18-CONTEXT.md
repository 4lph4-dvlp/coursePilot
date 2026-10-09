# Phase 18: Selected Materials Contract and Attachment Manifest - Context

**Gathered:** 2026-10-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a supported, versioned CoursePilot materials CLI/JSON contract for exact item and file selection. This is the upstream prerequisite for alpha-AOS Phase 20's non-code connector. Preserve the legacy `materials` and `files` invocation for existing users. Do not change credentials, LMS-family support, VOD, Notion, or unrelated in-progress work. Offline fixtures establish the public contract; real LMS calls require a separately approved account and task scope.

</domain>

<decisions>
## Implementation Decisions

### Public selection and stale-source guard

- **D-18-01:** Publish a versioned materials contract through CLI help, JSON output, `SKILL.md`, and `JSON_CONTRACT.md`. The old unversioned materials mode remains compatible. Unknown contract versions and structurally invalid selection requests fail before effects.
- **D-18-02:** A caller can obtain a bounded coarse course/week/module manifest without visiting individual material pages. It marks the attachment set `unknown` until inspected; LMS completion and planned paths are not saved-file evidence.
- **D-18-03:** Any attachment inspection that can visit a material page and change LMS viewed state is a distinct effect. The CLI exposes this fact, and the caller must approve it before invoking inspection. Inspection returns a complete attachment list only when CoursePilot can prove enumeration; otherwise it returns `unknown` with a reason.
- **D-18-04:** Selected performance names the exact course, module, file ID, and approved full-manifest digest. It re-observes source identity and the complete attachment set before download; an added, missing, renamed, or ambiguous file rejects stale approval before effects. It must never fall back to a whole-course/week download.
- **D-18-05:** Same-week unrelated modules do not block an unchanged approved module. A failed file can be retried alone without executing a verified sibling. Unknown or incomplete attachment sets cannot be reported as complete items.

### Evidence, compatibility, and safety

- **D-18-06:** Selected execution returns per-file status, source identity, saved path, size, and error. Partial failures preserve valid file outcomes; fatal/config/schema errors stop further effects. A repeated selection must avoid duplicate download when current source-bound local evidence proves the file already exists.
- **D-18-07:** Bound source item count, text length, and output size. Treat LMS titles and URLs as data; do not interpolate them into shell commands. Credential values, cookies, and personal course payloads do not enter repository artifacts or diagnostics.
- **D-18-08:** Preserve `materials --course/--week/--dry-run/--json` and the `files` alias for existing callers. New fields are documented with explicit version semantics and fixture-backed normal, partial, stale, and unknown examples.
- **D-18-09:** Publishing the contract is a costly or one-way decision. Before implementation, the executor must present the exact CLI flags and JSON shape for review; then verify the source commit, contract/skill fingerprints, tests, and installed runtime canary. An uninstalled worktree is not proof of a usable contract.

### The agent's Discretion

- Exact names and internal representation of attachment/file IDs, selection arguments, and digest encoding, provided the public version and all invariants above are explicit before the publication checkpoint.
- Parser strategy for supported Coursemos material pages. If a page cannot prove full enumeration without unsafe or unsupported behavior, emit `unknown` instead of fabricating completeness.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementation.**

- `.planning/ROADMAP.md` Phase 18 and `.planning/REQUIREMENTS.md` MCON-01..03.
- `skills/coursepilot/SKILL.md` and `skills/coursepilot/JSON_CONTRACT.md` — published invocation and result conventions.
- `src/coursepilot/cli.py`, `src/coursepilot/materials/models.py`, `src/coursepilot/materials/runner.py`, `src/coursepilot/materials/downloader.py`, and `src/coursepilot/scraper/material_parser.py` — current materials path.
- `tests/test_cli_materials.py`, `tests/test_materials_runner.py`, `tests/test_material_parser.py`, and `tests/test_material_downloader.py` — focused fixture patterns.
- The approved alpha-AOS Phase 20 decisions D-01..D-17 and its upstream acceptance contract are summarized above; resolve that project's path at execution rather than persisting a workstation path here.

</canonical_refs>

<code_context>
## Existing Code Insights

`run_materials_pipeline` filters course/week and passes every matching `MaterialItem` to `process_course_materials`. `MaterialItem` has one URL and `MaterialDownloadResult` has one `saved_path`. `extract_pluginfile_url` chooses one link from HTML; the selected contract needs a separate complete-or-unknown enumeration path before exact file execution. Keep the legacy processing route stable while extending a published contract mode.

</code_context>

<deferred>
## Deferred Ideas

Live account proof is deferred to an explicitly approved scope. Supporting Canvas, Blackboard, VOD, and Notion changes is outside this phase.

</deferred>
