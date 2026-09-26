---
quick_id: 260927-3u6
status: passed
verified: 2026-09-27T03:02:24+09:00
verifier: inline-codex-adapter
---

# CoursePilot goal verification

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
- `.venv/Scripts/coursepilot.exe --help` and legacy `kau-assistant.exe --help` from outside repository: both show CoursePilot, exit 0.
- `uv run --with pyyaml python -X utf8 <skill-creator>/scripts/quick_validate.py skills/coursepilot` and `skills/kau-lxp`: both valid. PyYAML is ephemeral, not a new project dependency.
- `alpha-aos project plan/status . --json`: BROWNFIELD_INIT selected and deployment CURRENT after setup.
- `git diff --check`: passed; tracked credential files unchanged; dependency lock change is package-name relocation, not dependency upgrades.

## Migration boundaries

Actual school URLs, provider-specific selectors and fixture filenames are not product-brand names and remain valid. Old Python and skill names intentionally remain as compatibility surfaces. The repository directory and Git remote stay unchanged. Historical phase/quick records are not rewritten.

No new LMS support, global per-agent rediscovery, LMS/Notion writes or package publication is claimed. Existing copied agent skills need an update; existing linked kau-lxp skills route to canonical instructions. Phase 17 remains pending. The valid canonical Claude copy created by an initially non-isolated legacy test was retained and documented; installer tests now isolate user homes.
