#!/usr/bin/env python3
"""
Gerenciamento de ciclo de vida e encerramento do T800.
"""

import signal
import sys
import time

import state
from logging_utils import log
from storage import conn

_shutting_down = False


def _safe_log(message, level="INFO"):
    try:
        log(message, level)
    except Exception:
        return


def _safe_call(description, func):
    try:
        func()
        return True
    except Exception as e:
        _safe_log(f"Falha ao {description}: {e}", "ERRO")
        return False


def _with_irc_lock(description, func, timeout=2.0):
    acquired = False
    try:
        acquired = state.irc_lock.acquire(timeout=timeout)
        if not acquired:
            _safe_log(f"Falha ao {description}: lock IRC indisponível", "ERRO")
            return False
        func()
        return True
    except Exception as e:
        _safe_log(f"Falha ao {description}: {e}", "ERRO")
        return False
    finally:
        if acquired:
            state.irc_lock.release()


def graceful_exit(signum, frame):
    global _shutting_down

    if _shutting_down:
        sys.exit(0)
        return

    _shutting_down = True
    _safe_log("Recebido sinal, encerrando...", "INFO")

    if state.irc:
        quit_sent = _send_quit()
        if quit_sent:
            _safe_call("aguardar QUIT", lambda: time.sleep(1))

        _close_irc()

    _safe_call(
        "encerrar executor",
        lambda: state.executor.shutdown(wait=False, cancel_futures=True),
    )
    _safe_call("fechar banco", lambda: conn.close())
    sys.exit(0)


def register_signal_handlers():
    signal.signal(signal.SIGINT, graceful_exit)
    signal.signal(signal.SIGTERM, graceful_exit)


def _send_quit():
    return _with_irc_lock(
        "enviar QUIT",
        lambda: state.irc.send(b"QUIT :Voltarei em breve\n"),
    )


def _close_irc():
    return _with_irc_lock(
        "fechar IRC",
        lambda: state.irc.close(),
    )
