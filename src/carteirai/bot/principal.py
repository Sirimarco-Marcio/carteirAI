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
from carteirai.orquestracao.orquestrador import Orquestrador
from carteirai.telegram.comandos import DespachanteComandos

import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from carteirai.financeiro.transacoes import ServicoTransacoes
from carteirai.financeiro.renda import ServicoRenda
from carteirai.financeiro.faturas import ServicoFaturas
from carteirai.infra.sqlalchemy_repos import (
    SqlAlchemyContaRepo, SqlAlchemyTransacaoRepo, SqlAlchemyFaturaRepo,
    SqlAlchemyFonteRepo, SqlAlchemyRegistroDiaRepo,
    SqlAlchemyUsuarioRepo, SqlAlchemyTransacaoIngestaoRepo, SqlAlchemyConsultaFinanceira,
)
from carteirai.fila.fila import Fila

_DATABASE_URL = os.getenv("DATABASE_URL")
if not _DATABASE_URL:
    print("ERRO: DATABASE_URL ausente no .env", file=sys.stderr)
    sys.exit(1)

# SQLAlchemy 2.0 com driver psycopg (v3) requer "postgresql+psycopg://"
if _DATABASE_URL.startswith("postgresql://"):
    _DATABASE_URL = _DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(_DATABASE_URL)
SessionLocal = scoped_session(sessionmaker(bind=engine))

class _UsuarioRepoSessao:
    """UsuarioRepo via SQLAlchemy, abrindo uma sessão (pooled) por chamada."""

    def chat_id_de(self, usuario_id):
        s = SessionLocal()
        try:
            return SqlAlchemyUsuarioRepo(s).chat_id_de(usuario_id)
        finally:
            SessionLocal.remove()

    def usuario_de_chat(self, chat_id):
        s = SessionLocal()
        try:
            return SqlAlchemyUsuarioRepo(s).usuario_de_chat(chat_id)
        finally:
            SessionLocal.remove()


class _TransacaoRepoSessao:
    """Porta do Orquestrador (hash_existe/transacoes/salvar) via SQLAlchemy, sessão por chamada."""

    def hash_existe(self, hash):
        s = SessionLocal()
        try:
            return SqlAlchemyTransacaoIngestaoRepo(s).hash_existe(hash)
        finally:
            SessionLocal.remove()

    def transacoes(self, usuario_id):
        s = SessionLocal()
        try:
            return SqlAlchemyTransacaoIngestaoRepo(s).transacoes(usuario_id)
        finally:
            SessionLocal.remove()

    def salvar(self, usuario_id, hash, transacao, possivel_duplicata):
        s = SessionLocal()
        try:
            return SqlAlchemyTransacaoIngestaoRepo(s).salvar(
                usuario_id, hash, transacao, possivel_duplicata
            )
        finally:
            SessionLocal.remove()

    def buscar(self, transacao_id):
        s = SessionLocal()
        try:
            return SqlAlchemyTransacaoIngestaoRepo(s).buscar(transacao_id)
        finally:
            SessionLocal.remove()

    def atualizar_status(self, transacao_id, status):
        s = SessionLocal()
        try:
            return SqlAlchemyTransacaoIngestaoRepo(s).atualizar_status(transacao_id, status)
        finally:
            SessionLocal.remove()


_ur = _UsuarioRepoSessao()
_tr = _TransacaoRepoSessao()

_db_path = os.environ.get("FILA_DB_PATH", os.environ.get("CARTEIRAI_DB", "/data/fila.db"))
# Fila Real (SQLite) usada pelo Worker
_fila_real = Fila(db_path=_db_path)


class _NoOpFila:
    def marcar(self, item_id, status): pass


def _brl(v) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


async def _enviar_resultado_orquestrador(ctx: ContextTypes.DEFAULT_TYPE, res, texto: str, usuario_id: str, chat_reply_id: str | None = None) -> None:
    """Envia o resultado do Orquestrador para o usuário. Se chat_reply_id for passado, responde lá, senão envia pro dono."""
    chat_dono = _ur.chat_id_de(usuario_id)
    dest_chat = chat_reply_id or chat_dono

    if res.status == "PENDENTE_APROVACAO":
        h = hash_exato(texto)
        t = res.transacao
        dup = res.possivel_duplicata
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
        if chat_reply_id: await ctx.bot.send_message(chat_reply_id, "ℹ️ Não parece uma transação (sem valor). Ignorado.")
    elif res.status == "DUPLICADA":
        if chat_reply_id: await ctx.bot.send_message(chat_reply_id, "♻️ Duplicata exata — descartada.")
    else:  # ERRO
        if chat_reply_id: await ctx.bot.send_message(chat_reply_id, f"❌ Não consegui extrair: {res.motivo_erro}")


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
        
    session = SessionLocal()
    try:
        conta_repo = SqlAlchemyContaRepo(session)
        transacao_repo = SqlAlchemyTransacaoRepo(session)
        fatura_repo = SqlAlchemyFaturaRepo(session)
        fonte_repo = SqlAlchemyFonteRepo(session)
        registro_repo = SqlAlchemyRegistroDiaRepo(session)
        
        renda_svc = ServicoRenda(fonte_repo, registro_repo)
        transacao_svc = ServicoTransacoes(conta_repo, transacao_repo)
        faturas_svc = ServicoFaturas(fatura_repo, conta_repo, transacao_repo)
        
        despachante = DespachanteComandos(
            consultas=SqlAlchemyConsultaFinanceira(session, usuario_id),
            renda_svc=renda_svc,
            transacao_svc=transacao_svc,
            faturas_svc=faturas_svc
        )
        resp = despachante.processar(update.message.text, usuario_id)
        await update.message.reply_text(resp)
    finally:
        SessionLocal.remove()


async def handle_notificacao(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = str(update.effective_chat.id)
    usuario_id = _ur.usuario_de_chat(chat_id)
    if usuario_id is None:
        return  # chat desconhecido: ignora (segurança)
    texto = update.message.text
    item = ItemFila(id=str(update.message.message_id), texto_bruto=texto, usuario_id=usuario_id,
                    origem="notificacao", status="PROCESSANDO", criada_em=update.message.date)
    orq = Orquestrador(_NoOpFila(), _tr, resolver_llm("gemini"), resolver_llm("local"), max_tentativas=3)
    res = await orq.processar(item)
    
    await _enviar_resultado_orquestrador(ctx, res, texto, usuario_id, chat_reply_id=chat_id)


async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    acao, _, h = (q.data or "").partition(":")
    
    session = SessionLocal()
    try:
        tr = SqlAlchemyTransacaoRepo(session)
        conta_repo = SqlAlchemyContaRepo(session)
        transacao_svc = ServicoTransacoes(conta_repo, tr)
        
        t = tr.buscar(h)
        if t is None:
            await q.edit_message_text("⚠️ Transação não encontrada."); return
        if _ur.chat_id_de(t.usuario_id) != str(q.message.chat.id):
            await q.edit_message_text("⚠️ Não autorizado."); return
        if t.status != "PENDENTE_APROVACAO":
            await q.edit_message_text("ℹ️ Já tratada."); return
            
        if acao in ("sim", "nova"):
            transacao_svc.confirmar(h)
            await q.edit_message_text("✅ Confirmado")
        elif acao in ("nao", "mesma"):
            transacao_svc.ignorar(h)
            await q.edit_message_text("❌ Ignorado")
        elif acao == "editar":
            await q.edit_message_text("✏️ Edição manual ainda não implementada.")
    finally:
        SessionLocal.remove()


async def worker_fila(ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Consome a Fila periodicamente e joga para o Orquestrador."""
    item = _fila_real.fetch_next()
    if not item:
        return
    
    logger.info(f"Processando item da Fila ID {item.id} (usuário: {item.usuario_id})")
    try:
        orq = Orquestrador(_fila_real, _tr, resolver_llm("gemini"), resolver_llm("local"), max_tentativas=3)
        res = await orq.processar(item)
        await _enviar_resultado_orquestrador(ctx, res, item.texto_bruto, item.usuario_id)
    except Exception as e:
        logger.error(f"Erro no orquestrador ao processar item {item.id}: {e}")
        _fila_real.marcar(item.id, "ERRO")


def main() -> None:
    app = Application.builder().token(_TOKEN).build()
    for c in ("saldo", "gastos", "pendentes", "ajuda", "faltei", "lancar", "pagar_fatura", "desfazer"):
        app.add_handler(CommandHandler(c, cmd_geral))
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_notificacao))
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    # Worker: Roda a cada 60s, começando em 5s
    if app.job_queue:
        app.job_queue.run_repeating(worker_fila, interval=60, first=5)
    
    logger.info("carteirAI bot principal iniciado. Background Worker ativado (60s).")
    app.run_polling()


if __name__ == "__main__":
    main()
