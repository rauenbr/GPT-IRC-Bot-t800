#!/usr/bin/env python3
"""
Bootstrap e loop principal do T800.
"""

import socket
import ssl
import time
import daemon

import state
from config import (
    debug_mode,
    raw_mode,
    nickname,
    context_mode,
    global_log,
    channel_history_max_chars,
)
from logging_utils import log
from irc_client import connect, reconnect, join_channels, irc_send_raw
from irc_parser import parse_irc_line
from triggers import extract_trigger_content
from filters import should_store_passive_channel_message
from question_handler import handle_question
from storage import load_metadata_and_counters, add_history_entry
from periods import init_period_state
from lifecycle import register_signal_handlers
from burst import maybe_summarize_burst


def start_bot():
    init_period_state()
    load_metadata_and_counters()
    register_signal_handlers()

    connect()
    joined = False

    while True:
        try:
            data = state.irc.recv(4096).decode("utf-8", errors="ignore")
            if raw_mode and data.strip():
                log(f"[RAW] {data.strip()}", "DEBUG")

        except (socket.timeout, ssl.SSLError):
            continue

        except Exception as e:
            log(f"Conexão perdida: {e}", "ERRO")
            reconnect()
            joined = False
            continue

        if not data:
            log("Socket retornou vazio. Reconectando...", "ERRO")
            reconnect()
            joined = False
            continue

        for line in data.splitlines():
            msg = parse_irc_line(line)
            if not msg:
                continue

            command = msg["command"]
            params = msg["params"]
            prefix = msg["prefix"]

            if command == "PING":
                if params:
                    irc_send_raw(f"PONG :{params[0]}")
                    log("PONG enviado ao servidor.", "DEBUG")
                continue

            if command == "ERROR":
                log("Erro do servidor (ERROR). Reconectando...", "ERRO")
                reconnect()
                joined = False
                break

            if command == "KICK":
                if len(params) >= 2 and params[1] == nickname:
                    log("Fui kickado do canal. Reconectando...", "ERRO")
                    reconnect()
                    joined = False
                    break
                continue

            if command in ("001", "004", "422") and not joined:
                log(f"Recebido {command}, fazendo JOIN nos canais...", "DEBUG")
                join_channels()
                joined = True
                continue

            if command != "PRIVMSG":
                continue

            if len(params) < 2 or not prefix:
                continue

            user = prefix.split("!", 1)[0]
            target = params[0]
            msg_text = params[1].strip()

            if not msg_text:
                continue

            # Mensagem privada (PM)
            if target == nickname:
                state.executor.submit(handle_question, user, user, msg_text)
                continue

            # Apenas canais
            if not target.startswith("#"):
                continue

            triggered, content = extract_trigger_content(msg_text)

            # Armazenamento passivo do canal para contexto
            if context_mode == "channelcontext":
                msg_clean = msg_text.strip()
                if should_store_passive_channel_message(user, msg_clean, triggered):
                    add_history_entry(target, user, msg_clean[:channel_history_max_chars])

                    # Tenta resumir bursts de mensagens recentes do canal
                    try:
                        maybe_summarize_burst(target)
                    except Exception as e:
                        log(f"[BURST ERROR] Falha ao processar burst em {target}: {e}", "ERRO")

            # Se ativou o bot, processa a pergunta
            if triggered and content:
                state.executor.submit(handle_question, user, target, content)

        time.sleep(0.2)


if __name__ == "__main__":
    if not debug_mode:
        with daemon.DaemonContext(
            stdout=open(global_log, "a"),
            stderr=open(global_log, "a")
        ):
            start_bot()
    else:
        start_bot()
