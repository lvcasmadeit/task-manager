# DECOMPOSITION.md — notification preference pipeline (PA5 Task 2)

Feature: a user has `notification_pref` in `email | sms | none` (default `none`),
stored on the user row as a nullable field. `PATCH /users/{id}/notifications`
updates it (invalid -> `ValidationError`), `GET /users/{id}/notifications`
returns it, and user list/detail responses include `notification_pref`.

This file was written **before** any subagent ran. Result lines marked
`RESULT:` were filled in afterwards.

## Pre-decomposition findings (read the repo first)

- There is no `routes/users.py`, no user list, and no HTTP framework; routes are
  plain functions returning `(status, body)`. "Existing user list/detail
  endpoints" therefore have to be created as handlers in `routes/users.py`.
- `CLAUDE.md` forbids editing `services/users.py` ("reference pattern"). Notification
  logic goes into a **new** `services/notifications.py`. A user-list service
  function is still needed; SA-2's prompt *explicitly asks* for a single appended
  `list_users` in `services/users.py` and forbids touching `get_user`.
- `services/users.py::get_user` already returns the stored row, so once the
  repository row carries `notification_pref`, user detail includes it with no
  service change.
- Storage convention: the stored value is `None` (nullable) until set. The
  notifications GET reports the effective value `"none"` for `None`. User
  list/detail return the raw stored value (`None`/`"email"`/`"sms"`/`"none"`).

## Subagent table

Every subagent is a fresh session (new Agent context, no carry-over). Each is
told to read `CLAUDE.md` first and gets exactly the prompt below.

| Field | SA-1: Data layer | SA-2: Service layer | SA-3: API layer | SA-4: Tests |
|---|---|---|---|---|
| **Input** | `CLAUDE.md`, `repositories/users.py`, `repositories/tasks.py` (style) | `CLAUDE.md`, `services/users.py`, `services/tasks.py`, `repositories/users.py`, `utils/errors.py` | `CLAUDE.md`, `routes/tasks.py`, `services/users.py`, `services/notifications.py`, `utils/errors.py` | `CLAUDE.md`, `services/notifications.py`, `services/users.py`, `routes/users.py`, `tests/test_tasks.py` (style) |
| **Task** | Give user rows a nullable `notification_pref` and add repository functions to list users and set the preference. | Add validated get/set notification services and a `list_users` service. | Add user list/detail and GET/PATCH notifications handlers. | Test the service and route behaviour end to end, ending with a green suite. |
| **Output** | `repositories/users.py` | `services/notifications.py` (new); `services/users.py` (append `list_users` only) | `routes/users.py` (new) | `tests/test_notifications.py` (new); `tests/test_routes_users.py` (new) |
| **Constraint** | Do not touch `services/`, `routes/`, `tests/`, `utils/errors.py`, `repositories/tasks.py`. | Do not touch `repositories/`, `routes/`, `tests/`, `services/tasks.py`; in `services/users.py` do not change `get_user`; `services/notifications.py` must not import `services/users.py`. | Do not touch `services/`, `repositories/`, `tests/`, `routes/tasks.py`; never import `repositories/` in `routes/users.py`. | Do not touch any non-test file; do not edit existing test files (`tests/test_tasks.py`, `tests/test_users.py`, `tests/test_routes_tasks.py`); import only from `routes/`, `services/`, `utils/`. |
| **Hand-off** | `repositories/users.py::find_all() -> list[dict]` and `set_notification_pref(user_id, pref) -> dict \| None` | `services/notifications.py::get_notification_pref(user_id) -> dict`, `set_notification_pref(user_id, pref) -> dict`; `services/users.py::list_users() -> list[dict]` | `routes/users.py::handle_list_users()`, `handle_get_user(user_id)`, `handle_get_notifications(user_id)`, `handle_update_notifications(user_id, body)` | Green `pytest -q` and clean `ruff check .` |

### Exact prompts

**SA-1 prompt**
> Work in /Users/lvcas/Developer/aiawcc/PA5/task-manager. Read CLAUDE.md first and obey it. In repositories/users.py ONLY: (1) add `"notification_pref": None` to the seed user row; (2) add `find_all() -> list[dict]` returning all user rows; (3) add `set_notification_pref(user_id: int, pref: str) -> dict | None` that stores pref on the user, replacing the row (not mutating in place), returning the new row or None if the user is absent; never raise, no validation. Google-style docstrings and type hints. Do not touch any other file. Run `.venv/bin/pytest -q` and `.venv/bin/ruff check .` (also `.venv/bin/ruff check --select E501 .`) and fix anything red. Report files changed and anything you did beyond this prompt.

**SA-2 prompt**
> Work in /Users/lvcas/Developer/aiawcc/PA5/task-manager. Read CLAUDE.md first and obey it. (1) Create services/notifications.py with `get_notification_pref(user_id: int) -> dict` and `set_notification_pref(user_id: int, pref: str) -> dict`, following the validate -> repository -> raise-on-missing -> return pattern of services/users.py::get_user. Valid prefs are exactly "email", "sms", "none" (case-sensitive; anything else, including None, non-str, "" or "EMAIL", raises ValidationError); invalid user_id (non-int, <=0, bool) raises ValidationError; unknown user raises NotFoundError. Both return `{"user_id": id, "notification_pref": value}`; get reports "none" when the stored value is None. Use repositories/users.py (find_by_id, set_notification_pref); do NOT import services/users.py. (2) Append `list_users() -> list[dict]` to services/users.py (returns repositories/users.py::find_all()); you may NOT change get_user or anything else in that file. Google-style docstrings and type hints. Do not touch any other file. Run `.venv/bin/pytest -q` and `.venv/bin/ruff check .` (also `.venv/bin/ruff check --select E501 .`) and fix anything red. Report files changed and anything you did beyond this prompt.

**SA-3 prompt**
> Work in /Users/lvcas/Developer/aiawcc/PA5/task-manager. Read CLAUDE.md first and obey it. Create routes/users.py ONLY, following routes/tasks.py::handle_get_task (call a service, catch AppError, return `(exc.status_code, {"error": exc.message})`): `handle_list_users() -> tuple[int, dict]` returning (200, {"users": [...]}) via services.users.list_users; `handle_get_user(user_id: int)` returning (200, user) via services.users.get_user; `handle_get_notifications(user_id: int)` returning (200, {...}) via services.notifications.get_notification_pref; `handle_update_notifications(user_id: int, body: dict)` calling services.notifications.set_notification_pref(user_id, body.get("notification_pref")) and returning (200, {...}). Routes only translate: no validation, no extra guards, never import repositories/. Google-style docstrings and type hints. Do not touch any other file. Run `.venv/bin/pytest -q` and `.venv/bin/ruff check .` (also `.venv/bin/ruff check --select E501 .`) and fix anything red. Report files changed and anything you did beyond this prompt.

**SA-4 prompt**
> Work in /Users/lvcas/Developer/aiawcc/PA5/task-manager. Read CLAUDE.md first and obey it. Create tests/test_notifications.py (service level: get default is "none"; set email/sms/none round-trips; invalid values "push", "", "EMAIL", None, 1 raise ValidationError; invalid user ids 0, -1, True, "1" raise ValidationError; unknown user 999 raises NotFoundError; a failed set leaves the stored value unchanged) and tests/test_routes_users.py (routes level: list includes user 1 with a "notification_pref" key; detail includes "notification_pref"; GET notifications 200; PATCH notifications 200 then GET reflects it; PATCH invalid -> 400 with "error"; PATCH unknown user -> 404; PATCH missing key -> 400). Tests may import only from routes/, services/, utils/ and pytest; never repositories/. Because state is shared in memory, restore user 1's preference to "none" at the end of tests that change it (use a fixture) and never assert counts. Do not touch any non-test file and do not edit existing test files. Run `.venv/bin/pytest -q` and `.venv/bin/ruff check .` (also `.venv/bin/ruff check --select E501 .`) and fix anything red. Report files changed and anything you did beyond this prompt.

## Execution record

Between subagents the lead (me) ran `git diff --name-only` against the previous
commit to check the **Constraint** field mechanically rather than trusting the
subagent's own report, then `pytest -q`.

| Subagent | Files changed (checked with `git status --short`, not self-report) | `pytest -q` | `ruff check .` / `--select E501` | Fix needed |
|---|---|---|---|---|
| SA-1 | `repositories/users.py` only | 90 passed | clean / clean | none |
| SA-2 | `services/notifications.py` (new), `services/users.py` (append of `list_users`; `get_user` untouched per `git diff`) | 90 passed | clean / clean | none |
| SA-3 | `routes/users.py` (new) | 90 passed | clean / clean | none |
| SA-4 | `tests/test_notifications.py`, `tests/test_routes_users.py` (new) | 117 passed | clean / clean | none |

**Read this table carefully:** `pytest -q` reported *90 passed* after SA-1, SA-2
and SA-3. That number is the Task 1 baseline, not evidence about the new code:
no test exercised `notification_pref` until SA-4. Each constraint kept the
subagent out of `tests/`, so the "verify after each subagent" gate was
vacuous for the first three. Only SA-4's 27 new tests (117 total) verified the
feature.

After SA-4 I probed the handlers by hand (`routes.users`):
`handle_update_notifications(1, {"notification_pref": "sms"})` -> `(200, ...)`,
detail and list both show `"sms"`, and `handle_update_notifications(1, None)`
raises an uncaught `AttributeError` (see Divergence).

## Divergence

**Did Claude follow the constraint field for every subagent?** Yes for every
file-level constraint. I verified this mechanically with `git status --short`
and `git diff` after each run; each subagent changed exactly its Output list.
The closest thing to a violation was a conflict between rules rather than
Claude ignoring one: `CLAUDE.md` says "never edit `services/users.py` unless
explicitly asked", while the feature needs a user-list service. SA-2's prompt
explicitly asked for one appended `list_users`; the diff shows only an append
and `get_user` is byte-identical. SA-2 volunteered the CLAUDE.md conflict in
its own report. Unrequested additions that stayed inside the allowed files:
SA-2 added a private `_validate_user_id` helper and a `VALID_PREFS` constant;
SA-4 added unknown-user and invalid-id tests beyond the list. Nothing outside
the Output list was touched.

**Did any subagent's output break the next one's assumption?** No hand-off
broke: the function names and signatures from SA-1 and SA-2 were used as given
by SA-3 and SA-4. Two weaknesses surfaced that the decomposition itself caused:
(1) the vacuous `pytest -q` gate described above; (2) an API inconsistency I
specified: `GET /users/{id}/notifications` reports `"none"` for an unset
preference, but user list/detail return the raw stored `None`. SA-4's tests
encode both behaviours, so they pass, but a client sees `null` in one place and
`"none"` in another. I did not recover from either, because nothing failed; I
am recording them as limitations. Also: `handle_update_notifications` and the
task handlers from Task 1 raise `AttributeError` for a non-dict body, a direct
result of telling SA-3 "no extra guards" (and of my Task 1 session 4 amendment).

**Would I write the decomposition differently?** Yes:
1. Let each subagent add the matching `tests/test_<module>.py` for its own layer
   (adding a new test file is allowed; editing existing ones is not). That makes
   the post-subagent `pytest -q` gate meaningful and matches `CLAUDE.md`'s
   "new behaviour needs a test".
2. Decide the `None` vs `"none"` representation in SA-1 (store `"none"` as the
   default) so reads are consistent in every endpoint.
3. Specify what handlers do with a non-dict body, instead of banning guards.
4. Resolve the `CLAUDE.md` vs `services/users.py` conflict before SA-2 by
   adding an explicit "append-only" rule, rather than relying on the prompt.
5. Put the `ruff --select E501` check in the base prompt from the start; it was
   only added because Task 1 session 5 found six long lines the default ruff
   config never reported.

## Honesty note on how this was executed

The four subagents ran as fresh, isolated Claude subagent contexts launched by a
lead assistant, each with exactly the prompt above and no carried-over context.
The lead wrote the decomposition and performed the file-level verification. If
this is submitted as your own work, review it and re-run the sessions yourself
in the Claude Code terminal; the supervision decisions here are the lead's, not
a record of you typing in a terminal.
