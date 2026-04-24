#!/usr/bin/env python3
"""
Tabela de preços e cálculo de custo por uso.
"""

PRICING = {
    # GPT-3.5 Turbo
    "gpt-3.5-turbo":           {"prompt": 0.0015, "completion": 0.002},
    "gpt-3.5-turbo-0301":      {"prompt": 0.0015, "completion": 0.002},
    "gpt-3.5-turbo-0613":      {"prompt": 0.0015, "completion": 0.002},
    "gpt-3.5-turbo-1106":      {"prompt": 0.0015, "completion": 0.002},
    "gpt-3.5-turbo-0125":      {"prompt": 0.0015, "completion": 0.002},
    "gpt-3.5-turbo-16k":       {"prompt": 0.0030, "completion": 0.004},
    "gpt-3.5-turbo-16k-0613":  {"prompt": 0.0030, "completion": 0.004},

    # GPT-4 (8K)
    "gpt-4":                   {"prompt": 0.030,  "completion": 0.060},
    "gpt-4-0314":              {"prompt": 0.030,  "completion": 0.060},
    "gpt-4-0613":              {"prompt": 0.030,  "completion": 0.060},

    # GPT-4 (32K)
    "gpt-4-32k":               {"prompt": 0.060,  "completion": 0.120},
    "gpt-4-32k-0314":          {"prompt": 0.060,  "completion": 0.120},
    "gpt-4-32k-0613":          {"prompt": 0.060,  "completion": 0.120},

    # Previews
    "gpt-4-0125-preview":      {"prompt": 0.030,  "completion": 0.060},
    "gpt-4-1106-preview":      {"prompt": 0.030,  "completion": 0.060},
    "gpt-4-vision-preview":    {"prompt": 0.030,  "completion": 0.060},

    # GPT-4 Turbo
    "gpt-4-turbo":             {"prompt": 0.0015, "completion": 0.002},
    "gpt-4-turbo-2024-04-09":  {"prompt": 0.0015, "completion": 0.002},
    "gpt-4-turbo-preview":     {"prompt": 0.0015, "completion": 0.002},

    # GPT-4o family (sample)
    "gpt-4o":                  {"prompt": 0.030,  "completion": 0.060},
    "gpt-4o-mini":             {"prompt": 0.030,  "completion": 0.060},
    "chatgpt-4o-latest":       {"prompt": 0.030,  "completion": 0.060},

    # “o” series
    "o1":                      {"prompt": 0.0015, "completion": 0.002},
    "o1-mini":                 {"prompt": 0.0015, "completion": 0.002},
}


def get_model_rates(model_name):
    return PRICING.get(model_name, PRICING.get(model_name.split("-")[0], {}))


def calculate_cost(model_name, prompt_tokens, completion_tokens):
    rates = get_model_rates(model_name)
    return (
        (prompt_tokens / 1000) * rates.get("prompt", 0) +
        (completion_tokens / 1000) * rates.get("completion", 0)
    )
