---
quick_id: 260928-gh1
status: complete
completed: 2026-09-28
execution: inline-codex-adapter
---

# Remove personal mapping file from Git history

Rewritten remote `main`: `8d2d1b03df3edbdb119b712eeb6fff0808424b02` (old head `8a761355eabe5e993a4e2783fad6d98ee8468ca1`).

- Cloned the single remote branch into an isolated mirror under `~/.coursepilot/history-rewrite-260928`, then used `git-filter-repo --path config/course_mappings.json --invert-paths` to remove that path from all reachable commits.
- The rewritten pre-documentation tip has the same Git tree ID as the original tip (`6e635e4a9ba17af36008bed44c7778e86878a0e3`), so application code and the current file tree were unchanged by the rewrite.
- Refreshed 93 GSD commit references in 24 planning files to the rewritten hashes and committed the documentation update as `8d2d1b0`.
- Force-pushed with an explicit lease against the original remote head. Fetched and aligned the local main branch, restored the pre-existing unstaged player edit from a verified patch, expired local reflogs, and pruned unreachable objects.
- Full suite passed after alignment: 432 tests. The home mapping file remained intact.

An automatic approval review rejected recursive removal of the isolated temporary folder despite a verified target path. The folder remains under `~/.coursepilot/history-rewrite-260928`; both temporary Git repositories contain only rewritten reachable history and no `config/course_mappings.json` path. GitHub may retain unreachable server-side objects or backups outside visible branch history.
