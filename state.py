#!/usr/bin/env python3
"""
Estado global em memória do T800.
"""

import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, date

# Contadores de tokens e custo desde a sessão atual
total_tokens_used = 0
total_cost_used = 0.0

# Contadores persistidos (dia e mês) carregados da DB
tokens_today = 0
cost_today = 0.0
tokens_month = 0
cost_month = 0.0

# Para reset de contadores
last_reset_daily = date.today()
last_reset_monthly = None  # será definido após ler config / inicialização

# Momento de início da sessão atual
start_time = datetime.now()

# Estado do IRC
irc = None

# Rate limit por usuário
rate_limits = {}

# Executor para processar perguntas em paralelo
executor = ThreadPoolExecutor(max_workers=3)

# Locks globais
irc_lock = threading.Lock()
db_lock = threading.Lock()
