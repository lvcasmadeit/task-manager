# RETRO.md: PA6 retrospective

(The PA5 retrospective that used to live here is preserved as `RETRO_PA5.md`.)

**1. Slash command value.** `scaffold-endpoint.md` saves the most prompt-writing
effort (COMMAND_LOG.md row 4, `/scaffold-endpoint tags POST`). The equivalent ad-hoc
prompt has to restate, every time: create `routes/tags.py`, `services/tags.py`,
`schemas/tags.py` and `repositories/tags.py`; copy `routes/tasks.py::handle_get_task`;
keep validation out of the route; raise `NotFoundError`/`ValidationError`; map POST to
201; add tests in new files; run `pytest -q` and `ruff check --select E501 .`. That is
about 430 words (`wc -w` of the file) against a five-word invocation, and it is the
prompt I would otherwise rewrite from memory and get subtly different each time (the
E501 misses in paragraph 2 of `RETRO_PA5.md` came from exactly such an omitted
constraint). `audit-errors.md` (404 words) is second: its
idempotency and "after every function" rules made the re-run in row 3 a no-op, and row
2 shows the pacing rule catching a real flaw, a test asserting `ValueError` that my first
version would have turned into a dead end. The scaffold run (row 4) created seven files,
took `pytest -q` from 163 to 171 passed, and left the route free of `repositories/`
imports. It also exposed that my first draft said nothing about `schemas/` imports,
which I fixed in the command's Context; an ad-hoc prompt would have lost that lesson.

**2. Hook reliability.** Both Part B vectors bypassed the baseline hook before
my fix (HOOK_LOG.md, Vector 1 and Vector 2: exit code 0 for both payloads). Vector 1
got through because `"utils/errors.py" in "Utils/errors.py"` is false in Python while the
macOS filesystem treats the two spellings as one file (`ls Utils` listed `utils/`).
Vector 2 got through because `settings.json` registered the hook for
`Write|Edit|MultiEdit` only, so a `printf x > utils/errors.py` Bash call never reached
the script. The rule "do not edit `utils/errors.py`" was written down in both
CLAUDE.md and `guard_writes.py`, yet enforcement was only as wide as the matcher and the
comparison: a rule is enforced only on the exact tool names and spellings the hook
inspects. A caveat: I verified by piping PreToolUse payloads into the script, not
in a live model session (the nested `claude -p` run failed to authenticate), and
HOOK_LOG.md says so for each vector.

**3. Advisory vs. deterministic.** The rule I left in CLAUDE.md's Do-not-touch section
is "Never modify the existing contents of `tests/test_tasks.py`, `tests/test_users.py`
or `tests/test_routes_tasks.py` from a task scoped to another feature". The hook cannot
see the task's scope, and those files are legitimately edited when the task *is* about
tasks or users, so blocking the path would break valid work. I would graduate it to
`BLOCKED_PATHS` when a task touching tasks or users behaviour lands with its tests in
a new `tests/test_<module>.py` (as `tests/test_guard_writes.py` and PA5's
`tests/test_notifications.py` did) so that nothing needs to edit the three files, and
CLAUDE.md names them frozen; at that point the scope exception disappears and the path
rule becomes unconditional. The signature rule and "no validation in routes" stay
advisory for the same reason: they depend on diff content, not on a path.

**4. Limits of hooks.** I wanted to enforce "run `pytest -q` before finishing ANY task"
(CLAUDE.md, Commands) and could not do it with PreToolUse. That event fires before a
single tool call and has no notion that the task is about to finish, so there is no
call at which to demand a green test run; I could only block bad actions, not require a
good one. The right mechanism is a `Stop` hook that runs `.venv/bin/pytest -q` and exits 2
to keep Claude working on failure (or CI as the backstop). A smaller limit is in the
repo itself: `cd utils && echo x > errors.py` still writes `utils/errors.py` because the
full path never appears in the command, which is recorded as a strict xfail,
`tests/test_guard_writes.py::test_bash_cd_then_relative_write_blocked`; a pre-commit
check on the file contents would catch it where the command string cannot.
