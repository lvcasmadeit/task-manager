# task-manager

Small in-memory Python task tracker. Python 3.12, pytest, ruff.

## Commands
- Install: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`
- Test: `.venv/bin/pytest -v` (run before finishing ANY task)
- Quick test: `.venv/bin/pytest -q` (run after every subagent/step; a count unchanged from the
  previous step means your new code is untested, not that it is verified)
- Single file: `.venv/bin/pytest tests/test_tasks.py -v`
- Lint: `.venv/bin/ruff check .`
- Line length: `.venv/bin/ruff check --select E501 .` (`pyproject.toml` sets 88 but default
  ruff rules do not enforce it, so `ruff check .` alone misses long lines)

## Architecture
Strict layering: `routes/` -> `services/` -> `repositories/`.
- `routes/` only translate: call a service, catch `AppError`, return `(status, body)`.
  Canonical example: `routes/tasks.py::handle_get_task`.
- `services/` hold all business logic and validation. Canonical example:
  `services/users.py::get_user`.
- `repositories/` own storage (in-memory dicts) and return `dict | None`; they never raise.
- A layer may only import the layer directly below it. Routes never import `repositories/`.
- Services never import other services (`services/tasks.py` must not import `services/users.py`);
  check cross-entity data through the other entity's repository, e.g. `repositories/users.py`.
- New data access goes in a `repositories/` function (e.g. `find_by_user_id`); services never
  touch `_TASKS` / `_USERS` directly.
- `routes/tasks.py` and `routes/users.py` only call `services/` and translate `AppError` into
  `(status, body)` exactly as `routes/tasks.py::handle_get_task` does; input parsing and
  validation (e.g. `services/tasks.py::list_tasks` turning `"3"` into `3`) lives in `services/`.

## Conventions
- Follow `services/users.py` as the pattern for every service function:
  validate input -> call repository -> raise on missing -> return the dict.
- Type hints on every parameter and return value (`services/tasks.py` currently lacks them;
  add them to any function you touch).
- Google-style docstrings (Args / Returns / Raises) on every public function.
- Errors: raise `NotFoundError` / `ValidationError` from `utils/errors.py`.
  Never raise bare `Exception`/`ValueError`, never return `None` for "not found".
- New behaviour needs a test in `tests/test_<module>.py` using `pytest.raises` for errors.

## Do not touch
- Never change an existing function signature in `services/` unless the task says so;
  routes and tests depend on them. "Signature" = name, parameter names/order/defaults;
  adding type hints is allowed and required, renaming or reordering is not.
- Never edit `services/users.py` or `utils/errors.py` unless explicitly asked: they are the
  reference pattern.
- `services/users.py` is append-only even when a task asks for a new function in it: never
  modify `get_user`, and never import `services/users.py` from `services/notifications.py`
  or `services/tasks.py` (go through `repositories/users.py`).
- Never put validation, body-type guards or `repositories/` imports in `routes/users.py` or
  `routes/tasks.py`; new notification logic goes in `services/notifications.py`, not in
  `services/users.py`.
- Never modify the existing contents of `tests/test_tasks.py`, `tests/test_users.py` or
  `tests/test_routes_tasks.py` from a task scoped to another feature; put new tests in a new
  `tests/test_<module>.py`.
- Never delete or weaken existing assertions in `tests/` to make a run pass.
- Never edit `.venv/`, `requirements.txt` or `pyproject.toml`; no new dependencies.
