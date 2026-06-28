# 08 — Contratos: Fila de Ingestão (Neon)  `FILA-N-*`

> Fonte: `docs/06-arquitetura-alvo.md` (Chunks A, C, D). A fila de ingestão é uma **tabela no Neon**
> (`fila_ingestao`) consumida pelo worker do Pi por polling. Substitui a fila SQLite anterior.
> Testes unitários devem rodar contra **SQLite em memória** (engine SQLAlchemy injetável) — a mesma
> classe roda em Postgres/Neon em produção. **Relógio injetável** (determinismo, nunca `now()` direto).

## Classe alvo
`carteirai.fila.fila_ingestao.FilaIngestao`
- Construtor: `FilaIngestao(engine, relogio=None, visibility_timeout_min=30, max_tentativas=5)`.
- `relogio`: callable `() -> datetime` (default `datetime.now`); usado em `criada_em`, `claimed_em`,
  `processada_em`.
- Deve garantir a tabela (`CREATE TABLE IF NOT EXISTS`) de forma **portável SQLite/Postgres**
  (recomendado: SQLAlchemy Core — `Table`/`MetaData`/`insert`/`update`/`select`).

## Campos da fila (`fila_ingestao`)
`id` (PK autoincrement), `id_hash` (text), `texto_bruto` (text), `usuario_id` (text),
`package_name` (text, nullable), `origem` (`notificacao|manual`), `status`
(`PENDENTE|PROCESSANDO|CONCLUIDO|DUPLICADA|ERRO`), `tentativas` (int, default 0),
`data_hora` (timestamp — vem do `posted_at`), `client_msg_id` (text, nullable, **único**),
`criada_em`, `claimed_em` (nullable), `processada_em` (nullable).

## Casos

- **FILA-N-01 — enqueue insere PENDENTE.** `enqueue(texto_bruto, usuario_id, origem, package_name,
  data_hora, client_msg_id=None)` cria o item com `status='PENDENTE'`, `tentativas=0`,
  `criada_em = relogio()`, `claimed_em/processada_em = None`, e retorna o item (com `id`).
- **FILA-N-02 — enqueue idempotente por `client_msg_id`.** Reenviar o mesmo `client_msg_id` **não**
  duplica (ON CONFLICT DO NOTHING); retorna o item já existente. `client_msg_id=None` nunca colide.
- **FILA-N-03 — claim FIFO.** `claim()` pega o `PENDENTE` mais antigo (ordem por `id`), marca
  `PROCESSANDO`, seta `claimed_em = relogio()`, e retorna o item.
- **FILA-N-04 — claim atômico.** Duas chamadas consecutivas de `claim()` **nunca** devolvem o mesmo
  item: a 2ª devolve o próximo `PENDENTE` ou `None`.
- **FILA-N-05 — claim vazio.** `claim()` devolve `None` quando não há `PENDENTE`.
- **FILA-N-06 — marcar final.** `marcar(item_id, status)` com `status` em
  `{CONCLUIDO, DUPLICADA, ERRO}` grava o status e seta `processada_em = relogio()`.
- **FILA-N-07 — reaper recupera órfãos.** `recuperar_orfaos()` devolve a `PENDENTE` todo item
  `PROCESSANDO` com `claimed_em` mais antigo que `visibility_timeout_min` (30 min), incrementando
  `tentativas`. Retorna a quantidade recuperada. `claimed_em` é zerado ao voltar.
- **FILA-N-08 — reaper preserva recentes.** Itens `PROCESSANDO` com `claimed_em` dentro da janela
  (< 30 min) **não** são tocados por `recuperar_orfaos()`.
- **FILA-N-09 — DLQ após max tentativas.** No `recuperar_orfaos()`, um item órfão que **já** atingiu
  `max_tentativas` (5) vai para `status='ERRO'` (dead-letter) em vez de voltar a `PENDENTE`.
- **FILA-N-10 — relógio determinístico.** Com `relogio` fixo injetado, `criada_em`/`claimed_em`/
  `processada_em` são exatamente o valor do relógio (sem chamar `datetime.now()`).

## Fora deste contrato (próximos)
- Worker loop (poll → claim → orquestrador → marcar + aprovação) → `FILA-N`/worker (contrato 09).
- Aviso no Telegram ao cair na DLQ → worker.
- Cálculo de `id_hash`/dedup exato já existe em `carteirai.dedup.dedup.hash_exato`.
</content>
