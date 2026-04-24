#!/usr/bin/env python3
"""
Conexão e envio básico ao IRC.
"""

import socket
import ssl
import time
from datetime import datetime

import state
from config import (
    server,
    port,
    usessl,
    password,
    nickname,
    ident,
    realname,
    channels,
)
from logging_utils import log
from storage import set_meta


def connect():
    while True:
        try:
            log(f"Conectando em {server}:{port}...", "INFO")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(30)

            if usessl:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                state.irc = ctx.wrap_socket(sock, server_hostname=server)
            else:
                state.irc = sock

            state.irc.connect((server, port))

            if password:
                state.irc.send(f"PASS {password}\n".encode())

            state.irc.send(f"NICK {nickname}\n".encode())
            state.irc.send(f"USER {ident} 0 * :{realname}\n".encode())

            log("Conectado ao IRC com sucesso!", "INFO")
            set_meta("last_conn", datetime.now().isoformat())
            return

        except Exception as e:
            log(f"Falha na conexão: {e}. Retentando em 5s...", "ERRO")
            time.sleep(5)


def reconnect():
    log("Reconectando...", "DEBUG")
    try:
        if state.irc:
            state.irc.close()
    except Exception:
        pass

    time.sleep(5)
    connect()


def irc_send_raw(text):
    with state.irc_lock:
        state.irc.send((text + "\n").encode())


def join_channels():
    for ch in channels:
        irc_send_raw(f"JOIN {ch}")
