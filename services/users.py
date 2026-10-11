"""User business logic. This is the style reference for all other services."""

from repositories import users as user_repo
from utils.errors import NotFoundError, ValidationError


def get_user(user_id: int) -> dict:
    """Fetch a user by id.

    Args:
        user_id: Positive integer id of the user.

    Returns:
        The user as a dict with id, name and email.

    Raises:
        ValidationError: If user_id is not a positive integer.
        NotFoundError: If no user has that id.
    """
    if not isinstance(user_id, int) or user_id <= 0:
        raise ValidationError(f"Invalid user id: {user_id!r}")
    user = user_repo.find_by_id(user_id)
    if user is None:
        raise NotFoundError(f"User {user_id} not found")
    return user
