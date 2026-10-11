# RETRO.md — PA5 retrospective

**1. Plan Mode value.** The amendment in PLAN_LOG.md session 3 prevented a
layering problem that would have needed a revert. The planner's first draft
noted that `?priority=abc` arrives as text and offered to convert it "in the
route layer"; accepted as written, that puts parsing in `routes/tasks.py`
against the `CLAUDE.md` rule that routes only translate. I amended the plan so
`services/tasks.py::list_tasks` accepts digit strings and converts them before
`_validate_priority`, which is exactly why `handle_list_tasks` in
`routes/tasks.py` is four lines and passes the raw value through. Session 1
paid off in the same way: moving the check into `_validate_priority` meant
sessions 2 and 3 called it instead of copying it, so a later change to the
range lives in one place.

**2. Plan Mode limits.** The case where output did not fully match was session
1: the implementer followed every amended step, but its report said it had kept
lines within the project's line length while `services/tasks.py:39` was 93
characters and `repositories/tasks.py:6` was 89, against `line-length = 88` in
`pyproject.toml`. The default `ruff check .` does not enable E501, so the tool I
was told to run stayed green and only `ruff check --select E501 .` in session 5
exposed six violations. A plan is a statement of what to do, not of everything
that must stay true; Plan Mode reliably gates intent for the steps written down,
and fails silently on constraints that live in config, are unenforced by the
default tooling, or are only claimed in the implementer's report (sessions 2
and 4 also reported "not a git repo" when git was initialised). The reliability
boundary is therefore the plan's own text plus whatever a separate check
verifies; I verified with `git diff` and `pytest -q`, not with the report.

**3. Subagent value.** The most important boundary was SA-2's constraint on
`services/users.py` in DECOMPOSITION.md: it could append `list_users` but not
change `get_user`, and `services/notifications.py` could not import
`services/users.py`. That file is the reference pattern in `CLAUDE.md`, and the
feature genuinely needed an edit there, so this was the one place where a rule
and the task collided; SA-2 stated the conflict itself in its report and the
`git diff` shows a pure append. In a single session I would have had no
file-level diff to check per layer and no fresh context to catch drift, and the
reference file could have been rewritten alongside the rest of the change; I did
not run that counterfactual, so this is an inference. The boundaries also had a
cost I should be upfront about: because they kept SA-1 to SA-3 out of `tests/`,
`pytest -q` read 90 passed three times in a row and told me nothing about the
new code until SA-4 (117 passed).

**4. Gap analysis.** The rule I would most want enforced mechanically is
"`services/users.py::get_user`, `utils/errors.py` and existing test files are
never modified; `services/users.py` may only be appended to." A hook that
enforces it would be a PreToolUse hook on Edit/Write that denies any change to
those paths unless the diff is a pure append (or an explicit allow flag is set
for that session), so the reference pattern cannot be rewritten even when a
prompt or a plan quietly asks for it.
