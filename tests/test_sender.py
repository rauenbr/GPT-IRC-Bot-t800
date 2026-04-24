from threading import Lock
from unittest.mock import Mock

import response_pipeline
import state


def test_send_message_sends_privmsg(monkeypatch):
    irc = Mock()
    monkeypatch.setattr(state, "irc", irc)
    monkeypatch.setattr(state, "irc_lock", Lock())
    monkeypatch.setattr(response_pipeline, "log", lambda *_args, **_kwargs: None)

    response_pipeline.send_message("#canal", "oi")

    irc.send.assert_called_once_with(b"PRIVMSG #canal :oi\n")


def test_send_message_ignores_empty_message(monkeypatch):
    irc = Mock()
    monkeypatch.setattr(state, "irc", irc)
    monkeypatch.setattr(state, "irc_lock", Lock())
    monkeypatch.setattr(response_pipeline, "log", lambda *_args, **_kwargs: None)

    response_pipeline.send_message("#canal", "")

    irc.send.assert_not_called()


def test_send_message_handles_disconnected_irc(monkeypatch):
    log_mock = Mock()
    monkeypatch.setattr(state, "irc", None)
    monkeypatch.setattr(state, "irc_lock", Lock())
    monkeypatch.setattr(response_pipeline, "log", log_mock)

    response_pipeline.send_message("#canal", "oi")

    log_mock.assert_called_with("Erro ao enviar mensagem: IRC não conectado", "ERRO")


def test_send_message_handles_send_exception(monkeypatch):
    irc = Mock()
    irc.send.side_effect = Exception("falha simulada")
    log_mock = Mock()
    monkeypatch.setattr(state, "irc", irc)
    monkeypatch.setattr(state, "irc_lock", Lock())
    monkeypatch.setattr(response_pipeline, "log", log_mock)

    response_pipeline.send_message("#canal", "oi")

    log_mock.assert_called_with("Erro ao enviar mensagem: falha simulada", "ERRO")
