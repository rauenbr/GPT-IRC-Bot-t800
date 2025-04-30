# Changelog

> **Este projeto é um fork de [knrd1/chatgpt](https://github.com/knrd1/chatgpt)**

Todas as alterações significativas estão registradas abaixo, em ordem decrescente de versão.

---

## [Unreleased]
- Preparação para v1.3.0  
  - Refatorar storage de histórico para NoSQL (opcional)  
  - Integração com novos endpoints de embeddings  
  - Melhorias no UX de comandos e nas métricas de uso  

---

## [1.2.1] – 2025-04-29  
**Patch de final de série 1.2**  
- **Burst summarization debug**  
  - Adiciona logs `[BURST CHECK]` (mensagens recentes vs. threshold),  
    `[BURST SUMMARY]`, `[BURST PROMPT]` (prompt enviado) e `[BURST RESULT]`.  
- **!history** (apenas em `debug_mode`)  
  - Exibe até `history_limit` entradas com timestamp `HH:MM` e nick do autor.  
  - Em `debug_mode=false`, responde que só funciona em modo debug.  
- **Prompt formatado**  
  - Prefixa cada linha de usuário no prompt com `"<nick>: <conteúdo>"`.  
- **Debug de prompt completo**  
  - Em `debug_mode=true`, antes de cada chamada à API:  
    1. Log `[ESTIMATIVA TOKENS] prompt≈N`  
    2. Log de cada mensagem (role + content) enviada.  
- **Correções de threading**  
  - Resolve `UnboundLocalError` em `handle_question`.  
- **Aprimoramento do tratamento de QUIT**  
  - Não confunde quit de outros usuários com desconexão do bot.

---

## [1.2.0] – 2025-04-27  
### Added
- **Novos comandos IRC**  
  - `!help`, `!status`, `!uptime`, `!model`, `!usage` (e `!history` só em debug).  
- **Persistência de tokens & custo**  
  - SQLite (`usage.db`) registra tokens e custo de cada request.  
  - Reset diário (00:00) e mensal (configurável via `monthly_start_day`).  
- **Comando `!usage`**  
  - Exibe:  
    - Tokens e custo do dia/mês.  
    - Data/hora do primeiro init, último init e última conexão (com deltas).  
    - Total de chamadas API desde o último init.  
    - Uso de memória RSS e CPU do processo.  
- **Rate-limit por usuário**  
  - Até **5 mensagens** por minuto; avisa com `[Rate Limit]`.  
- **Prefixação de contexto**  
  - Prompt ao OpenAI formata histórico com `"<nick>: <mensagem>"`.  
- **Conversa e burst summarization**  
  - Armazena histórico por target em SQLite.  
  - Se muitas mensagens em janela curta, sintetiza resumo e inclui no prompt.  
- **Tabela de preços completa**  
  - Valores por 1 000 tokens para GPT-3.5, GPT-4 (8K/32K), GPT-4 Turbo, GPT-4o e série “o”.  
- **Dependência**  
  - Exige `openai>=1.76.0` (para suportar `APIConnectionError`, `APITimeoutError`, etc.).

### Changed
- Reconexão automática: refina detecção de `KICK`, `ERROR`, `QUIT`.  
- `!status` passa a exibir tokens usados desde o startup.  

---

## [1.1.0] – 2025-02-06  
### Added
- **Flags `debug` e `raw`** em `chat.conf`.  
  - `debug_mode=true` habilita logs detalhados via `log(msg, level)`.  
  - `raw_mode=true` mostra todo tráfego IRC cru (`[RAW]`) no console.  
- **Graceful shutdown**  
  - Tratamento de `SIGINT`/`SIGTERM`, envia `QUIT` antes de sair.  
- **Daemon mode**  
  - `daemon.DaemonContext()` para rodar em background, redirecionando `stdout`/`stderr` para `log_file`.  
- **Função `log()`**  
  - Timestamp (`YYYY-MM-DD HH:MM:SS`) + nível (`INFO`/`DEBUG`/`ERRO`), grava em arquivo se não em debug.  
- **Conversão Markdown → IRC bold**  
  - `**texto**` → `\x02texto\x02`.  
- **Segmentação de mensagens**  
  - `send_message()` quebra mensagens >392 chars respeitando espaços.  
- **Modularização**  
  - Separa `connect()` e `start_bot()`, com retry e join automático.

---

## [1.0.2] – 2025-02-06  
### Added
- **Exceções OpenAI refinadas**  
  - Importa `APIConnectionError`, `APITimeoutError`, `RateLimitError`, `APIStatusError`.  
- **Parâmetro de timeout correto**  
  - Usa `timeout=request_timeout` em chamadas `chat.completions.create()`.  

### Changed
- Atualiza as listas `completion_models`, `chatcompletion_models` e `images_models`.  

---

## [1.0.1] – 2025-02-05  
### Added
- **Suporte a múltiplos endpoints**  
  - Distingue `client.chat.completions` (chat) e `client.completions` (completion).  
- **DALL·E image generation**  
  - `client.images.generate()` + `pyshorteners` para URL curta.  
- **Filtro de conteúdo**  
  - Bloqueia respostas contendo “.bang” com mensagem customizada.  
- **Type hints iniciais**  
  - Imports de `typing` para melhor legibilidade.  

---

## [1.0.0] – 2024-10-18  
> **Forked from [knrd1/chatgpt v1.0.0](https://github.com/knrd1/chatgpt/releases/tag/v1.0.0)**  
### Added
- Conexão básica IRC (SSL opcional), JOIN automático em canais configurados.  
- Integração inicial com OpenAI ChatCompletion.  
- Tratamento de `PING/PONG`, `PRIVMSG`, logging básico de eventos e erros.

---

