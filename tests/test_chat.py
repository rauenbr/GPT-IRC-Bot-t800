from unittest.mock import Mock

import chat
import state
from irc_parser import parse_irc_line


def setup_chat_defaults(monkeypatch):
    monkeypatch.setattr(chat, "log", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(chat, "join_channels", Mock())
    monkeypatch.setattr(chat, "reconnect", Mock())
    monkeypatch.setattr(chat, "irc_send_raw", Mock())
    monkeypatch.setattr(chat, "generate_random_nick", Mock(return_value="Terminator335"))
    monkeypatch.setattr(chat, "handle_question", Mock())
    monkeypatch.setattr(chat, "extract_trigger_content", lambda _msg: (False, None))
    monkeypatch.setattr(chat, "should_store_passive_channel_message", lambda *_args: False)
    monkeypatch.setattr(chat, "add_history_entry", Mock())
    monkeypatch.setattr(chat, "maybe_summarize_burst", Mock())
    monkeypatch.setattr(state, "current_nickname", None)
    monkeypatch.setattr(state, "executor", Mock())
    monkeypatch.setattr(state, "nick_retry_count", 0)


def test_433_generates_random_nick_sends_nick_and_waits_for_confirmation(monkeypatch):
    setup_chat_defaults(monkeypatch)
    monkeypatch.setattr(state, "current_nickname", "Terminator")

    joined, should_break = chat.process_irc_message(
        {"command": "433", "params": ["*", "Terminator", "Nickname is already in use"], "prefix": "server"},
        joined=False,
    )

    assert joined is False
    assert should_break is False
    assert state.current_nickname == "Terminator"
    chat.generate_random_nick.assert_called_once_with("Terminator")
    chat.irc_send_raw.assert_called_once_with("NICK Terminator335")
    chat.reconnect.assert_not_called()


def test_private_message_uses_active_random_nick(monkeypatch):
    setup_chat_defaults(monkeypatch)
    monkeypatch.setattr(state, "current_nickname", "Terminator335")

    joined, should_break = chat.process_irc_message(
        {
            "command": "PRIVMSG",
            "params": ["Terminator335", "mensagem privada"],
            "prefix": "alice!u@h",
        },
        joined=False,
    )

    assert joined is False
    assert should_break is False
    state.executor.submit.assert_called_once_with(chat.handle_question, "alice", "alice", "mensagem privada")


def test_kick_uses_active_random_nick(monkeypatch):
    setup_chat_defaults(monkeypatch)
    monkeypatch.setattr(state, "current_nickname", "Terminator335")

    joined, should_break = chat.process_irc_message(
        {
            "command": "KICK",
            "params": ["#canal", "Terminator335", "bye"],
            "prefix": "server",
        },
        joined=True,
    )

    assert joined is True
    assert should_break is False
    chat.irc_send_raw.assert_called_once_with("JOIN #canal")
    chat.reconnect.assert_not_called()


def test_ping_sends_pong(monkeypatch):
    setup_chat_defaults(monkeypatch)

    joined, should_break = chat.process_irc_message(
        {"command": "PING", "params": ["12345"], "prefix": None},
        joined=False,
    )

    assert joined is False
    assert should_break is False
    chat.irc_send_raw.assert_called_once_with("PONG :12345")


def test_001_004_422_join_only_once(monkeypatch):
    setup_chat_defaults(monkeypatch)

    joined, should_break = chat.process_irc_message(
        {"command": "001", "params": ["Terminator"], "prefix": "server"},
        joined=False,
    )
    assert joined is True
    assert should_break is False

    joined, should_break = chat.process_irc_message(
        {"command": "004", "params": [], "prefix": "server"},
        joined=joined,
    )
    assert joined is True
    assert should_break is False

    joined, should_break = chat.process_irc_message(
        {"command": "422", "params": [], "prefix": "server"},
        joined=joined,
    )
    assert joined is True
    assert should_break is False

    chat.join_channels.assert_called_once()


def test_error_calls_reconnect_and_breaks(monkeypatch):
    setup_chat_defaults(monkeypatch)

    joined, should_break = chat.process_irc_message(
        {"command": "ERROR", "params": ["bye"], "prefix": "server"},
        joined=True,
    )

    assert joined is False
    assert should_break is True
    chat.reconnect.assert_called_once()


def test_privmsg_channel_with_trigger_dispatches_handle_question(monkeypatch):
    setup_chat_defaults(monkeypatch)
    monkeypatch.setattr(chat, "extract_trigger_content", lambda _msg: (True, "conteudo"))

    joined, should_break = chat.process_irc_message(
        {
            "command": "PRIVMSG",
            "params": ["#canal", "Terminator: oi"],
            "prefix": "alice!u@h",
        },
        joined=False,
    )

    assert joined is False
    assert should_break is False
    state.executor.submit.assert_called_once_with(chat.handle_question, "alice", "#canal", "conteudo")


def test_channelcontext_stores_history_when_message_is_applicable(monkeypatch):
    setup_chat_defaults(monkeypatch)
    monkeypatch.setattr(chat, "extract_trigger_content", lambda _msg: (False, None))
    monkeypatch.setattr(chat, "should_store_passive_channel_message", lambda *_args: True)
    monkeypatch.setattr(chat, "context_mode", "channelcontext")

    joined, should_break = chat.process_irc_message(
        {
            "command": "PRIVMSG",
            "params": ["#canal", "mensagem normal de canal"],
            "prefix": "alice!u@h",
        },
        joined=False,
    )

    assert joined is False
    assert should_break is False
    chat.add_history_entry.assert_called_once()


def test_normal_channel_message_without_trigger_does_nothing(monkeypatch):
    setup_chat_defaults(monkeypatch)

    joined, should_break = chat.process_irc_message(
        {
            "command": "PRIVMSG",
            "params": ["#canal", "mensagem normal"],
            "prefix": "alice!u@h",
        },
        joined=False,
    )

    assert joined is False
    assert should_break is False
    state.executor.submit.assert_not_called()
    chat.add_history_entry.assert_not_called()


def test_sequential_433_then_001_joins_successfully(monkeypatch):
    setup_chat_defaults(monkeypatch)
    monkeypatch.setattr(state, "current_nickname", "Terminator")

    joined, should_break = chat.process_irc_message(
        {"command": "433", "params": ["*", "Terminator", "in use"], "prefix": "server"},
        joined=False,
    )
    assert joined is False
    assert should_break is False
    assert state.current_nickname == "Terminator"
    chat.irc_send_raw.assert_called_once_with("NICK Terminator335")

    joined, should_break = chat.process_irc_message(
        {"command": "001", "params": ["Terminator335"], "prefix": "server"},
        joined=joined,
    )
    assert joined is True
    assert should_break is False
    assert state.current_nickname == "Terminator335"
    chat.join_channels.assert_called_once()


def test_numeric_432_also_triggers_nick_fallback(monkeypatch):
    setup_chat_defaults(monkeypatch)
    monkeypatch.setattr(state, "current_nickname", "Terminator")

    joined, should_break = chat.process_irc_message(
        {"command": "432", "params": ["*", "Terminator", "Erroneous nickname"], "prefix": "server"},
        joined=False,
    )

    assert joined is False
    assert should_break is False
    chat.generate_random_nick.assert_called_once_with("Terminator")
    chat.irc_send_raw.assert_called_once_with("NICK Terminator335")
    chat.reconnect.assert_not_called()


def test_excessive_nick_retries_reconnects(monkeypatch):
    setup_chat_defaults(monkeypatch)
    monkeypatch.setattr(state, "nick_retry_count", chat.MAX_NICK_RETRY_COUNT)

    joined, should_break = chat.process_irc_message(
        {"command": "433", "params": ["*", "Terminator", "in use"], "prefix": "server"},
        joined=True,
    )

    assert joined is False
    assert should_break is True
    chat.reconnect.assert_called_once()


def test_nick_event_updates_current_nickname(monkeypatch):
    setup_chat_defaults(monkeypatch)
    monkeypatch.setattr(state, "current_nickname", "Terminator335")

    joined, should_break = chat.process_irc_message(
        {"command": "NICK", "params": ["Terminator777"], "prefix": "Terminator335!u@h"},
        joined=False,
    )

    assert joined is False
    assert should_break is False
    assert state.current_nickname == "Terminator777"


def test_irc_send_raw_appends_newline():
    parsed = parse_irc_line(":server 433 * Terminator :Nickname is already in use")
    assert parsed["command"] == "433"
