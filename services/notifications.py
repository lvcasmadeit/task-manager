"""Notification preference business logic."""

from repositories import users as user_repo
from utils.errors import NotFoundError, ValidationError

VALID_PREFS: tuple[str, ...] = ("email", "sms", "none")


def _validate_user_id(user_id: int) -> None:
    """Ensure user_id is a positive integer (bool is rejected).

    Args:
        user_id: The value to validate.

    Raises:
        ValidationError: If user_id is not a positive, non-bool integer.
    """
    if isinstance(user_id, bool) or not isinstance(user_id, int) or user_id <= 0:
        raise ValidationError(f"Invalid user id: {user_id!r}")


def get_notification_pref(user_id: int) -> dict:
    """Fetch a user's notification preference.

    Args:
        user_id: Positive integer id of the user.

    Returns:
        A dict with user_id and notification_pref. A user with no stored
        preference reports "none".

    Raises:
        ValidationError: If user_id is not a positive integer.
        NotFoundError: If no user has that id.
    """
    _validate_user_id(user_id)
    user = user_repo.find_by_id(user_id)
    if user is None:
        raise NotFoundError(f"User {user_id} not found")
    pref = user.get("notification_pref")
    return {"user_id": user_id, "notification_pref": "none" if pref is None else pref}


def set_notification_pref(user_id: int, pref: str) -> dict:
    """Set a user's notification preference.

    Args:
        user_id: Positive integer id of the user.
        pref: One of "email", "sms" or "none" (case-sensitive).

    Returns:
        A dict with user_id and the stored notification_pref.

    Raises:
        ValidationError: If user_id is not a positive integer or pref is not
            one of the valid preferences.
        NotFoundError: If no user has that id.
    """
    _validate_user_id(user_id)
    if not isinstance(pref, str) or pref not in VALID_PREFS:
        raise ValidationError(f"Invalid notification preference: {pref!r}")
    user = user_repo.set_notification_pref(user_id, pref)
    if user is None:
        raise NotFoundError(f"User {user_id} not found")
    return {"user_id": user_id, "notification_pref": user["notification_pref"]}
