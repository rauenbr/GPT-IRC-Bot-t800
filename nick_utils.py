#!/usr/bin/env python3
"""
Helpers relacionados ao nick ativo do bot.
"""

import state
from config import nickname


def get_active_nickname():
    return state.current_nickname or nickname
