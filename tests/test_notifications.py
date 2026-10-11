import pytest

from services.notifications import get_notification_pref, set_notification_pref
from utils.errors import NotFoundError, ValidationError


@pytest.fixture(autouse=True)
def _restore_pref():
    set_notification_pref(1, "none")
    yield
    set_notification_pref(1, "none")


def test_default_pref_is_none():
    result = get_notification_pref(1)
    assert result["user_id"] == 1
    assert result["notification_pref"] == "none"


@pytest.mark.parametrize("pref", ["email", "sms", "none"])
def test_set_round_trips(pref):
    result = set_notification_pref(1, pref)
    assert result == {"user_id": 1, "notification_pref": pref}
    assert get_notification_pref(1)["notification_pref"] == pref


@pytest.mark.parametrize("pref", ["push", "", "EMAIL", None, 1])
def test_set_invalid_pref_raises(pref):
    with pytest.raises(ValidationError):
        set_notification_pref(1, pref)


@pytest.mark.parametrize("user_id", [0, -1, True, "1"])
def test_get_invalid_user_id_raises(user_id):
    with pytest.raises(ValidationError):
        get_notification_pref(user_id)


@pytest.mark.parametrize("user_id", [0, -1, True, "1"])
def test_set_invalid_user_id_raises(user_id):
    with pytest.raises(ValidationError):
        set_notification_pref(user_id, "email")


def test_get_unknown_user_raises():
    with pytest.raises(NotFoundError):
        get_notification_pref(999)


def test_set_unknown_user_raises():
    with pytest.raises(NotFoundError):
        set_notification_pref(999, "email")


def test_failed_set_leaves_value_unchanged():
    set_notification_pref(1, "sms")
    with pytest.raises(ValidationError):
        set_notification_pref(1, "push")
    assert get_notification_pref(1)["notification_pref"] == "sms"
