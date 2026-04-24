#!/usr/bin/env python3
"""
Configuração do T800 carregada a partir de chat.conf
"""

import configparser
from pathlib import Path

# Lê o chat.conf no mesmo diretório deste arquivo
BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "chat.conf"

config = configparser.ConfigParser()
read_ok = config.read(CONFIG_FILE)

if not read_ok:
    raise FileNotFoundError(f"Arquivo de configuração não encontrado: {CONFIG_FILE}")

# IRC
server            = config.get('irc', 'server')
port              = config.getint('irc', 'port')
usessl            = config.getboolean('irc', 'ssl')
channels          = config.get('irc', 'channels').split(',')
nickname          = config.get('irc', 'nickname')
ident             = config.get('irc', 'ident')
realname          = config.get('irc', 'realname')
password          = config.get('irc', 'password')
debug_mode        = config.getboolean('irc', 'debug', fallback=False)
raw_mode          = config.getboolean('irc', 'raw',   fallback=False)

# OpenAI
api_key           = config.get('openai', 'api_key')

# ChatCompletion
model             = config.get('chatcompletion', 'model')
context_message   = config.get('chatcompletion', 'context')
temperature       = config.getfloat('chatcompletion', 'temperature')
max_tokens        = config.getint('chatcompletion', 'max_tokens')
top_p             = config.getfloat('chatcompletion', 'top_p')
frequency_penalty = config.getfloat('chatcompletion', 'frequency_penalty')
presence_penalty  = config.getfloat('chatcompletion', 'presence_penalty')
timeout           = config.getint('chatcompletion', 'request_timeout')

# Bot / DB / burst
global_log        = config.get('bot', 'log_file',           fallback="/var/log/chatgpt_irc.log")
HISTORY_LIMIT     = config.getint('bot', 'history_limit',    fallback=10)
monthly_start_day = config.getint('bot', 'monthly_start_day',fallback=1)
usage_db          = config.get('bot', 'usage_db',            fallback="usage.db")
burst_threshold   = config.getint('bot', 'burst_threshold',  fallback=5)
burst_window      = config.getint('bot', 'burst_window',     fallback=60)
burst_chunk_size  = config.getint('bot', 'burst_chunk_size', fallback=5)
MAX_MESSAGES      = config.getint('rate_limit', 'max_messages', fallback=5)
context_mode      = config.get('bot', 'context_mode', fallback='direct').strip().lower()
history_limit_direct = config.getint('bot', 'history_limit_direct', fallback=8)
history_limit_channelcontext = config.getint('bot', 'history_limit_channelcontext', fallback=12)
channel_history_max_chars = config.getint('bot', 'channel_history_max_chars', fallback=200)
assistant_history_max_chars = config.getint('bot', 'assistant_history_max_chars', fallback=180)
question_history_max_chars = config.getint('bot', 'question_history_max_chars', fallback=250)
ignore_short_channel_msgs = config.getboolean('bot', 'ignore_short_channel_msgs', fallback=True)
channel_min_msg_len = config.getint('bot', 'channel_min_msg_len', fallback=3)
if context_mode not in ("direct", "channelcontext"):
    context_mode = "direct"
