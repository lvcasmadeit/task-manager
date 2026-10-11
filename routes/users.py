"""HTTP-style handlers for users. Routes only translate; no business logic here."""

from services import notifications as notification_service
from services import users as user_service
from utils.errors import AppError


def handle_list_users() -> tuple[int, dict]:
    """Return (status_code, body) for a list-users request.

    Returns:
        (200, {"users": [...]}) on success, otherwise
        (error status, {"error": message}).
    """
    try:
        return 200, {"users": user_service.list_users()}
    except AppError as exc:
        return exc.status_code, {"error": exc.message}


def handle_get_user(user_id: int) -> tuple[int, dict]:
    """Return (status_code, body) for a get-user request.

    Args:
        user_id: Id of the user to fetch.

    Returns:
        (200, user) on success, otherwise (error status, {"error": message}).
    """
    try:
        return 200, user_service.get_user(user_id)
    except AppError as exc:
        return exc.status_code, {"error": exc.message}


def handle_get_notifications(user_id: int) -> tuple[int, dict]:
    """Return (status_code, body) for a get-notification-preference request.

    Args:
        user_id: Id of the user whose preference is requested.

    Returns:
        (200, {"user_id": ..., "notification_pref": ...}) on success,
        otherwise (error status, {"error": message}).
    """
    try:
        return 200, notification_service.get_notification_pref(user_id)
    except AppError as exc:
        return exc.status_code, {"error": exc.message}


def handle_update_notifications(user_id: int, body: dict) -> tuple[int, dict]:
    """Return (status_code, body) for an update-notification-preference request.

    Args:
        user_id: Id of the user whose preference is updated.
        body: Request body with "notification_pref".

    Returns:
        (200, {"user_id": ..., "notification_pref": ...}) on success,
        otherwise (error status, {"error": message}).
    """
    try:
        pref = notification_service.set_notification_pref(
            user_id, body.get("notification_pref")
        )
        return 200, pref
    except AppError as exc:
        return exc.status_code, {"error": exc.message}
