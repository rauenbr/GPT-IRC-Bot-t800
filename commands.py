#!/usr/bin/env python3
"""
Comandos IRC do T800.
"""

from datetime import datetime
import resource

import state
from constants import SCRIPT_VERSION
from config import model, monthly_start_day, debug_mode
from utils import fmt_delta
from response_pipeline import send_message
from storage import get_meta, get_recent_history, cursor, conn
from logging_utils import log


def handle_command(cmd, target):
    log(f"[COMANDO] {cmd}", "DEBUG")
    now = datetime.now()
    lc = cmd.lower()

    if lc == "!help":
        send_message(target, "Comandos: !help, !status, !uptime, !model, !usage, !history")

    elif lc == "!status":
        up = now - state.start_time
        send_message(
            target,
            f"Bot v{SCRIPT_VERSION} • sess up={fmt_delta(up)} • "
            f"tokens sess={state.total_tokens_used} (~${state.total_cost_used:.4f}) • model={model}"
        )

    elif lc == "!uptime":
        up = now - state.start_time
        send_message(target, f"Uptime sess: {fmt_delta(up)}")

    elif lc == "!model":
        send_message(target, f"Modelo: {model}")

    elif lc == "!usage":
        send_message(
            target,
            f"Hoje: {state.tokens_today} tok (~${state.cost_today:.4f}) | "
            f"Mês desde dia {monthly_start_day}: {state.tokens_month} tok (~${state.cost_month:.4f})"
        )

        first = datetime.fromisoformat(get_meta("first_init"))
        last_init = datetime.fromisoformat(get_meta("last_init"))
        last_conn = datetime.fromisoformat(get_meta("last_conn"))

        send_message(
            target,
            f"Primeiro init: {first.strftime('%Y-%m-%d %H:%M')}Z "
            f"({fmt_delta(now - first)} atrás)"
        )
        send_message(
            target,
            f"Último init: {last_init.strftime('%Y-%m-%d %H:%M')}Z "
            f"({fmt_delta(now - last_init)} atrás)"
        )
        send_message(
            target,
            f"Última conexão: {last_conn.strftime('%Y-%m-%d %H:%M')}Z "
            f"({fmt_delta(now - last_conn)} atrás)"
        )

        li = get_meta("last_init")
        with state.db_lock:
            cursor.execute("SELECT COUNT(*) FROM usage WHERE timestamp>=?", (li,))
            calls = cursor.fetchone()[0]

        ru = resource.getrusage(resource.RUSAGE_SELF)
        mem_mb = ru.ru_maxrss / 1024.0

        send_message(
            target,
            f"API calls: {calls} | Memória RSS: {mem_mb:.1f}MB | "
            f"CPU utime={ru.ru_utime:.2f}s stime={ru.ru_stime:.2f}s"
        )

    elif lc == "!clear":
        with state.db_lock:
            cursor.execute("DELETE FROM history WHERE target=?", (target,))
            conn.commit()
        send_message(target, "Histórico limpo.")

    elif lc == "!history" and debug_mode:
        hist = get_recent_history(target)
        if not hist:
            send_message(target, "Histórico vazio.")
        else:
            send_message(target, "Histórico recente:")
            for e in hist:
                ts = e["timestamp"].strftime("%H:%M")
                send_message(target, f"[{ts}] {e['role']}: {e['content']}")

    elif lc == "!history":
        send_message(target, "O comando !history só funciona em modo debug.")

    else:
        send_message(target, "Comando desconhecido. Use !help.")
