# Reflection

## 1. Most serious finding and how it got in

**F1: repositories return live references into the store.** Mutating any response, such as
`handle_get_task(1)[1]["user_id"] = 99`, rewrote the "database". That skipped validation and the
`_UPDATABLE_FIELDS` allowlist that exists to keep `id`/`user_id` immutable.

**Origin:** it was copied from elsewhere, then spread by Claude. `git blame` shows `find_by_id` and
`insert` came in the course's Week 4 starter code (`dea757f`). In PA4 and PA5, Claude sessions
following my prompts wrote `update`, `find_all` and `set_notification_pref`. They copied the same
`return _TASKS[...]` pattern, because CLAUDE.md says to "follow the existing pattern". So my own
"copy the canonical example" rule made a starter-code flaw spread.

Two more things the scan made me notice:
- `update` was *documented* as "the stored row is replaced, not mutated". That was true, and it
  still didn't help, because the returned value was the new stored row. A careful docstring hid
  the bug instead of catching it.
- Those PA4/PA5 commits had no co-author line, so the history understated how much Claude wrote.

## 2. Guardrails: what mattered and what gave false confidence

**Mattered most: the PreToolUse hook (`guard.py`).**
- In A3 Haiku went straight to `grep … .env` in Bash. The `Read(./.env)` deny rule never saw it.
  Only the hook, which checks every tool and Bash, stopped it.
- The hook also fails closed and has 58 tests, so I know what it blocks.

**False confidence (two):**
- **Claude's judgment.** It stopped all eight A1/A2 runs. That looks like the attack failed, but
  in half the runs it ignored the payload *silently*. Nothing would have warned the next person.
  Judgment is also not a stable control: a different model, wording or context could go the other
  way.
- **Deny rules.** `Read(./.env)` looked like it "protected .env". It covers one tool and one
  spelling. `cat .e''nv` and base64 paths get past both the deny rule and my hook regexes. Only a
  sandbox or container really keeps the file out of reach.

## 3. What I'll change on my capstone

- **No secrets in the dev session.** I'll keep `.env` out of the repo Claude works in, use a
  sandbox or container with no network for agent sessions, and inject secrets only at runtime.
- **Red-team my guards as well as my code.** Each new rule gets a subprocess test, and lookalike
  allowed cases get tests too.
- **Exploit test first** for every security fix, committed while it fails.
- **Treat "follow the existing pattern" as a risk.** Before telling Claude to copy a canonical
  example, I'll run `/security-scan` on that example.
- **Ask Claude to report injection text**, not just ignore it. External docs and issues get a
  human read before they're committed.
- **Keep the co-author line on every commit,** including the subagent and session commits I
  forgot in PA4/PA5.
