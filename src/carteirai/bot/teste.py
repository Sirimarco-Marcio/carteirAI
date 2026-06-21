"""
SPIKE de teste do Telegram — sem Neon, sem fila SQLite, estado em memória.

Objetivo: validar o pipeline completo LLM → Auditoria → confirmação do usuário
diretamente no Telegram, antes de integrar a fila e o banco.

O transporte real (App Android → Webhook/Polling → fila) fica para a fase seguinte.

Uso:
    python -m carteirai.bot.teste

Requer no .env:
    TELEGRAM_BOT_TOKEN=<token>
    GEMINI_API_KEY=<chave>
    LLM_PROVIDER=gemini   (opcional; o bot força "gemini")
"""

from __future__ import annotations

import logging
import sys
from itertools import count

from dotenv import load_dotenv

load_dotenv()

import os

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ---------------------------------------------------------------------------
# Verificação antecipada do token (falha clara antes de importar o SDK)
# ---------------------------------------------------------------------------
_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not _TOKEN:
    print(
        "ERRO: variável de ambiente TELEGRAM_BOT_TOKEN não encontrada.\n"
        "Defina-a no .env ou no ambiente antes de iniciar o bot.",
        file=sys.stderr,
    )
    sys.exit(1)

# ---------------------------------------------------------------------------
# Importações do SDK (após validar o token)
# ---------------------------------------------------------------------------
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from carteirai.ia.auditor import auditar
from carteirai.ia.base_llm import LLMError
from carteirai.ia.base_llm import resolver_llm

# ---------------------------------------------------------------------------
# Estado em memória (spike — sem persistência)
# ---------------------------------------------------------------------------
_id_counter = count(start=1)
_transacoes: dict[int, object] = {}  # id → TransacaoExtraida


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Responde /start com boas-vindas e o chat_id do usuário."""
    chat_id = update.effective_chat.id
    await update.message.reply_text(
        f"👋 Olá! Sou o bot de teste do carteirAI.\n\n"
        f"Envie o texto de uma notificação bancária e eu extraio a transação.\n\n"
        f"Seu chat_id: <code>{chat_id}</code>",
        parse_mode="HTML",
    )


async def handle_notificacao(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Trata mensagens de texto como notificações bancárias."""
    texto = update.message.text
    logger.info("── NOTIF recebida: %r", texto)

    # 1. Extração via LLM
    llm = resolver_llm("gemini")
    try:
        extraida = await llm.extrair(texto)
    except LLMError as exc:
        logger.info("   EXTRACAO FALHOU: %s", exc)
        await update.message.reply_text(f"❌ Não consegui extrair: {exc}")
        return

    # 2. Auditoria anti-alucinação
    res = auditar(texto, extraida)
    logger.info("   EXTRAIU: %s", extraida.model_dump())
    logger.info("   AUDIT:   %s", res.model_dump())

    # 3. Valor é rígido — se reprovado, para aqui
    valor_reprovado = any("valor" in f.lower() for f in res.falhas)
    if valor_reprovado:
        falhas_str = "\n• ".join(res.falhas)
        await update.message.reply_text(
            f"⚠️ Auditoria reprovou o VALOR (possível alucinação):\n• {falhas_str}"
        )
        return

    # 4. Transação aceita (valor ok; data pode ser inferida) — guardar em memória
    tid = next(_id_counter)
    _transacoes[tid] = extraida

    # Nota sobre a data
    data_inferida = any("data" in f.lower() for f in res.falhas)
    nota_data = " _(data do horário de recebimento)_" if data_inferida else ""

    # Formatar resposta
    valor_fmt = f"R$ {extraida.valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    resposta = (
        f"💰 *Transação extraída*\n"
        f"Valor: {valor_fmt}\n"
        f"Tipo: {extraida.tipo}\n"
        f"Forma: {extraida.forma}\n"
        f"Estabelecimento: {extraida.estabelecimento or '—'}\n"
        f"Categoria: {extraida.categoria}\n"
        f"Data/hora: {extraida.data_hora.strftime('%d/%m/%Y %H:%M')}{nota_data}\n\n"
        f"Confirma esta transação?"
    )

    teclado = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Sim", callback_data=f"aprovar:{tid}"),
            InlineKeyboardButton("❌ Não", callback_data=f"rejeitar:{tid}"),
            InlineKeyboardButton("✏️ Editar", callback_data=f"editar:{tid}"),
        ]
    ])

    await update.message.reply_text(resposta, parse_mode="Markdown", reply_markup=teclado)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Trata cliques nos botões inline."""
    query = update.callback_query
    await query.answer()

    data: str = query.data or ""
    if ":" not in data:
        await query.edit_message_text("⚠️ Callback desconhecido.")
        return

    acao, tid_str = data.split(":", 1)
    logger.info("   CLIQUE: %s tid=%s", acao, tid_str)

    if acao == "aprovar":
        await query.edit_message_text("✅ Confirmado")
    elif acao == "rejeitar":
        await query.edit_message_text("❌ Ignorado")
    elif acao == "editar":
        await query.edit_message_text("✏️ Edição manual ainda não implementada (spike)")
    else:
        await query.edit_message_text(f"⚠️ Ação desconhecida: {acao!r}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Inicia o bot com long-polling."""
    app = Application.builder().token(_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_notificacao)
    )
    app.add_handler(CallbackQueryHandler(handle_callback))

    logger.info("Bot de teste carteirAI iniciado. Pressione Ctrl+C para parar.")
    app.run_polling()


if __name__ == "__main__":
    main()
