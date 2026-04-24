from datetime import date

import state
from config import monthly_start_day
from logging_utils import log


def init_period_state():
    hoje = date.today()

    state.last_reset_daily = hoje

    if hoje.day >= monthly_start_day:
        state.last_reset_monthly = date(hoje.year, hoje.month, monthly_start_day)
    else:
        pm = hoje.month - 1 or 12
        py = hoje.year - 1 if hoje.month == 1 else hoje.year
        state.last_reset_monthly = date(py, pm, monthly_start_day)


def update_periods():
    hoje = date.today()

    if hoje != state.last_reset_daily:
        log("Reset diário de counters", "DEBUG")
        state.tokens_today = 0
        state.cost_today = 0.0
        state.last_reset_daily = hoje

    reset_pt = date(hoje.year, hoje.month, monthly_start_day)
    if hoje >= reset_pt and state.last_reset_monthly < reset_pt:
        log("Reset mensal de counters", "DEBUG")
        state.tokens_month = 0
        state.cost_month = 0.0
        state.last_reset_monthly = reset_pt
