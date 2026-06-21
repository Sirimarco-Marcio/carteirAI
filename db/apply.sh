#!/usr/bin/env bash
# Aplica o schema (migrations em ordem) + seed num banco Postgres/Neon.
# Lê DATABASE_URL do .env (ou do ambiente). Idempotente — seguro rodar de novo.
#
# Uso:
#   db/apply.sh                 # aplica migrations + seed
#   db/apply.sh --schema-only   # só migrations (sem seed)
#   DATABASE_URL=... db/apply.sh # sobrepõe a connection string
set -euo pipefail

raiz="$(cd "$(dirname "$0")/.." && pwd)"
cd "$raiz"

# Carrega .env se DATABASE_URL não veio do ambiente
if [ -z "${DATABASE_URL:-}" ] && [ -f .env ]; then
  # shellcheck disable=SC1091
  set -a; source .env; set +a
fi

if [ -z "${DATABASE_URL:-}" ]; then
  echo "ERRO: defina DATABASE_URL (no .env ou no ambiente)." >&2
  exit 1
fi

if ! command -v psql >/dev/null 2>&1; then
  echo "ERRO: 'psql' não encontrado. Instale o cliente do Postgres (ex: sudo dnf install postgresql)." >&2
  echo "Alternativa: cole o conteúdo de db/migrations/*.sql e db/seed.sql no SQL Editor do Neon." >&2
  exit 1
fi

echo ">> Aplicando migrations em $(echo "$DATABASE_URL" | sed -E 's#://[^@]+@#://***@#')"
for f in db/migrations/*.sql; do
  echo "   - $f"
  psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$f"
done

if [ "${1:-}" != "--schema-only" ]; then
  echo ">> Aplicando seed (db/seed.sql)"
  psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f db/seed.sql
fi

echo ">> OK. Tabelas:"
psql "$DATABASE_URL" -c "\dt"
