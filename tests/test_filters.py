import filters
import state


def setup_filter_config(monkeypatch):
    monkeypatch.setattr(filters, "context_mode", "channelcontext")
    monkeypatch.setattr(filters, "nickname", "Terminator")
    monkeypatch.setattr(filters, "ignore_short_channel_msgs", True)
    monkeypatch.setattr(filters, "channel_min_msg_len", 4)
    monkeypatch.setattr(state, "current_nickname", None)


def test_ignore_when_not_channelcontext(monkeypatch):
    monkeypatch.setattr(filters, "context_mode", "direct")
    assert not filters.should_store_passive_channel_message("usuario", "mensagem normal", False)


def test_ignore_bot_own_message(monkeypatch):
    setup_filter_config(monkeypatch)
    assert not filters.should_store_passive_channel_message("Terminator", "mensagem normal", False)


def test_ignore_bot_own_message_with_active_random_nick(monkeypatch):
    setup_filter_config(monkeypatch)
    monkeypatch.setattr(state, "current_nickname", "Terminator335")
    assert not filters.should_store_passive_channel_message("Terminator335", "mensagem normal", False)


def test_ignore_triggered_message(monkeypatch):
    setup_filter_config(monkeypatch)
    assert not filters.should_store_passive_channel_message("usuario", "mensagem normal", True)


def test_ignore_empty_message(monkeypatch):
    setup_filter_config(monkeypatch)
    assert not filters.should_store_passive_channel_message("usuario", "", False)


def test_ignore_command_message(monkeypatch):
    setup_filter_config(monkeypatch)
    assert not filters.should_store_passive_channel_message("usuario", "!comando qualquer", False)


def test_ignore_only_symbols(monkeypatch):
    setup_filter_config(monkeypatch)
    assert not filters.should_store_passive_channel_message("usuario", "!!!!!", False)


def test_ignore_laughter_noise(monkeypatch):
    setup_filter_config(monkeypatch)
    assert not filters.should_store_passive_channel_message("usuario", "kkkkkkkk", False)


def test_accept_normal_text(monkeypatch):
    setup_filter_config(monkeypatch)
    assert filters.should_store_passive_channel_message("usuario", "isso é uma mensagem válida", False)


def test_accept_meaningful_short_message(monkeypatch):
    setup_filter_config(monkeypatch)
    assert filters.should_store_passive_channel_message("usuario", "sim", False)
