from repositories import tasks as task_repo
from repositories import users as user_repo
from utils.errors import NotFoundError, ValidationError


def get_task(task_id: int) -> dict:
    """Fetch a task by id.

    Args:
        task_id: Positive integer id of the task.

    Returns:
        The task as a dict.

    Raises:
        ValidationError: If task_id is not a positive integer.
        NotFoundError: If no task has that id.
    """
    if not isinstance(task_id, int) or task_id <= 0:
        raise ValidationError(f"Invalid task id: {task_id!r}")
    task = task_repo.find_by_id(task_id)
    if task is None:
        raise NotFoundError(f"Task {task_id} not found")
    return task


def _validate_priority(priority: int) -> int:
    """Validate a task priority.

    Args:
        priority: Integer priority from 1 (highest) to 5 (lowest).

    Returns:
        The validated priority.

    Raises:
        ValidationError: If priority is not an int (bool excluded) in 1-5.
    """
    if isinstance(priority, bool) or not isinstance(priority, int) or not 1 <= priority <= 5:
        raise ValidationError(f"Invalid priority: {priority!r}")
    return priority


def create_task(user_id: int, title: str, priority: int = 3) -> dict:
    """Create a task owned by an existing user.

    Args:
        user_id: Positive integer id of the owning user.
        title: Non-empty task title.
        priority: Integer priority from 1 to 5. Defaults to 3.

    Returns:
        The stored task as a dict, including its new id.

    Raises:
        ValidationError: If user_id is not a positive integer, title is blank,
            or priority is not an integer from 1 to 5.
        NotFoundError: If no user has that id.
    """
    if not isinstance(user_id, int) or user_id <= 0:
        raise ValidationError(f"Invalid user id: {user_id!r}")
    if not isinstance(title, str) or not title.strip():
        raise ValidationError("Task title must be a non-empty string")
    _validate_priority(priority)
    if user_repo.find_by_id(user_id) is None:
        raise NotFoundError(f"User {user_id} not found")
    return task_repo.insert(
        {"user_id": user_id, "title": title.strip(), "done": False, "priority": priority}
    )


def get_tasks_for_user(user_id: int) -> list[dict]:
    """Fetch all tasks owned by a user.

    Args:
        user_id: Positive integer id of the user.

    Returns:
        The user's tasks as a list of dicts; empty if they have none.

    Raises:
        ValidationError: If user_id is not a positive integer.
        NotFoundError: If no user has that id.
    """
    if not isinstance(user_id, int) or user_id <= 0:
        raise ValidationError(f"Invalid user id: {user_id!r}")
    if user_repo.find_by_id(user_id) is None:
        raise NotFoundError(f"User {user_id} not found")
    return task_repo.find_by_user_id(user_id)
