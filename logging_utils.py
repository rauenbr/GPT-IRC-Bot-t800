#!/usr/bin/env python3
"""
Utilitários de logging do T800.
"""

from datetime import datetime

from config import debug_mode, global_log

def log(msg, level="INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{ts}] [{level}] {msg}"
    print(entry)
    if not debug_mode:
        with open(global_log, "a") as f:
            f.write(entry + "\n")
