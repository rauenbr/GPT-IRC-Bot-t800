from datetime import datetime
from threading import Lock
from types import SimpleNamespace
from unittest.mock import Mock

import commands
import state


def test_status_shows_active_nickname(monkeypatch):
    monkeypatch.setattr(state, "current_nickname", "Terminator335")
    monkeypatch.setattr(state, "start_time", commands.datetime.now())
    monkeypatch.setattr(state, "total_tokens_used", 123)
    monkeypatch.setattr(state, "total_cost_used", 0.5)
    monkeypatch.setattr(commands, "send_message", Mock())
    monkeypatch.setattr(commands, "log", lambda *_args, **_kwargs: None)

    commands.handle_command("!status", "#canal")

    sent = commands.send_message.call_args[0][1]
    assert "Bot v" in sent
    assert "nick=Terminator335" in sent
    assert "sess up=" in sent
    assert f"mode={commands.context_mode}" in sent
    assert "tokens sess=" in sent
    assert "model=" in sent


def test_usage_shows_expected_labels(monkeypatch):
    monkeypatch.setattr(state, "tokens_today", 100)
    monkeypatch.setattr(state, "cost_today", 1.25)
    monkeypatch.setattr(state, "tokens_month", 300)
    monkeypatch.setattr(state, "cost_month", 3.75)
    monkeypatch.setattr(state, "db_lock", Lock())
    monkeypatch.setattr(commands, "send_message", Mock())
    monkeypatch.setattr(commands, "log", lambda *_args, **_kwargs: None)

    fake_now = datetime(2026, 4, 24, 15, 0, 0)

    class FrozenDateTime:
        @classmethod
        def now(cls):
            return fake_now

        @classmethod
        def fromisoformat(cls, value):
            return datetime.fromisoformat(value)

    monkeypatch.setattr(commands, "datetime", FrozenDateTime)
    monkeypatch.setattr(
        commands,
        "get_meta",
        lambda key: {
            "first_init": "2026-04-20T10:00:00",
            "last_init": "2026-04-24T12:00:00",
            "last_conn": "2026-04-24T14:00:00",
        }[key],
    )

    cursor = Mock()
    cursor.fetchone.return_value = (3,)
    monkeypatch.setattr(commands, "cursor", cursor)
    monkeypatch.setattr(
        commands,
        "resource",
        SimpleNamespace(
            RUSAGE_SELF=0,
            getrusage=lambda _who: SimpleNamespace(ru_maxrss=2048, ru_utime=1.5, ru_stime=0.5),
        ),
    )

    commands.handle_command("!usage", "#canal")

    sent_messages = [call.args[1] for call in commands.send_message.call_args_list]

    assert any("Hoje:" in msg for msg in sent_messages)
    assert any("Mês desde dia" in msg for msg in sent_messages)
    assert any("Primeiro registro DB:" in msg for msg in sent_messages)
    assert any("Último start do bot:" in msg for msg in sent_messages)
    assert any("Última conexão IRC:" in msg for msg in sent_messages)
    assert any("Contexto:" in msg for msg in sent_messages)
    assert any("mode=" in msg for msg in sent_messages)
    assert any("hist=direct:" in msg for msg in sent_messages)
    assert any("/channel:" in msg for msg in sent_messages)
    assert any("chars=chan:" in msg for msg in sent_messages)
    assert any("/asst:" in msg for msg in sent_messages)
    assert any("/q:" in msg for msg in sent_messages)
    assert any("API calls:" in msg for msg in sent_messages)
    assert any("Memória RSS:" in msg for msg in sent_messages)


def test_usage_handles_none_metadata(monkeypatch):
    monkeypatch.setattr(state, "tokens_today", 100)
    monkeypatch.setattr(state, "cost_today", 1.25)
    monkeypatch.setattr(state, "tokens_month", 300)
    monkeypatch.setattr(state, "cost_month", 3.75)
    monkeypatch.setattr(state, "db_lock", Lock())
    monkeypatch.setattr(commands, "send_message", Mock())
    monkeypatch.setattr(commands, "log", lambda *_args, **_kwargs: None)

    class FrozenDateTime:
        @classmethod
        def now(cls):
            return datetime(2026, 4, 24, 15, 0, 0)

        @classmethod
        def fromisoformat(cls, value):
            return datetime.fromisoformat(value)

    monkeypatch.setattr(commands, "datetime", FrozenDateTime)
    monkeypatch.setattr(commands, "get_meta", lambda _key: None)

    cursor = Mock()
    cursor.fetchone.return_value = (3,)
    monkeypatch.setattr(commands, "cursor", cursor)
    monkeypatch.setattr(
        commands,
        "resource",
        SimpleNamespace(
            RUSAGE_SELF=0,
            getrusage=lambda _who: SimpleNamespace(ru_maxrss=2048, ru_utime=1.5, ru_stime=0.5),
        ),
    )

    commands.handle_command("!usage", "#canal")

    sent_messages = [call.args[1] for call in commands.send_message.call_args_list]
    assert any("Primeiro registro DB: indisponível" in msg for msg in sent_messages)
    assert any("Último start do bot: indisponível" in msg for msg in sent_messages)
    assert any("Última conexão IRC: indisponível" in msg for msg in sent_messages)


def test_usage_handles_invalid_metadata(monkeypatch):
    monkeypatch.setattr(state, "tokens_today", 100)
    monkeypatch.setattr(state, "cost_today", 1.25)
    monkeypatch.setattr(state, "tokens_month", 300)
    monkeypatch.setattr(state, "cost_month", 3.75)
    monkeypatch.setattr(state, "db_lock", Lock())
    monkeypatch.setattr(commands, "send_message", Mock())
    monkeypatch.setattr(commands, "log", lambda *_args, **_kwargs: None)

    class FrozenDateTime:
        @classmethod
        def now(cls):
            return datetime(2026, 4, 24, 15, 0, 0)

        @classmethod
        def fromisoformat(cls, value):
            return datetime.fromisoformat(value)

    monkeypatch.setattr(commands, "datetime", FrozenDateTime)
    monkeypatch.setattr(commands, "get_meta", lambda _key: "nao-e-data")

    cursor = Mock()
    cursor.fetchone.return_value = (3,)
    monkeypatch.setattr(commands, "cursor", cursor)
    monkeypatch.setattr(
        commands,
        "resource",
        SimpleNamespace(
            RUSAGE_SELF=0,
            getrusage=lambda _who: SimpleNamespace(ru_maxrss=2048, ru_utime=1.5, ru_stime=0.5),
        ),
    )

    commands.handle_command("!usage", "#canal")

    sent_messages = [call.args[1] for call in commands.send_message.call_args_list]
    assert any("Primeiro registro DB: indisponível" in msg for msg in sent_messages)
    assert any("Último start do bot: indisponível" in msg for msg in sent_messages)
    assert any("Última conexão IRC: indisponível" in msg for msg in sent_messages)


def test_help_lists_expected_commands_but_not_clear(monkeypatch):
    monkeypatch.setattr(commands, "send_message", Mock())
    monkeypatch.setattr(commands, "log", lambda *_args, **_kwargs: None)

    commands.handle_command("!help", "#canal")

    sent = commands.send_message.call_args[0][1]
    assert "!help" in sent
    assert "!status" in sent
    assert "!uptime" in sent
    assert "!model" in sent
    assert "!usage" in sent
    assert "!history" in sent
    assert "!clear" not in sent


def test_model_shows_current_model(monkeypatch):
    monkeypatch.setattr(commands, "send_message", Mock())
    monkeypatch.setattr(commands, "log", lambda *_args, **_kwargs: None)

    commands.handle_command("!model", "#canal")

    commands.send_message.assert_called_once_with("#canal", f"Modelo: {commands.model}")


def test_uptime_shows_session_uptime(monkeypatch):
    monkeypatch.setattr(state, "start_time", commands.datetime.now())
    monkeypatch.setattr(commands, "send_message", Mock())
    monkeypatch.setattr(commands, "log", lambda *_args, **_kwargs: None)

    commands.handle_command("!uptime", "#canal")

    sent = commands.send_message.call_args[0][1]
    assert "Uptime sess:" in sent


def test_history_debug_mode_with_entries(monkeypatch):
    monkeypatch.setattr(commands, "debug_mode", True)
    monkeypatch.setattr(commands, "send_message", Mock())
    monkeypatch.setattr(commands, "log", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        commands,
        "get_recent_history",
        lambda _target: [
            {"timestamp": datetime(2026, 4, 24, 10, 0, 0), "role": "alice", "content": "oi"},
            {"timestamp": datetime(2026, 4, 24, 10, 1, 0), "role": "assistant", "content": "resposta"},
        ],
    )

    commands.handle_command("!history", "#canal")

    sent_messages = [call.args[1] for call in commands.send_message.call_args_list]
    assert any("Histórico recente:" in msg for msg in sent_messages)
    assert any("alice: oi" in msg for msg in sent_messages)
    assert any("assistant: resposta" in msg for msg in sent_messages)


def test_history_debug_mode_with_empty_history(monkeypatch):
    monkeypatch.setattr(commands, "debug_mode", True)
    monkeypatch.setattr(commands, "send_message", Mock())
    monkeypatch.setattr(commands, "log", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(commands, "get_recent_history", lambda _target: [])

    commands.handle_command("!history", "#canal")

    commands.send_message.assert_called_once_with("#canal", "Histórico vazio.")


def test_history_non_debug_mode(monkeypatch):
    monkeypatch.setattr(commands, "debug_mode", False)
    monkeypatch.setattr(commands, "send_message", Mock())
    monkeypatch.setattr(commands, "log", lambda *_args, **_kwargs: None)

    commands.handle_command("!history", "#canal")

    commands.send_message.assert_called_once_with("#canal", "O comando !history só funciona em modo debug.")


def test_clear_deletes_history_for_target(monkeypatch):
    monkeypatch.setattr(state, "db_lock", Lock())
    monkeypatch.setattr(commands, "send_message", Mock())
    monkeypatch.setattr(commands, "log", lambda *_args, **_kwargs: None)
    cursor = Mock()
    conn = Mock()
    monkeypatch.setattr(commands, "cursor", cursor)
    monkeypatch.setattr(commands, "conn", conn)

    commands.handle_command("!clear", "#canal")

    cursor.execute.assert_called_once_with("DELETE FROM history WHERE target=?", ("#canal",))
    conn.commit.assert_called_once()
    commands.send_message.assert_called_once_with("#canal", "Histórico limpo.")


def test_unknown_command_returns_help_hint(monkeypatch):
    monkeypatch.setattr(commands, "send_message", Mock())
    monkeypatch.setattr(commands, "log", lambda *_args, **_kwargs: None)

    commands.handle_command("!naoexiste", "#canal")

    commands.send_message.assert_called_once_with("#canal", "Comando desconhecido. Use !help.")
