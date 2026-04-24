#!/usr/bin/env python3
"""
Detecção de triggers de interação com o bot.
"""

from config import nickname


def extract_trigger_content(msg_text):
    lc_msg = msg_text.lower()
    nick_lower = nickname.lower()

    is_command = msg_text.startswith("!")
    is_prefix = lc_msg.startswith(f"{nick_lower}:")
    is_suffix_q = lc_msg.endswith(f"{nick_lower}?")

    if is_prefix:
        content = msg_text[len(nickname) + 1:].strip()
        return True, content

    if is_suffix_q:
        content = msg_text[:-len(nickname) - 1].strip()
        return True, content

    if is_command:
        return True, msg_text.strip()

    return False, None
