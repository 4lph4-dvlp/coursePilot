---
schema_version: 1
open_count: 1
waived_count: 0
fixed_count: 0
total_count: 1
last_updated: 2026-09-23T04:52:51.487Z
---

# Broken Windows Ledger

> Cross-phase defect register. With `workflow.windows_enforce` enabled, `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | 05 | unmet-truth | .planning/phases/05-cli-reporting-antigravity-skill-packaging/05-LIVE-EVIDENCE.md |  | D-26 live evidence: check/sync both exit 2 (ConfigError) because .env LMS_USERNAME/LMS_PASSWORD are empty; real course-count>=1 evidence not yet captured. User must fill real LMS credentials in .env and re-run. | open |  | 2026-09-23T04:52:51.487Z |  |

````json
[
  {
    "id": 1,
    "kind": "unmet-truth",
    "phase": "05",
    "file": ".planning/phases/05-cli-reporting-antigravity-skill-packaging/05-LIVE-EVIDENCE.md",
    "line": null,
    "description": "D-26 live evidence: check/sync both exit 2 (ConfigError) because .env LMS_USERNAME/LMS_PASSWORD are empty; real course-count>=1 evidence not yet captured. User must fill real LMS credentials in .env and re-run.",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-09-23T04:52:51.487Z",
    "resolved_at": null
  }
]
````
