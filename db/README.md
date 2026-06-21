# Banco de dados — processo de criação (Neon / Postgres)

O schema é **versionado em SQL** (não criado à mão no console). Assim, qualquer banco
Neon limpo nasce **idêntico e compatível com a aplicação**. Fonte da verdade do modelo:
`docs/02-modelo-de-dados.md`.

## Estrutura
- `migrations/0001_init.sql` — DDL completo (tabelas, FKs, checks, índices). Idempotente.
- `seed.sql` — dados de base (categorias autorizadas). Idempotente.
- `apply.sh` — aplica migrations + seed usando `DATABASE_URL`.

## Como gerar um banco novo e limpo
1. Crie um projeto/branch novo no Neon e copie a connection string.
2. Coloque-a no `.env` como `DATABASE_URL=...` (ou exporte no ambiente).
3. Rode:
   ```bash
   db/apply.sh
   ```
   Precisa do cliente `psql` (`sudo dnf install postgresql`). Sem ele, alternativa:
   cole o conteúdo de `migrations/0001_init.sql` e `seed.sql` no **SQL Editor do Neon**.

## Evolução do schema (futuro)
- Mudanças no modelo = **nova migration** `migrations/000N_descricao.sql` (nunca editar uma já aplicada).
- `apply.sh` roda todas em ordem; como são `IF NOT EXISTS`/`ON CONFLICT`, reaplicar é seguro.
- Quando a app ganhar a camada SQLAlchemy, os models devem refletir exatamente este schema
  (ou adotamos Alembic gerando as migrations a partir dos models). Por ora, o SQL é o canônico.

## Notas de design (de docs/02)
- `transacoes.id_hash` e `fila_mensagens.id_hash` = dedup exato (hash do texto bruto normalizado).
- Índice `ix_transacoes_softmatch (usuario_id, valor, estabelecimento, data_hora)` = soft-match
  (possível duplicata semântica → confirmação especial no Telegram).
- Compra no crédito não mexe em `saldo_atual`: entra ligada a uma `fatura`; saldo só cai no pagamento.
