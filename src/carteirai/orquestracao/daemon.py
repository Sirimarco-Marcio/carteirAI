"""Worker daemon de produção (Pi) — polling da fila_ingestao no Neon (docs/06 Chunk C).

Roda como processo separado do bot. A cada ciclo (~10 min): drena a fila (claim → orquestrador →
notificação) e recupera órfãos (reaper). O LLM é chamado fora do loop do bot.

Rodar:  PYTHONPATH=src python -m carteirai.orquestracao.daemon
Requer no ambiente: DATABASE_URL, TELEGRAM_BOT_TOKEN, e GEMINI_API_KEY (se provider gemini).
Variáveis opcionais: LLM_PROVIDER (default gemini), INTERVALO_SEG (default 600).

NOTA: este entrypoint só é validável em runtime com Neon + Telegram reais (sem teste automatizado).
A montagem (montar_worker) é a mesma exercitada por tests/integration/test_pipeline_worker.py.
"""

from __future__ import annotations

import asyncio
import logging
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from carteirai.fila.fila_ingestao import FilaIngestao
from carteirai.ia.base_llm import resolver_llm
from carteirai.infra.sqlalchemy_repos import (
    SqlAlchemyTransacaoIngestaoRepo,
    SqlAlchemyUsuarioRepo,
)
from carteirai.orquestracao.montagem import montar_worker
from carteirai.telegram.aprovacao import ServicoAprovacao
from carteirai.telegram.telegram_port import TelegramPortHttpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("carteirai.daemon")


def _normalizar_dsn(dsn: str) -> str:
    # SQLAlchemy 2.0 + psycopg v3 requer o prefixo postgresql+psycopg://
    if dsn.startswith("postgresql://"):
        return dsn.replace("postgresql://", "postgresql+psycopg://", 1)
    return dsn


def construir_worker(engine, session_factory, token: str, provider: str, fallback: str | None):
    """Monta o WorkerIngestao com os adapters reais (engine Neon, Telegram via httpx)."""
    fila = FilaIngestao(engine)
    sessao = session_factory()
    repo = SqlAlchemyTransacaoIngestaoRepo(sessao)
    usuario_repo = SqlAlchemyUsuarioRepo(sessao)
    telegram = TelegramPortHttpx(token)
    # ServicoAprovacao: solicitar_aprovacao usa telegram + usuario_repo; o repo cobre o buscar dos callbacks.
    servico_aprov = ServicoAprovacao(telegram, usuario_repo, repo, None)
    return montar_worker(
        fila=fila,
        transacao_repo=repo,
        llm_principal=resolver_llm(provider),
        llm_fallback=resolver_llm(fallback) if fallback else None,
        servico_aprovacao=servico_aprov,
    )


async def loop() -> None:
    dsn = _normalizar_dsn(os.environ["DATABASE_URL"])
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    provider = os.getenv("LLM_PROVIDER", "gemini")
    fallback = "local" if provider == "gemini" else "gemini"
    intervalo = int(os.getenv("INTERVALO_SEG", "600"))

    engine = create_engine(dsn, pool_pre_ping=True)
    session_factory = scoped_session(sessionmaker(bind=engine))

    logger.info("Worker daemon iniciado (intervalo=%ss, provider=%s).", intervalo, provider)
    while True:
        try:
            worker = construir_worker(engine, session_factory, token, provider, fallback)
            await worker.tick()
        except Exception as e:  # um ciclo ruim não derruba o daemon
            logger.error("Erro no ciclo do worker: %s", e)
        finally:
            session_factory.remove()
        await asyncio.sleep(intervalo)


def main() -> None:
    asyncio.run(loop())


if __name__ == "__main__":
    main()
