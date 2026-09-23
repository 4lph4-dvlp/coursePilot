---
schema_version: 1
open_count: 1
waived_count: 0
fixed_count: 1
total_count: 2
last_updated: 2026-09-23T07:49:10.769Z
---

# Broken Windows Ledger

> Cross-phase defect register. With `workflow.windows_enforce` enabled, `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | 05 | unmet-truth | .planning/phases/05-cli-reporting-antigravity-skill-packaging/05-LIVE-EVIDENCE.md |  | D-26 live evidence: check/sync both exit 2 (ConfigError) because .env LMS_USERNAME/LMS_PASSWORD are empty; real course-count>=1 evidence not yet captured. User must fill real LMS credentials in .env and re-run. | fixed |  | 2026-09-23T04:52:51.487Z | 2026-09-23T07:49:09.819Z |
| 2 | 05 | unmet-truth | src/kau_assistant/scraper/navigator.py |  | UAT G-05-1: KAU LMS lecture (VOD) deadlines never parsed. navigator requests /report/progress/index.php (real: /report/ubcompletion/progress.php, whose table has no period column), and the course-home fallback ignores span.displayoptions > span.text-ubstrap where the lecture period lives. All lectures get due_date=None and are dropped (D-11), so no lecture reaches check/sync. | open |  | 2026-09-23T07:49:10.769Z |  |

````json
[
  {
    "id": 1,
    "kind": "unmet-truth",
    "phase": "05",
    "file": ".planning/phases/05-cli-reporting-antigravity-skill-packaging/05-LIVE-EVIDENCE.md",
    "line": null,
    "description": "D-26 live evidence: check/sync both exit 2 (ConfigError) because .env LMS_USERNAME/LMS_PASSWORD are empty; real course-count>=1 evidence not yet captured. User must fill real LMS credentials in .env and re-run.",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-09-23T04:52:51.487Z",
    "resolved_at": "2026-09-23T07:49:09.819Z"
  },
  {
    "id": 2,
    "kind": "unmet-truth",
    "phase": "05",
    "file": "src/kau_assistant/scraper/navigator.py",
    "line": null,
    "description": "UAT G-05-1: KAU LMS lecture (VOD) deadlines never parsed. navigator requests /report/progress/index.php (real: /report/ubcompletion/progress.php, whose table has no period column), and the course-home fallback ignores span.displayoptions > span.text-ubstrap where the lecture period lives. All lectures get due_date=None and are dropped (D-11), so no lecture reaches check/sync.",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-09-23T07:49:10.769Z",
    "resolved_at": null
  }
]
````
