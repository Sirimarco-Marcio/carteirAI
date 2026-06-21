-- carteirAI — schema inicial (Neon / Postgres)
-- Fonte da verdade: docs/02-modelo-de-dados.md
-- Idempotente (IF NOT EXISTS) para poder rodar num banco limpo com segurança.
-- Aplicar com: db/apply.sh  (usa DATABASE_URL do .env)

BEGIN;

-- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------------------------------------------------------------------------
-- Núcleo
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS familias (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    nome             text NOT NULL,
    saldo_acumulado  numeric(14,2) NOT NULL DEFAULT 0   -- patrimônio que vai somando
);

CREATE TABLE IF NOT EXISTS usuarios (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    familia_id        uuid NOT NULL REFERENCES familias(id) ON DELETE CASCADE,
    nome              text NOT NULL,
    telegram_chat_id  text UNIQUE,                       -- roteamento de aprovação
    role              text NOT NULL DEFAULT 'membro'
                          CHECK (role IN ('admin','membro'))
);

CREATE TABLE IF NOT EXISTS instituicoes (
    id    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    nome  text NOT NULL,
    tipo  text NOT NULL CHECK (tipo IN ('banco','carteira','cartao'))
);

CREATE TABLE IF NOT EXISTS contas (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id      uuid NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    instituicao_id  uuid NOT NULL REFERENCES instituicoes(id),
    tipo            text NOT NULL CHECK (tipo IN ('corrente','credito','dinheiro')),
    limite          numeric(14,2),     -- só cartão
    saldo_atual     numeric(14,2) NOT NULL DEFAULT 0,   -- corrente/dinheiro
    dia_fechamento  int,               -- só cartão (1..31)
    dia_vencimento  int,               -- só cartão (1..31)
    CHECK (dia_fechamento IS NULL OR dia_fechamento BETWEEN 1 AND 31),
    CHECK (dia_vencimento IS NULL OR dia_vencimento BETWEEN 1 AND 31)
);

CREATE TABLE IF NOT EXISTS categorias (
    id    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    nome  text NOT NULL UNIQUE,
    tipo  text NOT NULL DEFAULT 'despesa' CHECK (tipo IN ('despesa','receita'))
);

-- ---------------------------------------------------------------------------
-- Competência (mês fechado) e Fatura (cartão)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS competencias (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    familia_id       uuid NOT NULL REFERENCES familias(id) ON DELETE CASCADE,
    mes              int  NOT NULL CHECK (mes BETWEEN 1 AND 12),
    ano              int  NOT NULL,
    renda_prevista   numeric(14,2) NOT NULL DEFAULT 0,
    renda_realizada  numeric(14,2),                     -- preenchido no /fechar_mes
    total_gasto      numeric(14,2) NOT NULL DEFAULT 0,
    sobra            numeric(14,2),
    status           text NOT NULL DEFAULT 'ABERTA' CHECK (status IN ('ABERTA','FECHADA')),
    UNIQUE (familia_id, mes, ano)
);

CREATE TABLE IF NOT EXISTS faturas (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    conta_id     uuid NOT NULL REFERENCES contas(id) ON DELETE CASCADE,   -- cartão
    mes          int  NOT NULL CHECK (mes BETWEEN 1 AND 12),
    ano          int  NOT NULL,
    valor_total  numeric(14,2) NOT NULL DEFAULT 0,
    vencimento   date,
    status       text NOT NULL DEFAULT 'ABERTA' CHECK (status IN ('ABERTA','FECHADA','PAGA')),
    UNIQUE (conta_id, mes, ano)
);

-- ---------------------------------------------------------------------------
-- Transações (id_hash = dedup exato do texto bruto normalizado)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS transacoes (
    id_hash            text PRIMARY KEY,                -- dedup exato
    conta_id           uuid REFERENCES contas(id) ON DELETE SET NULL,
    usuario_id         uuid NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    categoria_id       uuid REFERENCES categorias(id),
    fatura_id          uuid REFERENCES faturas(id) ON DELETE SET NULL,     -- null se não-cartão
    competencia_id     uuid REFERENCES competencias(id) ON DELETE SET NULL,
    valor              numeric(14,2) NOT NULL,
    data_hora          timestamptz NOT NULL,
    estabelecimento    text,
    tipo               text NOT NULL CHECK (tipo IN ('entrada','saida')),
    forma              text NOT NULL CHECK (forma IN ('debito','credito','pix','dinheiro')),
    parcela_atual      int NOT NULL DEFAULT 1,
    parcelas_total     int NOT NULL DEFAULT 1,
    status             text NOT NULL DEFAULT 'PENDENTE_APROVACAO'
                           CHECK (status IN ('PENDENTE_APROVACAO','CONFIRMADA','IGNORADA')),
    possivel_duplicata boolean NOT NULL DEFAULT false,  -- soft-match → confirmação especial
    origem             text NOT NULL CHECK (origem IN ('notificacao','manual')),
    criada_em          timestamptz NOT NULL DEFAULT now()
);

-- soft-match: mesmo usuário + valor + estabelecimento dentro de uma janela de tempo
CREATE INDEX IF NOT EXISTS ix_transacoes_softmatch
    ON transacoes (usuario_id, valor, estabelecimento, data_hora);
CREATE INDEX IF NOT EXISTS ix_transacoes_competencia ON transacoes (competencia_id);
CREATE INDEX IF NOT EXISTS ix_transacoes_fatura      ON transacoes (fatura_id);
CREATE INDEX IF NOT EXISTS ix_transacoes_status      ON transacoes (status);

-- ---------------------------------------------------------------------------
-- Renda
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fontes_renda (
    id                     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id             uuid NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    nome                   text NOT NULL,                       -- UERJ / Convem / BNDES
    tipo_calculo           text NOT NULL CHECK (tipo_calculo IN ('fixo_mensal','por_dia')),
    valor_base             numeric(14,2) NOT NULL DEFAULT 0,    -- mensal OU por dia
    valor_alimentacao_dia  numeric(14,2) NOT NULL DEFAULT 0,
    valor_transporte_dia   numeric(14,2) NOT NULL DEFAULT 0,
    dias_semana            jsonb NOT NULL DEFAULT '[]'::jsonb,  -- [1,2,3,4,5] = seg-sex
    ativa                  boolean NOT NULL DEFAULT true
);

CREATE TABLE IF NOT EXISTS registro_dias (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    fonte_renda_id  uuid NOT NULL REFERENCES fontes_renda(id) ON DELETE CASCADE,
    data            date NOT NULL,
    status          text NOT NULL CHECK (status IN ('presencial','remoto','falta')),
    UNIQUE (fonte_renda_id, data)
);

-- ---------------------------------------------------------------------------
-- Reservas / Dívidas
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS reservas (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    familia_id  uuid NOT NULL REFERENCES familias(id) ON DELETE CASCADE,
    nome        text NOT NULL,
    tipo        text NOT NULL CHECK (tipo IN ('reserva','investimento')),
    saldo       numeric(14,2) NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS dividas_creditos (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id        uuid NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    contraparte_nome  text NOT NULL,
    tipo              text NOT NULL CHECK (tipo IN ('devo','me_devem')),
    valor             numeric(14,2) NOT NULL,
    vencimento        date,
    status            text NOT NULL DEFAULT 'aberta' CHECK (status IN ('aberta','quitada'))
);

-- ---------------------------------------------------------------------------
-- Fila de mensagens (buffer/durabilidade no Pi → também serve de log no Neon)
-- id_hash = dedup exato do texto bruto normalizado
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fila_mensagens (
    id_hash       text PRIMARY KEY,
    texto_bruto   text NOT NULL,
    usuario_id    uuid REFERENCES usuarios(id) ON DELETE SET NULL,
    origem        text NOT NULL CHECK (origem IN ('notificacao','manual')),
    status        text NOT NULL DEFAULT 'PENDENTE'
                      CHECK (status IN ('PENDENTE','PROCESSANDO','CONCLUIDO','DUPLICADA','ERRO')),
    criada_em     timestamptz NOT NULL DEFAULT now(),
    processada_em timestamptz
);

COMMIT;
