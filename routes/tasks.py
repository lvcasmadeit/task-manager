"""HTTP-style handlers for tasks. Routes only translate; no business logic here."""

from services import tasks as task_service
from utils.errors import AppError


def handle_get_task(task_id: int) -> tuple[int, dict]:
    """Return (status_code, body) for a get-task request."""
    try:
        return 200, task_service.get_task(task_id)
    except AppError as exc:
        return exc.status_code, {"error": exc.message}
