# PLAN_LOG.md — Plan Mode supervision log (PA5 Task 1)

Feature: task `priority` (int 1–5, 1 = urgent, default 3). Baseline before the
work: 13 tests passing. After: 90 passing (`pytest -q`), `ruff check .` clean,
and `ruff check --select E501 .` clean after session 5.

How each session ran: a read-only planning subagent produced a plan from the
prompt; I (the lead) amended it; a fresh implementing subagent received only the
amended plan; I then verified with `git diff` and `pytest -q` rather than the
implementer's report. No framework exists in this repo, so "POST/PATCH/GET" are
plain handlers returning `(status, body)` in `routes/tasks.py`.

| Session # | Prompt summary (≤15 words) | Did you amend the plan? | What you changed | Did output match amended plan? |
|---|---|---|---|---|
| 1 | Add priority to tasks: default 3, validated 1–5, in repo seed and `create_task`. | Yes | Original plan inlined the bool/int/range check in `create_task` and added optional `DEFAULT_PRIORITY`/`MIN`/`MAX` constants, with `pytest` only at the very end. I amended to a private `_validate_priority` helper (so a later `update_task` and `list_tasks` reuse it instead of copying the check), no module constants, and `pytest -q` after the service edit and again after the tests. | **Partially.** All amended steps were done and tests went 13 -> 25. Divergence: the implementer's report said it wrapped the insert call "to stay within ruff's line length", but it left the helper's `if` (93 chars) and a seed row (89 chars) over the configured `line-length = 88`. Default ruff rules do not include E501, so `ruff check .` said "All checks passed" and nobody noticed; I only found it in session 5 with `--select E501`. The plan never mentioned line length, so this is output that did not meet an unwritten project constraint, not a skipped plan item. It also added a Google docstring to the helper that the plan did not list (harmless, matches `CLAUDE.md`). |
| 2 | Add `update_task` for PATCH: title, done, priority; `id` and `user_id` immutable. | Yes | (a) Repository `update` must build `{**row, **allowed}` and replace the stored row, not mutate in place. (b) Original plan raised `ValidationError("No fields to update")` on an empty PATCH; amended to return the task unchanged (404 if absent), because PATCH `{}` should be idempotent. (c) Tests in `tests/test_tasks.py` may import only `services/` and `utils/`, so the planned repository-whitelist test and the `TypeError`-on-unknown-kwarg test were dropped. | Yes. 25 -> 48 tests; the implementer followed all three amendments. It added one test the plan implied but did not list (no fields on a missing task -> 404). Its report claimed the directory was "not a git repo"; that was false (git was initialised in Phase 0) and had no effect on the output. |
| 3 | Add `list_tasks` with optional priority filter for GET `?priority=n`. | Yes | Original plan had two repository functions (`find_all`, `find_by_priority`) and rejected any `str`. Amended to one `find_all(priority=None)`, and to accept digit-only strings in the **service** (converted with `int()`, then `_validate_priority`), because query-string values arrive as text and the plan agent's own note would have pushed that parsing into the route, against "routes only translate". | Yes. 48 -> 61 tests. Judgement call by the implementer, not in the plan: `str.isascii() and str.isdigit()` so non-ASCII digits are rejected; `"03"` is accepted as 3. I accepted this. |
| 4 | Add create/update/list route handlers exposing priority. | Yes | Original plan put tests in `tests/test_tasks.py` and included an "optional guard" for non-dict bodies. Amended: tests go in a new `tests/test_routes_tasks.py` importing only `routes/`, and no extra guards or logic in routes. | **Yes as written, but the amendment I made created a latent bug.** Handlers match the amended plan (61 -> 90 tests), yet with the guard removed `handle_create_task(None)` / `handle_update_task(1, None)` raise `AttributeError` instead of returning a 400. I only found this later, while probing `routes/users.py` in Task 2. Also three test lines exceeded 88 chars (see session 5). |
| 5 | Wrap the six lines over 88 characters left by sessions 1 and 4. | No | No amendment: I previewed the change with `ruff format --diff` on exactly three files and confirmed it touched only the six long lines before applying it. This session was not run through a separate planning subagent; the "plan" was my own inline preview. | Yes. `ruff check --select E501 .` found six violations (`repositories/tasks.py:6`, `services/tasks.py:39,68`, `tests/test_routes_tasks.py:27,34,107`); the baseline commit had none. After `ruff format` on the three files: clean, 90 tests still pass. |

## Summary against the Task 1 requirements

- Rows: 5 (requirement: ≥ 4).
- Real amendments: sessions 1–4 (requirement: ≥ 2).
- Output not fully matching the amended plan: session 1 (partially), with the
  caveat above. In this run I did **not** observe a subagent ignoring an
  explicit plan item; the failures were (i) an implementer report that was
  wrong about something the plan did not specify, and (ii) a bug introduced by
  my own amendment in session 4. I am reporting both rather than claiming a
  more dramatic failure.
- Tests: `tests/test_tasks.py` covers priority validation, update and list
  filtering (e.g. `test_list_tasks_filter_priority`, the priority-5 vs priority-4
  membership test); `tests/test_routes_tasks.py` covers the handlers.

## Honesty note

Sessions were executed by a lead assistant orchestrating isolated subagents, not
by typing `/plan` in an interactive Claude Code terminal. Re-run the sessions
yourself before submitting if the assignment requires first-hand logs.
