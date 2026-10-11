"""In-memory task storage."""

_UPDATABLE_FIELDS = frozenset({"title", "done", "priority"})

_TASKS: dict[int, dict] = {
    1: {
        "id": 1,
        "user_id": 1,
        "title": "Write CLAUDE.md",
        "done": False,
        "priority": 1,
    },
    2: {"id": 2, "user_id": 1, "title": "Run pytest", "done": True, "priority": 3},
}


def find_by_id(task_id: int) -> dict | None:
    """Return the task row for task_id, or None if absent."""
    return _TASKS.get(task_id)


def find_by_user_id(user_id: int) -> list[dict]:
    """Return all task rows owned by user_id (possibly empty)."""
    return [t for t in _TASKS.values() if t["user_id"] == user_id]


def find_all(priority: int | None = None) -> list[dict]:
    """Return all task rows, optionally filtered by priority.

    Args:
        priority: If given, only rows whose priority equals this value are
            returned. If None, every row is returned.

    Returns:
        The matching task rows (possibly empty). Never raises.
    """
    return [t for t in _TASKS.values() if priority is None or t["priority"] == priority]


def insert(task: dict) -> dict:
    """Store a task, assigning the next integer id, and return it."""
    task_id = max(_TASKS, default=0) + 1
    _TASKS[task_id] = {**task, "id": task_id}
    return _TASKS[task_id]


def update(task_id: int, fields: dict) -> dict | None:
    """Update the mutable fields of a stored task.

    Only title, done and priority are applied; any other key (including id and
    user_id) is silently ignored. The stored row is replaced, not mutated.

    Args:
        task_id: Id of the task to update.
        fields: Mapping of field names to new values.

    Returns:
        The updated task row, or None if no task has that id.
    """
    row = _TASKS.get(task_id)
    if row is None:
        return None
    allowed = {k: v for k, v in fields.items() if k in _UPDATABLE_FIELDS}
    _TASKS[task_id] = {**row, **allowed}
    return _TASKS[task_id]
