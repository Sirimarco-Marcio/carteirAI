#!/usr/bin/env bash
# Inicia o bot do Telegram em background e o servidor FastAPI em foreground

echo "🤖 Iniciando Telegram Bot (principal.py)..."
python -m carteirai.bot.principal &

echo "🌐 Iniciando FastAPI (ingestao)..."
exec uvicorn carteirai.ingestao.app:app --host 0.0.0.0 --port 8000
