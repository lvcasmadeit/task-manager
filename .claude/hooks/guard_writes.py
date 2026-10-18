#!/usr/bin/env python3
"""PreToolUse hook for task-manager.

Claude Code pipes the pending tool call to stdin as JSON. Exit 0 allows it;
exit 2 blocks it and feeds stderr back to Claude. Three guards:

1. Path guard (Write/Edit/MultiEdit): no writes to BLOCKED_PATHS.
2. Content guard (Write/Edit/MultiEdit): files in CONTENT_GUARDED_PATHS may not
   receive a hardcoded database connection string.
3. Bash guard: destructive command patterns, and shell writes to BLOCKED_PATHS.

To add a rule: append to BLOCKED_PATHS (path), BASH_PATTERNS (command regex)
or CONTENT_GUARDED_PATHS, then add a case to tests/test_guard_writes.py.
"""

import json
import os
import re
import shlex
import sys
from pathlib import Path

PROJECT_ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()

# Project-relative, POSIX style, compared case-insensitively (macOS and Windows
# filesystems treat Utils/errors.py and utils/errors.py as the same file).
# A trailing "/" protects everything under that directory.
#
# Week 7 (MCP): mcp__<server>__<tool> calls also fire PreToolUse. Every rule
# below should apply to MCP tools that write files (e.g. a filesystem server's
# write_file / edit_file): match on tool_name startswith "mcp__" and read the
# path from tool_input["path"]. The Bash guard's patterns should apply to any
# MCP shell or database tool (execute_sql: DROP/TRUNCATE TABLE).
BLOCKED_PATHS = [
    "utils/errors.py",
    "services/users.py",
    "requirements.txt",
    "pyproject.toml",
    ".venv/",
]

# Files Claude may write, but whose new content is inspected.
CONTENT_GUARDED_PATHS = ["services/tasks.py"]

CONNECTION_STRING = re.compile(
    r"\b(?:postgres(?:ql)?(?:\+\w+)?://|sqlite(?:\+\w+)?:///)", re.IGNORECASE
)

# (name, regex) pairs matched against the whole Bash command. Word boundaries
# stop "drop table" matching inside e.g. "backdrop tablet".
BASH_PATTERNS = [
    (
        "destructive SQL (DROP/TRUNCATE TABLE)",
        re.compile(r"\b(?:drop|truncate)\s+table\b", re.IGNORECASE),
    ),
    (
        "git force-push",
        re.compile(
            r"\bgit\s+(?:-\S+\s+)*push\b[^;&|\n]*?"
            r"(?<=\s)(?:--force\S*|-[a-zA-Z]*f[a-zA-Z]*)(?=\s|$)"
        ),
    ),
]

# Verbs that write to a path appearing anywhere in the same command.
SHELL_WRITE = re.compile(
    r"(?:^|[\s;&|(])(?:sudo\s+)?(?:tee|cp|mv|dd|truncate|ln|rsync|patch|shred|rm)\s"
    r"|\bsed\s+(?:-\S*\s+)*(?:-\S*i\S*|--in-place)"
    r"|\bperl\s+(?:-\S*\s+)*-\S*i"
    r"|\bof="
    r"|\bgit\s+(?:checkout|restore|apply)\b"
    r"|\.write\(|write_text|write_bytes|\bshutil\.|os\.(?:replace|rename|remove|unlink)"
    r"|\bopen\([^)]*['\"][wax]\+?b?['\"]",
    re.IGNORECASE,
)


def rel_path(file_path: str) -> str:
    """Return file_path as a normalised, lower-cased project-relative POSIX path."""
    p = Path(file_path)
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    p = Path(os.path.normpath(p))
    try:
        rel = p.relative_to(PROJECT_ROOT)
    except ValueError:
        return p.as_posix().casefold()
    return rel.as_posix().casefold()


def is_blocked(rel: str, rules: list[str]) -> str | None:
    """Return the matching rule from rules, or None."""
    for rule in rules:
        r = rule.casefold()
        if r.endswith("/"):
            if rel.startswith(r) or rel == r.rstrip("/"):
                return rule
        elif rel == r:
            return rule
    return None


def new_content(tool_name: str, tool_input: dict) -> str:
    """Return all text a Write/Edit/MultiEdit call is about to put in the file."""
    if tool_name == "Write":
        return tool_input.get("content", "")
    if tool_name == "Edit":
        return tool_input.get("new_string", "")
    return "\n".join(e.get("new_string", "") for e in tool_input.get("edits", []))


def has_rm_rf(command: str) -> bool:
    """Token-level check for rm with both recursive and force flags."""
    for segment in re.split(r"[;&|\n]+", command):
        try:
            tokens = shlex.split(segment)
        except ValueError:
            tokens = segment.split()
        for i, tok in enumerate(tokens):
            if os.path.basename(tok) != "rm":
                continue
            flags = set()
            for arg in tokens[i + 1 :]:
                if arg.startswith("--"):
                    flags.add(arg[2:])
                elif arg.startswith("-") and len(arg) > 1:
                    flags.update(arg[1:])
            if flags & {"r", "R", "recursive"} and flags & {"f", "force"}:
                return True
    return False


def bash_write_target(command: str) -> str | None:
    """Return a BLOCKED_PATHS rule that the command appears to write to.

    Known gap: a path assembled at run time (``cd utils && echo x > errors.py``,
    variables, base64) never appears whole in the command text.
    """
    cmd = command.casefold().replace("\\", "/")
    for rule in BLOCKED_PATHS:
        r = re.escape(rule.casefold())
        redirect = re.search(rf">\|?\s*[\"']?(?:[^\s\"'<>|;&]*/)?{r}", cmd)
        mentioned = re.search(rf"(?<![\w.-]){r}", cmd)
        if redirect or (mentioned and SHELL_WRITE.search(cmd)):
            return rule
    return None


def check_bash(command: str) -> str | None:
    """Return a block reason for a Bash command, or None to allow it."""
    for name, pattern in BASH_PATTERNS:
        if pattern.search(command):
            return f"Bash command blocked: {name}."
    if has_rm_rf(command):
        return "Bash command blocked: rm -rf (recursive force delete)."
    rule = bash_write_target(command)
    if rule:
        return f"Bash command blocked: it writes to protected path {rule}."
    cmd = command.casefold()
    for guarded in CONTENT_GUARDED_PATHS:
        if guarded.casefold() in cmd and CONNECTION_STRING.search(command):
            return connection_string_message(guarded)
    return None


def connection_string_message(path: str) -> str:
    return (
        f"Hardcoded database connection string in {path}. Connection strings "
        "must come from environment variables (e.g. os.environ['DATABASE_URL'])."
    )


def check(event: dict) -> str | None:
    """Return a block reason for the tool call in event, or None to allow it."""
    tool = event.get("tool_name", "")
    tool_input = event.get("tool_input") or {}
    if tool == "Bash":
        return check_bash(tool_input.get("command", ""))
    if tool in ("Write", "Edit", "MultiEdit"):
        path = tool_input.get("file_path", "")
        rel = rel_path(path)
        rule = is_blocked(rel, BLOCKED_PATHS)
        if rule:
            return f"{rule} is protected and may not be edited (see guard_writes.py)."
        guarded = is_blocked(rel, CONTENT_GUARDED_PATHS)
        if guarded and CONNECTION_STRING.search(new_content(tool, tool_input)):
            return connection_string_message(guarded)
    return None


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"guard_writes.py: could not parse hook input: {exc}", file=sys.stderr)
        return 1
    reason = check(event)
    if reason:
        print(f"BLOCKED: {reason}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
