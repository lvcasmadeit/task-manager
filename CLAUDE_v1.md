# task-manager

Small in-memory Python task tracker. Python 3.12, pytest, ruff.

## Commands
- Install: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`
- Test: `.venv/bin/pytest -v` (run before finishing ANY task)
- Single file: `.venv/bin/pytest tests/test_tasks.py -v`
- Lint: `.venv/bin/ruff check .`

## Architecture
Strict layering: `routes/` -> `services/` -> `repositories/`.
- `routes/` only translate: call a service, catch `AppError`, return `(status, body)`.
  Canonical example: `routes/tasks.py::handle_get_task`.
- `services/` hold all business logic and validation. Canonical example:
  `services/users.py::get_user`.
- `repositories/` own storage (in-memory dicts) and return `dict | None`; they never raise.
- A layer may only import the layer directly below it. Routes never import `repositories/`.

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
  routes and tests depend on them.
- Never edit `services/users.py` or `utils/errors.py` unless explicitly asked: they are the
  reference pattern.
- Never delete or weaken existing assertions in `tests/` to make a run pass.
- Never edit `.venv/`, `requirements.txt` or `pyproject.toml`; no new dependencies.
