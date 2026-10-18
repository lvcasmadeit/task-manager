"""Tests for .claude/hooks/guard_writes.py, run the way Claude Code runs it."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / ".claude" / "hooks" / "guard_writes.py"


def run_hook(tool_name: str, tool_input: dict) -> subprocess.CompletedProcess:
    """Pipe a PreToolUse event into the hook and return the finished process."""
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps({"tool_name": tool_name, "tool_input": tool_input}),
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(ROOT)},
    )


def bash(command: str) -> subprocess.CompletedProcess:
    return run_hook("Bash", {"command": command})


@pytest.mark.parametrize(
    "tool, path",
    [
        ("Write", "utils/errors.py"),
        ("Write", "Utils/errors.py"),  # vector 1: case
        ("Edit", "UTILS/ERRORS.PY"),
        ("Edit", str(ROOT / "Utils" / "errors.py")),
        ("MultiEdit", "services/users.py"),
        ("Write", "./pyproject.toml"),
        ("Write", ".venv/lib/site.py"),
        ("Write", "services/../utils/errors.py"),
    ],
)
def test_path_guard_blocks(tool, path):
    result = run_hook(tool, {"file_path": path, "content": "x", "new_string": "x"})
    assert result.returncode == 2
    assert "BLOCKED" in result.stderr


@pytest.mark.parametrize(
    "path", ["routes/users.py", "services/tasks.py", "utils/errors_extra.py"]
)
def test_path_guard_allows(path):
    assert run_hook("Write", {"file_path": path, "content": "x"}).returncode == 0


@pytest.mark.parametrize(
    "command",
    [
        "printf x > utils/errors.py",  # vector 2: bash indirect write
        "cat <<EOF > ./Utils/Errors.py\nhi\nEOF",
        'echo x >> "utils/errors.py"',
        "tee services/users.py <<< hi",
        "sed -i '' s/a/b/ pyproject.toml",
        "python3 -c \"open('services/users.py','w').write('x')\"",
        "mv /tmp/x.py utils/errors.py",
    ],
)
def test_bash_path_write_blocked(command):
    assert bash(command).returncode == 2


@pytest.mark.parametrize(
    "command",
    [
        "cat utils/errors.py",
        ".venv/bin/pytest -q 2>&1 | tail -3",
        "grep -n users services/users.py",
        "echo hi > tests/test_new.py",
        ".venv/bin/pip install -r requirements.txt",
    ],
)
def test_bash_reads_and_unrelated_writes_allowed(command):
    assert bash(command).returncode == 0


@pytest.mark.parametrize(
    "command",
    [
        'psql -c "DROP TABLE tasks"',
        "psql -c 'truncate   table users;'",
        "rm -rf build",
        "rm -fr build",
        "rm -r -f build",
        "sudo rm --recursive --force build",
        "git push --force origin main",
        "git push -f",
        "git push origin main --force-with-lease",
    ],
)
def test_bash_destructive_patterns_blocked(command):
    assert bash(command).returncode == 2


@pytest.mark.parametrize(
    "command",
    [
        "rm tmp.txt",
        "rm -r build",
        "echo backdrop tablet",
        "git push -u origin main",
        "git push origin main --follow-tags",
        "grep -rf patterns.txt .",
    ],
)
def test_bash_near_misses_allowed(command):
    assert bash(command).returncode == 0


@pytest.mark.parametrize(
    "content",
    [
        'DB = "postgresql://u:p@localhost/tasks"',
        "DB = 'sqlite:///tasks.db'",
        'DB = "postgresql+psycopg://u@h/db"',
    ],
)
def test_content_guard_blocks_connection_strings(content):
    for tool, tool_input in [
        ("Write", {"file_path": "services/tasks.py", "content": content}),
        ("Edit", {"file_path": "services/tasks.py", "new_string": content}),
        (
            "MultiEdit",
            {"file_path": "services/tasks.py", "edits": [{"new_string": content}]},
        ),
    ]:
        result = run_hook(tool, tool_input)
        assert result.returncode == 2
        assert "environment variables" in result.stderr


def test_content_guard_allows_env_lookup_and_other_files():
    env_lookup = 'DB = os.environ["DATABASE_URL"]'
    assert (
        run_hook(
            "Write", {"file_path": "services/tasks.py", "content": env_lookup}
        ).returncode
        == 0
    )
    # The content guard covers only the files named in CONTENT_GUARDED_PATHS.
    sqlite = "DB = 'sqlite:///x.db'"
    assert (
        run_hook("Write", {"file_path": "notes.md", "content": sqlite}).returncode == 0
    )


def test_other_tools_and_bad_input():
    assert run_hook("Read", {"file_path": "utils/errors.py"}).returncode == 0
    broken = subprocess.run(
        [sys.executable, str(HOOK)],
        input="not json",
        capture_output=True,
        text=True,
        check=False,
    )
    assert broken.returncode == 1


@pytest.mark.xfail(
    strict=True,
    reason="Known gap (HOOK_LOG.md): a path split by cd never appears whole.",
)
def test_bash_cd_then_relative_write_blocked():
    assert bash("cd utils && echo x > errors.py").returncode == 2
