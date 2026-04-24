#!/usr/bin/env python3
"""
Comandos IRC do T800.
"""

from datetime import datetime
import resource

import state
from constants import SCRIPT_VERSION
from config import (
    model,
    monthly_start_day,
    debug_mode,
    context_mode,
    history_limit_direct,
    history_limit_channelcontext,
    channel_history_max_chars,
    assistant_history_max_chars,
    question_history_max_chars,
)
from nick_utils import get_active_nickname
from utils import fmt_delta
from response_pipeline import send_message
from storage import get_meta, get_recent_history, cursor, conn
from logging_utils import log


def _format_meta_datetime(label, value, now):
    try:
        if not value:
            raise ValueError("metadata ausente")
        parsed = datetime.fromisoformat(value)
        return f"{label} {parsed.strftime('%Y-%m-%d %H:%M')}Z ({fmt_delta(now - parsed)} atrás)"
    except Exception:
        return f"{label} indisponível"


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
            f"Bot v{SCRIPT_VERSION} • nick={get_active_nickname()} • sess up={fmt_delta(up)} • mode={context_mode} • "
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

        send_message(
            target,
            _format_meta_datetime("Primeiro registro DB:", get_meta("first_init"), now)
        )
        send_message(
            target,
            _format_meta_datetime("Último start do bot:", get_meta("last_init"), now)
        )
        send_message(
            target,
            _format_meta_datetime("Última conexão IRC:", get_meta("last_conn"), now)
        )
        send_message(
            target,
            f"Contexto: mode={context_mode} | "
            f"hist=direct:{history_limit_direct}/channel:{history_limit_channelcontext} | "
            f"chars=chan:{channel_history_max_chars}/asst:{assistant_history_max_chars}/q:{question_history_max_chars}"
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
