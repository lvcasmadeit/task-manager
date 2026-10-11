import pytest

from routes.users import (
    handle_get_notifications,
    handle_get_user,
    handle_list_users,
    handle_update_notifications,
)


@pytest.fixture(autouse=True)
def _restore_pref():
    handle_update_notifications(1, {"notification_pref": "none"})
    yield
    handle_update_notifications(1, {"notification_pref": "none"})


def test_list_users_includes_notification_pref():
    status, body = handle_list_users()
    assert status == 200
    user = next(u for u in body["users"] if u["id"] == 1)
    assert "notification_pref" in user


def test_get_user_includes_notification_pref():
    status, body = handle_get_user(1)
    assert status == 200
    assert "notification_pref" in body


def test_get_notifications_ok():
    status, body = handle_get_notifications(1)
    assert status == 200
    assert body["notification_pref"] == "none"


def test_patch_then_get_reflects_change():
    status, body = handle_update_notifications(1, {"notification_pref": "email"})
    assert status == 200
    assert body["notification_pref"] == "email"
    status, body = handle_get_notifications(1)
    assert status == 200
    assert body["notification_pref"] == "email"


def test_patch_invalid_returns_400():
    status, body = handle_update_notifications(1, {"notification_pref": "push"})
    assert status == 400
    assert "error" in body


def test_patch_unknown_user_returns_404():
    status, body = handle_update_notifications(999, {"notification_pref": "sms"})
    assert status == 404
    assert "error" in body


def test_patch_missing_key_returns_400():
    status, body = handle_update_notifications(1, {})
    assert status == 400
    assert "error" in body
