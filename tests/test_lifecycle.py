from threading import Lock
from unittest.mock import Mock, call

import lifecycle
import state


def _setup_shutdown_env(monkeypatch, irc):
    executor = Mock()
    conn = Mock()
    exit_mock = Mock()
    sleep_mock = Mock()
    log_mock = Mock()

    monkeypatch.setattr(lifecycle, "_shutting_down", False)
    monkeypatch.setattr(state, "irc", irc)
    monkeypatch.setattr(state, "irc_lock", Lock())
    monkeypatch.setattr(state, "executor", executor)
    monkeypatch.setattr(lifecycle, "conn", conn)
    monkeypatch.setattr(lifecycle.sys, "exit", exit_mock)
    monkeypatch.setattr(lifecycle.time, "sleep", sleep_mock)
    monkeypatch.setattr(lifecycle, "log", log_mock)

    return executor, conn, exit_mock, sleep_mock, log_mock


def test_graceful_exit_with_connected_irc(monkeypatch):
    irc = Mock()
    executor, conn, exit_mock, sleep_mock, _log_mock = _setup_shutdown_env(monkeypatch, irc)

    lifecycle.graceful_exit(None, None)

    irc.send.assert_called_once_with(b"QUIT :Voltarei em breve\n")
    sleep_mock.assert_called_once_with(1)
    irc.close.assert_called_once_with()
    executor.shutdown.assert_called_once_with(wait=False, cancel_futures=True)
    conn.close.assert_called_once_with()
    exit_mock.assert_called_once_with(0)


def test_graceful_exit_with_disconnected_irc(monkeypatch):
    executor, conn, exit_mock, sleep_mock, _log_mock = _setup_shutdown_env(monkeypatch, None)

    lifecycle.graceful_exit(None, None)

    sleep_mock.assert_not_called()
    executor.shutdown.assert_called_once_with(wait=False, cancel_futures=True)
    conn.close.assert_called_once_with()
    exit_mock.assert_called_once_with(0)


def test_graceful_exit_when_quit_send_fails(monkeypatch):
    irc = Mock()
    irc.send.side_effect = Exception("send failed")
    executor, conn, exit_mock, sleep_mock, _log_mock = _setup_shutdown_env(monkeypatch, irc)

    lifecycle.graceful_exit(None, None)

    irc.send.assert_called_once_with(b"QUIT :Voltarei em breve\n")
    sleep_mock.assert_not_called()
    irc.close.assert_called_once_with()
    executor.shutdown.assert_called_once_with(wait=False, cancel_futures=True)
    conn.close.assert_called_once_with()
    exit_mock.assert_called_once_with(0)


def test_graceful_exit_when_irc_close_fails(monkeypatch):
    irc = Mock()
    irc.close.side_effect = Exception("close failed")
    executor, conn, exit_mock, sleep_mock, _log_mock = _setup_shutdown_env(monkeypatch, irc)

    lifecycle.graceful_exit(None, None)

    irc.send.assert_called_once_with(b"QUIT :Voltarei em breve\n")
    sleep_mock.assert_called_once_with(1)
    irc.close.assert_called_once_with()
    executor.shutdown.assert_called_once_with(wait=False, cancel_futures=True)
    conn.close.assert_called_once_with()
    exit_mock.assert_called_once_with(0)


def test_graceful_exit_with_unavailable_irc_lock(monkeypatch):
    irc = Mock()
    executor, conn, exit_mock, sleep_mock, _log_mock = _setup_shutdown_env(monkeypatch, irc)
    original_with_irc_lock = lifecycle._with_irc_lock

    def _fast_with_irc_lock(description, func, timeout=2.0):
        return original_with_irc_lock(description, func, timeout=0.01)

    monkeypatch.setattr(lifecycle, "_with_irc_lock", _fast_with_irc_lock)

    state.irc_lock.acquire()
    try:
        lifecycle.graceful_exit(None, None)
    finally:
        state.irc_lock.release()

    irc.send.assert_not_called()
    irc.close.assert_not_called()
    sleep_mock.assert_not_called()
    executor.shutdown.assert_called_once_with(wait=False, cancel_futures=True)
    conn.close.assert_called_once_with()
    exit_mock.assert_called_once_with(0)


def test_graceful_exit_is_reentrant(monkeypatch):
    irc = Mock()
    executor, conn, exit_mock, sleep_mock, _log_mock = _setup_shutdown_env(monkeypatch, irc)
    monkeypatch.setattr(lifecycle, "_shutting_down", True)

    lifecycle.graceful_exit(None, None)

    irc.send.assert_not_called()
    irc.close.assert_not_called()
    sleep_mock.assert_not_called()
    executor.shutdown.assert_not_called()
    conn.close.assert_not_called()
    exit_mock.assert_called_once_with(0)


def test_register_signal_handlers_registers_sigint_and_sigterm(monkeypatch):
    signal_mock = Mock()
    monkeypatch.setattr(lifecycle.signal, "signal", signal_mock)

    lifecycle.register_signal_handlers()

    assert signal_mock.call_args_list == [
        call(lifecycle.signal.SIGINT, lifecycle.graceful_exit),
        call(lifecycle.signal.SIGTERM, lifecycle.graceful_exit),
    ]
