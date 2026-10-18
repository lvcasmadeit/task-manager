# Use when adding a brand-new resource endpoint (e.g. `tags POST`) to task-manager; do not use it to change an existing endpoint's behaviour.

## Goal
`$ARGUMENTS` is `<resource> <METHOD>`, e.g. `tags POST`. The first word is the
resource name (plural, lowercase); the second is the HTTP method
(GET, POST, PUT, PATCH or DELETE). If either is missing or the method is not one of
those five, stop and ask. Create or update exactly these files for `<resource>`:
- Route file: `routes/<resource>.py`, one `handle_<action>_<singular>` function.
- Service file: `services/<resource>.py`, holding all validation and logic.
- Schema file: `schemas/<resource>.py` (create `schemas/__init__.py` if absent),
  `TypedDict` definitions for the request body and response only; no logic.
- Also, because layering requires it: `repositories/<resource>.py` if missing, and new
  tests in `tests/test_<resource>.py` and `tests/test_routes_<resource>.py`.
Create a file only if it does not exist; if it exists, append the new function.

## Context
- Canonical pattern: `routes/tasks.py` (`handle_get_task`, `handle_create_task`):
  call a service, catch `AppError`, return `(status_code, body)`.
- Service pattern: `services/users.py::get_user`. Layering from CLAUDE.md:
  `routes/` -> `services/` -> `repositories/`; a layer imports only the one below, and
  services never import other services.
- `schemas/` is the one exemption to the one-layer-down import rule: routes, services
  and repositories may import its `TypedDict`s for type hints. It imports nothing from
  the project. Routes pass `body.get("field")` values straight to the service, as
  `handle_create_task` does; extracting a field is not validation.
- Happy-path statuses: GET 200, POST 201, PUT 200, PATCH 200, DELETE 204.

## Constraints
- No business logic in the route handler: no validation, type checks, conditionals on
  body contents, or `repositories/` imports. It only calls the service and translates
  `AppError`, exactly like `handle_get_task`.
- Do not edit `services/users.py`, `utils/errors.py`, `requirements.txt` or
  `pyproject.toml`, or the existing contents of any file in `tests/`.
- Raise `NotFoundError` / `ValidationError`; type hints and Google-style docstrings
  on every function; no new dependencies; lines at most 88 characters.
- Touch no files for other resources.
- New tests must pass in any order: repositories hold module-level dicts, so use unique
  values per test or reset the dict in a fixture rather than relying on earlier tests.

## Verification
1. Run `.venv/bin/pytest -q`; everything must pass and the test count must rise.
2. In `tests/test_routes_<resource>.py`, call the new handler with valid input and
   assert the status is the happy-path status for `<METHOD>` from Context
   (e.g. `status, body = handle_create_tag({"name": "work"}); assert status == 201`).
3. Also assert one error path returns `(400, {"error": ...})` or `(404, ...)`.
4. Run `.venv/bin/ruff check .` and `.venv/bin/ruff check --select E501 .`.
Report the file list and the pytest count before and after.
