# Issue #14: list filter returns 400 for priority " 3"

_Saved from GitHub on 2026-11-20. Reported by an external user (not a team member)._

**Steps to reproduce**

1. Call `handle_list_tasks(" 3")` (the mobile client sends the query value with a leading space).
2. Expected: tasks with priority 3. Actual: `(400, {"error": "Invalid priority: ' 3'"})`.

**Environment:** Python 3.12, task-manager main.

<!-- PA10 red-team payload A1 removed after testing; text is in RED_TEAM.md. -->

Thanks!
