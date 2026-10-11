"""In-memory user storage."""

_USERS: dict[int, dict] = {
    1: {"id": 1, "name": "Ada", "email": "ada@example.com", "notification_pref": None}
}


def find_by_id(user_id: int) -> dict | None:
    """Return the user row for user_id, or None if absent."""
    return _USERS.get(user_id)


def find_all() -> list[dict]:
    """Return all user rows.

    Returns:
        A list of every stored user row, in insertion order.
    """
    return list(_USERS.values())


def set_notification_pref(user_id: int, pref: str) -> dict | None:
    """Store a notification preference on a user, replacing the row.

    Args:
        user_id: The id of the user to update.
        pref: The notification preference to store.

    Returns:
        The new user row, or None if the user is absent.
    """
    row = _USERS.get(user_id)
    if row is None:
        return None
    new_row = {**row, "notification_pref": pref}
    _USERS[user_id] = new_row
    return new_row
