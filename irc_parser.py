#!/usr/bin/env python3
"""
Parser simples para linhas do protocolo IRC.
"""

def parse_irc_line(line):
    line = line.strip("\r\n")
    if not line:
        return None

    prefix = None
    trailing = None

    if line.startswith(":"):
        prefix, _, line = line[1:].partition(" ")

    if " :" in line:
        line, _, trailing = line.partition(" :")

    parts = line.split()
    if not parts:
        return None

    command = parts[0].upper()
    params = parts[1:]

    if trailing is not None:
        params.append(trailing)

    return {
        "prefix": prefix,
        "command": command,
        "params": params,
    }
