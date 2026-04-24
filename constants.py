# Auto-generated from monolithic chat.py
# Review imports and shared globals before production use.

#!/usr/bin/env python3
"""
IRC-GPT Bot (T800) v1.3.0

Requisitos:
- Python 3.10+
- openai>=1.76.0
- tiktoken>=0.4.0
- SQLite (builtin)
- resource (builtin)
- Dependências padrão: ssl, socket, threading, daemon, configparser, etc.
"""

import sys
import re
import socket
import ssl
import time
import signal
import configparser
import daemon
import threading
import sqlite3
import resource
from datetime import datetime, timedelta, date

import openai
from openai import APIError, APIConnectionError, RateLimitError
import tiktoken  # para estimativa de tokens em debug

SCRIPT_VERSION = "1.3.1-beta"
