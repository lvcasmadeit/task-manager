"""In-memory task storage."""

_TASKS: dict[int, dict] = {
    1: {"id": 1, "user_id": 1, "title": "Write CLAUDE.md", "done": False, "priority": 1},
    2: {"id": 2, "user_id": 1, "title": "Run pytest", "done": True, "priority": 3},
}


def find_by_id(task_id: int) -> dict | None:
    """Return the task row for task_id, or None if absent."""
    return _TASKS.get(task_id)


def find_by_user_id(user_id: int) -> list[dict]:
    """Return all task rows owned by user_id (possibly empty)."""
    return [t for t in _TASKS.values() if t["user_id"] == user_id]


def insert(task: dict) -> dict:
    """Store a task, assigning the next integer id, and return it."""
    task_id = max(_TASKS, default=0) + 1
    _TASKS[task_id] = {**task, "id": task_id}
    return _TASKS[task_id]
