from datetime import date

import state
from config import monthly_start_day
from logging_utils import log


def get_monthly_cycle_start(hoje, start_day=None):
    if start_day is None:
        start_day = monthly_start_day

    if hoje.day >= start_day:
        return date(hoje.year, hoje.month, start_day)

    prev_month = hoje.month - 1 or 12
    prev_year = hoje.year - 1 if hoje.month == 1 else hoje.year
    return date(prev_year, prev_month, start_day)


def init_period_state():
    hoje = date.today()

    state.last_reset_daily = hoje
    state.last_reset_monthly = get_monthly_cycle_start(hoje)


def update_periods():
    hoje = date.today()

    if hoje != state.last_reset_daily:
        log("Reset diário de counters", "DEBUG")
        state.tokens_today = 0
        state.cost_today = 0.0
        state.last_reset_daily = hoje

    reset_pt = get_monthly_cycle_start(hoje)
    if state.last_reset_monthly is None:
        state.last_reset_monthly = reset_pt

    if state.last_reset_monthly < reset_pt:
        log("Reset mensal de counters", "DEBUG")
        state.tokens_month = 0
        state.cost_month = 0.0
        state.last_reset_monthly = reset_pt
