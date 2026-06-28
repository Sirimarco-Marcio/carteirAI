"""Composição (raiz de montagem) do pipeline do worker de ingestão.

Junta as peças reais numa única função, para o entrypoint de produção e os testes de
integração compartilharem exatamente a mesma fiação (ver docs/06 Chunk C e
tests/integration/test_pipeline_worker.py).

As bordas (LLM, Telegram, repositório do Neon) são injetadas — em produção, adapters reais;
nos testes, fakes. Esta função não conhece env vars nem cria conexões: quem chama injeta tudo.
"""

from __future__ import annotations

from carteirai.orquestracao.orquestrador import Orquestrador
from carteirai.orquestracao.worker import WorkerIngestao
from carteirai.telegram.notificador import NotificadorTelegram


def montar_worker(
    *,
    fila,
    transacao_repo,
    llm_principal,
    servico_aprovacao,
    llm_fallback=None,
    max_tentativas: int = 3,
) -> WorkerIngestao:
    """Monta o WorkerIngestao com Orquestrador + NotificadorTelegram já fiados.

    Args:
        fila: FilaIngestao (SQLite nos testes; Neon/SQLAlchemy em produção).
        transacao_repo: porta RepoTransacoes (FakeTransacaoRepo nos testes; TransacaoRepoNeon em prod).
        llm_principal: BaseLLM principal (FakeLLM nos testes; Gemini/Local em prod).
        servico_aprovacao: ServicoAprovacao já construído (telegram + usuario_repo).
        llm_fallback: BaseLLM de fallback (opcional).
        max_tentativas: tentativas de reflexão por provider (D8 = 3).

    Returns:
        WorkerIngestao pronto para `await worker.tick()`.
    """
    orquestrador = Orquestrador(
        fila=fila,
        transacao_repo=transacao_repo,
        llm_principal=llm_principal,
        llm_fallback=llm_fallback,
        max_tentativas=max_tentativas,
    )
    notificador = NotificadorTelegram(servico_aprovacao)
    return WorkerIngestao(fila, orquestrador, notificador)
