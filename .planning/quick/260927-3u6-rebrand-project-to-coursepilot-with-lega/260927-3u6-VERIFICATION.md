---
quick_id: 260927-3u6
status: passed
verified: 2026-09-27T03:02:24+09:00
verifier: inline-codex-adapter
---

# CoursePilot goal verification

> Historical verification for this task's commit only. Product identifiers were normalized by quick task 260927-4dc, which superseded the compatibility boundary below and removed all former entry points and routing skills. Historical test counts and results are preserved; consult that task's verification for current installation guarantees.

All five must-have truths pass for the approved rebranding scope. Verification is inline, not independent-agent review.

| Truth | Evidence | Result |
|---|---|---|
| CoursePilot is canonical across product/package/CLI/skill | pyproject metadata/console entry points; src/coursepilot; skills/coursepilot frontmatter; README/PROJECT identity; wheel smoke | Passed |
| Legacy entry points preserve runtime identity | Two import-order child-process tests compare config/domain/scraper/exceptions/CLI/Notion modules, model/enum classes, settings singleton and canonical specs; both module and console --help work outside repo | Passed |
| School selection explicit and existing state preserved | Neutral empty URL default; opt-in kau profile; explicit-URL precedence/environment tests; SessionManager guard before Playwright; activity round-trip and unchanged cache/download paths | Passed |
| Broad vision distinguished from implemented support | README/PROJECT/skill state Coursemos-family support and future separate LMS integration work; no platform adapter code added | Passed |
| Packaging/installation works outside checkout | Built wheel installs independently, resolves bundled skill, copies skill into temporary agent home; old/new module/console smoke checks; both skill validators pass | Passed |

## Commands and results

- `uv run --extra dev python -m pytest -o addopts= -q --disable-warnings`: **419 passed**, 19.64 seconds, exit 0.
- `uv build --wheel --out-dir <OS temp>/coursepilot-rebrand-wheel`: exit 0; coursepilot-0.1.0-py3-none-any.whl.
- `uv run --no-project --reinstall-package coursepilot --with <wheel> python ...` from OS temporary directory: final wheel imports, canonical module spec, bundled skill and isolated install passed.
- Canonical and formerly named console executables passed --help from outside the repository at this commit, exit 0.
- `uv run --with pyyaml python -X utf8 <skill-creator>/scripts/quick_validate.py skills/coursepilot` and the former routing skill: both valid at this commit. PyYAML is ephemeral, not a new project dependency.
- `alpha-aos project plan/status . --json`: BROWNFIELD_INIT selected and deployment CURRENT after setup.
- `git diff --check`: passed; tracked credential files unchanged; dependency lock change is package-name relocation, not dependency upgrades.

## Migration boundaries

At this commit, school URLs/selectors were preserved and compatibility surfaces were retained. Quick task 260927-4dc later removed those surfaces, normalized historical document terminology and renamed generic LMS fixtures. The active repository directory, Git history and remote remain unchanged.

No new LMS support, global per-agent rediscovery, LMS/Notion writes or package publication is claimed. All existing agent skills now need canonical reinstallation. Phase 17 remains pending. The valid canonical Claude copy created by an initially non-isolated legacy test was retained and documented; installer tests now isolate user homes.
