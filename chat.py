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
from irc_client import connect, reconnect, join_channels, irc_send_raw, generate_random_nick
from irc_parser import parse_irc_line
from triggers import extract_trigger_content
from filters import should_store_passive_channel_message
from question_handler import handle_question
from storage import load_metadata_and_counters, add_history_entry
from periods import init_period_state
from lifecycle import register_signal_handlers
from burst import maybe_summarize_burst
from nick_utils import get_active_nickname


MAX_NICK_RETRY_COUNT = 5
MAX_RECV_BUFFER = 8192


def _retry_nickname(joined):
    state.nick_retry_count += 1
    if state.nick_retry_count > MAX_NICK_RETRY_COUNT:
        log("[NICK] Excesso de tentativas de nick. Reconectando...", "ERRO")
        reconnect()
        return False, True

    active_nick = get_active_nickname()
    log(f"[NICK] Nick em uso/indisponível: {active_nick}", "INFO")
    new_nick = generate_random_nick(active_nick)
    log(f"[NICK] Tentando nick alternativo randômico: {new_nick}", "INFO")
    irc_send_raw(f"NICK {new_nick}")
    return joined, False


def _extract_complete_lines(recv_buffer, data):
    combined = recv_buffer + data
    parts = combined.split("\n")

    if combined.endswith("\n"):
        lines = parts[:-1]
        recv_buffer = ""
    else:
        lines = parts[:-1]
        recv_buffer = parts[-1]

    lines = [line.rstrip("\r") for line in lines if line.rstrip("\r")]

    if len(recv_buffer) > MAX_RECV_BUFFER:
        log("Buffer de recv excedeu limite e foi descartado", "ERRO")
        recv_buffer = ""

    return lines, recv_buffer


def _process_irc_lines(lines, joined):
    for line in lines:
        try:
            msg = parse_irc_line(line)
        except Exception as e:
            log(f"Erro ao parsear linha IRC '{line}': {e}", "ERRO")
            continue

        if not msg:
            continue

        try:
            joined, should_break = process_irc_message(msg, joined)
        except Exception as e:
            log(f"Erro ao processar mensagem IRC '{line}': {e}", "ERRO")
            continue

        if should_break:
            return joined, True

    return joined, False


def _submit_question(user, target, content):
    try:
        state.executor.submit(handle_question, user, target, content)
    except Exception as e:
        log(f"Erro ao submeter tarefa para {target} por {user}: {e}", "ERRO")


def process_irc_message(msg, joined):
    command = msg["command"]
    params = msg["params"]
    prefix = msg["prefix"]

    if command == "PING":
        if params:
            irc_send_raw(f"PONG :{params[0]}")
            log("PONG enviado ao servidor.", "DEBUG")
        return joined, False

    if command == "ERROR":
        log("Erro do servidor (ERROR). Reconectando...", "ERRO")
        reconnect()
        return False, True

    if command in ("432", "433", "436", "437"):
        return _retry_nickname(joined)

    if command == "NICK" and prefix:
        user = prefix.split("!", 1)[0]
        if params:
            new_nick = params[-1].lstrip(":")
            active_nick = get_active_nickname()

            if user in (active_nick, nickname):
                state.current_nickname = new_nick
                log(f"[NICK] Nick ativo: {state.current_nickname}", "INFO")
        return joined, False

    if command == "KICK":
        active_nick = get_active_nickname()
        if len(params) >= 2 and params[1] == active_nick:
            canal = params[0]
            log(f"Fui kickado de {canal}. Tentando rejoin...", "INFO")
            irc_send_raw(f"JOIN {canal}")
            return joined, False
        return joined, False

    if command in ("001", "004", "422") and not joined:
        if command == "001" and params:
            state.current_nickname = params[0]
            log(f"[NICK] Nick ativo: {state.current_nickname}", "INFO")
        state.nick_retry_count = 0
        log(f"Recebido {command}, fazendo JOIN nos canais...", "DEBUG")
        # TODO futuro:
        # Avaliar estratégia de rejoin/recovery sem depender exclusivamente do numeric 001
        # após reconnect. Considerar fallback de JOIN caso o servidor não envie 001/004/422.
        join_channels()
        return True, False

    if command != "PRIVMSG":
        return joined, False

    if len(params) < 2 or not prefix:
        return joined, False

    user = prefix.split("!", 1)[0]
    target = params[0]
    msg_text = params[1].strip()

    if not msg_text:
        return joined, False

    active_nick = get_active_nickname()
    if target == active_nick:
        _submit_question(user, user, msg_text)
        return joined, False

    if not target.startswith("#"):
        return joined, False

    triggered, content = extract_trigger_content(msg_text)

    if context_mode == "channelcontext":
        msg_clean = msg_text.strip()
        if should_store_passive_channel_message(user, msg_clean, triggered):
            history_saved = False
            try:
                add_history_entry(target, user, msg_clean[:channel_history_max_chars])
                history_saved = True
            except Exception as e:
                log(f"Erro ao salvar histórico passivo: {e}", "ERRO")

            if history_saved:
                try:
                    maybe_summarize_burst(target)
                except Exception as e:
                    log(f"[BURST ERROR] Falha ao processar burst em {target}: {e}", "ERRO")

    if triggered and content:
        _submit_question(user, target, content)

    return joined, False


def start_bot():
    init_period_state()
    load_metadata_and_counters()
    register_signal_handlers()

    connect()
    joined = False
    recv_buffer = ""

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
            recv_buffer = ""
            joined = False
            continue

        if not data:
            log("Socket retornou vazio. Reconectando...", "ERRO")
            reconnect()
            recv_buffer = ""
            joined = False
            continue

        lines, recv_buffer = _extract_complete_lines(recv_buffer, data)
        joined, connection_reset = _process_irc_lines(lines, joined)
        if connection_reset:
            recv_buffer = ""
            joined = False
            continue

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
