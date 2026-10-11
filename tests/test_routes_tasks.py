import pytest

from routes.tasks import (
    handle_create_task,
    handle_get_task,
    handle_list_tasks,
    handle_update_task,
)


def _create(**overrides) -> dict:
    body = {"user_id": 1, "title": "Route task"}
    body.update(overrides)
    status, task = handle_create_task(body)
    assert status == 201
    return task


def test_create_without_priority_defaults_to_3():
    status, task = handle_create_task({"user_id": 1, "title": "No priority"})
    assert status == 201
    assert task["priority"] == 3


@pytest.mark.parametrize("priority", [1, 5])
def test_create_valid_priority(priority):
    status, task = handle_create_task(
        {"user_id": 1, "title": "P", "priority": priority}
    )
    assert status == 201
    assert task["priority"] == priority


@pytest.mark.parametrize("priority", [0, 6, "3", 3.0, True, None])
def test_create_invalid_priority(priority):
    status, body = handle_create_task(
        {"user_id": 1, "title": "P", "priority": priority}
    )
    assert status == 400
    assert "error" in body


@pytest.mark.parametrize("body", [{"user_id": 1, "title": "   "}, {"user_id": 1}])
def test_create_blank_or_missing_title(body):
    status, resp = handle_create_task(body)
    assert status == 400
    assert "error" in resp


def test_create_unknown_user():
    status, body = handle_create_task({"user_id": 999, "title": "x"})
    assert status == 404
    assert "error" in body


def test_get_after_create_matches():
    task = _create(title="Roundtrip", priority=2)
    status, fetched = handle_get_task(task["id"])
    assert status == 200
    assert fetched == task


def test_update_priority_only():
    task = _create(title="Keep title", priority=3)
    status, updated = handle_update_task(task["id"], {"priority": 1})
    assert status == 200
    assert updated["priority"] == 1
    assert updated["title"] == "Keep title"
    assert updated["done"] is False


def test_update_title_and_done():
    task = _create(priority=4)
    status, updated = handle_update_task(task["id"], {"title": "Renamed", "done": True})
    assert status == 200
    assert updated["title"] == "Renamed"
    assert updated["done"] is True
    assert updated["priority"] == 4


def test_update_empty_body_unchanged():
    task = _create()
    status, updated = handle_update_task(task["id"], {})
    assert status == 200
    assert updated == task


def test_update_invalid_priority_no_partial_write():
    task = _create(title="Original")
    status, body = handle_update_task(task["id"], {"title": "Changed", "priority": 9})
    assert status == 400
    assert "error" in body
    _, fetched = handle_get_task(task["id"])
    assert fetched == task


def test_update_missing_task():
    status, body = handle_update_task(999, {"title": "x"})
    assert status == 404
    assert "error" in body


def test_update_invalid_task_id():
    status, body = handle_update_task(0, {"title": "x"})
    assert status == 400
    assert "error" in body


def test_update_ignores_id_and_user_id_in_body():
    task = _create()
    status, updated = handle_update_task(
        task["id"], {"id": 1, "user_id": 2, "priority": 2}
    )
    assert status == 200
    assert updated["id"] == task["id"]
    assert updated["user_id"] == task["user_id"]
    assert updated["priority"] == 2


def test_list_unfiltered_includes_seed_tasks():
    status, body = handle_list_tasks()
    assert status == 200
    ids = {t["id"] for t in body["tasks"]}
    assert {1, 2} <= ids


def test_list_string_filter_equals_int_filter():
    _, as_str = handle_list_tasks("1")
    _, as_int = handle_list_tasks(1)
    assert as_str == as_int


def test_list_filter_excludes_other_priorities():
    task = _create(priority=5)
    status, in_five = handle_list_tasks("5")
    assert status == 200
    assert task["id"] in {t["id"] for t in in_five["tasks"]}
    status, in_four = handle_list_tasks("4")
    assert status == 200
    assert task["id"] not in {t["id"] for t in in_four["tasks"]}


@pytest.mark.parametrize("priority", ["abc", "", "0", "6", "3.0"])
def test_list_invalid_priority(priority):
    status, body = handle_list_tasks(priority)
    assert status == 400
    assert "error" in body


def test_list_every_task_has_priority():
    _, body = handle_list_tasks()
    assert all("priority" in t for t in body["tasks"])
