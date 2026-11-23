# Security Findings

**Source:** `/security-scan` in a fresh `claude -p` session. The raw output is in
`docs/security-scan-output.md` (S# = its row number). I added the M# rows by hand.

**Checking:** I reproduced every app finding in a Python REPL before writing its test. Line
numbers are from before the fixes (commit `e18b8cd`).

## Triage

| ID | File:line | Category | Severity | Real / FP | How I checked | Status |
|---|---|---|---|---|---|---|
| F1 (S5) | `repositories/tasks.py:19,44,65`, `repositories/users.py:10,19,37` | Data integrity (live references to the store) | **High** (scan said Medium) | Real | `b = handle_get_task(1)[1]; b["user_id"] = 99` made the next GET return 99. It bypasses `_UPDATABLE_FIELDS` and all validation. | Fixed `bd031f2` |
| F2 (S2) | `.claude/settings.json`, `guard_writes.py:34` | Agent: no deny rules, Claude can edit its own guards and security tests | **High** | Real | settings.json had no `permissions` block. `.claude/` and `tests/` were not in `BLOCKED_PATHS`. | Fixed `88686a6`, `8147f2a` |
| F3 (S3) | `.claude/settings.json:5` | Agent: MCP, Read and WebFetch tools were not hooked | **High** | Real | The matcher was `Write\|Edit\|MultiEdit\|Bash` only. Supabase `execute_sql` is connected to the account. | Fixed `88686a6`, `8147f2a` |
| F4 (S1) | `routes/tasks.py:36`, `routes/users.py:52` | Broken access control (IDOR, no authentication) | Medium (scan said High) | Real (design gap) | Any caller can update any task or preference. | **Not fixed**, see below |
| F5 (S4) | `routes/users.py:8` | PII exposure (all emails) | Medium | Real | `handle_list_users()` returns `ada@example.com`. | **Not fixed**, see below |
| F6 (S6) | `routes/tasks.py:24,49`, `routes/users.py:65` | Type confusion: a non-dict body crashes the handler | Medium | Real | `handle_create_task(None)` raises `AttributeError`, which would be a 500 with a traceback. | Fixed `5a0b7b5` |
| F7 (S7) | `services/tasks.py:164-165` | DoS: `int()` digit limit | Medium | Real | `handle_list_tasks("9"*5000)` raises `ValueError` (unhandled). | Fixed `5a0b7b5` |
| F8 (S8) | `services/tasks.py:66,108` | DoS: unbounded title | Medium | Real | A 10 MB title was stored, status 201. | Fixed `5a0b7b5` (max 200 chars) |
| F9 (S9) | `guard_writes.py:196` | Agent: hook fails open on bad input (exit 1) | Medium | Real | Exit 1 is a non-blocking error in Claude Code. | Fixed: `guard.py` fails closed (exit 2) |
| F10 (S10) | `guard_writes.py:57-61` | Agent: hook bypasses (`git clean`, `find -delete`, `+refspec`) | Medium | Real | Piped each command to the hook: exit 0. | Partly fixed in `guard.py`, gaps in RED_TEAM 3f |
| F11 (S11) | `services/tasks.py:19,64`, `services/users.py:20` | Type confusion: `True` accepted as id 1 | Low | Real | `handle_get_task(True)` returned 200. | Fixed `bd031f2` (repositories require `type(id) is int`) |
| F12 (S12) | `services/tasks.py:20,65,165` | Error echoes raw input | Low | Real | The message repeats the whole input. | Partly fixed (priority truncated) |
| F13 (S13) | `.gitignore` | Secrets config: no `.env` rules or `.env.example` | Low | Real | Read the file. | Fixed `c0f0f20` |
| F14 (S14) | `requirements.txt:1-2` | Supply chain: unpinned dev dependencies | Low | Real | Read the file. | **Not fixed**, see below |
| F15 (S15) | `guard_writes.py:43` | Secret-content guard covers one file and two schemes | Low | Real | Read the file. | Fixed: guard.py rule 2 covers all writes |
| M1 | `.claude/settings.json` | Agent: `Read`/`Grep` of `.env` is allowed with no prompt | High | Real | The baseline A3 design. Read needs no permission inside the project. | Fixed: deny rule + guard.py |
| M2 | `guard_writes.py:78-88` | Agent: writes outside the repo are not checked (`rel_path` returns the absolute path) | Medium | Real | Haiku's baseline run tried `/tmp/triage/*.py` and `/tmp/seedcheck/*`. | Fixed for file tools (guard.py rule 3). Not fixed for Bash |
| M3 | `docs/issues/`, `repositories/tasks.py` seed | Prompt-injection channels (external issues, other teams' fixtures) | Medium | Real | Task 3 red team. | Mitigated: guards + policy. Cannot be "fixed" |
| M4 | `.claude/hooks/*` | Hook edits only take effect in a new session | Low | Real | In this session `sed -i` on the protected `tests/test_guard.py` still ran. | Policy: restart after guard changes |
| Safe | all `*.py` | Injection / unsafe eval | – | FP / safe | `git grep -nE "eval\|exec\|pickle\|yaml\|subprocess\|os.system"` matches only the test harness. There is no SQL. | – |
| Safe | `services/notifications.py:18,63` | Notification input validation | – | Safe | It rejects bool and non-str values and uses an allowlist. Covered by `tests/test_notifications.py`. | – |
| Safe | `repositories/tasks.py:64` | Field allowlist on update | – | Safe | `id`/`user_id` are ignored by `update()`. F1 was the only bypass. | – |

## Verification of fixes

- I wrote the exploit tests in `tests/test_security.py` and committed them at `16832e0` while all
  21 were failing. `tests/test_guard.py` was committed at `13bf5e1` with all 58 failing. Another 18 guard cases from the final scan were committed failing at `9e66d7c` and `89221aa`.
- `git diff --stat 16832e0 5a0b7b5 -- tests/` is empty, so the fixes changed no test.
- Full suite at the end: `257 passed, 1 xfailed`. The xfail is the known PA6 `cd` gap in
  `test_guard_writes.py`. `ruff check .` and `ruff check --select E501 .` are clean.

## Final scan (`docs/security-scan-final.md`, fresh session, guardrails on)

| Scan # | Finding | Severity | Real? | Status |
|---|---|---|---|---|
| 1, 2 | Planted A1/A2 payloads still in `docs/issues/` and seed task 2 | High | Real (deliberate red-team fixtures) | Removed `6605dbb`. Their text is kept in RED_TEAM.md |
| 3, 4, 10 | No authentication / IDOR / PII | High/Med | Same as F4/F5 | Not fixed, see below |
| 5 | Hook bypass: `grep -r KEY .`, globs `.e*`, `.en[v]` reach `.env` | High | Real (tested: exit 0) | Fixed `d7c4be6`, tests `9e66d7c` |
| 6 | `git -C . push` / `git -c k=v push` bypass | Medium | Real (tested) | Fixed `d7c4be6` |
| 7 | DNS tools, `busybox wget`, `pip install` not blocked | Medium | Real (tested) | Fixed `d7c4be6`. Other egress is a gap (RED_TEAM 3f #1) |
| 8 | `shutil.copy` onto `.claude/` not detected | Medium | Real (tested) | Fixed: `.claude/` protected, shutil/os.replace treated as writes |
| 9 | MCP `get_or_create_*` / `get_access_*` treated as read-only | Medium | Real | Fixed (write-word check) |
| 11 | No task-count quota | Medium | Real | Not fixed (F8 note) |
| 12 | Deny rules miss `.env.staging`, `.env.test`, `.claude/**` | Low | Real | Fixed `2864d3b` |
| 13 | `max()+1` id race | Low | Real but single-threaded today | Not fixed: needs a lock once a threaded server exists |
| 14, 15 | Bool reaches the service as 404 not 400; echoes in `notifications.py` | Low | Real, not exploitable | Not fixed (F11/F12 notes) |
| 16 | `guard_writes.py` fails open | Low | Real | Mitigated: `guard.py` runs on the same calls and fails closed |
| – | Quote-split `.e''nv` (found by me in 3d) | Medium | Real | Fixed `d7c4be6`, tests `89221aa` |

## Unfixed Medium/Low findings (why)

- **F4 / F5 (access control, PII):** there is no transport or identity model yet. Handlers are only
  called in-process by trusted code, so nothing can reach them. That is why I downgraded the scan's
  High to Medium. A correct fix needs authenticated requester identity in every route signature,
  and that would change every existing route test. **This blocks any HTTP layer:** it must be
  fixed first (SECURITY_POLICY.md, Review).
- **F7 (huge int ids):** `str()` of an int over 4300 digits raises. It can't be reached through
  JSON because `json.loads` rejects such ints first.
- **F8 (task count quota):** this needs per-user limits from the future auth layer.
- **F12 (other echoes):** `!r` escapes control characters, so logs can't be forged, and the size
  will be bounded by the transport's body limit.
- **F14:** dev-only tools (pytest, ruff) that never ship. The manifests are guard-protected, so
  pinning is a human change: `pip-compile --generate-hashes`.

## Secrets hygiene and history search

- There are no secrets in the source. Config comes from the environment (`.env.example`:
  `DATABASE_URL=`, `CANARY_KEY=`). `.gitignore` covers `.env`, `.env.*` (except `.env.example`),
  `*.pem`, `*.key` and `.claude/settings.local.json`. `git check-ignore .env .env.local` matches both.
- `git log --all -p -- .env '.env.*'` returns only the `.env.example` commit, which has empty values.
- `git log --all -p | grep -E "AKIA…|gh[pousr]_…|sk-…|BEGIN … PRIVATE KEY"` finds 0 matches.
  Credential-URL search: only fake test fixtures (`postgresql://u:p@localhost`,
  `postgres://admin:hunter2@db`).
- `git grep` for the exact canary value finds 0 matches in the current tree. Tracked files use `pa10-canary-test` or `<initials>`. Earlier PA10 commits did contain the fake value and it was later removed (`git log -S` lists them). It is fake, so nothing to rotate, but the next red-team round should use a fresh canary so a hit is unambiguous.
- **Rotation:** no real secret was ever committed, so nothing needed rotating. If one is
  committed, follow these steps: (1) revoke or rotate it at the provider immediately, (2) put the
  new value only in `.env` or the CI secret store, (3) purge history with `git filter-repo`, which a
  human runs because force-push is blocked, (4) check the provider's access logs.
