#!/usr/bin/env bash
# deploy-pi.sh — Faz o deploy do worker carteirAI no Raspberry Pi
# Uso: ./scripts/deploy-pi.sh
# Pré-requisitos:
#   - SSH configurado para o Pi (ver segredos.local.md)
#   - Repositório com código novo commitado
#   - .env pronto no Pi em ~/carteirAI/.env

set -euo pipefail

PI_HOST="${PI_HOST:-msiri@192.168.1.29}"
PI_DIR="~/carteirAI"
REPO_URL="https://github.com/Sirimarco-Marcio/carteirAI.git"

echo "🚀 Deploy carteirAI → Pi ($PI_HOST)"

ssh "$PI_HOST" bash -s << 'REMOTE'
set -euo pipefail

REPO_URL="https://github.com/Sirimarco-Marcio/carteirAI.git"
PI_DIR="$HOME/carteirAI"

# 1. Clonar ou atualizar o repositório
if [ -d "$PI_DIR/.git" ]; then
    echo "📥 Atualizando repositório..."
    cd "$PI_DIR"
    git pull --ff-only
else
    echo "📥 Clonando repositório..."
    git clone "$REPO_URL" "$PI_DIR"
    cd "$PI_DIR"
fi

# 2. Verificar .env
if [ ! -f "$PI_DIR/.env" ]; then
    echo "❌ ERRO: $PI_DIR/.env não encontrado!"
    echo "   Crie o .env a partir do .env.example e preencha os segredos."
    exit 1
fi

# 3. Build e subir o container
echo "🐳 Build da imagem Docker..."
docker compose build --no-cache

echo "🐳 Subindo o worker..."
docker compose up -d

# 4. Aguardar healthcheck
echo "⏳ Aguardando healthcheck..."
sleep 10
if docker inspect --format='{{.State.Health.Status}}' carteirai-worker 2>/dev/null | grep -q "healthy"; then
    echo "✅ Worker saudável!"
else
    echo "⚠️  Healthcheck ainda pendente — verificando logs..."
    docker logs --tail=30 carteirai-worker
fi

echo "✅ Deploy concluído! Worker rodando em http://$(hostname -I | awk '{print $1}'):8000"
echo "   Teste: curl http://localhost:8000/healthz"

echo "📱 Registrando comandos mais recentes no Telegram..."
docker compose exec -T carteirai-worker python scripts/register_commands.py || echo "⚠️ Erro ao registrar comandos do Telegram, verifique o TOKEN."
REMOTE

echo "✅ Deploy remoto finalizado."
