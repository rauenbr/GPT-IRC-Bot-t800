#!/usr/bin/env python3
"""
Funções utilitárias gerais.
"""

def fmt_delta(delta):
    d = delta.days
    h, rem = divmod(delta.seconds, 3600)
    m, s = divmod(rem, 60)

    parts = []
    if d:
        parts.append(f"{d}d")
    if h:
        parts.append(f"{h}h")
    if m:
        parts.append(f"{m}m")
    parts.append(f"{s}s")

    return " ".join(parts)
