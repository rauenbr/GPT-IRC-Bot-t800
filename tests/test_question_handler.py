from threading import Lock
from unittest.mock import Mock

import question_handler
import state


def reset_token_counters():
    state.total_tokens_used = 0
    state.tokens_today = 0
    state.tokens_month = 0


def test_handle_question_uses_llm_client_and_updates_token_counters(monkeypatch):
    reset_token_counters()

    llm_mock = Mock(
        return_value=(
            "linha 1\nlinha 2",
            {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
            },
        )
    )
    add_history_entry = Mock()
    send_message = Mock()
    cursor = Mock()
    conn = Mock()

    monkeypatch.setattr(question_handler, "generate_chat_completion", llm_mock)
    monkeypatch.setattr(question_handler, "check_rate_limit", lambda _user: True)
    monkeypatch.setattr(question_handler, "update_periods", lambda: None)
    monkeypatch.setattr(question_handler, "add_history_entry", add_history_entry)
    monkeypatch.setattr(
        question_handler,
        "get_recent_history",
        lambda _target: [{"role": "alice", "content": "pergunta anterior"}],
    )
    monkeypatch.setattr(question_handler, "send_message", send_message)
    monkeypatch.setattr(question_handler, "convert_markdown_to_irc", lambda text: text)
    monkeypatch.setattr(question_handler, "log", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(question_handler, "cursor", cursor)
    monkeypatch.setattr(question_handler, "conn", conn)
    monkeypatch.setattr(state, "db_lock", Lock())

    question_handler.handle_question("alice", "#canal", "pergunta atual")

    llm_mock.assert_called_once()
    send_message.assert_any_call("#canal", "linha 1")
    send_message.assert_any_call("#canal", "linha 2")
    assert state.total_tokens_used == 15
    assert state.tokens_today == 15
    assert state.tokens_month == 15
    assert add_history_entry.call_count == 2
    cursor.execute.assert_called_once()
    conn.commit.assert_called_once()

    reset_token_counters()
def test_handle_question_handles_llm_exception_without_crashing(monkeypatch):
    reset_token_counters()

    from unittest.mock import Mock
    import state

    send_message = Mock()

    def raise_error(*_args, **_kwargs):
        raise Exception("falha simulada")

    monkeypatch.setattr(question_handler, "generate_chat_completion", raise_error)
    monkeypatch.setattr(question_handler, "check_rate_limit", lambda _user: True)
    monkeypatch.setattr(question_handler, "update_periods", lambda: None)
    monkeypatch.setattr(question_handler, "add_history_entry", Mock())
    monkeypatch.setattr(
        question_handler,
        "get_recent_history",
        lambda _target: [{"role": "alice", "content": "pergunta anterior"}],
    )
    monkeypatch.setattr(question_handler, "send_message", send_message)
    monkeypatch.setattr(question_handler, "convert_markdown_to_irc", lambda text: text)
    monkeypatch.setattr(question_handler, "log", lambda *_args, **_kwargs: None)

    question_handler.handle_question("alice", "#canal", "pergunta atual")

    send_message.assert_called_once_with("#canal", "[Erro interno]")
    assert state.total_tokens_used == 0
    assert state.tokens_today == 0
    assert state.tokens_month == 0
