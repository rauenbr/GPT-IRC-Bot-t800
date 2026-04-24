#!/usr/bin/env python3
"""
Pipeline de envio de respostas para o IRC.
"""

import state
from logging_utils import log


def send_message(target, message):
    if not message:
        return

    try:
        with state.irc_lock:
            if not state.irc:
                raise RuntimeError("IRC não conectado")

            state.irc.send(f"PRIVMSG {target} :{message}\n".encode())

        log(f"[SEND] -> {target}: {message}", "DEBUG")

    except Exception as e:
        log(f"Erro ao enviar mensagem: {e}", "ERRO")
