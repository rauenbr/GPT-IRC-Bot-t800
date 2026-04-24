#!/usr/bin/env python3
"""
Resumo automático de bursts de mensagens em canais.
"""

from datetime import datetime

import state
from config import (
    context_mode,
    burst_window,
    burst_threshold,
    burst_chunk_size,
    model,
    timeout,
)
from logging_utils import log
from storage import get_recent_history, add_history_entry, cursor, conn
from llm_client import generate_summary


SUMMARY_PREFIX = "[Resumido]"


def _is_summary_entry(entry):
    if not entry:
        return False
    return (
        entry.get("role") == "assistant"
        and isinstance(entry.get("content"), str)
        and entry["content"].startswith(SUMMARY_PREFIX)
    )


def maybe_summarize_burst(target):
    # Segurança extra: burst só faz sentido em canal com channelcontext ativo
    if context_mode != "channelcontext":
        return

    if not target or not target.startswith("#"):
        return

    hist = get_recent_history(target)
    if not hist:
        log("[BURST CHECK] Histórico vazio, sem resumo.", "DEBUG")
        return

    now = datetime.now()
    recent = [
        e for e in hist
        if (now - e["timestamp"]).total_seconds() <= burst_window
    ]

    log(
        f"[BURST CHECK] {len(recent)} msgs nos últimos {burst_window}s "
        f"(threshold={burst_threshold})",
        "DEBUG"
    )

    if len(recent) < burst_threshold:
        log("[BURST CHECK] Não atingiu threshold, sem resumo.", "DEBUG")
        return

    chunk = recent[-burst_chunk_size:]
    if not chunk:
        log("[BURST CHECK] Chunk vazio, sem resumo.", "DEBUG")
        return

    # Evita resumir em cascata um bloco que já foi resumido recentemente
    if _is_summary_entry(chunk[-1]):
        log("[BURST CHECK] Última entrada já é resumo, ignorando.", "DEBUG")
        return

    # Evita gerar resumo quando quase tudo do chunk já é resumo
    summary_count = sum(1 for e in chunk if _is_summary_entry(e))
    if summary_count >= max(1, len(chunk) - 1):
        log("[BURST CHECK] Chunk dominado por resumos anteriores, ignorando.", "DEBUG")
        return

    log(f"[BURST SUMMARY] Disparando resumo de {len(chunk)} msgs", "DEBUG")

    prompt = (
        "Resuma em 2–3 linhas estas mensagens, indicando quem falou cada parte:\n"
        + "\n".join(f"{e['role']}: {e['content']}" for e in chunk)
    )
    log(f"[BURST PROMPT] {prompt}", "DEBUG")

    try:
        summary, _usage = generate_summary(
            prompt,
            {
                "model": model,
                "temperature": 0.5,
                "max_tokens": 150,
                "timeout": timeout,
            },
        )

        if not summary:
            log("[BURST ERROR] Resposta vazia da OpenAI no resumo.", "ERRO")
            return

        summary = summary.strip()
        log(f"[BURST RESULT] {summary}", "DEBUG")

        cutoff = chunk[0]["timestamp"].isoformat()

        with state.db_lock:
            cursor.execute(
                "DELETE FROM history WHERE target=? AND timestamp>=?",
                (target, cutoff),
            )
            conn.commit()

        add_history_entry(target, "assistant", f"{SUMMARY_PREFIX} {summary}")

    except Exception as e:
        log(f"[BURST ERROR] {e}", "ERRO")
