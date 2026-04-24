#!/usr/bin/env python3
"""
Persistência SQLite e histórico do T800.
"""

import sqlite3
from datetime import datetime, timedelta

import state
from config import (
    config,
    usage_db,
    context_message,
    monthly_start_day,
    history_limit_direct,
    history_limit_channelcontext,
    context_mode,
)
from logging_utils import log
from periods import get_monthly_cycle_start

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


def _safe_fromisoformat(value):
    try:
        if not value:
            return None
        return datetime.fromisoformat(value)
    except Exception:
        return None

def set_meta(key, value):
    with state.db_lock:
        cursor.execute(
            "INSERT OR REPLACE INTO metadata (key,value) VALUES (?,?)",
            (key, value)
        )
        conn.commit()

def get_meta(key):
    with state.db_lock:
        cursor.execute("SELECT value FROM metadata WHERE key=?", (key,))
        row = cursor.fetchone()
    return row[0] if row else None

def load_metadata_and_counters():
    if config.getboolean("bot", "clear_history_on_start", fallback=False):
        log("Limpando histórico ao iniciar...", "INFO")
        with state.db_lock:
            cursor.execute("DELETE FROM history")
            conn.commit()

    last_context = get_meta("last_context")
    if last_context != context_message:
        log("Context mudou, limpando histórico...", "INFO")
        with state.db_lock:
            cursor.execute("DELETE FROM history")
            conn.commit()
        set_meta("last_context", context_message)

    now_dt = datetime.now()
    now = now_dt.isoformat()
    if not get_meta("first_init"):
        set_meta("first_init", now)
    set_meta("last_init", now)

    day_start = now_dt.replace(
        hour=0, minute=0, second=0, microsecond=0
    ).isoformat()

    with state.db_lock:
        cursor.execute(
            "SELECT SUM(total_tokens), SUM(cost) FROM usage WHERE timestamp>=?",
            (day_start,)
        )
        tok_sum, cost_sum = cursor.fetchone()

    state.tokens_today = tok_sum or 0
    state.cost_today = cost_sum or 0.0

    monthly_cycle_start = get_monthly_cycle_start(now_dt.date(), monthly_start_day)
    m_start = now_dt.replace(
        year=monthly_cycle_start.year,
        month=monthly_cycle_start.month,
        day=monthly_cycle_start.day,
        hour=0, minute=0, second=0, microsecond=0
    )

    with state.db_lock:
        cursor.execute(
            "SELECT SUM(total_tokens), SUM(cost) FROM usage WHERE timestamp>=?",
            (m_start.isoformat(),)
        )
        tok_sum, cost_sum = cursor.fetchone()

    state.tokens_month = tok_sum or 0
    state.cost_month = cost_sum or 0.0

    with state.db_lock:
        cursor.execute("SELECT MAX(timestamp) FROM history")
        row = cursor.fetchone()[0]

    last_history_dt = _safe_fromisoformat(row)
    if last_history_dt and (now_dt - last_history_dt) > timedelta(minutes=30):
        with state.db_lock:
            cursor.execute("DELETE FROM history")
            conn.commit()

# -------------------------
# Histórico em DB
# -------------------------

def get_history_limit_for_target(target):
    if target.startswith("#"):
        if context_mode == "channelcontext":
            return history_limit_channelcontext
        return history_limit_direct
    return history_limit_direct

def add_history_entry(target, role, content):
    ts = datetime.now().isoformat()
    limit = get_history_limit_for_target(target)

    with state.db_lock:
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
        """, (target, limit))
        conn.commit()

def get_recent_history(target, limit=None):
    if limit is None:
        limit = get_history_limit_for_target(target)

    with state.db_lock:
        cursor.execute("""
          SELECT role,content,timestamp
            FROM history
           WHERE target=?
           ORDER BY timestamp DESC
           LIMIT ?
        """, (target, limit))
        rows = cursor.fetchall()

    result = []
    for r, c, t in reversed(rows):
        parsed = _safe_fromisoformat(t)
        if parsed is None:
            continue
        result.append(
            {
                "role": r,
                "content": c,
                "timestamp": parsed,
            }
        )
    return result
