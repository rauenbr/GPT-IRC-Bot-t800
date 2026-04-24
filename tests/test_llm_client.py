from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import llm_client

CHAT_CONFIG = {
    "model": "gpt-4o",
    "temperature": 0.9,
    "max_tokens": 12000,
    "top_p": 1,
    "frequency_penalty": 0,
    "presence_penalty": 0,
    "timeout": 10,
}

def make_response(text, prompt_tokens=11, completion_tokens=7, total_tokens=18):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))],
        usage=SimpleNamespace(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        ),
    )


def test_generate_chat_completion_returns_text_and_usage(monkeypatch):
    mock_create = Mock(return_value=make_response("resposta final"))
    monkeypatch.setattr(llm_client.openai.chat.completions, "create", mock_create)

    text, usage = llm_client.generate_chat_completion(
        [{"role": "user", "content": "oi"}],
        {
            "model": "gpt-4o",
            "temperature": 0.9,
            "max_tokens": 12000,
            "top_p": 1,
            "frequency_penalty": 0,
            "presence_penalty": 0,
            "timeout": 60,
        },
    )

    assert text == "resposta final"
    assert usage == {
        "prompt_tokens": 11,
        "completion_tokens": 7,
        "total_tokens": 18,
    }
    mock_create.assert_called_once()


def test_generate_summary_returns_text_and_usage(monkeypatch):
    mock_create = Mock(return_value=make_response("resumo pronto", 5, 3, 8))
    monkeypatch.setattr(llm_client.openai.chat.completions, "create", mock_create)

    text, usage = llm_client.generate_summary(
        "resuma isso",
        {
            "model": "gpt-4o",
            "temperature": 0.5,
            "max_tokens": 150,
            "timeout": 60,
        },
    )

    assert text == "resumo pronto"
    assert usage == {
        "prompt_tokens": 5,
        "completion_tokens": 3,
        "total_tokens": 8,
    }
    mock_create.assert_called_once()


def test_usage_to_dict_with_none_returns_zeroes():
    assert llm_client._usage_to_dict(None) == {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
    }


def test_get_setting_supports_dict():
    assert llm_client._get_setting({"model": "gpt-4o"}, "model") == "gpt-4o"


def test_get_setting_supports_object():
    obj = SimpleNamespace(model="gpt-4o")
    assert llm_client._get_setting(obj, "model") == "gpt-4o"


def test_get_setting_raises_keyerror_for_missing_dict_key():
    with pytest.raises(KeyError, match="Config obrigatória ausente para chamada LLM: model"):
        llm_client._get_setting({}, "model")


def test_get_setting_raises_keyerror_for_missing_object_attribute():
    with pytest.raises(KeyError, match="Config obrigatória ausente para chamada LLM: model"):
        llm_client._get_setting(SimpleNamespace(), "model")
def test_generate_chat_completion_handles_exception(monkeypatch):
    def raise_error(*args, **kwargs):
        raise Exception("API error")

    monkeypatch.setattr(llm_client.openai.chat.completions, "create", raise_error)

    with pytest.raises(Exception):
        llm_client.generate_chat_completion(
            [{"role": "user", "content": "oi"}],
            {
                "model": "gpt-4o",
                "temperature": 0.9,
                "max_tokens": 12000,
                "top_p": 1,
                "frequency_penalty": 0,
                "presence_penalty": 0,
                "timeout": 10,
            },
        )


def test_generate_chat_completion_handles_missing_usage(monkeypatch):
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))],
        usage=None,
    )

    monkeypatch.setattr(llm_client.openai.chat.completions, "create", lambda *a, **k: response)

    text, usage = llm_client.generate_chat_completion(
        [{"role": "user", "content": "oi"}],
        {
            "model": "gpt-4o",
            "temperature": 0.9,
            "max_tokens": 12000,
            "top_p": 1,
            "frequency_penalty": 0,
            "presence_penalty": 0,
            "timeout": 10,
        }, )

    assert text == "ok"
    assert usage == {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
    }


def test_generate_chat_completion_handles_missing_content(monkeypatch):
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=None))],
        usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1, total_tokens=2),
    )

    monkeypatch.setattr(llm_client.openai.chat.completions, "create", lambda *a, **k: response)

    text, usage = llm_client.generate_chat_completion(
        [{"role": "user", "content": "oi"}],
        {
               "model": "gpt-4o",
               "temperature": 0.9,
               "max_tokens": 12000,
               "top_p": 1,
               "frequency_penalty": 0,
               "presence_penalty": 0,
               "timeout": 10,
        },
    )

    assert text == ""
