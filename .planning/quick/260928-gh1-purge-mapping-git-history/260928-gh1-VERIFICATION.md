---
quick_id: 260928-gh1
status: passed_with_cleanup_limit
verified: 2026-09-28
---

# Verification

| Check | Evidence | Result |
|---|---|---|
| Exact remote branch replacement | Original `main` SHA recorded as `8a76135`; conditional `--force-with-lease` push succeeded; fresh `git ls-remote` returned `8d2d1b0`. | Passed |
| Historical path absent | In rewritten mirror, work clone, and aligned source: `git log --all -- config/course_mappings.json` and `git rev-list --objects --all -- config/course_mappings.json` returned no output. | Passed for reachable Git history |
| Current code preserved | Original and rewritten tip tree IDs matched before GSD reference update. The follow-up commit changed only 24 `.planning` files. | Passed |
| GSD references preserved | Commit map refreshed 93 references across 24 files; no ambiguous mappings; `git diff --cached --check` passed. | Passed |
| User work preserved | The pre-existing unstaged `result = None` change was saved as a 719-byte patch, checked against the rewritten tree, reapplied, and verified as the only tracked working-tree modification. | Passed |
| Local unreachable objects removed | `git reflog expire --expire=now --expire-unreachable=now --all`, `git gc --prune=now`, and `git fsck --full --no-reflogs --unreachable` completed with no reported objects. | Passed |
| Full regression | `uv run --extra dev python -m pytest -o addopts= -q --disable-warnings` after local alignment. | 432 passed |
| Temporary folder cleanup | `Remove-Item -LiteralPath ... -Recurse -Force` against a validated path was rejected by automatic policy review. Both temporary Git repositories were checked to have no historical mapping path. | Cleanup limited |

The rewrite removes the file from reachable Git branch history. It cannot guarantee erasure of server-side caches, backups, old clones, screenshots, or copied content. No Notion write or LMS playback was performed.
