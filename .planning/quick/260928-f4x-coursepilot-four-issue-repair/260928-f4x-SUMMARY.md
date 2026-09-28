---
quick_id: 260928-f4x
status: complete
completed: 2026-09-28
execution: inline-codex-adapter
---

# Material, Scheduler, storage, and title repair

Code commit: `836ecf6`.

- Material previews now report `planned`; actual CSMSDoc viewer only items report `viewed_only` with the missing original link explained. Module 2847 is included by the full inventory, though its LMS completion means the default incomplete list omits it.
- Scheduler skill instructions use CoursePilot's existing notion-client token path for preview/apply and `watch sync-notion` for retroactive completion. Hermes has a junction to the edited source skill.
- Relative cache, download, mapping, debug, and board state paths resolve under the project root. Existing project caches remain in place.
- Current course abbreviations are complete for the observed baseline. Repeated course/week labels are shortened, and a unique LMS source may safely rename an existing Scheduler page after collision checks. No live Notion writes occurred.
- Focused tests and the full 426 test suite passed. Live LMS checks verified material 2847 and the view-only file limit. Live Notion preview performed zero writes and had zero errors but had no actions in the selected scope.

Original file download for 2847 remains unavailable through the site's document viewer. Phase 17 deployment and broad E2E verification remain pending. The pre-existing player edit and untracked root artifacts were preserved.
