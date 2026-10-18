# Use after editing a file when `ruff check --select E501` reports lines over 88 characters; do not use it to change logic, rename things, or fix other lint rules.

## Goal
Wrap every line longer than 88 characters in `$ARGUMENTS` (one file path) so that
`.venv/bin/ruff check --select E501 $ARGUMENTS` reports no violations, without
changing behaviour.

## Context
- `pyproject.toml` sets `line-length = 88`, but plain `ruff check .` does not enforce
  E501, so it stays green on long lines. That is why E501 is selected explicitly.
- Prefer the style already used in the file (e.g. the parenthesised multi-line
  conditions in `services/tasks.py::_validate_priority`). Docstrings may be re-wrapped
  but their wording must not change.

## Constraints
- Line breaks, indentation and the parentheses needed to wrap a line only: no renames,
  no reordering, no new or removed statements, no logic changes, no changed string
  contents. Split a long string with implicit concatenation, putting the `f` prefix
  only on the pieces that contain `{}` and keeping the spaces where the break falls.
- Edit only `$ARGUMENTS`. Never touch `pyproject.toml` (not even to change the limit)
  or `requirements.txt`, `utils/errors.py` or `services/users.py`.
- Do not wrap lines that are already within 88 characters.

## Verification
1. Run `.venv/bin/ruff check --select E501 $ARGUMENTS`; it must print "All checks passed!".
2. Run `.venv/bin/pytest -q`; the pass count must equal the count before you started.
3. Run `git diff --stat` and confirm only `$ARGUMENTS` changed.
