#!/usr/bin/env python3
"""
Controle simples de rate limit por usuário.
"""

from datetime import datetime, timedelta

import state
from config import MAX_MESSAGES


def check_rate_limit(user):
    now = datetime.now()
    window = timedelta(minutes=1)

    with state.rate_limit_lock:
        state.rate_limits.setdefault(user, [])
        state.rate_limits[user] = [
            t for t in state.rate_limits[user]
            if now - t <= window
        ]

        if len(state.rate_limits[user]) >= MAX_MESSAGES:
            return False

        state.rate_limits[user].append(now)
        return True
