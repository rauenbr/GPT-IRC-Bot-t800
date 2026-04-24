#!/usr/bin/env python3
"""
Cliente centralizado para chamadas OpenAI.
"""

import openai

from config import api_key


openai.api_key = api_key


def _get_setting(config, key):
    if isinstance(config, dict):
        if key in config:
            return config[key]
        raise KeyError(f"Config obrigatória ausente para chamada LLM: {key}")
    if hasattr(config, key):
        return getattr(config, key)
    raise KeyError(f"Config obrigatória ausente para chamada LLM: {key}")


def _usage_to_dict(usage):
    if usage is None:
        return {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }
    return {
        "prompt_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
        "completion_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
        "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
    }


def generate_chat_completion(messages, config):
    """
    Recebe mensagens no formato atual do projeto.
    Retorna:
        text (str),
        usage (dict)
    """
    resp = openai.chat.completions.create(
        model=_get_setting(config, "model"),
        messages=messages,
        temperature=_get_setting(config, "temperature"),
        max_tokens=_get_setting(config, "max_tokens"),
        top_p=_get_setting(config, "top_p"),
        frequency_penalty=_get_setting(config, "frequency_penalty"),
        presence_penalty=_get_setting(config, "presence_penalty"),
        timeout=_get_setting(config, "timeout"),
    )
    text = resp.choices[0].message.content or ""
    return text, _usage_to_dict(resp.usage)


def generate_summary(prompt, config):
    """
    Recebe prompt de resumo.
    Retorna:
        text (str),
        usage (dict)
    """
    resp = openai.chat.completions.create(
        model=_get_setting(config, "model"),
        messages=[
            {"role": "system", "content": "Você é um resumidor de chat IRC."},
            {"role": "user", "content": prompt},
        ],
        temperature=_get_setting(config, "temperature"),
        max_tokens=_get_setting(config, "max_tokens"),
        timeout=_get_setting(config, "timeout"),
    )
    text = resp.choices[0].message.content or ""
    return text, _usage_to_dict(resp.usage)
