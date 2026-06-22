"""Bot principal (fiação real) — liga Telegram ↔ Orquestrador ↔ Neon.

Funções:
- Comandos: /start, /saldo, /gastos <cat>, /pendentes, /ajuda (via DespachanteComandos + Neon).
- Notificação (texto): pipeline real (dedup → LLM → auditor → grava no Neon) e manda aprovação
  com botões pro chat do dono (membro sem chat → admin).
- Callbacks: [Sim]/[Não]/[Editar] (e duplicata) → confirma/ignora no Neon, com checagem de dono.

Rodar: PYTHONPATH=src python -m carteirai.bot.principal
Requer no .env: TELEGRAM_BOT_TOKEN, DATABASE_URL, GEMINI_API_KEY (extração).
"""

from __future__ import annotations

import logging
import os
import sys

from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("carteirai.bot")

_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not _TOKEN:
    print("ERRO: TELEGRAM_BOT_TOKEN ausente no .env", file=sys.stderr)
    sys.exit(1)

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters,
)

from carteirai.dedup.dedup import hash_exato
from carteirai.dominio.dtos import ItemFila
from carteirai.ia.base_llm import resolver_llm
from carteirai.infra.neon_repos import (
    ConsultaFinanceiraNeon, TransacaoRepoNeon, UsuarioRepoNeon,
)
from carteirai.orquestracao.orquestrador import Orquestrador
from carteirai.telegram.comandos import DespachanteComandos

_ur = UsuarioRepoNeon()
_tr = TransacaoRepoNeon()


class _NoOpFila:
    def marcar(self, item_id, status): pass


def _brl(v) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        f"👋 carteirAI ligado.\nSeu chat_id: <code>{update.effective_chat.id}</code>\n"
        f"Comandos: /saldo /gastos <categoria> /pendentes", parse_mode="HTML")


async def cmd_geral(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = str(update.effective_chat.id)
    usuario_id = _ur.usuario_de_chat(chat_id)
    if usuario_id is None:
        await update.message.reply_text("Chat não cadastrado.")
        return
    resp = DespachanteComandos(ConsultaFinanceiraNeon(usuario_id)).processar(update.message.text, usuario_id)
    await update.message.reply_text(resp)


async def handle_notificacao(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = str(update.effective_chat.id)
    usuario_id = _ur.usuario_de_chat(chat_id)
    if usuario_id is None:
        return  # chat desconhecido: ignora (segurança)
    texto = update.message.text
    item = ItemFila(id=update.message.message_id, texto_bruto=texto, usuario_id=usuario_id,
                    origem="notificacao", status="PROCESSANDO", criada_em=update.message.date)
    orq = Orquestrador(_NoOpFila(), _tr, resolver_llm("gemini"), max_tentativas=3)
    res = await orq.processar(item)

    if res.status == "PENDENTE_APROVACAO":
        h = hash_exato(texto)
        t = res.transacao
        dup = res.possivel_duplicata
        chat_dono = _ur.chat_id_de(usuario_id)
        if dup:
            txt = f"⚠️ Parece repetida: {_brl(t.valor)} em {t.estabelecimento or '—'}. É a mesma ou nova?"
            kb = [[InlineKeyboardButton("É a mesma", callback_data=f"mesma:{h}"),
                   InlineKeyboardButton("É nova", callback_data=f"nova:{h}")]]
        else:
            txt = (f"💰 {t.tipo} {_brl(t.valor)} · {t.forma}\n{t.estabelecimento or '—'} · {t.categoria}\n"
                   f"Confirma?")
            kb = [[InlineKeyboardButton("✅ Sim", callback_data=f"sim:{h}"),
                   InlineKeyboardButton("❌ Não", callback_data=f"nao:{h}"),
                   InlineKeyboardButton("✏️ Editar", callback_data=f"editar:{h}")]]
        await ctx.bot.send_message(chat_dono, txt, reply_markup=InlineKeyboardMarkup(kb))
    elif res.status == "IGNORADA":
        await update.message.reply_text("ℹ️ Não parece uma transação (sem valor). Ignorado.")
    elif res.status == "DUPLICADA":
        await update.message.reply_text("♻️ Duplicata exata — descartada.")
    else:  # ERRO
        await update.message.reply_text(f"❌ Não consegui extrair: {res.motivo_erro}")


async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    acao, _, h = (q.data or "").partition(":")
    t = _tr.buscar(h)
    if t is None:
        await q.edit_message_text("⚠️ Transação não encontrada."); return
    if _ur.chat_id_de(t.usuario_id) != str(q.message.chat.id):
        await q.edit_message_text("⚠️ Não autorizado."); return
    if t.status != "PENDENTE_APROVACAO":
        await q.edit_message_text("ℹ️ Já tratada."); return
    if acao in ("sim", "nova"):
        _tr.atualizar_status(h, "CONFIRMADA"); await q.edit_message_text("✅ Confirmado")
    elif acao in ("nao", "mesma"):
        _tr.atualizar_status(h, "IGNORADA"); await q.edit_message_text("❌ Ignorado")
    elif acao == "editar":
        await q.edit_message_text("✏️ Edição manual ainda não implementada.")


def main() -> None:
    app = Application.builder().token(_TOKEN).build()
    for c in ("saldo", "gastos", "pendentes", "ajuda"):
        app.add_handler(CommandHandler(c, cmd_geral))
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_notificacao))
    app.add_handler(CallbackQueryHandler(handle_callback))
    logger.info("carteirAI bot principal iniciado.")
    app.run_polling()


if __name__ == "__main__":
    main()
