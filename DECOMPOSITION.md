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

RESULT_PLACEHOLDER
