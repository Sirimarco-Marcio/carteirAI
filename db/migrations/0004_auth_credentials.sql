-- carteirAI — credenciais de acesso (e-mail + senha bcrypt)
-- Separado de usuarios: um usuário pode não ter login web (ex: membro sem acesso ao painel).
-- Idempotente.

BEGIN;

CREATE TABLE IF NOT EXISTS auth_credentials (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id  uuid        NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    email       text        NOT NULL UNIQUE,
    senha_hash  text        NOT NULL,
    criado_em   timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_auth_credentials_email ON auth_credentials (email);

COMMIT;
