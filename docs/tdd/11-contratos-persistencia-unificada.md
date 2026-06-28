# 11 — Contratos: Persistência unificada (SQLAlchemy)  `PERS-U-*`

> Objetivo (task #6 / defeitos A1/A2): matar o `infra/neon_repos.py` (psycopg cru, conexão por
> chamada) reimplementando suas 3 classes como **SQLAlchemy** (mesma `Session`/engine pooled do
> resto), **mantendo as mesmas assinaturas de porta** (consumidores não mudam). Testes em SQLite
> reaproveitando o `SQLITE_SCHEMA` de `tests/integration/test_sqlalchemy_repos.py`.

## Classes alvo (em `carteirai/infra/sqlalchemy_repos.py`)
Todas recebem uma `Session` do SQLAlchemy.

### `SqlAlchemyUsuarioRepo(session)` — porta `UsuarioRepo`
- `chat_id_de(usuario_id) -> str | None`: o `telegram_chat_id` do usuário; se nulo, cai no
  `telegram_chat_id` do **admin** da mesma família (COALESCE).
- `usuario_de_chat(chat_id) -> str | None`: id do usuário com aquele `telegram_chat_id`.

### `SqlAlchemyTransacaoIngestaoRepo(session)` — porta do Orquestrador + APROV
- `hash_existe(hash) -> bool`.
- `transacoes(usuario_id) -> list[TransacaoSimilar]` (valor, estabelecimento, data_hora).
- `salvar(usuario_id, hash, transacao: TransacaoExtraida, possivel_duplicata) -> None`:
  INSERT em `transacoes` resolvendo `categoria_id` por nome, `origem='notificacao'`,
  `status='PENDENTE_APROVACAO'`, idempotente (`ON CONFLICT (id_hash) DO NOTHING` / checagem prévia).
- `buscar(transacao_id) -> Transacao | None` (id == id_hash).
- `atualizar_status(transacao_id, status) -> None`.

### `SqlAlchemyConsultaFinanceira(session, usuario_id)` — porta `ConsultaFinanceira`
- `saldo() -> Decimal`: `familias.saldo_acumulado` via usuário→família.
- `gastos_por_categoria(categoria) -> Decimal`: soma de `transacoes` CONFIRMADA + tipo `saida` da
  **família** na **competência atual** (mês corrente). *Portável: calcular o intervalo do mês em
  Python (sem `date_trunc`/`now()` do Postgres) e filtrar `data_hora` no intervalo.*
- `pendentes() -> list[Transacao]`: transações `PENDENTE_APROVACAO` da família.

## Casos (testes em SQLite — reaproveitar SQLITE_SCHEMA + session/seed)
- **PERS-U-01** — `chat_id_de`: usuário com chat próprio → devolve o próprio chat.
- **PERS-U-02** — `chat_id_de`: membro **sem** chat → devolve o chat do admin da família.
- **PERS-U-03** — `usuario_de_chat`: chat conhecido → id; desconhecido → None.
- **PERS-U-04** — `hash_existe`: hash presente → True; ausente → False.
- **PERS-U-05** — `transacoes(usuario)`: devolve os similares (valor/estab/data) do usuário.
- **PERS-U-06** — `salvar(...)`: INSERT com `origem='notificacao'`, status PENDENTE_APROVACAO e
  `categoria_id` resolvido pelo nome; reenviar o mesmo hash não duplica.
- **PERS-U-07** — `buscar(hash)`: devolve `Transacao` mapeada; inexistente → None.
- **PERS-U-08** — `atualizar_status`: muda o status no banco.
- **PERS-U-09** — `saldo()`: devolve `saldo_acumulado` da família do usuário.
- **PERS-U-10** — `gastos_por_categoria`: soma só CONFIRMADA+saida+categoria do mês corrente;
  ignora outras categorias, pendentes e meses anteriores.
- **PERS-U-11** — `pendentes()`: lista só PENDENTE_APROVACAO da família.

## Depois (fora deste contrato, eu faço na fiação do entrypoint)
- Trocar `bot/principal.py` para usar só os repos SQLAlchemy e **apagar `infra/neon_repos.py`**.
</content>
