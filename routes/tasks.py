"""HTTP-style handlers for tasks. Routes only translate; no business logic here."""

from services import tasks as task_service
from utils.errors import AppError


def handle_get_task(task_id: int) -> tuple[int, dict]:
    """Return (status_code, body) for a get-task request."""
    try:
        return 200, task_service.get_task(task_id)
    except AppError as exc:
        return exc.status_code, {"error": exc.message}


def handle_create_task(body: dict) -> tuple[int, dict]:
    """Return (status_code, body) for a create-task request.

    Args:
        body: Request body with "user_id", "title" and optional "priority".

    Returns:
        (201, task) on success, otherwise (error status, {"error": message}).
    """
    try:
        return 201, task_service.create_task_from_body(body)
    except AppError as exc:
        return exc.status_code, {"error": exc.message}


def handle_update_task(task_id: int, body: dict) -> tuple[int, dict]:
    """Return (status_code, body) for an update-task request.

    Args:
        task_id: Id of the task to update.
        body: Request body with optional "title", "done" and "priority".

    Returns:
        (200, task) on success, otherwise (error status, {"error": message}).
    """
    try:
        return 200, task_service.update_task_from_body(task_id, body)
    except AppError as exc:
        return exc.status_code, {"error": exc.message}


def handle_list_tasks(priority: str | int | None = None) -> tuple[int, dict]:
    """Return (status_code, body) for a list-tasks request.

    Args:
        priority: Optional priority filter, as an int or query-string digits.

    Returns:
        (200, {"tasks": [...]}) on success, otherwise
        (error status, {"error": message}).
    """
    try:
        return 200, {"tasks": task_service.list_tasks(priority)}
    except AppError as exc:
        return exc.status_code, {"error": exc.message}
