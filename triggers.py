#!/usr/bin/env python3
"""
Detecção de triggers de interação com o bot.
"""

from config import nickname
from nick_utils import get_active_nickname


def extract_trigger_content(msg_text):
    is_command = msg_text.startswith("!")

    if is_command:
        return True, msg_text.strip()

    lc_msg = msg_text.lower()
    possible_nicks = []
    for nick in (nickname, get_active_nickname()):
        if nick and nick.lower() not in possible_nicks:
            possible_nicks.append(nick.lower())

    for nick_lower in possible_nicks:
        if lc_msg.startswith(f"{nick_lower}:"):
            content = msg_text[len(nick_lower) + 1:].strip()
            return True, content

        if lc_msg.endswith(f"{nick_lower}?"):
            content = msg_text[:-len(nick_lower) - 1].strip()
            return True, content

    return False, None
