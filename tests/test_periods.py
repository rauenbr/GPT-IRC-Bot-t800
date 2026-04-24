from datetime import date

import periods
import state


class FakeDate(date):
    _today = date(2026, 4, 24)

    @classmethod
    def today(cls):
        return cls._today


def set_today(monkeypatch, today_value):
    FakeDate._today = today_value
    monkeypatch.setattr(periods, "date", FakeDate)


def reset_period_state():
    state.tokens_today = 10
    state.cost_today = 1.5
    state.tokens_month = 50
    state.cost_month = 7.5
    state.last_reset_daily = date(2026, 4, 20)
    state.last_reset_monthly = date(2026, 4, 1)


def test_init_period_state_when_today_is_after_monthly_start(monkeypatch):
    monkeypatch.setattr(periods, "monthly_start_day", 10)
    set_today(monkeypatch, date(2026, 4, 24))

    periods.init_period_state()

    assert state.last_reset_daily == date(2026, 4, 24)
    assert state.last_reset_monthly == date(2026, 4, 10)


def test_init_period_state_when_today_is_before_monthly_start(monkeypatch):
    monkeypatch.setattr(periods, "monthly_start_day", 20)
    set_today(monkeypatch, date(2026, 4, 10))

    periods.init_period_state()

    assert state.last_reset_daily == date(2026, 4, 10)
    assert state.last_reset_monthly == date(2026, 3, 20)


def test_init_period_state_handles_january_rolling_back_to_previous_year(monkeypatch):
    monkeypatch.setattr(periods, "monthly_start_day", 20)
    set_today(monkeypatch, date(2026, 1, 10))

    periods.init_period_state()

    assert state.last_reset_daily == date(2026, 1, 10)
    assert state.last_reset_monthly == date(2025, 12, 20)


def test_update_periods_without_day_change_keeps_counters(monkeypatch):
    monkeypatch.setattr(periods, "monthly_start_day", 1)
    set_today(monkeypatch, date(2026, 4, 24))
    monkeypatch.setattr(periods, "log", lambda *_args, **_kwargs: None)
    reset_period_state()
    state.last_reset_daily = date(2026, 4, 24)
    state.last_reset_monthly = date(2026, 4, 1)

    periods.update_periods()

    assert state.tokens_today == 10
    assert state.cost_today == 1.5
    assert state.tokens_month == 50
    assert state.cost_month == 7.5


def test_update_periods_resets_daily_counters(monkeypatch):
    monkeypatch.setattr(periods, "monthly_start_day", 1)
    set_today(monkeypatch, date(2026, 4, 24))
    monkeypatch.setattr(periods, "log", lambda *_args, **_kwargs: None)
    reset_period_state()
    state.last_reset_daily = date(2026, 4, 23)
    state.last_reset_monthly = date(2026, 4, 1)

    periods.update_periods()

    assert state.tokens_today == 0
    assert state.cost_today == 0.0
    assert state.last_reset_daily == date(2026, 4, 24)


def test_update_periods_resets_monthly_counters(monkeypatch):
    monkeypatch.setattr(periods, "monthly_start_day", 20)
    set_today(monkeypatch, date(2026, 4, 24))
    monkeypatch.setattr(periods, "log", lambda *_args, **_kwargs: None)
    reset_period_state()
    state.last_reset_daily = date(2026, 4, 24)
    state.last_reset_monthly = date(2026, 3, 20)

    periods.update_periods()

    assert state.tokens_month == 0
    assert state.cost_month == 0.0
    assert state.last_reset_monthly == date(2026, 4, 20)


def test_update_periods_does_not_reset_monthly_when_already_current(monkeypatch):
    monkeypatch.setattr(periods, "monthly_start_day", 20)
    set_today(monkeypatch, date(2026, 4, 24))
    monkeypatch.setattr(periods, "log", lambda *_args, **_kwargs: None)
    reset_period_state()
    state.last_reset_daily = date(2026, 4, 24)
    state.last_reset_monthly = date(2026, 4, 20)

    periods.update_periods()

    assert state.tokens_month == 50
    assert state.cost_month == 7.5
    assert state.last_reset_monthly == date(2026, 4, 20)


def test_update_periods_handles_none_last_reset_monthly(monkeypatch):
    monkeypatch.setattr(periods, "monthly_start_day", 20)
    set_today(monkeypatch, date(2026, 4, 24))
    monkeypatch.setattr(periods, "log", lambda *_args, **_kwargs: None)
    reset_period_state()
    state.last_reset_daily = date(2026, 4, 24)
    state.last_reset_monthly = None

    periods.update_periods()

    assert state.last_reset_monthly == date(2026, 4, 20)
    assert state.tokens_month == 50
    assert state.cost_month == 7.5
