import pytest

from services import tasks
from utils.errors import NotFoundError, ValidationError


def test_create_task_unknown_user():
    with pytest.raises(NotFoundError):
        tasks.create_task(999, "x")


def test_create_task_blank_title():
    with pytest.raises(ValidationError):
        tasks.create_task(1, "   ")


def test_create_task_invalid_user_id():
    with pytest.raises(ValidationError):
        tasks.create_task(-5, "x")


def test_get_task_missing():
    with pytest.raises(NotFoundError):
        tasks.get_task(999)


def test_get_task_invalid():
    with pytest.raises(ValidationError):
        tasks.get_task(0)


def test_get_task_ok():
    assert tasks.get_task(1)["title"] == "Write CLAUDE.md"


def test_create_task():
    task = tasks.create_task(1, "New")
    assert task["done"] is False and task["id"] >= 3


def test_get_tasks_for_user_ok():
    result = tasks.get_tasks_for_user(1)
    assert result and all(t["user_id"] == 1 for t in result)


def test_get_tasks_for_user_unknown():
    with pytest.raises(NotFoundError):
        tasks.get_tasks_for_user(999)


def test_get_tasks_for_user_invalid():
    with pytest.raises(ValidationError):
        tasks.get_tasks_for_user(0)
