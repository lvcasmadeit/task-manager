import pytest

from services import users
from utils.errors import NotFoundError, ValidationError


def test_get_user_ok():
    assert users.get_user(1)["name"] == "Ada"


def test_get_user_missing():
    with pytest.raises(NotFoundError):
        users.get_user(999)


def test_get_user_invalid():
    with pytest.raises(ValidationError):
        users.get_user(-1)
