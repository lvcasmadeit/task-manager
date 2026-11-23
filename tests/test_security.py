"""PA10 exploit tests. Each test passes only when the attack it describes fails.

Finding ids (F#) refer to SECURITY_FINDINGS.md.
"""

import copy

import pytest

from repositories import tasks as task_repo
from repositories import users as user_repo
from routes.tasks import (
    handle_create_task,
    handle_get_task,
    handle_list_tasks,
    handle_update_task,
)
from routes.users import (
    handle_get_user,
    handle_list_users,
    handle_update_notifications,
)


@pytest.fixture(autouse=True)
def restore_store():
    """Snapshot both stores so a successful attack cannot leak into other tests."""
    tasks_before = copy.deepcopy(task_repo._TASKS)
    users_before = copy.deepcopy(user_repo._USERS)
    yield
    task_repo._TASKS.clear()
    task_repo._TASKS.update(tasks_before)
    user_repo._USERS.clear()
    user_repo._USERS.update(users_before)


def _new_task() -> dict:
    status, task = handle_create_task({"user_id": 1, "title": "victim"})
    assert status == 201
    return task


# F1 (High): responses are live references into the store.


def test_f1_mutating_get_response_cannot_change_owner():
    task = _new_task()
    _, body = handle_get_task(task["id"])
    body["user_id"] = 999  # attacker-controlled serializer / middleware
    assert handle_get_task(task["id"])[1]["user_id"] == 1


def test_f1_mutating_create_response_cannot_change_store():
    _, created = handle_create_task({"user_id": 1, "title": "x"})
    created["done"] = "not-a-bool"
    assert handle_get_task(created["id"])[1]["done"] is False


def test_f1_mutating_update_response_cannot_change_id():
    task = _new_task()
    _, updated = handle_update_task(task["id"], {"title": "y"})
    updated["user_id"] = 999
    assert handle_get_task(task["id"])[1]["user_id"] == 1


def test_f1_mutating_list_response_cannot_change_store():
    _new_task()
    _, body = handle_list_tasks()
    for t in body["tasks"]:
        t["priority"] = 99  # bypasses _validate_priority
    assert all(t["priority"] != 99 for t in handle_list_tasks()[1]["tasks"])


def test_f1_mutating_user_response_cannot_change_email():
    _, user = handle_get_user(1)
    user["email"] = "attacker@evil.test"
    _, users = handle_list_users()
    users["users"][0]["notification_pref"] = "pwned"
    _, fresh = handle_get_user(1)
    assert fresh["email"] == "ada@example.com"
    assert fresh["notification_pref"] != "pwned"


# F6 (Medium): non-dict bodies crash the handler (500 + traceback).


@pytest.mark.parametrize("body", [None, [], "x", 42])
def test_f6_non_dict_create_body_is_400(body):
    status, resp = handle_create_task(body)
    assert status == 400 and "error" in resp


@pytest.mark.parametrize("body", [None, [], "x"])
def test_f6_non_dict_update_body_is_400(body):
    task = _new_task()
    status, resp = handle_update_task(task["id"], body)
    assert status == 400 and "error" in resp


@pytest.mark.parametrize("body", [None, [], "x"])
def test_f6_non_dict_notification_body_is_400(body):
    status, resp = handle_update_notifications(1, body)
    assert status == 400 and "error" in resp


# F7 (Medium): a long digit string makes int() raise ValueError (unhandled).


def test_f7_huge_priority_string_is_400():
    status, resp = handle_list_tasks("9" * 5000)
    assert status == 400 and "error" in resp


def test_f7_error_does_not_echo_huge_input():
    _, resp = handle_list_tasks("9" * 5000)
    assert len(resp.get("error", "")) < 200


# F8 (Medium): unbounded title length (memory DoS).


def test_f8_oversized_title_rejected_on_create():
    status, _ = handle_create_task({"user_id": 1, "title": "A" * 1_000_000})
    assert status == 400


def test_f8_oversized_title_rejected_on_update():
    task = _new_task()
    status, _ = handle_update_task(task["id"], {"title": "A" * 1_000_000})
    assert status == 400


# F11 (Low): bool accepted as an integer id.


def test_f11_bool_task_id_is_not_task_1():
    status, _ = handle_get_task(True)
    assert status != 200


def test_f11_bool_user_id_cannot_own_a_task():
    status, _ = handle_create_task({"user_id": True, "title": "t"})
    assert status != 201
