-- carteirAI — mapeamento app→conta (docs/06 Chunk B)
-- Guarda o package_name do app de origem em cada conta, para o worker resolver
-- a conta a partir da notificação. Idempotente.

BEGIN;

ALTER TABLE contas ADD COLUMN IF NOT EXISTS package_name text;

-- Busca rápida por (usuario, package) ao resolver a conta de uma notificação.
CREATE INDEX IF NOT EXISTS ix_contas_usuario_package
    ON contas (usuario_id, package_name);

COMMIT;
