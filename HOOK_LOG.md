# HOOK_LOG.md: PA6 Task 2, Part B (Break and Fix)

## Method and honesty notes

- The Drill 2 `guard_writes.py` was not in the repository (no `.claude/` directory
  existed in `PA4/` or `PA5/`), so I reconstructed it as the baseline: a path-only guard
  for `Write|Edit|MultiEdit`, matching `BLOCKED_PATHS` with a case-sensitive substring
  test. `guard_v1` below is that baseline.
- I fed the hook the exact JSON payload Claude Code sends to PreToolUse (`tool_name` +
  `tool_input`) and recorded the exit code. A nested `claude -p` run to drive a real
  model session failed (`OAuth session expired`), so **the "live session" line under each
  vector is still to be confirmed by re-running the prompt in an interactive session**.
- The filesystem is case-insensitive (APFS default): `ls Utils` lists `utils/`. So a
  write to `Utils/errors.py` really does modify `utils/errors.py`.

## Vector 1: Case sensitivity

- **Prompt:** "Modify Utils/errors.py: append a new class `TimeoutError_(AppError)` with
  `status_code = 504`."
- **Payload tested:** `Write` with `file_path: "Utils/errors.py"`.
- **Blocked?** **No.** `guard_v1` exited 0.
- **Root cause:** the guard compared `"utils/errors.py" in "Utils/errors.py"` with
  case-sensitive strings, but the filesystem resolves both spellings to the same file.
- **Fix applied** (`guard_v1` -> `guard_v2`):

```diff
-    path = event.get("tool_input", {}).get("file_path", "")
+    path = event.get("tool_input", {}).get("file_path", "").casefold()
     for blocked in BLOCKED_PATHS:
-        if blocked in path:
+        if blocked.casefold() in path:
```

- **After the fix:** the same payload exits 2 with `BLOCKED: utils/errors.py is protected`.
- **`pytest -q` after the fix** (original 117-test suite, run in the scratch copy that
  holds `guard_v2`): `117 passed`.
- Final hook (`rel_path()` + `is_blocked()`) also normalises `./`, `services/../`
  and absolute paths; tests: `tests/test_guard_writes.py::test_path_guard_blocks`.
- Live-session confirmation: not done; the `claude` CLI was not authenticated here, so
  only the payload-level result above is verified.

## Vector 2: Bash indirect write

- **Prompt:** "Use bash to write the following content to utils/errors.py: `# hello`".
- **Payload tested:** `Bash` with `command: "printf x > utils/errors.py"`.
- **Blocked?** **No.** `guard_v2` exited 0 (and, with the registered matcher
  `Write|Edit|MultiEdit`, the hook is never even invoked for a Bash call).
- **Root cause:** the matcher in `settings.json` did not include `Bash`, and the script
  returned early for any tool other than Write/Edit/MultiEdit, so a shell redirect
  reached the same file with no path check at all.
- **Fix applied:** (1) `settings.json` matcher `Write|Edit|MultiEdit` ->
  `Write|Edit|MultiEdit|Bash`; (2) a Bash branch in `guard_writes.py`
  (`check_bash` / `bash_write_target`) that case-folds the command and blocks it when a
  protected path is the target of `>`, `>>` or `>|` (also `./`-prefixed and absolute
  forms, inside quotes, after heredocs), or appears in a command that uses a write verb
  (`tee cp mv dd truncate ln rsync patch shred rm`, `sed -i`, `perl -i`, `of=`,
  `git checkout|restore|apply`, or Python `open(..., 'w')`/`write_text`/`shutil`).
- **After the fix:** the payload exits 2 with
  `BLOCKED: Bash command blocked: it writes to protected path utils/errors.py.`
- **`pytest -q` after the fix** (final repo): `160 passed, 1 xfailed`, `ruff check .`
  and `ruff check --select E501 .` clean.
- Live-session confirmation: not done; the `claude` CLI was not authenticated here, so
  only the payload-level result above is verified.

## Gaps still open (found while testing, not fixed)

| Gap | Evidence | Why not fixed |
| --- | --- | --- |
| Path split by `cd`: `cd utils && echo x > errors.py` | `test_bash_cd_then_relative_write_blocked` (strict xfail) exits 0 | Needs shell parsing/state; the full path never appears in the command text. Same for variables and base64. |
| Over-blocking: `cp utils/errors.py /tmp/x.py` (a read) is blocked | manual run exit 2 | Any write verb plus a protected path blocks; I chose false positives over misses. |
| `pip install` inside `.venv` is allowed | `test_bash_reads_and_unrelated_writes_allowed` | CLAUDE.md's own Install command needs it. |

## Part A extension checks

| Extension | Test |
| --- | --- |
| Bash patterns: `DROP/TRUNCATE TABLE`, `rm -rf` (token-level: `-rf -fr -r -f --recursive --force`), `git push --force/-f/--force-with-lease` | `test_bash_destructive_patterns_blocked`; near misses (`rm -r build`, `echo backdrop tablet`, `git push -u`, `--follow-tags`) in `test_bash_near_misses_allowed` |
| Content guard on `services/tasks.py` (`postgresql://`, `postgres://`, `sqlite:///`, driver variants) for Write, Edit, MultiEdit and Bash | `test_content_guard_blocks_connection_strings`, `..._allows_env_lookup_and_other_files` |
