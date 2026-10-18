# Use when a service module still raises bare exceptions or returns None for "not found"; do not use it to redesign validation rules or touch routes.

## Goal
Audit every public function in `$ARGUMENTS` (a path under `services/`) and make its
error handling use `AppError` subclasses from `utils/errors.py`:
- `NotFoundError` for a missing resource, `ValidationError` for bad input.
- Replace bare `Exception` / `ValueError` / `TypeError` raises, and any `return None`
  that means "not found", with the matching `AppError` subclass.
- For each function you change, update its `Raises:` docstring section and add type
  hints and a Google-style docstring if missing (CLAUDE.md requires them on any
  function you touch). Leave skipped functions alone.

## Context
- Pattern to copy: `services/users.py::get_user` (validate -> repository -> raise on
  missing -> return the dict). Error classes live in `utils/errors.py`.
- Repositories return `dict | None` and never raise; the service turns `None` into
  `NotFoundError`. Routes already catch `AppError`.
- Tests are in `tests/test_<module>.py`; use `pytest.raises(<ErrorClass>)` for new ones.

## Constraints
- Work one function at a time, top to bottom. Report each as FIXED or SKIPPED.
- Idempotency: if a function already raises `AppError` subclasses correctly (no bare
  exceptions, no `None` for "not found"), SKIP it. Do not rewrite, reformat, rename or
  re-docstring it. A second run of this command on the same file must change nothing.
- Never change a function's name or parameter names/order/defaults. Before replacing
  a `return None`, `grep -rn "<function_name>(" --include='*.py' --exclude-dir=.venv .`;
  if any caller in `routes/` or `services/` relies on the `None`, SKIP and report it.
- Do not touch `utils/errors.py` or `services/users.py` (reference pattern; the
  PreToolUse hook blocks them), and do not edit anything outside `$ARGUMENTS`
  except a new test in `tests/test_<module>.py`.
- Do not add dependencies or new error classes.

## Verification
After every function you change (not when you are done), run `.venv/bin/pytest -q` and
confirm the count did not drop and nothing fails before moving to the next function.
If the only failure is an assertion in `tests/test_<module>.py` that expects the old
behaviour of the function you just changed (`pytest.raises(ValueError)`, `is None`),
update that single assertion to the new `AppError` subclass and say so in the report;
never delete or loosen an assertion. Any other failure: revert that function and report.
At the end, run `.venv/bin/ruff check .` and `.venv/bin/ruff check --select E501 .`,
and print a FIXED / SKIPPED table with one row per function.
