#!/usr/bin/env python3
"""
Registra os comandos do bot no Telegram para que o menu de "/" apareça para o usuário.
Requer TELEGRAM_BOT_TOKEN no arquivo .env.
"""
import os
import sys
import httpx

# Tenta carregar .env caso o python-dotenv esteja instalado
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    print("❌ ERRO: TELEGRAM_BOT_TOKEN não encontrado nas variáveis de ambiente nem no .env")
    sys.exit(1)

# Lista de comandos que o bot suporta
COMMANDS = [
    {"command": "saldo", "description": "Verifica seu saldo atual"},
    {"command": "gastos", "description": "Uso: /gastos <categoria>"},
    {"command": "pendentes", "description": "Lista transações esperando aprovação"},
    {"command": "faltei", "description": "Uso: /faltei ou /faltei DD/MM"},
    {"command": "lancar", "description": "Faz um lançamento manual guiado"},
    {"command": "pagar_fatura", "description": "Paga a fatura do cartão aberta"},
    {"command": "desfazer", "description": "Desfaz a última transação confirmada"},
    {"command": "giro", "description": "Consulta capital de giro"},
    {"command": "cartao", "description": "Consulta cartões"},
    {"command": "limite", "description": "Consulta limite livre dos cartões"},
    {"command": "relatorio", "description": "Gera relatório da competência"},
    {"command": "fechar_mes", "description": "Fecha o mês atual"},
    {"command": "divida", "description": "Consulta dívidas em aberto"}
]

url = f"https://api.telegram.org/bot{TOKEN}/setMyCommands"

print("📡 Enviando comandos para o Telegram...")
try:
    response = httpx.post(url, json={"commands": COMMANDS})
    response.raise_for_status()
    data = response.json()
    if data.get("ok"):
        print("✅ Comandos registrados com sucesso! O menu '/' já deve aparecer no seu Telegram.")
    else:
        print(f"❌ Falha no Telegram: {data}")
except Exception as e:
    print(f"❌ Erro de rede ou requisição: {e}")
