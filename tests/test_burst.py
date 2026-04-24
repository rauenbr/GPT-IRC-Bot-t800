from datetime import datetime, timedelta
from threading import Lock
from unittest.mock import Mock

import burst
import state


def test_burst_below_threshold_does_not_call_summary(monkeypatch):
    summary_mock = Mock(return_value=("resumo", {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}))

    monkeypatch.setattr(burst, "generate_summary", summary_mock)
    monkeypatch.setattr(burst, "context_mode", "channelcontext")
    monkeypatch.setattr(burst, "burst_threshold", 3)
    monkeypatch.setattr(burst, "burst_window", 60)
    monkeypatch.setattr(
        burst,
        "get_recent_history",
        lambda _target: [
            {"role": "alice", "content": "oi", "timestamp": datetime.now() - timedelta(seconds=10)},
            {"role": "bob", "content": "fala", "timestamp": datetime.now() - timedelta(seconds=5)},
        ],
    )
    monkeypatch.setattr(burst, "log", lambda *_args, **_kwargs: None)

    burst.maybe_summarize_burst("#canal")

    summary_mock.assert_not_called()


def test_burst_above_threshold_calls_summary_and_stores_result(monkeypatch):
    now = datetime(2026, 4, 24, 12, 0, 0)

    summary_mock = Mock(
        return_value=(
            "resumo consolidado",
            {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5},
        )
    )
    add_history_entry = Mock()
    cursor = Mock()
    conn = Mock()

    class FrozenDateTime:
        @classmethod
        def now(cls):
            return now

    monkeypatch.setattr(burst, "generate_summary", summary_mock)
    monkeypatch.setattr(burst, "context_mode", "channelcontext")
    monkeypatch.setattr(burst, "burst_threshold", 3)
    monkeypatch.setattr(burst, "burst_window", 60)
    monkeypatch.setattr(burst, "burst_chunk_size", 3)
    monkeypatch.setattr(burst, "datetime", FrozenDateTime)
    monkeypatch.setattr(
        burst,
        "get_recent_history",
        lambda _target: [
            {"role": "alice", "content": "msg 1", "timestamp": now - timedelta(seconds=20)},
            {"role": "bob", "content": "msg 2", "timestamp": now - timedelta(seconds=10)},
            {"role": "carol", "content": "msg 3", "timestamp": now - timedelta(seconds=5)},
        ],
    )
    monkeypatch.setattr(burst, "add_history_entry", add_history_entry)
    monkeypatch.setattr(burst, "cursor", cursor)
    monkeypatch.setattr(burst, "conn", conn)
    monkeypatch.setattr(burst, "log", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(state, "db_lock", Lock())

    burst.maybe_summarize_burst("#canal")

    summary_mock.assert_called_once()
    cursor.execute.assert_called_once()
    conn.commit.assert_called_once()
    add_history_entry.assert_called_once_with("#canal", "assistant", "[Resumido] resumo consolidado")
