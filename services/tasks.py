from repositories import tasks as task_repo
from repositories import users as user_repo
from utils.errors import NotFoundError, ValidationError

MAX_TITLE_LEN = 200


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
    if (
        isinstance(priority, bool)
        or not isinstance(priority, int)
        or not 1 <= priority <= 5
    ):
        raise ValidationError(f"Invalid priority: {priority!r}")
    return priority


def _validate_title(title: str) -> str:
    """Validate a task title.

    Args:
        title: Candidate title.

    Returns:
        The stripped title.

    Raises:
        ValidationError: If title is not a non-blank string of at most
            MAX_TITLE_LEN characters.
    """
    if not isinstance(title, str) or not title.strip():
        raise ValidationError("Task title must be a non-empty string")
    if len(title) > MAX_TITLE_LEN:
        raise ValidationError(f"Task title must be at most {MAX_TITLE_LEN} characters")
    return title.strip()


def _require_body(body: dict) -> dict:
    """Return body if it is a dict, otherwise raise.

    Raises:
        ValidationError: If body is not a dict (e.g. None, a list or a string).
    """
    if not isinstance(body, dict):
        raise ValidationError("Request body must be a JSON object")
    return body


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
    _validate_title(title)
    _validate_priority(priority)
    if user_repo.find_by_id(user_id) is None:
        raise NotFoundError(f"User {user_id} not found")
    return task_repo.insert(
        {
            "user_id": user_id,
            "title": title.strip(),
            "done": False,
            "priority": priority,
        }
    )


def update_task(
    task_id: int,
    title: str | None = None,
    done: bool | None = None,
    priority: int | None = None,
) -> dict:
    """Update the title, done flag and/or priority of a task.

    Args:
        task_id: Positive integer id of the task.
        title: New non-blank title (stripped), or None to leave unchanged.
        done: New done flag, or None to leave unchanged.
        priority: New integer priority from 1 to 5, or None to leave unchanged.

    Returns:
        The updated task as a dict (unchanged if no field was provided).

    Raises:
        ValidationError: If task_id is not a positive integer, title is blank
            or not a string, done is not a bool, or priority is not an
            integer from 1 to 5.
        NotFoundError: If no task has that id.
    """
    if not isinstance(task_id, int) or task_id <= 0:
        raise ValidationError(f"Invalid task id: {task_id!r}")
    fields: dict = {}
    if title is not None:
        fields["title"] = _validate_title(title)
    if done is not None:
        if not isinstance(done, bool):
            raise ValidationError(f"Invalid done flag: {done!r}")
        fields["done"] = done
    if priority is not None:
        fields["priority"] = _validate_priority(priority)
    if not fields:
        task = task_repo.find_by_id(task_id)
    else:
        task = task_repo.update(task_id, fields)
    if task is None:
        raise NotFoundError(f"Task {task_id} not found")
    return task


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


def list_tasks(priority: int | str | None = None) -> list[dict]:
    """List tasks, optionally filtered by priority.

    Args:
        priority: Integer priority from 1 to 5, a string of digits (as
            received from a query string, converted with int()), or None for
            no filter. Defaults to None.

    Returns:
        The matching tasks as a list of dicts; empty if none match.

    Raises:
        ValidationError: If priority is a string that is not purely digits,
            or is not an integer from 1 to 5 (bool and float are rejected).
    """
    if priority is None:
        return task_repo.find_all()
    if isinstance(priority, str):
        if len(priority) > 3 or not (priority.isascii() and priority.isdigit()):
            raise ValidationError(f"Invalid priority: {priority[:20]!r}")
        priority = int(priority)
    _validate_priority(priority)
    return task_repo.find_all(priority)


def create_task_from_body(body: dict) -> dict:
    """Create a task from a request body.

    Args:
        body: Mapping with "user_id", "title" and optional "priority".

    Returns:
        The stored task as a dict.

    Raises:
        ValidationError: If body is not a dict or any field is invalid.
        NotFoundError: If no user has that id.
    """
    body = _require_body(body)
    if "priority" in body:
        return create_task(body.get("user_id"), body.get("title"), body["priority"])
    return create_task(body.get("user_id"), body.get("title"))


def update_task_from_body(task_id: int, body: dict) -> dict:
    """Update a task from a request body.

    Args:
        task_id: Id of the task to update.
        body: Mapping with optional "title", "done" and "priority".

    Returns:
        The updated task as a dict.

    Raises:
        ValidationError: If body is not a dict or any field is invalid.
        NotFoundError: If no task has that id.
    """
    body = _require_body(body)
    return update_task(
        task_id,
        title=body.get("title"),
        done=body.get("done"),
        priority=body.get("priority"),
    )
