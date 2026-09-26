---
name: kau-lxp
description: "Legacy compatibility entry for CoursePilot, formerly KAU LXP Assistant. Use when explicitly invoking kau-lxp or continuing an existing installation; coursework management is documented in the canonical coursepilot skill."
---

# CoursePilot — legacy skill entry

This installed skill name is retained for compatibility. Do not maintain a second workflow here.

1. Resolve the repository root from this folder's `repo-root.txt`. If it is absent in a linked installation, resolve the actual filesystem target of this skill folder and use its grandparent (the repository containing `skills/kau-lxp`). Do not guess a user workspace path.
2. Read `<repository root>/skills/coursepilot/SKILL.md` completely and follow it, resolving `{{COURSEPILOT_REPO}}` to that root. Read its `JSON_CONTRACT.md` when needed. If the canonical skill is unavailable, report the installation problem instead of inventing commands.
3. CoursePilot is the current name. `python -m kau_assistant` remains a CLI compatibility alias. Existing credentials, cache paths and explicit `LMS_URL` settings do not need to be renamed.

New installations use `uv --directory "<repository root>" run python -m coursepilot install-skill --agent <agent>`. Do not replace or remove this legacy installation without user authorization.
