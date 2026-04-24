# Changelog

> **Este projeto é um fork de [knrd1/chatgpt](https://github.com/knrd1/chatgpt)**

Todas as alterações significativas estão registradas abaixo, em ordem decrescente de versão.

---
## [1.3.2] – 2026-04-23  
### Testes automatizados
- Implementação da suíte inicial de testes com `pytest`.
- Criação de testes para os módulos:
  - `filters.py`
  - `triggers.py`
  - `markdown_irc.py`
- Total de 26 testes implementados e validados com sucesso.

### Correções
- Correção de bug na conversão de underline em `markdown_irc.py`, onde o caractere de fechamento era removido indevidamente.
- Ajuste no uso de `strip()` para preservar caracteres de controle IRC.

### Refatoração e limpeza
- Remoção de imports desnecessários em `markdown_irc.py` herdados do código monolítico.
- Isolamento da função `convert_markdown_to_irc`, eliminando dependências externas indevidas.
- Ajustes para garantir comportamento determinístico e testável dos módulos.

### Ambiente e execução
- Configuração de ambiente virtual (`venv`) para execução isolada.
- Padronização das dependências necessárias ao projeto.
- Criação de `.gitignore` adequado para exclusão de arquivos temporários, cache e dados locais.

### Integração com repositório
- Sincronização do código refatorado com o repositório principal.
- Consolidação de baseline estável com testes automatizados passando.
---
## [1.3.1] – 2026-04-11
- **Reorganização estrutural do código** 
  - Reorganização inicial do `chat.py` monolítico em estrutura modular, mantendo o comportamento externo do bot.
  - Manutenção do `chat.py` como bootstrap e loop principal, com delegação das rotinas auxiliares para módulos específicos.
  - Criação/organização dos módulos de configuração, estado, logging, ciclo de vida, conexão IRC, parser IRC, persistência SQLite, comandos, triggers, filtros, rate limit, períodos, burst summarization, processamento de perguntas, envio de respostas, pricing, conversão Markdown/IRC e utilitários.
  - Centralização do estado global em `state.py` e consolidação do acesso ao SQLite em `storage.py`.
  - Separação das regras de filtros, triggers, rate limit e parsing IRC em módulos próprios.
  - Organização do controle de períodos, incluindo reset diário e mensal de uso.
  - Preparação de estrutura para evolução futura dos módulos `context_builder.py`, `llm_client.py` e `token_debug.py`.
  - Criação da estrutura inicial de testes unitários para parser IRC, triggers, filtros, envio, Markdown/IRC, rate limit e construção de contexto.
  - Preservação do tratamento de reconexão, encerramento gracioso, histórico, contadores de uso, logs e comandos administrativos.
  - Versão focada exclusivamente em organização interna, legibilidade e preparação estrutural, sem alteração funcional relevante no comportamento do bot.
---
## [1.3] – 2026-04-04
- **Estabilidade operacional e concorrência**
  - Substituição de threads soltas por `ThreadPoolExecutor(max_workers=3)`.
  - Introdução de `irc_lock` para serializar envios ao socket IRC.
  - Introdução de `db_lock` para proteger acessos concorrentes ao SQLite.
  - Revisão do loop principal e do fluxo de despacho, deixando o bot significativamente mais estável em uso normal e em VPS limitada. :contentReference[oaicite:0]{index=0}

- **Parser e dispatch de IRC reforçados**
  - Novo parsing estruturado de linhas IRC com `parse_irc_line()`.
  - Helpers `irc_send_raw()` e `join_channels()` para centralizar envio e JOIN.
  - Correção do fluxo de canal/PM, inclusive de casos em que o trigger era reconhecido mas a pergunta não chegava corretamente ao handler.
  - Suporte consolidado a `PING/PONG`, `ERROR`, `KICK`, PM e JOIN automático. :contentReference[oaicite:1]{index=1}

- **Detecção de trigger mais flexível**
  - Suporte a múltiplos formatos de ativação:
    - `!comando`
    - `Nick: mensagem`
    - `mensagem Nick?`
  - Introdução de `extract_trigger_content()` para normalizar a entrada antes do envio ao modelo. :contentReference[oaicite:2]{index=2}

- **Modos de contexto (`direct` / `channelcontext`)**
  - Novo `context_mode` com fallback seguro para `direct`.
  - `direct`: histórico mantém apenas interações dirigidas ao bot e respostas do bot.
  - `channelcontext`: além das interações dirigidas ao bot, o bot acompanha passivamente mensagens normais recentes do canal para responder com mais contexto. :contentReference[oaicite:3]{index=3}

- **Separação entre contexto ativo e passivo**
  - Contexto ativo: perguntas e respostas diretamente ligadas ao bot.
  - Contexto passivo: mensagens recentes do canal, filtradas para reduzir ruído.
  - Mantida a distinção de quem falou o quê no prompt enviado ao modelo. :contentReference[oaicite:4]{index=4}

- **Histórico com limites dinâmicos e controle de custo**
  - Novas opções:
    - `history_limit_direct`
    - `history_limit_channelcontext`
    - `channel_history_max_chars`
    - `assistant_history_max_chars`
    - `question_history_max_chars`
    - `ignore_short_channel_msgs`
    - `channel_min_msg_len`
  - `add_history_entry()` e `get_recent_history()` passaram a respeitar limites por modo/alvo.
  - Perguntas, respostas e mensagens passivas do canal passaram a ter truncamento configurável para reduzir consumo de tokens. :contentReference[oaicite:5]{index=5}

- **Filtro de contexto passivo do canal**
  - Nova função `should_store_passive_channel_message()` para evitar que o `channelcontext` vire depósito de ruído.
  - Ignora, entre outros:
    - mensagens vazias
    - triggers dirigidas ao bot
    - comandos iniciados com `!`
    - mensagens muito curtas sem valor semântico
    - pontuação pura
    - risadas e repetições clássicas
    - mensagens dominadas por repetição exagerada
  - Preserva mensagens curtas potencialmente úteis, como “sim”, “não”, “talvez”, “foi”, “caiu” etc. :contentReference[oaicite:6]{index=6}

- **SQLite endurecido**
  - `set_meta()`, `get_meta()`, `load_metadata_and_counters()`, `add_history_entry()`, `get_recent_history()`, `!usage`, `!clear`, trechos de burst summarization e inserts em `usage` passaram a operar sob `db_lock`.
  - Redução do risco de disputa de cursor, inconsistência de escrita e erros sob concorrência. :contentReference[oaicite:7]{index=7}

- **Reset e limpeza de histórico**
  - Suporte a `clear_history_on_start`.
  - Limpeza automática do histórico quando o `context_message` muda, usando `last_context` em `metadata`.
  - Limpeza do histórico quando a última entrada fica antiga demais.
  - Comando `!clear` para limpar o histórico do alvo atual. :contentReference[oaicite:8]{index=8}

- **`handle_question()` alinhado com os novos modos**
  - Mantém comandos fora do fluxo da OpenAI.
  - Continua preservando `rate limit`, contadores e custo.
  - Passou a gravar pergunta e resposta respeitando truncamentos configuráveis.
  - Mantém no prompt a identificação do autor de cada mensagem (`nick: conteúdo`). :contentReference[oaicite:9]{index=9}

- **Compatibilidade de tokenização**
  - Em debug, o cálculo estimado de tokens ganhou fallback para `o200k_base` quando `encoding_for_model()` não reconhece o modelo. :contentReference[oaicite:10]{index=10}

- **Conversão Markdown/LaTeX → IRC ampliada**
  - `convert_markdown_to_irc()` deixou de tratar apenas `**bold**`.
  - Agora cobre, de forma pragmática para IRC:
    - `**negrito**`
    - `__underline__`
    - `` `inline code` ``
    - blocos de código
    - links markdown
    - headings
    - quotes
    - listas simples
    - limpeza de itálico e strikethrough
    - normalização parcial de LaTeX básico (`\frac`, `\sqrt`, `\pm` etc.) para texto simples
  - A conversão foi focada no que vale a pena no IRC, sem tentar virar parser completo de Markdown/LaTeX. :contentReference[oaicite:11]{index=11}

- **Ajuste de personalidade**
  - Prompt de sistema encurtado e endurecido.
  - Redução de respostas excessivamente simpáticas/genéricas.
  - Maior objetividade e menos “tom de atendente prestativo demais”. :contentReference[oaicite:12]{index=12}

- **Observabilidade**
  - Melhor visibilidade do fluxo de contexto, prompt, tokens e custo por requisição em modo debug.
  - O estado atual já reflete operação estável com `!status`, `!usage`, `!clear`, contexto por canal, envio segmentado e histórico enriquecido. :contentReference[oaicite:13]{index=13}
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

