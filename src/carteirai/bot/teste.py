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
from decimal import Decimal
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


def _fmt_brl(valor: Decimal) -> str:
    """Formata Decimal como R$ 1.234,56."""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _teclado_parcelas(tid: int) -> InlineKeyboardMarkup:
    """Botões para o usuário informar o nº de parcelas de uma compra no crédito."""
    opcoes = [1, 2, 3, 6, 10, 12]
    botoes = [
        InlineKeyboardButton(f"{n}x" if n > 1 else "à vista", callback_data=f"parc:{tid}:{n}")
        for n in opcoes
    ]
    # 3 por linha
    linhas = [botoes[i:i + 3] for i in range(0, len(botoes), 3)]
    return InlineKeyboardMarkup(linhas)


def _montar_aprovacao(tid: int, extraida) -> tuple[str, InlineKeyboardMarkup]:
    """Mensagem + teclado de confirmação final, já com info de parcelas no crédito."""
    linhas = [
        "💰 *Transação extraída*",
        f"Valor: {_fmt_brl(extraida.valor)}",
        f"Tipo: {extraida.tipo}",
        f"Forma: {extraida.forma}",
        f"Estabelecimento: {extraida.estabelecimento or '—'}",
        f"Categoria: {extraida.categoria}",
        f"Data/hora: {extraida.data_hora.strftime('%d/%m/%Y %H:%M')}",
    ]
    if extraida.forma == "credito" and extraida.parcelas_total > 1:
        n = extraida.parcelas_total
        por_parcela = (extraida.valor / Decimal(n)).quantize(Decimal("0.01"))
        linhas.append(
            f"Parcelas: *{n}x de {_fmt_brl(por_parcela)}* "
            f"(compromete o limite nas próximas {n} faturas)"
        )
    elif extraida.forma == "credito":
        linhas.append("Parcelas: à vista (1x)")

    linhas.append("\nConfirma esta transação?")
    teclado = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Sim", callback_data=f"aprovar:{tid}"),
        InlineKeyboardButton("❌ Não", callback_data=f"rejeitar:{tid}"),
        InlineKeyboardButton("✏️ Editar", callback_data=f"editar:{tid}"),
    ]])
    return "\n".join(linhas), teclado


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

    # 2. DATA é programática: vem do horário da mensagem (no real, do postedAt da notificação).
    #    A LLM não decide data/ano.
    extraida.data_hora = update.message.date

    # 3. Auditoria — só o VALOR é rígido (anti-alucinação). Data não é auditada (é confiável).
    res = auditar(texto, extraida)
    logger.info("   EXTRAIU: %s", extraida.model_dump())
    valor_reprovado = any("valor" in f.lower() for f in res.falhas)
    logger.info("   VALOR_REPROVADO: %s | falhas=%s", valor_reprovado, res.falhas)
    if valor_reprovado:
        await update.message.reply_text(
            "⚠️ Não parece uma transação (não encontrei o valor no texto). Ignorado."
        )
        return

    # 4. Guarda e decide o fluxo
    tid = next(_id_counter)
    _transacoes[tid] = extraida

    # Crédito sem nº de parcelas conhecido → perguntar antes de confirmar
    if extraida.forma == "credito" and extraida.parcelas_total <= 1:
        await update.message.reply_text(
            f"💳 Compra no crédito de {_fmt_brl(extraida.valor)} em "
            f"{extraida.estabelecimento or 'estabelecimento'}.\n\nEm quantas parcelas?",
            reply_markup=_teclado_parcelas(tid),
        )
        return

    texto_resp, teclado = _montar_aprovacao(tid, extraida)
    await update.message.reply_text(texto_resp, parse_mode="Markdown", reply_markup=teclado)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Trata cliques nos botões inline."""
    query = update.callback_query
    await query.answer()

    partes = (query.data or "").split(":")
    acao = partes[0] if partes else ""
    logger.info("   CLIQUE: %s", query.data)

    # Seleção de parcelas → fixa parcelas_total e mostra a confirmação final
    if acao == "parc" and len(partes) == 3:
        tid = int(partes[1])
        n = int(partes[2])
        extraida = _transacoes.get(tid)
        if extraida is None:
            await query.edit_message_text("⚠️ Transação expirou (spike sem persistência).")
            return
        extraida.parcelas_total = n
        logger.info("   PARCELAS definidas: tid=%s n=%s", tid, n)
        texto_resp, teclado = _montar_aprovacao(tid, extraida)
        await query.edit_message_text(texto_resp, parse_mode="Markdown", reply_markup=teclado)
        return

    if acao == "aprovar":
        await query.edit_message_text("✅ Confirmado")
    elif acao == "rejeitar":
        await query.edit_message_text("❌ Ignorado")
    elif acao == "editar":
        await query.edit_message_text("✏️ Edição manual ainda não implementada (spike)")
    else:
        await query.edit_message_text(f"⚠️ Ação desconhecida: {query.data!r}")


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
