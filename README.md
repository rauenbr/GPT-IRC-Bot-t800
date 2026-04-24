# GPT-IRC Bot (T800) – v1.3.4

Um bot de IRC em Python que usa a OpenAI para responder perguntas, gerar imagens e manter contexto de conversa.  
Fork do projeto [knrd1/chatgpt](https://github.com/knrd1/chatgpt), mantido em [rauenbr/GPT-IRC-Bot-t800](https://github.com/rauenbr/GPT-IRC-Bot-t800).

Arquitetura atual:
- `llm_client.py` é o ponto único de integração com a OpenAI.
- `pricing.py` centraliza o cálculo de custo.
- O projeto está organizado em módulos separados para configuração, estado, triggers, filtros, contexto, persistência e envio.

---

## 🚀 Funcionalidades

- **Chat Completions** (`/v1/chat/completions`)  
  Modelos suportados: GPT-4, GPT-4o, GPT-4 Turbo, GPT-3.5 Turbo e variantes.

- **Legacy Completions** (`/v1/completions`)  
  Modelos: `davinci-002`, `babbage-002`, `gpt-3.5-turbo-instruct`.

- **Geração de Imagens** (`/v1/images/generations`)  
  Modelos: `dall-e-2`, `dall-e-3` — retorna URL TinyURL.

- **Contexto de Conversa**  
  Armazena até N mensagens por canal/usuário e prefixa `<nick>: mensagem` no prompt.

- **Burst Summarization**  
  Se X mensagens chegam em Y segundos, sintetiza um resumo automático para economizar tokens.

- **Rate-limit**  
  Limite de 5 mensagens por usuário por minuto (aviso automático).

- **Métricas de Uso**  
  SQLite (`usage.db`) registra tokens e custo diário/mensal.  
  Comando `!usage` exibe:  
  - Tokens usados no dia/mês  
  - Custo estimado (USD)  
  - Total de chamadas API  
  - Uptime, última inicialização/conexão  
  - Uso de memória (RSS) e CPU do processo

- **Comandos IRC**  
  ```
  !help     — lista comandos  
  !status   — versão, estado e tokens desde startup  
  !uptime   — tempo de atividade atual  
  !model    — modelo configurado  
  !usage    — estatísticas de uso (tokens, custo, CPU, RAM)  
  !history  — (modo debug) exibe histórico de contexto
  ```

- **Debug & Raw**  
  - `debug=true` → logs detalhados (INFO/DEBUG/ERRO)  
  - `raw=true`   → dump de todo tráfego IRC cru

- **Daemon & Graceful Shutdown**  
  - Roda em segundo plano com `python-daemon`  
  - Trata `SIGINT`/`SIGTERM`, envia `QUIT` antes de sair

- **Formatação IRC**  
  - Converte `**texto**` em negrito IRC (`\x02texto\x02`)  
  - Quebra mensagens >392 caracteres respeitando espaços

---

## ⚙️ Pré-requisitos

- Python 3.10+  
- Biblioteca oficial OpenAI `>=1.76.0`  
- `pyshorteners`, `python-daemon`, `tiktoken`, `psutil`  
- Conta e **API Key** da OpenAI (inicia com `sk-…`)

---

## 📥 Instalação

```bash
git clone https://github.com/rauenbr/GPT-IRC-Bot-t800.git irc-gpt
cd irc-gpt

python3 -m pip install --upgrade pip
pip3 install   openai>=1.76.0   pyshorteners   python-daemon   tiktoken   psutil
```

---

## ⚙️ Configuração

1. Copie o exemplo:
   ```bash
   cp example-chat.conf chat.conf
   ```
2. Edite `chat.conf`, ajustando:

   ```ini
   [openai]
   api_key           = sk-XXXXXXXXXXXXXXXXXXXX

   [chatcompletion]
   model             = gpt-4o
   context           = Você é Terminator, um assistente de IRC direto, eficiente e confiante.
   temperature       = 0.9
   max_tokens        = 12000
   top_p             = 1
   frequency_penalty = 0
   presence_penalty  = 0
   request_timeout   = 60

   [irc]
   server            = irc.redesul.org
   port              = 6697
   ssl               = true
   channels          = #warez,#bot,#ajuda
   nickname          = Terminator
   ident             = AI
   realname          = Bot de inteligência artificial, sob o ChatGPT.
   password          =
   debug             = true
   raw               = false

   [bot]
   log_file          = gptirc.log
   history_limit     = 25
   burst_threshold   = 20
   burst_window      = 60
   burst_chunk_size  = 20
   usage_db          = usage.db
   monthly_start_day = 1
   context_mode      = channelcontext
   history_limit_direct = 8
   history_limit_channelcontext = 12
   channel_history_max_chars = 200
   assistant_history_max_chars = 180
   question_history_max_chars = 250
   ignore_short_channel_msgs = true

   [rate_limit]
   max_messages      = 5
   ```

---

## ▶️ Execução

### Modo foreground (debug)
```bash
python3 chat.py
```

### Modo daemon (produção)
- Ajuste `debug=false` em `chat.conf`
- Execute:
  ```bash
  python3 chat.py &
  ```

---

## 💬 Uso no IRC

Mencione o nick (case-insensitive) terminando com `:` ou `?`:
```
<user> irc-gpt bot: qual o status?
<bot> Bot operacional • v1.3.4 • tokens=1234
```
Em canais privados (PM), o bot responde sem prefixo.

---

## 🐳 Docker

1. **Build**  
   ```bash
   docker build -t irc-gpt-bot .
   ```
2. **Run**  
   ```bash
   docker run -d      -v "$(pwd)/chat.conf:/app/chat.conf"      --name irc-gpt      irc-gpt-bot
   ```

---

## 🔗 Links

- 📖 **API Reference**: https://platform.openai.com/docs/api-reference  
- 🔍 **Modelos**: https://platform.openai.com/docs/models  
- 🏠 **Repositório**: https://github.com/rauenbr/GPT-IRC-Bot-t800  

> **Versão:** 1.3.4 • **Data:** 2026-04-24  
