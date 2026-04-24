from datetime import datetime, timedelta

import pytest

import rate_limit
import state


@pytest.fixture(autouse=True)
def clear_rate_limits():
    state.rate_limits.clear()
    yield
    state.rate_limits.clear()


def set_now(monkeypatch, current_time):
    class FrozenDateTime:
        @classmethod
        def now(cls):
            return current_time

    monkeypatch.setattr(rate_limit, "datetime", FrozenDateTime)


def test_allows_first_message_for_new_user(monkeypatch):
    now = datetime(2026, 4, 24, 12, 0, 0)
    set_now(monkeypatch, now)

    assert rate_limit.check_rate_limit("alice") is True
    assert state.rate_limits["alice"] == [now]


def test_allows_up_to_five_messages_within_window(monkeypatch):
    now = datetime(2026, 4, 24, 12, 0, 0)
    set_now(monkeypatch, now)

    results = [rate_limit.check_rate_limit("alice") for _ in range(5)]

    assert results == [True, True, True, True, True]
    assert state.rate_limits["alice"] == [now, now, now, now, now]


def test_blocks_sixth_message_within_one_minute(monkeypatch):
    now = datetime(2026, 4, 24, 12, 0, 0)
    set_now(monkeypatch, now)
    state.rate_limits["alice"] = [now - timedelta(seconds=10)] * 5

    assert rate_limit.check_rate_limit("alice") is False
    assert len(state.rate_limits["alice"]) == 5


def test_discards_expired_timestamps_and_allows_new_message(monkeypatch):
    now = datetime(2026, 4, 24, 12, 0, 0)
    set_now(monkeypatch, now)
    state.rate_limits["alice"] = [
        now - timedelta(seconds=61),
        now - timedelta(seconds=60),
        now - timedelta(seconds=59),
        now - timedelta(seconds=10),
    ]

    assert rate_limit.check_rate_limit("alice") is True
    assert state.rate_limits["alice"] == [
        now - timedelta(seconds=60),
        now - timedelta(seconds=59),
        now - timedelta(seconds=10),
        now,
    ]


def test_rate_limit_is_isolated_per_user(monkeypatch):
    now = datetime(2026, 4, 24, 12, 0, 0)
    set_now(monkeypatch, now)
    state.rate_limits["alice"] = [now - timedelta(seconds=5)] * 5

    assert rate_limit.check_rate_limit("alice") is False
    assert rate_limit.check_rate_limit("bob") is True
    assert state.rate_limits["bob"] == [now]
