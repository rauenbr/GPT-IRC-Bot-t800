import re
from threading import Lock
from unittest.mock import Mock

import irc_client
import state
from irc_client import generate_random_nick, irc_send_raw, join_channels


def test_generate_random_nick_matches_expected_pattern():
    nick = generate_random_nick("Terminator")

    assert re.fullmatch(r"Terminator\d{3}", nick)


def test_generate_random_nick_does_not_exceed_max_length():
    nick = generate_random_nick("TerminatorMuitoGrande")

    assert len(nick) <= 16
    assert re.fullmatch(r".+\d{3}", nick)


def test_generate_random_nick_with_empty_base_returns_three_digits():
    nick = generate_random_nick("")

    assert re.fullmatch(r"\d{3}", nick)
    assert len(nick) == 3


def test_irc_send_raw_appends_newline(monkeypatch):
    irc = Mock()
    monkeypatch.setattr(state, "irc", irc)
    monkeypatch.setattr(state, "irc_lock", Lock())

    irc_send_raw("NICK Terminator335")

    irc.send.assert_called_once_with(b"NICK Terminator335\n")
    sent = irc.send.call_args[0][0]
    assert isinstance(sent, bytes)
    assert sent.endswith(b"\n")
    assert not sent.endswith(b"\r\n")


def test_join_channels_sends_join_for_each_configured_channel(monkeypatch):
    send_raw = Mock()
    monkeypatch.setattr(irc_client, "channels", ["#warez", "#teste"])
    monkeypatch.setattr(irc_client, "irc_send_raw", send_raw)

    join_channels()

    assert send_raw.call_args_list[0].args[0] == "JOIN #warez"
    assert send_raw.call_args_list[1].args[0] == "JOIN #teste"


def test_connect_without_ssl_and_without_password(monkeypatch):
    sock = Mock()
    socket_ctor = Mock(return_value=sock)
    set_meta = Mock()

    monkeypatch.setattr(irc_client, "usessl", False)
    monkeypatch.setattr(irc_client, "password", "")
    monkeypatch.setattr(irc_client.socket, "socket", socket_ctor)
    monkeypatch.setattr(irc_client, "set_meta", set_meta)
    monkeypatch.setattr(irc_client, "log", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(state, "current_nickname", None)

    irc_client.connect()

    socket_ctor.assert_called_once_with(irc_client.socket.AF_INET, irc_client.socket.SOCK_STREAM)
    sock.settimeout.assert_called_once_with(30)
    sock.connect.assert_called_once_with((irc_client.server, irc_client.port))
    assert sock.send.call_args_list[0].args[0] == f"NICK {irc_client.nickname}\n".encode()
    assert sock.send.call_args_list[1].args[0] == f"USER {irc_client.ident} 0 * :{irc_client.realname}\n".encode()
    assert state.current_nickname == irc_client.nickname
    assert set_meta.call_count == 1
    assert set_meta.call_args[0][0] == "last_conn"


def test_connect_with_password_sends_pass_before_nick_and_user(monkeypatch):
    sock = Mock()
    socket_ctor = Mock(return_value=sock)
    set_meta = Mock()

    monkeypatch.setattr(irc_client, "usessl", False)
    monkeypatch.setattr(irc_client, "password", "senha")
    monkeypatch.setattr(irc_client.socket, "socket", socket_ctor)
    monkeypatch.setattr(irc_client, "set_meta", set_meta)
    monkeypatch.setattr(irc_client, "log", lambda *_args, **_kwargs: None)

    irc_client.connect()

    assert sock.send.call_args_list[0].args[0] == b"PASS senha\n"
    assert sock.send.call_args_list[1].args[0] == f"NICK {irc_client.nickname}\n".encode()
    assert sock.send.call_args_list[2].args[0] == f"USER {irc_client.ident} 0 * :{irc_client.realname}\n".encode()


def test_connect_with_ssl_wraps_socket_and_connects_wrapped_socket(monkeypatch):
    raw_sock = Mock()
    wrapped_sock = Mock()
    ctx = Mock()
    ctx.wrap_socket.return_value = wrapped_sock
    socket_ctor = Mock(return_value=raw_sock)
    create_ctx = Mock(return_value=ctx)
    set_meta = Mock()

    monkeypatch.setattr(irc_client, "usessl", True)
    monkeypatch.setattr(irc_client, "password", "")
    monkeypatch.setattr(irc_client.socket, "socket", socket_ctor)
    monkeypatch.setattr(irc_client.ssl, "create_default_context", create_ctx)
    monkeypatch.setattr(irc_client, "set_meta", set_meta)
    monkeypatch.setattr(irc_client, "log", lambda *_args, **_kwargs: None)

    irc_client.connect()

    assert ctx.check_hostname is False
    assert ctx.verify_mode == irc_client.ssl.CERT_NONE
    ctx.wrap_socket.assert_called_once_with(raw_sock, server_hostname=irc_client.server)
    wrapped_sock.connect.assert_called_once_with((irc_client.server, irc_client.port))


def test_reconnect_closes_sleeps_and_connects(monkeypatch):
    irc = Mock()
    sleep = Mock()
    connect = Mock()

    monkeypatch.setattr(state, "irc", irc)
    monkeypatch.setattr(irc_client.time, "sleep", sleep)
    monkeypatch.setattr(irc_client, "connect", connect)
    monkeypatch.setattr(irc_client, "log", lambda *_args, **_kwargs: None)

    irc_client.reconnect()

    irc.close.assert_called_once()
    sleep.assert_called_once_with(5)
    connect.assert_called_once()


def test_reconnect_ignores_close_failure_and_continues(monkeypatch):
    irc = Mock()
    irc.close.side_effect = Exception("falha no close")
    sleep = Mock()
    connect = Mock()

    monkeypatch.setattr(state, "irc", irc)
    monkeypatch.setattr(irc_client.time, "sleep", sleep)
    monkeypatch.setattr(irc_client, "connect", connect)
    monkeypatch.setattr(irc_client, "log", lambda *_args, **_kwargs: None)

    irc_client.reconnect()

    sleep.assert_called_once_with(5)
    connect.assert_called_once()
