import sqlite3
from datetime import datetime
from threading import Lock

import state
import storage


class FakeDateTime(datetime):
    current = datetime(2026, 4, 24, 15, 0, 0)

    @classmethod
    def now(cls, tz=None):
        if tz is not None:
            return tz.fromutc(cls.current.replace(tzinfo=tz))
        return cls.current

    @classmethod
    def fromisoformat(cls, value):
        return datetime.fromisoformat(value)


def setup_memory_db(monkeypatch):
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE usage (
        timestamp TEXT,
        model TEXT,
        prompt_tokens INTEGER,
        completion_tokens INTEGER,
        total_tokens INTEGER,
        cost REAL
    )""")
    cursor.execute("""
    CREATE TABLE history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        target TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        timestamp TEXT NOT NULL
    )""")
    cursor.execute("""
    CREATE TABLE metadata (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )""")
    conn.commit()

    monkeypatch.setattr(storage, "conn", conn)
    monkeypatch.setattr(storage, "cursor", cursor)
    monkeypatch.setattr(state, "db_lock", Lock())
    monkeypatch.setattr(storage, "log", lambda *_args, **_kwargs: None)
    return conn, cursor


def reset_state_counters():
    state.tokens_today = 0
    state.cost_today = 0.0
    state.tokens_month = 0
    state.cost_month = 0.0


def test_set_meta_and_get_meta(monkeypatch):
    setup_memory_db(monkeypatch)

    storage.set_meta("key1", "value1")

    assert storage.get_meta("key1") == "value1"


def test_get_meta_returns_none_for_missing_key(monkeypatch):
    setup_memory_db(monkeypatch)

    assert storage.get_meta("missing") is None


def test_set_meta_replaces_existing_value(monkeypatch):
    setup_memory_db(monkeypatch)

    storage.set_meta("key1", "value1")
    storage.set_meta("key1", "value2")

    assert storage.get_meta("key1") == "value2"


def test_get_history_limit_for_private_target(monkeypatch):
    monkeypatch.setattr(storage, "history_limit_direct", 8)

    assert storage.get_history_limit_for_target("alice") == 8


def test_get_history_limit_for_channel_in_direct_mode(monkeypatch):
    monkeypatch.setattr(storage, "context_mode", "direct")
    monkeypatch.setattr(storage, "history_limit_direct", 8)

    assert storage.get_history_limit_for_target("#canal") == 8


def test_get_history_limit_for_channel_in_channelcontext_mode(monkeypatch):
    monkeypatch.setattr(storage, "context_mode", "channelcontext")
    monkeypatch.setattr(storage, "history_limit_channelcontext", 12)

    assert storage.get_history_limit_for_target("#canal") == 12


def test_add_history_entry_inserts_record(monkeypatch):
    conn, cursor = setup_memory_db(monkeypatch)
    monkeypatch.setattr(storage, "history_limit_direct", 10)
    monkeypatch.setattr(storage, "context_mode", "direct")
    monkeypatch.setattr(storage, "datetime", FakeDateTime)

    storage.add_history_entry("alice", "user", "oi")

    cursor.execute("SELECT target, role, content FROM history")
    assert cursor.fetchall() == [("alice", "user", "oi")]
    conn.close()


def test_add_history_entry_respects_limit_per_target(monkeypatch):
    conn, cursor = setup_memory_db(monkeypatch)
    monkeypatch.setattr(storage, "history_limit_direct", 2)
    monkeypatch.setattr(storage, "context_mode", "direct")
    monkeypatch.setattr(storage, "datetime", FakeDateTime)

    for idx in range(3):
        FakeDateTime.current = datetime(2026, 4, 24, 15, 0, idx)
        storage.add_history_entry("alice", "user", f"msg{idx}")

    cursor.execute("SELECT content FROM history WHERE target=? ORDER BY timestamp", ("alice",))
    assert [row[0] for row in cursor.fetchall()] == ["msg1", "msg2"]
    conn.close()


def test_add_history_entry_does_not_trim_other_targets(monkeypatch):
    conn, cursor = setup_memory_db(monkeypatch)
    monkeypatch.setattr(storage, "history_limit_direct", 2)
    monkeypatch.setattr(storage, "context_mode", "direct")
    monkeypatch.setattr(storage, "datetime", FakeDateTime)

    for idx in range(3):
        FakeDateTime.current = datetime(2026, 4, 24, 15, 0, idx)
        storage.add_history_entry("alice", "user", f"a{idx}")
    storage.add_history_entry("bob", "user", "b0")

    cursor.execute("SELECT content FROM history WHERE target=? ORDER BY timestamp", ("bob",))
    assert [row[0] for row in cursor.fetchall()] == ["b0"]
    conn.close()


def test_get_recent_history_returns_chronological_order(monkeypatch):
    conn, cursor = setup_memory_db(monkeypatch)
    cursor.executemany(
        "INSERT INTO history (target, role, content, timestamp) VALUES (?,?,?,?)",
        [
            ("#canal", "user", "primeira", "2026-04-24T10:00:00"),
            ("#canal", "assistant", "segunda", "2026-04-24T10:01:00"),
        ],
    )
    conn.commit()

    hist = storage.get_recent_history("#canal")

    assert [entry["content"] for entry in hist] == ["primeira", "segunda"]
    assert isinstance(hist[0]["timestamp"], datetime)
    conn.close()


def test_get_recent_history_respects_explicit_limit(monkeypatch):
    conn, cursor = setup_memory_db(monkeypatch)
    cursor.executemany(
        "INSERT INTO history (target, role, content, timestamp) VALUES (?,?,?,?)",
        [
            ("#canal", "user", "m1", "2026-04-24T10:00:00"),
            ("#canal", "user", "m2", "2026-04-24T10:01:00"),
            ("#canal", "user", "m3", "2026-04-24T10:02:00"),
        ],
    )
    conn.commit()

    hist = storage.get_recent_history("#canal", limit=2)

    assert [entry["content"] for entry in hist] == ["m2", "m3"]
    conn.close()


def test_get_recent_history_ignores_invalid_timestamp(monkeypatch):
    conn, cursor = setup_memory_db(monkeypatch)
    cursor.executemany(
        "INSERT INTO history (target, role, content, timestamp) VALUES (?,?,?,?)",
        [
            ("#canal", "user", "valida", "2026-04-24T10:00:00"),
            ("#canal", "user", "invalida", "not-a-date"),
        ],
    )
    conn.commit()

    hist = storage.get_recent_history("#canal")

    assert [entry["content"] for entry in hist] == ["valida"]
    conn.close()


def test_load_metadata_and_counters_clears_history_on_start(monkeypatch):
    conn, cursor = setup_memory_db(monkeypatch)
    reset_state_counters()
    monkeypatch.setattr(storage, "datetime", FakeDateTime)
    monkeypatch.setattr(storage.config, "getboolean", lambda section, key, fallback=False: True if key == "clear_history_on_start" else fallback)

    cursor.execute("INSERT INTO history (target, role, content, timestamp) VALUES (?,?,?,?)", ("#canal", "user", "oi", "2026-04-24T10:00:00"))
    conn.commit()

    storage.load_metadata_and_counters()

    cursor.execute("SELECT COUNT(*) FROM history")
    assert cursor.fetchone()[0] == 0
    conn.close()


def test_load_metadata_and_counters_clears_history_when_context_changes(monkeypatch):
    conn, cursor = setup_memory_db(monkeypatch)
    reset_state_counters()
    monkeypatch.setattr(storage, "datetime", FakeDateTime)
    monkeypatch.setattr(storage.config, "getboolean", lambda *_args, **_kwargs: False)

    storage.set_meta("last_context", "antigo")
    cursor.execute("INSERT INTO history (target, role, content, timestamp) VALUES (?,?,?,?)", ("#canal", "user", "oi", "2026-04-24T10:00:00"))
    conn.commit()

    storage.load_metadata_and_counters()

    cursor.execute("SELECT COUNT(*) FROM history")
    assert cursor.fetchone()[0] == 0
    assert storage.get_meta("last_context") == storage.context_message
    conn.close()


def test_load_metadata_and_counters_creates_first_init_when_missing(monkeypatch):
    conn, _cursor = setup_memory_db(monkeypatch)
    reset_state_counters()
    monkeypatch.setattr(storage, "datetime", FakeDateTime)
    monkeypatch.setattr(storage.config, "getboolean", lambda *_args, **_kwargs: False)

    storage.load_metadata_and_counters()

    assert storage.get_meta("first_init") == FakeDateTime.current.isoformat()
    assert storage.get_meta("last_init") == FakeDateTime.current.isoformat()
    conn.close()


def test_load_metadata_and_counters_preserves_first_init_when_existing(monkeypatch):
    conn, _cursor = setup_memory_db(monkeypatch)
    reset_state_counters()
    monkeypatch.setattr(storage, "datetime", FakeDateTime)
    monkeypatch.setattr(storage.config, "getboolean", lambda *_args, **_kwargs: False)
    storage.set_meta("first_init", "2026-04-01T08:00:00")

    storage.load_metadata_and_counters()

    assert storage.get_meta("first_init") == "2026-04-01T08:00:00"
    assert storage.get_meta("last_init") == FakeDateTime.current.isoformat()
    conn.close()


def test_load_metadata_and_counters_calculates_daily_counters(monkeypatch):
    conn, cursor = setup_memory_db(monkeypatch)
    reset_state_counters()
    monkeypatch.setattr(storage, "datetime", FakeDateTime)
    monkeypatch.setattr(storage.config, "getboolean", lambda *_args, **_kwargs: False)
    cursor.executemany(
        "INSERT INTO usage VALUES (?,?,?,?,?,?)",
        [
            ("2026-04-24T09:00:00", "gpt-4o", 1, 1, 10, 1.0),
            ("2026-04-23T09:00:00", "gpt-4o", 1, 1, 99, 9.9),
        ],
    )
    conn.commit()

    storage.load_metadata_and_counters()

    assert state.tokens_today == 10
    assert state.cost_today == 1.0
    conn.close()


def test_load_metadata_and_counters_calculates_monthly_counters(monkeypatch):
    conn, cursor = setup_memory_db(monkeypatch)
    reset_state_counters()
    monkeypatch.setattr(storage, "datetime", FakeDateTime)
    monkeypatch.setattr(storage.config, "getboolean", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(storage, "monthly_start_day", 20)
    cursor.executemany(
        "INSERT INTO usage VALUES (?,?,?,?,?,?)",
        [
            ("2026-04-22T09:00:00", "gpt-4o", 1, 1, 20, 2.0),
            ("2026-04-10T09:00:00", "gpt-4o", 1, 1, 99, 9.9),
        ],
    )
    conn.commit()

    storage.load_metadata_and_counters()

    assert state.tokens_month == 20
    assert state.cost_month == 2.0
    conn.close()


def test_load_metadata_and_counters_clears_old_history(monkeypatch):
    conn, cursor = setup_memory_db(monkeypatch)
    reset_state_counters()
    monkeypatch.setattr(storage, "datetime", FakeDateTime)
    monkeypatch.setattr(storage.config, "getboolean", lambda *_args, **_kwargs: False)
    cursor.execute("INSERT INTO history (target, role, content, timestamp) VALUES (?,?,?,?)", ("#canal", "user", "old", "2026-04-24T14:00:00"))
    conn.commit()

    storage.load_metadata_and_counters()

    cursor.execute("SELECT COUNT(*) FROM history")
    assert cursor.fetchone()[0] == 0
    conn.close()


def test_load_metadata_and_counters_ignores_invalid_max_timestamp(monkeypatch):
    conn, cursor = setup_memory_db(monkeypatch)
    reset_state_counters()
    monkeypatch.setattr(storage, "datetime", FakeDateTime)
    monkeypatch.setattr(storage.config, "getboolean", lambda *_args, **_kwargs: False)
    storage.set_meta("last_context", storage.context_message)
    cursor.execute("INSERT INTO history (target, role, content, timestamp) VALUES (?,?,?,?)", ("#canal", "user", "bad", "not-a-date"))
    conn.commit()

    storage.load_metadata_and_counters()

    cursor.execute("SELECT COUNT(*) FROM history")
    assert cursor.fetchone()[0] == 1
    conn.close()
