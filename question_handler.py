#!/usr/bin/env python3
"""
Processamento principal de perguntas ao bot.
"""

from datetime import datetime

import openai
import tiktoken

import state
from config import (
    model,
    context_message,
    temperature,
    max_tokens,
    top_p,
    frequency_penalty,
    presence_penalty,
    timeout,
    debug_mode,
    question_history_max_chars,
    assistant_history_max_chars,
)
from pricing import calculate_cost
from commands import handle_command
from rate_limit import check_rate_limit
from periods import update_periods
from storage import add_history_entry, get_recent_history, cursor, conn
from response_pipeline import send_message
from markdown_irc import convert_markdown_to_irc
from logging_utils import log


def handle_question(user, target, question):
    # comandos não entram no fluxo da OpenAI
    if question.startswith("!"):
        handle_command(question, target)
        return

    if not check_rate_limit(user):
        send_message(target, "[Rate Limit] muito rápido.")
        return

    update_periods()

    # grava nick real no histórico em vez de sempre "user"
    question_to_store = question[:question_history_max_chars]
    add_history_entry(target, user, question_to_store)

    # monta prompt incluindo quem falou o quê
    hist = get_recent_history(target)
    messages = [{"role": "system", "content": context_message}]
    for e in hist:
        if e["role"] == "assistant":
            messages.append({"role": "assistant", "content": e["content"]})
        else:
            messages.append({"role": "user", "content": f"{e['role']}: {e['content']}"})

    if debug_mode:
        try:
            enc = tiktoken.encoding_for_model(model)
        except Exception:
            enc = tiktoken.get_encoding("o200k_base")

        pts = sum(len(enc.encode(m["content"])) for m in messages)
        log(f"[ESTIMATIVA TOKENS] prompt≈{pts}", "DEBUG")
        log("Prompt enviado para OpenAI (mensagens):", "DEBUG")
        for msg_obj in messages:
            log(f"  {msg_obj['role']}: {msg_obj['content']}", "DEBUG")

    try:
        log("Enviando chamada para OpenAI...", "DEBUG")
        resp = openai.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            timeout=timeout
        )

        usage = resp.usage
        log(
            f"[TOKENS] prompt={usage.prompt_tokens} • completion={usage.completion_tokens} • total={usage.total_tokens}",
            "DEBUG"
        )

        state.total_tokens_used += usage.total_tokens
        state.tokens_today += usage.total_tokens
        state.tokens_month += usage.total_tokens

        cost = calculate_cost(
           model,
           usage.prompt_tokens,
           usage.completion_tokens
        )
        state.total_cost_used += cost
        state.cost_today += cost
        state.cost_month += cost
        log(f"[CUSTO] ${cost:.6f}", "DEBUG")

        with state.db_lock:
            cursor.execute(
                "INSERT INTO usage VALUES (?,?,?,?,?,?)",
                (
                    datetime.now().isoformat(),
                    model,
                    usage.prompt_tokens,
                    usage.completion_tokens,
                    usage.total_tokens,
                    cost
                )
            )
            conn.commit()

        answer = resp.choices[0].message.content.strip()

        # salva resposta do assistant truncada para não deixar o próprio bot dominar o histórico curto do canal/PM
        answer_to_store = answer[:assistant_history_max_chars]
        add_history_entry(target, "assistant", answer_to_store)

        for line in answer.split("\n"):
            if line.strip():
                send_message(target, convert_markdown_to_irc(line))

        log(f"Resposta enviada para {target}: {answer.splitlines()[0]}", "INFO")

    except Exception as e:
        log(f"Erro na API ou interno: {e}", "ERRO")
        send_message(target, "[Erro interno]")
