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


def test_create_task_default_priority():
    assert tasks.create_task(1, "Default priority")["priority"] == 3


@pytest.mark.parametrize("priority", [1, 5])
def test_create_task_explicit_priority(priority):
    assert tasks.create_task(1, "Explicit priority", priority)["priority"] == priority


@pytest.mark.parametrize("priority", [0, 6, -1])
def test_create_task_priority_out_of_range(priority):
    with pytest.raises(ValidationError):
        tasks.create_task(1, "x", priority)


@pytest.mark.parametrize("priority", ["3", 3.0, None, True])
def test_create_task_priority_wrong_type(priority):
    with pytest.raises(ValidationError):
        tasks.create_task(1, "x", priority)


@pytest.mark.parametrize("task_id", [1, 2])
def test_seed_tasks_have_valid_priority(task_id):
    priority = tasks.get_task(task_id)["priority"]
    assert isinstance(priority, int) and 1 <= priority <= 5


def test_update_task_title_stripped():
    task = tasks.create_task(1, "Old")
    assert tasks.update_task(task["id"], title="  New title  ")["title"] == "New title"


def test_update_task_done():
    task = tasks.create_task(1, "Finish me")
    assert tasks.update_task(task["id"], done=True)["done"] is True
    assert tasks.get_task(task["id"])["done"] is True


@pytest.mark.parametrize("priority", [1, 5])
def test_update_task_priority(priority):
    task = tasks.create_task(1, "Reprioritise")
    assert tasks.update_task(task["id"], priority=priority)["priority"] == priority


def test_update_task_all_fields():
    task = tasks.create_task(1, "Before")
    result = tasks.update_task(task["id"], title=" After ", done=True, priority=2)
    assert result["title"] == "After"
    assert result["done"] is True
    assert result["priority"] == 2
    assert tasks.get_task(task["id"]) == result


def test_update_task_preserves_id_and_user_id():
    task = tasks.create_task(1, "Keep identity")
    result = tasks.update_task(task["id"], title="Renamed", done=True, priority=4)
    assert result["id"] == task["id"]
    assert result["user_id"] == 1


@pytest.mark.parametrize("priority", [0, 6, -1])
def test_update_task_priority_out_of_range(priority):
    task = tasks.create_task(1, "Range")
    with pytest.raises(ValidationError):
        tasks.update_task(task["id"], priority=priority)


@pytest.mark.parametrize("priority", ["3", 3.0, True])
def test_update_task_priority_wrong_type(priority):
    task = tasks.create_task(1, "Type")
    with pytest.raises(ValidationError):
        tasks.update_task(task["id"], priority=priority)


@pytest.mark.parametrize("title", ["", "   "])
def test_update_task_blank_title(title):
    task = tasks.create_task(1, "Not blank")
    with pytest.raises(ValidationError):
        tasks.update_task(task["id"], title=title)


@pytest.mark.parametrize("done", ["yes", 1, 0])
def test_update_task_done_not_bool(done):
    task = tasks.create_task(1, "Done type")
    with pytest.raises(ValidationError):
        tasks.update_task(task["id"], done=done)


@pytest.mark.parametrize("task_id", [0, -1])
def test_update_task_invalid_id(task_id):
    with pytest.raises(ValidationError):
        tasks.update_task(task_id, title="x")


def test_update_task_missing():
    with pytest.raises(NotFoundError):
        tasks.update_task(999, title="x")


def test_update_task_no_fields_missing_task():
    with pytest.raises(NotFoundError):
        tasks.update_task(999)


def test_update_task_no_fields_unchanged():
    task = tasks.create_task(1, "Untouched")
    snapshot = dict(task)
    assert tasks.update_task(task["id"]) == snapshot
    assert tasks.get_task(task["id"]) == snapshot


def test_update_task_invalid_priority_no_partial_write():
    task = tasks.create_task(1, "Original")
    with pytest.raises(ValidationError):
        tasks.update_task(task["id"], title="Changed", priority=9)
    assert tasks.get_task(task["id"])["title"] == "Original"
