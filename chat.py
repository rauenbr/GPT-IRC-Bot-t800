#!/usr/bin/env python3
"""
GPT-IRC Bot (T800) v1.2.1

Requisitos:
- Python 3.10+
- openai>=1.76.0
- tiktoken>=0.4.0
- SQLite (builtin)
- resource (builtin)
- Dependências padrão: ssl, socket, threading, daemon, configparser, etc.
"""

import sys
import re
import socket
import ssl
import time
import signal
import configparser
import daemon
import threading
import sqlite3
import resource
from datetime import datetime, timedelta, date

import openai
from openai import APIError, APIConnectionError, RateLimitError
import tiktoken  # para estimativa de tokens em debug

# -------------------------
# Configurações e Globais
# -------------------------

SCRIPT_VERSION = "1.2.1"

# Contadores de tokens e custo desde a sessão atual
total_tokens_used = 0
total_cost_used   = 0.0

# Contadores persistidos (dia e mês) carregados da DB
tokens_today = 0
cost_today   = 0.0
tokens_month = 0
cost_month   = 0.0

# Para reset de contadores
last_reset_daily   = date.today()
last_reset_monthly = None  # será definido após ler config

# Pricing (USD por 1k tokens)
PRICING = {
    # GPT-3.5 Turbo
    "gpt-3.5-turbo":           {"prompt": 0.0015, "completion": 0.002},
    "gpt-3.5-turbo-0301":      {"prompt": 0.0015, "completion": 0.002},
    "gpt-3.5-turbo-0613":      {"prompt": 0.0015, "completion": 0.002},
    "gpt-3.5-turbo-1106":      {"prompt": 0.0015, "completion": 0.002},
    "gpt-3.5-turbo-0125":      {"prompt": 0.0015, "completion": 0.002},
    "gpt-3.5-turbo-16k":       {"prompt": 0.0030, "completion": 0.004},
    "gpt-3.5-turbo-16k-0613":  {"prompt": 0.0030, "completion": 0.004},

    # GPT-4 (8K)
    "gpt-4":                   {"prompt": 0.030,  "completion": 0.060},
    "gpt-4-0314":              {"prompt": 0.030,  "completion": 0.060},
    "gpt-4-0613":              {"prompt": 0.030,  "completion": 0.060},

    # GPT-4 (32K)
    "gpt-4-32k":               {"prompt": 0.060,  "completion": 0.120},
    "gpt-4-32k-0314":          {"prompt": 0.060,  "completion": 0.120},
    "gpt-4-32k-0613":          {"prompt": 0.060,  "completion": 0.120},

    # Previews
    "gpt-4-0125-preview":      {"prompt": 0.030,  "completion": 0.060},
    "gpt-4-1106-preview":      {"prompt": 0.030,  "completion": 0.060},
    "gpt-4-vision-preview":    {"prompt": 0.030,  "completion": 0.060},

    # GPT-4 Turbo
    "gpt-4-turbo":             {"prompt": 0.0015, "completion": 0.002},
    "gpt-4-turbo-2024-04-09":  {"prompt": 0.0015, "completion": 0.002},
    "gpt-4-turbo-preview":     {"prompt": 0.0015, "completion": 0.002},

    # GPT-4o family (sample)
    "gpt-4o":                       {"prompt": 0.030,  "completion": 0.060},
    "gpt-4o-mini":                  {"prompt": 0.030,  "completion": 0.060},
    "chatgpt-4o-latest":            {"prompt": 0.030,  "completion": 0.060},

    # “o” series
    "o1":                   {"prompt": 0.0015, "completion": 0.002},
    "o1-mini":              {"prompt": 0.0015, "completion": 0.002},
}

start_time = datetime.now()

# -------------------------
# Leitura de chat.conf
# -------------------------

config = configparser.ConfigParser()
config.read('chat.conf')

# IRC
server            = config.get('irc', 'server')
port              = config.getint('irc', 'port')
usessl            = config.getboolean('irc', 'ssl')
channels          = config.get('irc', 'channels').split(',')
nickname          = config.get('irc', 'nickname')
ident             = config.get('irc', 'ident')
realname          = config.get('irc', 'realname')
password          = config.get('irc', 'password')
debug_mode        = config.getboolean('irc', 'debug', fallback=False)
raw_mode          = config.getboolean('irc', 'raw',   fallback=False)

# OpenAI
openai.api_key    = config.get('openai', 'api_key')

# ChatCompletion
model             = config.get('chatcompletion', 'model')
context_message   = config.get('chatcompletion', 'context')
temperature       = config.getfloat('chatcompletion', 'temperature')
max_tokens        = config.getint('chatcompletion', 'max_tokens')
top_p             = config.getfloat('chatcompletion', 'top_p')
frequency_penalty = config.getfloat('chatcompletion', 'frequency_penalty')
presence_penalty  = config.getfloat('chatcompletion', 'presence_penalty')
timeout           = config.getint('chatcompletion', 'request_timeout')

# Bot / DB / burst
global_log        = config.get('bot', 'log_file',           fallback="/var/log/chatgpt_irc.log")
HISTORY_LIMIT     = config.getint('bot', 'history_limit',    fallback=10)
monthly_start_day = config.getint('bot', 'monthly_start_day',fallback=1)
usage_db          = config.get('bot', 'usage_db',            fallback="usage.db")
burst_threshold   = config.getint('bot', 'burst_threshold',  fallback=5)
burst_window      = config.getint('bot', 'burst_window',     fallback=60)
burst_chunk_size  = config.getint('bot', 'burst_chunk_size', fallback=5)

# Inicializa last_reset_monthly
today = date.today()
if today.day >= monthly_start_day:
    last_reset_monthly = date(today.year, today.month, monthly_start_day)
else:
    pm = today.month - 1 or 12
    py = today.year - 1 if today.month == 1 else today.year
    last_reset_monthly = date(py, pm, monthly_start_day)

irc = None
rate_limits = {}

# -------------------------
# SQLite setup
# -------------------------

conn = sqlite3.connect(usage_db, check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS usage (
    timestamp TEXT,
    model TEXT,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_tokens INTEGER,
    cost REAL
)""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp TEXT NOT NULL
)""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
)""")
conn.commit()

# -------------------------
# Metadata init & counters
# -------------------------

def set_meta(key, value):
    cursor.execute("INSERT OR REPLACE INTO metadata (key,value) VALUES (?,?)", (key, value))
    conn.commit()

def get_meta(key):
    cursor.execute("SELECT value FROM metadata WHERE key=?", (key,))
    row = cursor.fetchone()
    return row[0] if row else None

def load_metadata_and_counters():
    now = datetime.now().isoformat()
    if not get_meta('first_init'):
        set_meta('first_init', now)
    set_meta('last_init', now)

    # tokens/custo do dia
    day_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    cursor.execute("SELECT SUM(total_tokens), SUM(cost) FROM usage WHERE timestamp>=?", (day_start,))
    tok_sum, cost_sum = cursor.fetchone()
    global tokens_today, cost_today
    tokens_today = tok_sum or 0
    cost_today   = cost_sum or 0.0

    # tokens/custo do mês
    m = datetime.now()
    if m.day >= monthly_start_day:
        m_start = m.replace(day=monthly_start_day, hour=0, minute=0, second=0, microsecond=0)
    else:
        pm = m.month - 1 or 12
        py = m.year - 1 if m.month == 1 else m.year
        m_start = m.replace(year=py, month=pm, day=monthly_start_day,
                            hour=0, minute=0, second=0, microsecond=0)
    cursor.execute("SELECT SUM(total_tokens), SUM(cost) FROM usage WHERE timestamp>=?", (m_start.isoformat(),))
    tok_sum, cost_sum = cursor.fetchone()
    global tokens_month, cost_month
    tokens_month = tok_sum or 0
    cost_month   = cost_sum or 0.0

    # limpa histórico se última entrada >30min
    cursor.execute("SELECT MAX(timestamp) FROM history")
    row = cursor.fetchone()[0]
    if row and (datetime.now() - datetime.fromisoformat(row)) > timedelta(minutes=30):
        cursor.execute("DELETE FROM history")
        conn.commit()

load_metadata_and_counters()

# -------------------------
# Helpers
# -------------------------

def log(msg, level="INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{ts}] [{level}] {msg}"
    print(entry)
    if not debug_mode:
        with open(global_log, "a") as f:
            f.write(entry + "\n")

def fmt_delta(delta):
    d = delta.days
    h, rem = divmod(delta.seconds, 3600)
    m, s = divmod(rem, 60)
    parts = []
    if d: parts.append(f"{d}d")
    if h: parts.append(f"{h}h")
    if m: parts.append(f"{m}m")
    parts.append(f"{s}s")
    return " ".join(parts)

def graceful_exit(signum, frame):
    global irc
    log("Recebido sinal, enviando QUIT...", "INFO")
    if irc:
        try:
            irc.send(b"QUIT :Voltarei em breve\n")
            time.sleep(1)
            irc.close()
        except: pass
    conn.close()
    sys.exit(0)

signal.signal(signal.SIGINT, graceful_exit)
signal.signal(signal.SIGTERM, graceful_exit)

# -------------------------
# Conexão IRC
# -------------------------

def connect():
    global irc
    while True:
        try:
            log(f"Conectando em {server}:{port}...", "INFO")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(30)
            if usessl:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                irc = ctx.wrap_socket(sock, server_hostname=server)
            else:
                irc = sock
            irc.connect((server, port))
            if password:
                irc.send(f"PASS {password}\n".encode())
            irc.send(f"NICK {nickname}\n".encode())
            irc.send(f"USER {ident} 0 * :{realname}\n".encode())
            log("Conectado ao IRC com sucesso!", "INFO")
            set_meta('last_conn', datetime.now().isoformat())
            return
        except Exception as e:
            log(f"Falha na conexão: {e}. Retentando em 5s...", "ERRO")
            time.sleep(5)

def reconnect():
    log("Reconectando...", "DEBUG")
    try: irc.close()
    except: pass
    time.sleep(5)
    connect()

# -------------------------
# Rate limit
# -------------------------

def check_rate_limit(user):
    now = datetime.now()
    window = timedelta(minutes=1)
    rate_limits.setdefault(user, [])
    rate_limits[user] = [t for t in rate_limits[user] if now - t <= window]
    if len(rate_limits[user]) >= 5:
        return False
    rate_limits[user].append(now)
    return True

# -------------------------
# Histórico em DB
# -------------------------

def add_history_entry(target, role, content):
    ts = datetime.now().isoformat()
    cursor.execute(
        "INSERT INTO history (target,role,content,timestamp) VALUES (?,?,?,?)",
        (target, role, content, ts)
    )
    conn.commit()
    cursor.execute("""
      DELETE FROM history
       WHERE id IN (
         SELECT id FROM history
          WHERE target=?
          ORDER BY timestamp DESC
          LIMIT -1 OFFSET ?
       )
    """, (target, HISTORY_LIMIT))
    conn.commit()

def get_recent_history(target):
    cursor.execute("""
      SELECT role,content,timestamp
        FROM history
       WHERE target=?
       ORDER BY timestamp DESC
       LIMIT ?
    """, (target, HISTORY_LIMIT))
    rows = cursor.fetchall()
    return [
        {"role": r, "content": c, "timestamp": datetime.fromisoformat(t)}
        for r, c, t in reversed(rows)
    ]

# -------------------------
# Reset diário/mensal
# -------------------------

def update_periods():
    global tokens_today, cost_today, last_reset_daily
    global tokens_month, cost_month, last_reset_monthly

    hoje = date.today()
    if hoje != last_reset_daily:
        log("Reset diário de counters", "DEBUG")
        tokens_today = 0
        cost_today   = 0.0
        last_reset_daily = hoje

    reset_pt = date(hoje.year, hoje.month, monthly_start_day)
    if hoje >= reset_pt and last_reset_monthly < reset_pt:
        log("Reset mensal de counters", "DEBUG")
        tokens_month = 0
        cost_month   = 0.0
        last_reset_monthly = reset_pt

# -------------------------
# Burst summarization
# -------------------------

def maybe_summarize_burst(target):
    hist   = get_recent_history(target)
    now    = datetime.now()
    recent = [e for e in hist if (now - e["timestamp"]).total_seconds() <= burst_window]
    log(f"[BURST CHECK] {len(recent)} msgs nos últimos {burst_window}s (threshold={burst_threshold})", "DEBUG")
    if len(recent) < burst_threshold:
        log("[BURST CHECK] Não atingiu threshold, sem resumo.", "DEBUG")
        return

    chunk = recent[-burst_chunk_size:]
    log(f"[BURST SUMMARY] Disparando resumo de {len(chunk)} msgs", "DEBUG")
    prompt = (
        "Resuma em 2–3 linhas estas mensagens, indicando quem falou cada parte:\n"
        + "\n".join(f"{e['role']}: {e['content']}" for e in chunk)
    )
    log(f"[BURST PROMPT] {prompt}", "DEBUG")

    resp = openai.chat.completions.create(
        model=model,
        messages=[
            {"role":"system","content":"Você é um resumidor de chat IRC."},
            {"role":"user","content":prompt}
        ],
        temperature=0.5,
        max_tokens=150,
        timeout=timeout
    )
    summary = resp.choices[0].message.content.strip()
    log(f"[BURST RESULT] {summary}", "DEBUG")

    cutoff = chunk[0]["timestamp"].isoformat()
    cursor.execute("DELETE FROM history WHERE target=? AND timestamp>=?", (target, cutoff))
    conn.commit()
    add_history_entry(target, "assistant", f"[Resumido] {summary}")

# -------------------------
# Markdown → IRC bold
# -------------------------

def convert_markdown_to_irc(text):
    return re.sub(r"\*\*(.*?)\*\*", lambda m: "\x02"+m.group(1)+"\x02", text)

# -------------------------
# Envio de mensagem
# -------------------------

def send_message(target, message, max_length=392):
    while message:
        part = message[:max_length]
        if len(message) <= max_length:
            to_send = message
            message = ""
        else:
            idx     = part.rfind(" ")
            to_send = part if idx < 0 else part[:idx]
            message = message[len(to_send):].lstrip()
        irc.send(f"PRIVMSG {target} :{to_send}\n".encode())
    log(f"PRIVMSG -> {target}: {to_send}", "DEBUG")

# -------------------------
# Comandos IRC
# -------------------------

def handle_command(cmd, target):
    log(f"[COMANDO] {cmd}", "DEBUG")
    now = datetime.now()
    lc  = cmd.lower()

    if lc == "!help":
        send_message(target, "Comandos: !help, !status, !uptime, !model, !usage, !history")

    elif lc == "!status":
        up = now - start_time
        send_message(target,
            f"GPT-IRC Bot (T800) v{SCRIPT_VERSION} by Rauen • sess up={fmt_delta(up)} • "
            f"tokens sess={total_tokens_used} (~${total_cost_used:.4f}) • model={model} •"
            f"https://github.com/rauenbr/GPT-IRC-Bot-t800"
        )

    elif lc == "!uptime":
        up = now - start_time
        send_message(target, f"Uptime sess: {fmt_delta(up)}")

    elif lc == "!model":
        send_message(target, f"Modelo: {model}")

    elif lc == "!usage":
        send_message(target,
            f"Hoje: {tokens_today} tok (~${cost_today:.4f}) | "
            f"Mês desde dia {monthly_start_day}: {tokens_month} tok (~${cost_month:.4f})"
        )
        first = datetime.fromisoformat(get_meta('first_init'))
        last_init = datetime.fromisoformat(get_meta('last_init'))
        last_conn = datetime.fromisoformat(get_meta('last_conn'))
        send_message(target,
            f"Primeiro init: {first.strftime('%Y-%m-%d %H:%M')}Z "
            f"({fmt_delta(now-first)} atrás)"
        )
        send_message(target,
            f"Último init: {last_init.strftime('%Y-%m-%d %H:%M')}Z "
            f"({fmt_delta(now-last_init)} atrás)"
        )
        send_message(target,
            f"Última conexão: {last_conn.strftime('%Y-%m-%d %H:%M')}Z "
            f"({fmt_delta(now-last_conn)} atrás)"
        )
        li = get_meta('last_init')
        cursor.execute("SELECT COUNT(*) FROM usage WHERE timestamp>=?", (li,))
        calls = cursor.fetchone()[0]
        ru = resource.getrusage(resource.RUSAGE_SELF)
        mem_mb = ru.ru_maxrss / 1024.0
        send_message(target,
            f"API calls: {calls} | Memória RSS: {mem_mb:.1f}MB | "
            f"CPU utime={ru.ru_utime:.2f}s stime={ru.ru_stime:.2f}s"
        )

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

# -------------------------
# Processa pergunta
# -------------------------

def handle_question(user, target, question):
    global total_tokens_used, total_cost_used
    global tokens_today, cost_today, tokens_month, cost_month

    # comandos não entram no histórico
    if question.startswith("!"):
        handle_command(question, target)
        return

    if not check_rate_limit(user):
        send_message(target, "[Rate Limit] muito rápido.")
        return

    update_periods()
    # grava nick real no histórico em vez de sempre "user"
    add_history_entry(target, user, question)

    # monta prompt incluindo quem falou o quê
    hist = get_recent_history(target)
    messages = [{"role": "system", "content": context_message}]
    for e in hist:
        if e["role"] == "assistant":
            messages.append({"role": "assistant", "content": e["content"]})
        else:
            messages.append({"role": "user", "content": f"{e['role']}: {e['content']}"})

    if debug_mode:
        enc = tiktoken.encoding_for_model(model)
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
        log(f"[TOKENS] prompt={usage.prompt_tokens} • completion={usage.completion_tokens} • total={usage.total_tokens}", "DEBUG")

        total_tokens_used += usage.total_tokens
        tokens_today       += usage.total_tokens
        tokens_month       += usage.total_tokens

        rates = PRICING.get(model, PRICING.get(model.split("-")[0], {}))
        cost = ((usage.prompt_tokens/1000)*rates.get("prompt",0)
              + (usage.completion_tokens/1000)*rates.get("completion",0))
        total_cost_used += cost
        cost_today       += cost
        cost_month       += cost
        log(f"[CUSTO] ${cost:.6f}", "DEBUG")

        cursor.execute(
            "INSERT INTO usage VALUES (?,?,?,?,?,?)",
            (datetime.now().isoformat(), model,
             usage.prompt_tokens, usage.completion_tokens,
             usage.total_tokens, cost)
        )
        conn.commit()

        answer = resp.choices[0].message.content.strip()
        add_history_entry(target, "assistant", answer)
        for line in answer.split("\n"):
            if line.strip():
                send_message(target, convert_markdown_to_irc(line))
        log(f"Resposta enviada para {target}: {answer.splitlines()[0]}", "INFO")

    except Exception as e:
        log(f"Erro na API ou interno: {e}", "ERRO")
        send_message(target, "[Erro interno]")

# -------------------------
# Loop principal
# -------------------------

def start_bot():
    connect()
    joined = False
    while True:
        try:
            data = irc.recv(4096).decode("utf-8")
            if raw_mode:
                log(f"[RAW] {data.strip()}", "DEBUG")
        except (UnicodeDecodeError, socket.timeout, ssl.SSLError):
            continue
        except Exception as e:
            log(f"Conexão perdida: {e}", "ERRO")
            reconnect()
            joined = False
            continue

        if not data:
            reconnect()
            joined = False
            continue

        for line in data.strip().split("\n"):
            parts = line.split()
            if not parts: continue

            if parts[0] == "PING":
                irc.send(f"PONG {parts[1]}\n".encode())
                log("PONG enviado ao servidor.", "DEBUG")
                continue

            if parts[1] == "ERROR":
                log("Erro do servidor (ERROR). Reconectando...", "ERRO")
                reconnect(); joined = False; break
            if parts[1] == "KICK" and parts[2] == nickname:
                log("Fui kickado do canal. Reconectando...", "ERRO")
                reconnect(); joined = False; break

            code = parts[1] if len(parts) > 1 else ""
            if code in ("001","004","422","MODE") and not joined:
                log(f"Recebido {code}, fazendo JOIN nos canais...", "DEBUG")
                for ch in channels:
                    irc.send(f"JOIN {ch}\n".encode())
                joined = True
                continue

            if parts[1] == "PRIVMSG":
                user   = parts[0][1:].split('!')[0]
                target = parts[2]
                msg    = ' '.join(parts[3:])[1:]

                # case-insensitive: !comando, prefixo "Nick:", sufixo "Nick?"
                lc_msg     = msg.lower()
                nick_lower = nickname.lower()
                is_command = msg.startswith("!")
                is_prefix  = lc_msg.startswith(f"{nick_lower}:")
                is_suffix_q= lc_msg.endswith(f"{nick_lower}?")

                if target.startswith("#") and (is_command or is_prefix or is_suffix_q):
                    if is_prefix:
                        content = msg[len(nickname)+1:].strip()
                    elif is_suffix_q:
                        content = msg[:-len(nickname)-1].strip()
                    else:
                        content = msg
                    threading.Thread(
                        target=handle_question,
                        args=(user, target, content),
                        daemon=True
                    ).start()

                elif target == nickname:
                    content = msg
                    threading.Thread(
                        target=handle_question,
                        args=(user, user, content),
                        daemon=True
                    ).start()

        time.sleep(0.5)

# -------------------------
# Execução
# -------------------------

if not debug_mode:
    with daemon.DaemonContext(stdout=open(global_log, "a"), stderr=open(global_log, "a")):
        start_bot()
else:
    start_bot()
