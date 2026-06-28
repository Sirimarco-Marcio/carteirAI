-- carteirAI — fila de ingestão no Neon (arquitetura nova, docs/06 Chunk A/C/D)
-- A fila vive no Neon: a Vercel faz INSERT (via /api/ingestao) e o worker do Pi faz polling.
-- Espelha a tabela criada por carteirai.fila.fila_ingestao.FilaIngestao (SQLAlchemy Core).
-- Idempotente. Aplicar com: db/apply.sh (usa DATABASE_URL do .env).

BEGIN;

CREATE TABLE IF NOT EXISTS fila_ingestao (
    id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_hash        text        NOT NULL,                  -- dedup exato (hash do texto)
    texto_bruto    text        NOT NULL,
    usuario_id     text        NOT NULL,                  -- id do usuário (derivado do token na Vercel)
    package_name   text,                                  -- app de origem → resolve a conta
    origem         text        NOT NULL
                       CHECK (origem IN ('notificacao','manual')),
    status         text        NOT NULL DEFAULT 'PENDENTE'
                       CHECK (status IN ('PENDENTE','PROCESSANDO','CONCLUIDO','DUPLICADA','ERRO')),
    tentativas     int         NOT NULL DEFAULT 0,        -- incrementado pelo reaper
    data_hora      timestamptz NOT NULL,                  -- posted_at (momento real do evento)
    client_msg_id  text UNIQUE,                           -- idempotência de transporte (retry do POST)
    criada_em      timestamptz NOT NULL DEFAULT now(),
    claimed_em     timestamptz,                           -- setado no claim; base do reaper
    processada_em  timestamptz
);

-- Claim FIFO eficiente: pega o PENDENTE mais antigo.
CREATE INDEX IF NOT EXISTS ix_fila_ingestao_pendente
    ON fila_ingestao (status, id);

-- Reaper: varre PROCESSANDO por claimed_em (órfãos além do visibility timeout).
CREATE INDEX IF NOT EXISTS ix_fila_ingestao_claimed
    ON fila_ingestao (status, claimed_em);

COMMIT;
