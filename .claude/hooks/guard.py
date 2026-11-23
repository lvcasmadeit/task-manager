#!/usr/bin/env python3
"""PA10 PreToolUse guard for task-manager.

Claude Code pipes the pending tool call to stdin as JSON. Exit 0 allows it;
exit 2 blocks it and sends stderr (always starting "Blocked:") back to Claude.
Anything unexpected (bad JSON, wrong types, a crash) also exits 2: fail closed.

Generic checks: secret files, network / ways out, destructive commands.
Project rules:
  1. Guardrails and security tests are read-only for Claude (PROTECTED).
  2. Canary and secret-looking values may not be written anywhere.
  3. File-writing tools may not write outside the repository.

The older .claude/hooks/guard_writes.py (PA6) still runs alongside and protects
utils/errors.py, services/users.py and the manifests.
"""

import json
import os
import re
import shlex
import sys
from pathlib import Path

PROJECT_ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()

FILE_TOOLS = ("Read", "Write", "Edit", "MultiEdit", "NotebookEdit", "Grep", "Glob")
WRITE_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")

# --- secret files -----------------------------------------------------------
# .env and .env.<anything> except .env.example; key material.
SECRET_FILE = re.compile(
    r"(?<![\w.-])\.env(?:\.(?!example(?![\w.-]))[\w.-]+)?(?![\w.-])"
    r"|(?<![\w-])[\w.-]*\.(?:pem|key|p12)(?![\w.-])"
    r"|(?<![\w.-])id_(?:rsa|ed25519)\b",
    re.IGNORECASE,
)

# --- project rule 1: protected paths (project-relative, case-insensitive) ---
PROTECTED = [
    ".claude/settings.json",
    ".claude/settings.local.json",
    ".claude/hooks/",
    "tests/test_security.py",
    "tests/test_guard.py",
    "tests/test_guard_writes.py",
]

# --- project rule 2: values that must never be written ---------------------
SECRET_VALUE = re.compile(
    r"pa10-canary-"
    r"|CANARY_KEY[ \t]*=[ \t]*[^\s#]"
    r"|\bAKIA[0-9A-Z]{16}\b"
    r"|\bgh[pousr]_[A-Za-z0-9]{20,}"
    r"|\bsk-[A-Za-z0-9_-]{20,}"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----"
    r"|\b[a-z][\w+.-]*://[^\s/:@'\"]+:[^\s@'\"]+@",
    re.IGNORECASE,
)

# --- network ----------------------------------------------------------------
NETWORK_CMDS = {
    "curl", "wget", "nc", "ncat", "netcat", "socat", "telnet", "ssh", "scp",
    "sftp", "ftp", "rsync", "gh", "http", "https", "aria2c",
}
NETWORK_CODE = re.compile(
    r"/dev/(?:tcp|udp)/|\burllib\b|\brequests\b|\bhttpx\b|http\.(?:client|server)"
    r"|\bsocket\b|\burlopen\b|\bfetch\(",
    re.IGNORECASE,
)
GIT_NETWORK = re.compile(r"\bgit\s+(?:-\S+\s+)*(?:push|remote\s+(?:add|set-url))\b")
# MCP tools whose action name starts with one of these are treated as read-only.
MCP_READ_ONLY = re.compile(r"^(?:get|list|search|read|query|count|aggregate|guide)")

# --- destructive ------------------------------------------------------------
DESTRUCTIVE = [
    ("git reset --hard", re.compile(r"\bgit\s+reset\s+(?:\S+\s+)*--hard\b")),
    ("git clean -f", re.compile(r"\bgit\s+clean\s+(?:\S+\s+)*-\w*f")),
    ("find -delete", re.compile(r"\bfind\b[^;&|]*\s-(?:delete|exec\s+rm)\b")),
    ("shutil.rmtree", re.compile(r"\bshutil\.rmtree\b|\bos\.removedirs\b")),
    (
        "SQL DROP/TRUNCATE",
        re.compile(r"\b(?:drop|truncate)\s+(?:table|database)\b", re.IGNORECASE),
    ),
    ("disk wipe", re.compile(r"\bmkfs\b|\bdd\s+[^;&|]*of=/dev/")),
]

# Shell verbs that write to a path mentioned in the same command.
SHELL_WRITE = re.compile(
    r"(?:^|[\s;&|(])(?:sudo\s+)?(?:tee|cp|mv|dd|truncate|ln|rsync|patch|rm|chmod)\s"
    r"|\bsed\s+(?:-\S*\s+)*(?:-\S*i\S*|--in-place)|\bperl\s+(?:-\S*\s+)*-\S*i"
    r"|\bgit\s+(?:checkout|restore|apply)\b|\.write\(|write_text|write_bytes"
    r"|\bopen\([^)]*['\"][wax]\+?b?['\"]",
    re.IGNORECASE,
)

WRAPPERS = {
    "sudo", "env", "nohup", "time", "timeout", "command", "exec", "xargs", "nice",
}
SHELLS = {"bash", "sh", "zsh", "dash"}


class InvalidInput(Exception):
    """Raised when the hook input is not a well-formed PreToolUse event."""


def rel_path(file_path: str) -> str | None:
    """Return a lower-cased project-relative POSIX path, or None if outside."""
    p = Path(file_path).expanduser()
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    p = Path(os.path.normpath(p))
    try:
        return p.relative_to(PROJECT_ROOT).as_posix().casefold()
    except ValueError:
        return None


def protected_rule(rel: str) -> str | None:
    for rule in PROTECTED:
        r = rule.casefold()
        if rel == r or (r.endswith("/") and (rel.startswith(r) or rel == r[:-1])):
            return rule
    return None


def segments(command: str) -> list[list[str]]:
    """Split a command into simple commands, each a token list."""
    out = []
    for seg in re.split(r"[;&|\n]+|\$\(|`|\(|\)", command):
        try:
            tokens = shlex.split(seg)
        except ValueError:
            tokens = seg.split()
        if tokens:
            out.append(tokens)
    return out


def command_names(tokens: list[str]) -> list[str]:
    """Return the program name(s) a token list runs, skipping wrappers."""
    names: list[str] = []
    for tok in tokens:
        # Skip VAR=value prefixes and the options/durations of a wrapper.
        if "=" in tok or tok.startswith("-") or tok.replace(".", "").isdigit():
            continue
        base = os.path.basename(tok)
        names.append(base)
        if base not in WRAPPERS:
            break
    return names


def has_rm_rf(tokens: list[str]) -> bool:
    for i, tok in enumerate(tokens):
        if os.path.basename(tok) != "rm":
            continue
        flags: set[str] = set()
        for arg in tokens[i + 1 :]:
            if arg.startswith("--"):
                flags.add(arg[2:])
            elif arg.startswith("-") and len(arg) > 1:
                flags.update(arg[1:])
        if flags & {"r", "R", "recursive"} and flags & {"f", "force"}:
            return True
    return False


def check_bash(command: str, depth: int = 0) -> str | None:
    if SECRET_FILE.search(command):
        return "the command touches a secret file (.env, keys). Use .env.example."
    if SECRET_VALUE.search(command):
        return "the command contains the canary or a secret-looking value."
    if GIT_NETWORK.search(command):
        return "git push / remote changes are for humans only (SECURITY_POLICY.md)."
    if NETWORK_CODE.search(command):
        return "the command opens a network connection from code."
    for name, pattern in DESTRUCTIVE:
        if pattern.search(command):
            return f"destructive command ({name})."
    for tokens in segments(command):
        names = command_names(tokens)
        if any(n in NETWORK_CMDS for n in names):
            return f"network tool ({names[-1]}) is not allowed in this project."
        if has_rm_rf(tokens):
            return "destructive command (rm -rf)."
        if names and names[-1] in SHELLS and "-c" in tokens and depth < 3:
            inner = tokens[tokens.index("-c") + 1 :]
            reason = check_bash(" ".join(inner), depth + 1)
            if reason:
                return reason
    lowered = command.casefold().replace("\\", "/")
    for rule in PROTECTED:
        r = re.escape(rule.casefold())
        mentioned = re.search(rf"(?<![\w.-]){r}", lowered)
        redirect = re.search(rf">\|?\s*[\"']?(?:[^\s\"'<>|;&]*/)?{r}", lowered)
        if redirect or (mentioned and SHELL_WRITE.search(lowered)):
            return f"{rule} is a protected guardrail/security test (project rule 1)."
    return None


def written_text(tool: str, tool_input: dict) -> str:
    if tool == "Write":
        return str(tool_input.get("content", ""))
    if tool == "Edit":
        return str(tool_input.get("new_string", ""))
    if tool == "NotebookEdit":
        return str(tool_input.get("new_source", ""))
    edits = tool_input.get("edits") or []
    return "\n".join(str(e.get("new_string", "")) for e in edits if isinstance(e, dict))


def check_file_tool(tool: str, tool_input: dict) -> str | None:
    path = tool_input.get("file_path") or tool_input.get("notebook_path")
    path = path or tool_input.get("path") or ""
    if not isinstance(path, str):
        raise InvalidInput("file path is not a string")
    targets = [path, str(tool_input.get("pattern", "")) if tool == "Glob" else ""]
    targets.append(str(tool_input.get("glob", "")))
    if any(t and SECRET_FILE.search(t) for t in targets):
        return f"{path or 'that pattern'} is a secret file. Read .env.example instead."
    if tool not in WRITE_TOOLS:
        return None
    rel = rel_path(path)
    if rel is None:
        return f"{path} is outside the repository (project rule 3)."
    rule = protected_rule(rel)
    if rule:
        return f"{rule} is a protected guardrail/security test (project rule 1)."
    if SECRET_VALUE.search(written_text(tool, tool_input)):
        return "the new content contains the canary or a secret value (project rule 2)."
    return None


def check(event: object) -> str | None:
    if not isinstance(event, dict):
        raise InvalidInput("event is not an object")
    tool = event.get("tool_name")
    tool_input = event.get("tool_input")
    if not isinstance(tool, str) or not tool:
        raise InvalidInput("missing tool_name")
    if not isinstance(tool_input, dict):
        raise InvalidInput("tool_input is not an object")
    if tool == "Bash":
        command = tool_input.get("command")
        if not isinstance(command, str):
            raise InvalidInput("Bash command is not a string")
        return check_bash(command)
    if tool in FILE_TOOLS:
        return check_file_tool(tool, tool_input)
    if tool == "WebFetch":
        return "WebFetch is a way out for data; ask the user to fetch the page."
    if tool.startswith("mcp__"):
        action = tool.rsplit("__", 1)[-1]
        if not MCP_READ_ONLY.match(action):
            return f"MCP tool {tool} can write or send data; a human must run it."
        if SECRET_VALUE.search(json.dumps(tool_input)):
            return "the MCP call contains the canary or a secret value."
    return None


def main() -> int:
    try:
        reason = check(json.loads(sys.stdin.read()))
    except (json.JSONDecodeError, InvalidInput) as exc:
        reason = f"invalid hook input ({exc}); failing closed."
    except Exception as exc:  # noqa: BLE001 - any crash must block, not allow
        reason = f"guard.py error ({type(exc).__name__}); failing closed."
    if reason:
        print(f"Blocked: {reason}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
