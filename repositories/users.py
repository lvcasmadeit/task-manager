"""In-memory user storage."""

_USERS: dict[int, dict] = {1: {"id": 1, "name": "Ada", "email": "ada@example.com"}}


def find_by_id(user_id: int) -> dict | None:
    """Return the user row for user_id, or None if absent."""
    return _USERS.get(user_id)
