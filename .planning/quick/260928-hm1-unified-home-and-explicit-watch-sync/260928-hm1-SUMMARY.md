---
quick_id: 260928-hm1
status: complete
completed: 2026-09-28
execution: inline-codex-adapter
---

# Explicit watch sync and unified private storage

Code commit: `aa14345`.

- The agent skill now uses `watch --update-notion` when the same user request explicitly authorizes playback and marking the completed Scheduler tasks. Ordinary watching remains no-write; later or unclear completion requests use a read-only preview and scoped approval. The runner only updates a matching page after actual playback reports completion.
- Added read-only `watch scheduler-tasks --json` to identify incomplete Scheduler lecture pages and `watch --task-title` to target one exact scheduled video. Duplicate titles are excluded; missing LMS matches are not replaced with a different video.
- Source checkout and wheel now both place credentials, cache, downloads, mapping, debug, and board state under `Path.home() / ".coursepilot"`. Relative output paths are anchored there and traversal is refused; explicit absolute paths remain user-controlled.
- Moved this machine's `.env`, `.cache`, `downloads`, and course mappings to `C:\Users\alpha\.coursepilot`; moved 34 root JSON/log artifacts to its `artifacts` subdirectory. Moved generated `repo-root.txt` there too. No secret contents were printed or committed.
- Removed `config/course_mappings.json` from the current Git tree and ignored the path. Personal aliases are read from the home file, rather than embedded as package defaults.
- Reinstalled all five supported agent targets using `--link`: Claude, Codex, Antigravity, Pi, and Hermes. Every target resolves to the source skill and matches its SHA-256 content. Link metadata is stored under the home data root.

The remote `main` previously tracked the mapping file. A normal deletion commit removes it from the latest tree when pushed; historical commits retain the old contents unless Git history is separately rewritten. The pre-existing player edit remains unstaged. Phase 17 remains pending.
