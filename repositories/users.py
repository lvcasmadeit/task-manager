"""In-memory user storage."""

_USERS: dict[int, dict] = {
    1: {"id": 1, "name": "Ada", "email": "ada@example.com", "notification_pref": None}
}


def _row(user_id: int) -> dict | None:
    """Return the stored row for user_id; non-int ids (including bool) miss."""
    if type(user_id) is not int:
        return None
    return _USERS.get(user_id)


def find_by_id(user_id: int) -> dict | None:
    """Return a copy of the user row for user_id, or None if absent."""
    row = _row(user_id)
    return None if row is None else dict(row)


def find_all() -> list[dict]:
    """Return all user rows.

    Returns:
        A list of every stored user row, in insertion order.
    """
    return [dict(u) for u in _USERS.values()]


def set_notification_pref(user_id: int, pref: str) -> dict | None:
    """Store a notification preference on a user, replacing the row.

    Args:
        user_id: The id of the user to update.
        pref: The notification preference to store.

    Returns:
        The new user row, or None if the user is absent.
    """
    row = _row(user_id)
    if row is None:
        return None
    _USERS[user_id] = {**row, "notification_pref": pref}
    return dict(_USERS[user_id])
