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


def graceful_exit(signum, frame):
    log("Recebido sinal, enviando QUIT...", "INFO")
    if state.irc:
        try:
            state.irc.send(b"QUIT :Voltarei em breve\n")
            time.sleep(1)
            state.irc.close()
        except Exception:
            pass

    conn.close()
    sys.exit(0)


def register_signal_handlers():
    signal.signal(signal.SIGINT, graceful_exit)
    signal.signal(signal.SIGTERM, graceful_exit)
