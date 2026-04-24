#!/usr/bin/env python3
"""
Filtros para decidir se mensagens de canal devem entrar no contexto.
"""

import re
from collections import Counter

from config import (
    context_mode,
    nickname,
    ignore_short_channel_msgs,
    channel_min_msg_len,
)


def should_store_passive_channel_message(user, msg_text, triggered):
    if context_mode != "channelcontext":
        return False

    if user == nickname:
        return False

    if triggered:
        return False

    if not msg_text:
        return False

    msg = msg_text.strip()
    if not msg:
        return False

    # ignora comandos
    if msg.startswith("!"):
        return False

    lowered = msg.lower()

    meaningful_short_msgs = {
        "sim", "não", "nao", "talvez",
        "foi", "caiu", "subiu", "voltou",
        "esse", "essa", "isso", "aquilo",
        "aqui", "ali", "lá", "la",
        "tem", "teve", "era", "é", "e",
        "qual", "quem", "onde", "como", "quando"
    }

    weak_msgs = {
        "kkk", "kkkk", "kkkkk", "kkkkkk",
        "rs", "rss", "haha", "hahaha", "hehe", "hehehe",
        "ok", "blz", "ah", "ahn", "hum", "hmm",
        "oxe", "ouxe", "vish", "sei", "sei lá", "sla"
    }

    # mensagens muito curtas
    if ignore_short_channel_msgs and len(msg) < channel_min_msg_len:
        if lowered not in meaningful_short_msgs:
            return False

    # só símbolo
    if not any(ch.isalnum() for ch in msg):
        return False

    # mensagens fracas
    if lowered in weak_msgs:
        return False

    # risadas repetidas
    if re.fullmatch(r'(ha|he|hi|hu|rs|kk)+', lowered):
        return False

    # caractere repetido
    if re.fullmatch(r'(.)\1{3,}', lowered):
        return False

    # pontuação repetida
    if re.fullmatch(r'[?!.\-_=+*~#@]{3,}', msg):
        return False

    # dominância de um caractere
    chars_only = re.sub(r'\s+', '', lowered)
    if len(chars_only) >= 6:
        counts = Counter(chars_only)
        most_common_count = counts.most_common(1)[0][1]
        if (most_common_count / len(chars_only)) > 0.7:
            return False

    return True
