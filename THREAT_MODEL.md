# Threat Model: task-manager

In-memory Python task tracker. Layers: `routes/` → `services/` → `repositories/`. It has no
HTTP server yet; `routes/*.handle_*` are the entry points a future web layer will call.

## Assets

| Asset | Where | Why it matters |
|---|---|---|
| Task and user store | `repositories/tasks.py::_TASKS`, `repositories/users.py::_USERS` | Stands in for the database. If it changes, ownership (`user_id`) and data integrity are lost |
| User PII (name, email, notification pref) | `_USERS` | Privacy. Emails can be harvested |
| Secrets | untracked `.env` (`CANARY_KEY` now, `DATABASE_URL` later) | Leaking one gives access to infrastructure |
| Guardrails | `.claude/settings.json`, `.claude/hooks/*.py` | If Claude edits them, every other control is off |
| Security tests | `tests/test_security.py` | If a fix weakens them, it can hide a regression |
| Git history / GitHub repo | `.git`, `origin` | A pushed secret stays public. History can be rewritten (force-push) |

## Untrusted inputs

**App (reaches the code):**
- `routes/tasks.py`: `handle_create_task(body)`, `handle_update_task(task_id, body)`,
  `handle_get_task(task_id)`, `handle_list_tasks(priority)` (query-string value).
- `routes/users.py`: `handle_get_user(user_id)`, `handle_get_notifications(user_id)`,
  `handle_update_notifications(user_id, body)`.
- Every value is caller-controlled: type, size and identity (there is no authentication).

**Agent (reaches Claude):**
- Seed/fixture data in `repositories/*.py`, which teammates edit (titles, names).
- Docs and bug reports from other people (`docs/`, pasted GitHub issue text, PR descriptions).
- Code from other people: vendored files, PR diffs, the output of `pip install`.
- Web pages (WebFetch/WebSearch) and MCP servers connected to the account (Supabase, Vercel,
  Slack, Notion, Docs). Their tool results are untrusted text.
- Test output and tracebacks, which echo input data.

## Ways out

- Network from Bash: `curl`, `wget`, `nc`, `ssh`/`scp`, `python -c "urllib..."`, `pip install <url>`.
- Claude tools: WebFetch (a URL with data in its query string), WebSearch.
- MCP tools that write or send: Slack post, Notion/Docs create, Supabase `execute_sql`, Vercel deploy.
- `git commit` + `git push`, `gh issue/pr comment` (public text).
- Files that are later shared: committed docs, test fixtures, logs, error messages returned to clients.

## Lethal trifecta check

**Yes, one exists:** an ordinary Claude Code session in this repo that is asked to *"triage this
GitHub issue / teammate doc and fix it"*.

- **Private data:** Claude can `Read` the untracked `.env` (canary / `DATABASE_URL`). By default
  Read inside the project needs no permission.
- **Untrusted content:** the issue text, the doc or the seed data it is told to read.
- **Way out:** Bash `curl`, WebFetch, `git push`/`gh` and account-level MCP tools (Slack, Notion,
  Docs) are all available in the session.

All three meet in one context. Task 3 breaks the chain: deny rules and the hook block reading
`.env*`, network tools and pushes, and the hook blocks writing the canary into any file. The
cleanest way to stop it is not to have the private data in the session at all (Task 3f).
