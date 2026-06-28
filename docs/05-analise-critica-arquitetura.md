# 05 — Análise crítica da arquitetura

> Revisão feita em 2026-06-27 lendo docs + código real (`src/`, `db/`, `docker-compose.yml`,
> `Dockerfile`, `scripts/`). Objetivo: listar **cada defeito** que impede ou ameaça o
> funcionamento, para você validar e priorizar. Ordenado por gravidade.
>
> Legenda de severidade: 🔴 quebra/bloqueia · 🟠 estrutural (vai doer cedo) ·
> 🟡 robustez/operação · 🔵 produto/dados · ⚪ dívida menor.

---

## Veredito em uma frase

A camada de **domínio** (financeiro, dedup, auditor, IA) está bem desenhada e testada
(TDD), mas a **fiação** (ingestão → fila → worker → Neon → Telegram) tem furos que hoje
**impedem o caminho feliz de funcionar ponta-a-ponta**, e a arquitetura real **divergiu da
documentada** no ponto mais central (transporte e modelo de execução). O que está testado
é unidade; o que está quebrado é a integração — e não há teste de integração.

---

## 🔴 Defeitos que quebram / bloqueiam o funcionamento

### C1 — Transação de notificação nunca recebe `conta_id` → confirmar quebra o saldo
- A ingestão grava a transação sem conta: `TransacaoRepoNeon.salvar` (`infra/neon_repos.py:69`)
  **não insere `conta_id`** (fica `NULL` no banco).
- Na confirmação, `ServicoTransacoes.confirmar` (`financeiro/transacoes.py:65`) faz
  `conta = self._contas.buscar(t.conta_id)` e logo usa `conta.saldo_atual`.
- Para débito/pix/dinheiro, `t.conta_id` chega vazio (`_map_row` devolve `""` quando `NULL`,
  `infra/sqlalchemy_repos.py:140`), `buscar` retorna `None` → **`AttributeError` ao confirmar**.
  Só transações de **crédito** sobrevivem (porque pulam o saldo).
- **Causa raiz de produto:** a notificação não diz de qual conta/cartão saiu o dinheiro.
  Nada no pipeline resolve isso. Sem decidir como mapear notificação → conta, o saldo
  **nunca** vai fechar. É o gap número 1.

### C2 — Dois caminhos de ingestão divergentes; o do Telegram ignora a fila
- Caminho A (app Android): `POST /ingestao` → `RoteadorIngestao` → **Fila SQLite** →
  `worker_fila` (job a cada 60s) → `Orquestrador` (`bot/principal.py:195`).
- Caminho B (texto no Telegram): `handle_notificacao` (`bot/principal.py:150`) processa
  **síncrono, com `_NoOpFila()`** — não passa pela fila, não tem durabilidade, e roda
  **dentro do handler do bot**.
- Resultado: dois fluxos para a mesma coisa, com semânticas diferentes (durável vs. volátil),
  tipos de `id` diferentes (`int` autoincrement na fila vs. `str(message_id)` no Telegram),
  e só um deles é resiliente a reinício.

### C3 — Qualquer texto enviado ao bot vira tentativa de transação
- `MessageHandler(filters.TEXT & ~filters.COMMAND, handle_notificacao)` (`bot/principal.py:216`):
  toda mensagem que não é comando é jogada na IA como se fosse notificação de banco.
- Conversa, resposta, "oi", colar um endereço → chamada de LLM + possível transação espúria
  `PENDENTE_APROVACAO`. Ruído garantido e custo de LLM à toa.

### C4 — SQLite compartilhado entre dois processos + uso cross-thread
- `start-all.sh` sobe **dois processos**: o bot (`python -m ...bot.principal &`) e o
  uvicorn (`uvicorn ...ingestao.app`). Ambos abrem **o mesmo arquivo** `/data/fila.db`:
  o FastAPI escreve (`enqueue`), o bot lê/marca (`fetch_next`/`marcar`).
- `Fila` usa `sqlite3.connect(db_path)` sem WAL e sem `timeout` (`fila/fila.py:23`) →
  alto risco de **`database is locked`** sob escrita concorrente.
- Pior: a conexão é criada **uma vez no import** (`_fila_real = Fila(...)`, `bot/principal.py:74`)
  e usada pelo `job_queue` em outra thread. `sqlite3` é `check_same_thread=True` por padrão →
  risco de **`SQLite objects created in a thread can only be used in that same thread`**.
- E ainda: o FastAPI da ingestão cria **outra** `Fila` apontando pro mesmo arquivo
  (`ingestao/app.py:66`). São conexões independentes ao mesmo SQLite, sem coordenação.

### C5 — A doc de arquitetura descreve um sistema diferente do implementado
- Docs 01/03 dizem que o transporte é **App → Telegram (canal) → Pi por polling**
  (diagrama em `01-visao-e-arquitetura.md:62-68`; fluxo A em `03-fluxos.md`).
- O código implementado é **App → HTTP `/ingestao` direto no Pi** (opção D3-b), sem Telegram
  no transporte. A decisão D3 ficou **em aberto/ambígua** em `DECISOES-PENDENTES.md:20-24` e o
  código seguiu um caminho que a doc não reflete.
- O Fluxo C promete *"trigger recalcula saldo / fatura / competência"* (`03-fluxos.md:65`),
  mas **não existe nenhum trigger** na migration (`db/migrations/0001_init.sql`) — isso é
  lógica de aplicação (`ServicoTransacoes`). Doc promete algo que o schema não tem.
- Consequência prática: a documentação não serve de fonte da verdade para operar o sistema.

---

## 🟠 Defeitos estruturais de arquitetura

### A1 — Dois conjuntos de repositórios redundantes e divergentes
- `infra/neon_repos.py` (psycopg cru) **e** `infra/sqlalchemy_repos.py` (SQLAlchemy).
  O bot usa **os dois ao mesmo tempo**: `TransacaoRepoNeon` no orquestrador
  (`bot/principal.py:70`) e `SqlAlchemyTransacaoRepo` nos comandos/callbacks
  (`bot/principal.py:171`).
- Eles **discordam** sobre o mesmo conceito: `SqlAlchemyTransacaoRepo.salvar` grava
  `origem='manual'` fixo e nunca preenche `categoria_id` (sempre devolve `"Outros"`,
  `sqlalchemy_repos.py:148`); `TransacaoRepoNeon.salvar` resolve a categoria por subquery e
  grava `origem='notificacao'`. Duas verdades para a mesma tabela.
- Mantê-los sincronizados é trabalho dobrado e fonte certa de bug. **Escolha um** (recomendo
  SQLAlchemy, pelo pool e pela tipagem) e apague o outro.

### A2 — Conexão Postgres por chamada, sem pool, contra o Neon
- `neon_repos.py` faz `psycopg.connect(self._dsn)` **a cada método** (ex. `:37`, `:42`, `:56`).
  Cada `/saldo`, cada dedup, cada `salvar` abre TCP+TLS novo contra o Neon (que ainda
  suspende/cold-start). Latência e custo desnecessários.
- Ao mesmo tempo existe um `create_engine` + `scoped_session` (`bot/principal.py:66`) que
  **tem** pool, mas só é usado pela metade do código. Dois mecanismos de conexão coexistem.

### A3 — Worker não é um worker; é um job dentro do bot
- A doc vende um *"worker persistente"*. Na prática, o processamento da fila é um
  `job_queue.run_repeating(worker_fila, interval=60)` **dentro do processo do PTB**
  (`bot/principal.py:221`). Se o bot cai, a fila para. Não há processo de worker isolado,
  apesar do `docker-compose` falar em "1 container para o worker".
- O caminho B (Telegram) processa LLM **inline no handler** → durante uma extração lenta
  (SSH/Ollama pode levar até 180s, `local_ssh_adapter.py:47`), **o bot inteiro trava** e não
  responde a mais ninguém.

### A4 — Custo de latência do pior caso é catastrófico
- Reflexão: 3 tentativas por provider (`max_tentativas=3`), 2 providers → até **6 chamadas de
  LLM** por mensagem. Com o adapter local a 180s de timeout cada, uma única notificação pode
  levar **~18 min** no pior caso, segurando o slot de processamento. Com a fila serial
  (1 item por minuto), um item ruim atrasa todos os outros.

### A5 — `posted_at` do app é descartado; a data fica errada
- O payload traz `posted_at` (ms) (`ingestao/app.py:41`), mas o `RoteadorIngestao` **ignora**
  e o pipeline usa `item.criada_em` (hora em que chegou ao Pi) como `data_hora`
  (`orquestrador.py:78`). O backlog prevê **buffer offline no app** — então notificações vão
  chegar atrasadas e gravar a data errada.
- Espalham-se `datetime.now()` *naive* (sem timezone) em vários pontos
  (`gemini_adapter.py:114`, `local_ssh_adapter.py:83`, `transacoes.py:115`) contra colunas
  `timestamptz` no Postgres → comparações de janela (soft-match) e relatórios sujeitos a
  erro de fuso.

---

## 🟡 Robustez e operação

### O1 — Itens "ERRO" na fila não têm retry nem visibilidade
- `marcar(..., "ERRO")` deixa o item parado para sempre. Não há dead-letter, reprocessamento,
  contador de tentativas na fila, nem alerta além de uma mensagem no chat. Se a fila empacar,
  ninguém percebe.

### O2 — `fetch_next` reivindica mas nunca libera em caso de crash
- O claim marca `PROCESSANDO` atomicamente (bom), mas se o processo morre no meio, o item
  fica **preso em `PROCESSANDO`** para sempre — `fetch_next` só pega `PENDENTE`. Sem
  *visibility timeout* / reaper, todo crash perde um item.

### O3 — Dedup exato carrega o histórico inteiro do usuário para a RAM
- `soft_match` itera `self._repo.transacoes(usuario_id)` (`dedup/dedup.py:58`), e
  `TransacaoRepoNeon.transacoes` faz `SELECT ... FROM transacoes WHERE usuario_id = ...`
  **sem filtro de janela nem de status** (`neon_repos.py:61`). Hoje é barato; com o tempo é um
  full-scan crescente a cada notificação. O índice `ix_transacoes_softmatch` existe mas a
  query não o usa (não filtra por valor/estabelecimento/data no SQL).

### O4 — Build da imagem Docker no Pi 3B (1GB RAM)
- O `Dockerfile` instala `gcc`+`libpq-dev` e compila dependências no próprio Pi (`Dockerfile:12`).
  Build de `psycopg`/SQLAlchemy/google-genai num Pi 3B com ~686MB livres é lento e pode
  estourar memória. Recomendo build em outra máquina (buildx/registry) e só `pull` no Pi.

### O5 — Healthcheck depende de `curl`, ausente na imagem slim
- `docker-compose.yml:31` faz healthcheck com `curl`, mas o `python:3.13-slim` não traz `curl`
  e o Dockerfile não o instala → healthcheck sempre falha (container marcado `unhealthy`).

### O6 — Reflexão só corrige "valor"; resto da extração passa sem auditoria
- O orquestrador só olha `falhas_valor` (`orquestrador.py:81`). O auditor até gera falha de
  **data**, mas ela é silenciosamente descartada (e a data nem vem da LLM — código morto de
  fato). Erros de **`tipo` (entrada/saida)** e **`forma`** — que definem o efeito no saldo —
  não são auditados nem corrigidos. Um "saída" classificado como "entrada" inverte o saldo.

### O7 — Dependência operacional frágil no LLM local (SSH→VPN→faculdade)
- `LocalSSHAdapter` faz `subprocess.run([ssh_cmd, "ollama run ..."])` por VPN para a faculdade
  (`local_ssh_adapter.py:42`). VPN cai, máquina desliga, latência alta. Como **fallback** é
  aceitável; como **principal** (cenário real hoje, já que a chave Gemini estourou cota —
  `DECISOES-PENDENTES.md:11`) é frágil demais para ser a peça central.

---

## 🔵 Segurança

### S1 — `POST /ingestao` é aberto, sem autenticação
- Qualquer cliente na rede pode injetar transações: o `usuario_id` vem **no corpo**
  (`ingestao/app.py:37`), sem token, HMAC ou allowlist. Não há prova de que o app é legítimo.
  Basta um POST para criar transações em nome de qualquer usuário. Mínimo: um segredo
  compartilhado (header) + validação do `usuario_id` contra a família.

### S2 — Segredos já vazaram e seguem pendentes de rotação
- `DECISOES-PENDENTES.md:96-100`: connection string do Neon e token do bot vazaram no chat;
  rotação ainda **pendente**. Enquanto não rotacionar, o sistema está exposto.

### S3 — `usuario_id` confiável vindo do cliente
- A identidade da pessoa é o que o app carimba (`neon_repos.py:5` confirma: `usuarios.id` ==
  UUID que o app envia). Sem assinatura, dá para se passar por outro usuário. Relacionado a S1.

---

## 🔵 Produto / modelo de dados (gaps que vão travar o uso real)

### P1 — Não há bootstrap/onboarding; tudo depende de UUIDs pré-existentes
- O app precisa carimbar um `usuario_id` que já exista em `usuarios`. Não há fluxo de cadastro
  de família/usuário/contas/cartões/renda (você pediu isso explicitamente em D4/D5,
  `DECISOES-PENDENTES.md:34-40`). Sem onboarding, o sistema só roda com dados inseridos à mão.

### P2 — Notificação → conta/cartão não tem mapeamento (liga em C1)
- Mesmo com onboarding, falta a regra que diz "notificação do app X / banco Y → conta Z".
  Sem isso, `conta_id` fica nulo (C1) e fatura/saldo não fecham.

### P3 — Fatura/competência não são amarradas na ingestão
- `salvar` (notificação) não preenche `fatura_id` nem `competencia_id`. A regra "crédito entra
  na fatura" (handoff) não acontece no fluxo automático — só existe nos serviços testados em
  unidade, que ninguém chama nesse caminho.

### P4 — "Editar" e parte dos comandos são stubs
- Callback `editar` responde *"ainda não implementada"* (`bot/principal.py:190`). Vários
  comandos (`/lancar`, `/pagar_fatura`, `/faltei`, `/desfazer`) caem todos em `cmd_geral` →
  `DespachanteComandos` — verificar a cobertura real de cada um (fora do escopo desta leitura).

---

## ⚪ Dívida menor / inconsistências

- **D1** Categorias: o handoff lista 14 (sem "Pix") (`00-handoff.md:39`), o seed tem 15 com
  "Pix" (`db/seed.sql:16`). Seed está certo conforme decisão D7; alinhar a doc 00.
- **D2** `ItemFila.id` é `int` na fila e `str` no caminho Telegram — tipagem incoerente.
- **D3** `_map_row` força `categoria="Outros"` sempre (`sqlalchemy_repos.py:148`) — perde a
  categoria real ao ler pelo repo SQLAlchemy.
- **D4** Lixo versionado/no diretório: `app-debug.apk`, `carteirai-notifier.apk` (~13MB cada),
  `avatar.zip`, `test_mcp.py`, `stitch_preview/` soltos na raiz — limpar/`.gitignore`.
- **D5** Atualizações de status no Neon (`atualizar_status`, `salvar`) usam `with psycopg.connect`
  sem `commit()` explícito — depende do autocommit do context manager; confirmar que persiste.
- **D6** Sem teste de integração ponta-a-ponta: nenhum teste cobre o bot principal, os dois
  caminhos de ingestão, nem a interação real fila↔worker↔Neon. O risco mora exatamente aí.

---

## Matriz de priorização (o que atacar primeiro)

| # | Defeito | Sev. | Esforço | Prioridade |
|---|---------|------|---------|-----------|
| C1 | `conta_id` nulo → confirmar quebra | 🔴 | médio | **1** |
| P1/P2 | Onboarding + mapeamento notificação→conta | 🔴/🔵 | alto | **2** |
| C2/C3 | Unificar ingestão numa fila só; parar de tratar todo texto como transação | 🔴 | médio | **3** |
| C4/A3 | Modelo de execução: worker isolado + SQLite seguro (WAL/timeout/thread) | 🔴/🟠 | médio | **4** |
| S1/S2 | Auth no `/ingestao` + rotação de segredos | 🔵 | baixo | **5** |
| A1/A2 | Um conjunto de repositórios + pool de conexão | 🟠 | médio | 6 |
| O6 | Auditar `tipo`/`forma` (não só valor) | 🟡 | baixo | 7 |
| A5 | Usar `posted_at` + timezone consistente | 🟠 | baixo | 8 |
| O1/O2 | Retry/DLQ + reaper de `PROCESSANDO` órfão | 🟡 | médio | 9 |
| C5 | Reconciliar docs com a arquitetura real | 🟠 | baixo | 10 |
| O3/O4/O5 | Query de dedup com janela, build fora do Pi, curl no healthcheck | 🟡 | baixo | 11 |

---

## Recomendações de arquitetura-alvo (resumo)

1. **Uma porta de entrada, uma fila.** App e Telegram (se mantido) escrevem no mesmo
   `POST /ingestao`; o handler do bot só **enfileira**, nunca processa LLM inline. Texto comum
   no chat **não** vira transação por padrão (exigir comando ou heurística mínima).
2. **Worker como processo separado** do bot, consumindo a fila. Se quiser manter SQLite,
   ligar **WAL + `busy_timeout`** e abrir conexão **por operação/thread**; ou trocar a fila do
   Pi por uma tabela no próprio Neon (menos peças móveis) — avaliar custo.
3. **Resolver conta na confirmação:** a mensagem de aprovação no Telegram deve perguntar/assumir
   a conta (ou inferir do app de origem), preenchendo `conta_id`/`fatura_id` antes de confirmar.
4. **Um repositório só** (SQLAlchemy com pool) e apagar o paralelo em psycopg cru.
5. **Auth no ingestão** (segredo compartilhado/HMAC) + rotação imediata dos segredos vazados.
6. **Auditar tipo e forma**, não só valor — são eles que definem o efeito no saldo.
7. **Reconciliar a documentação** (docs 01/03) com o que foi de fato construído, e remover a
   promessa de "trigger" que não existe.
8. **Onboarding** de família/usuário/contas/renda como pré-requisito de qualquer uso real.

> Nada aqui condena o projeto — a base de domínio é sólida. O trabalho é fechar a fiação e
> alinhar doc × código antes de declarar o caminho feliz como funcional.
</content>
</invoke>
