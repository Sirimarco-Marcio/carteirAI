"""Testes de integração do pipeline worker (INT-W-01..04).
Referência: docs/tdd/04-plano-integracao.md §Pipeline do worker.

Componentes reais: FilaIngestao (SQLite), Orquestrador, Auditor, NotificadorTelegram, WorkerIngestao.
Fakes de borda: FakeLLM (extração), FakeTransacaoRepo (Neon), FakeTelegram + FakeUsuarioRepo (Telegram).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine

from carteirai.dedup.dedup import TransacaoSimilar, hash_exato
from carteirai.dominio.dtos import TransacaoExtraida
from carteirai.fila.fila_ingestao import FilaIngestao
from carteirai.orquestracao.orquestrador import Orquestrador
from carteirai.orquestracao.worker import WorkerIngestao
from carteirai.telegram.aprovacao import ServicoAprovacao
from carteirai.telegram.notificador import NotificadorTelegram
from tests.fakes import (
    FakeLLM,
    FakeTransacaoRepo,
    FakeTelegram,
    FakeUsuarioRepo,
    RelogioFake,
)

# ---------------------------------------------------------------------------
# Constantes compartilhadas
# ---------------------------------------------------------------------------

_USUARIO_ID = "usuario-pipeline"
_CHAT_ID = "chat-pipeline-99"
# Data/hora fixa para o posted_at dos itens (determinismo).
_POSTED_AT = datetime(2026, 6, 21, 10, 0, 0)

# Texto canônico: contém "R$ 50,00" e a palavra "compra" + "pix"
# → auditor aprova valor (50.00), tipo (saida via "compra"), forma (pix via "pix")
_TEXTO_VALIDO = "compra R$ 50,00 pix em 21/06"

# Texto sem valor monetário → auditor retorna "sem números monetários" → IGNORADA
_TEXTO_SEM_VALOR = "bom dia, novidades hoje"


# ---------------------------------------------------------------------------
# Helper: monta toda a pilha real com fakes nas bordas
# ---------------------------------------------------------------------------


def _montar_pipeline(
    repo: FakeTransacaoRepo,
    principal: FakeLLM,
) -> tuple[FilaIngestao, WorkerIngestao, FakeTelegram]:
    """Instancia FilaIngestao (SQLite), Orquestrador, NotificadorTelegram e WorkerIngestao.

    Cada chamada cria um engine SQLite em memória isolado (sem arquivo temporário compartilhado).
    Retorna (fila, worker, telegram) para que o teste possa enqueue e depois inspecionar.
    """
    engine = create_engine("sqlite://")
    relogio = RelogioFake(_POSTED_AT)
    fila = FilaIngestao(engine, relogio=relogio)

    orquestrador = Orquestrador(
        fila=fila,
        transacao_repo=repo,
        llm_principal=principal,
        max_tentativas=2,
    )

    telegram = FakeTelegram()
    usuario_repo = FakeUsuarioRepo({_USUARIO_ID: _CHAT_ID})
    servico_aprov = ServicoAprovacao(telegram, usuario_repo, None, None)
    notificador = NotificadorTelegram(servico_aprov)

    worker = WorkerIngestao(fila, orquestrador, notificador)
    return fila, worker, telegram


def _transacao_extraida_valida() -> TransacaoExtraida:
    """TransacaoExtraida coerente com _TEXTO_VALIDO (valor=50, tipo=saida, forma=pix)."""
    return TransacaoExtraida(
        valor=Decimal("50.00"),
        data_hora=_POSTED_AT,          # será sobrescrito pelo orquestrador com posted_at, ok
        estabelecimento="Loja Teste",
        categoria="Alimentação",
        forma="pix",
        tipo="saida",
        parcelas_total=1,
    )


# ---------------------------------------------------------------------------
# INT-W-01 — notificação válida nova → transação salva, fila CONCLUIDO, aprovação enviada
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_INT_W_01_happy_path_transacao_nova():
    """INT-W-01: texto com valor; LLM extrai coerente; repo vazio; após tick():
    - repo.salvos tem 1 item
    - fila.buscar(id).status == 'CONCLUIDO'
    - 1 mensagem enviada ao chat do dono com botão 'sim:<hash>'
    """
    repo = FakeTransacaoRepo()
    principal = FakeLLM(transacao=_transacao_extraida_valida())
    fila, worker, telegram = _montar_pipeline(repo, principal)

    item = fila.enqueue(
        texto_bruto=_TEXTO_VALIDO,
        usuario_id=_USUARIO_ID,
        origem="notificacao",
        package_name=None,
        data_hora=_POSTED_AT,
    )

    await worker.tick()

    # Transação salva no repo
    assert len(repo.salvos) == 1, f"esperava 1 salvo, obteve {len(repo.salvos)}"

    # Fila marcada como CONCLUIDO
    item_atualizado = fila.buscar(item.id)
    assert item_atualizado is not None
    assert item_atualizado.status == "CONCLUIDO", (
        f"esperava status 'CONCLUIDO', obteve '{item_atualizado.status}'"
    )

    # Exatamente 1 mensagem de aprovação enviada ao chat do dono
    assert len(telegram.enviados) == 1, (
        f"esperava 1 envio, obteve {len(telegram.enviados)}"
    )
    chat_id_enviado, _texto, botoes = telegram.enviados[0]
    assert chat_id_enviado == _CHAT_ID, (
        f"esperava envio para '{_CHAT_ID}', foi para '{chat_id_enviado}'"
    )

    # Botão "sim:<hash>" presente
    assert botoes is not None
    hash_esperado = hash_exato(_TEXTO_VALIDO)
    dados_botoes = [data for _label, data in botoes]
    assert any(d == f"sim:{hash_esperado}" for d in dados_botoes), (
        f"esperava botão 'sim:{hash_esperado}', recebeu: {dados_botoes}"
    )


# ---------------------------------------------------------------------------
# INT-W-02 — duplicata exata → fila DUPLICADA, nada salvo, nada enviado, LLM não chamado
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_INT_W_02_duplicata_exata():
    """INT-W-02: hash do texto já está no repo → após tick():
    - fila.buscar(id).status == 'DUPLICADA'
    - repo.salvos vazio
    - telegram.enviados vazio
    - principal.chamadas == 0 (LLM nem chamado)
    """
    hash_existente = hash_exato(_TEXTO_VALIDO)
    repo = FakeTransacaoRepo(hashes={hash_existente})
    principal = FakeLLM(transacao=_transacao_extraida_valida())
    fila, worker, telegram = _montar_pipeline(repo, principal)

    item = fila.enqueue(
        texto_bruto=_TEXTO_VALIDO,
        usuario_id=_USUARIO_ID,
        origem="notificacao",
        package_name=None,
        data_hora=_POSTED_AT,
    )

    await worker.tick()

    # Fila marcada como DUPLICADA
    item_atualizado = fila.buscar(item.id)
    assert item_atualizado is not None
    assert item_atualizado.status == "DUPLICADA", (
        f"esperava status 'DUPLICADA', obteve '{item_atualizado.status}'"
    )

    # Nada salvo
    assert repo.salvos == [], f"esperava nada salvo, obteve {repo.salvos}"

    # Nada enviado ao Telegram
    assert telegram.enviados == [], (
        f"esperava silêncio no Telegram, obteve {telegram.enviados}"
    )

    # LLM não foi chamado
    assert principal.chamadas == 0, (
        f"esperava 0 chamadas ao LLM, obteve {principal.chamadas}"
    )


# ---------------------------------------------------------------------------
# INT-W-03 — não-transação (texto sem valor) → fila CONCLUIDO (IGNORADA), silêncio
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_INT_W_03_nao_transacao_ignorada_silenciosa():
    """INT-W-03: texto sem números monetários; LLM extrai qualquer valor; após tick():
    - fila.buscar(id).status == 'CONCLUIDO'  (IGNORADA é silenciosa e fecha com CONCLUIDO)
    - repo.salvos vazio
    - telegram.enviados vazio
    """
    repo = FakeTransacaoRepo()
    # LLM extrai valor qualquer — o auditor vai reclamar "sem números monetários"
    principal = FakeLLM(transacao=_transacao_extraida_valida())
    fila, worker, telegram = _montar_pipeline(repo, principal)

    item = fila.enqueue(
        texto_bruto=_TEXTO_SEM_VALOR,
        usuario_id=_USUARIO_ID,
        origem="notificacao",
        package_name=None,
        data_hora=_POSTED_AT,
    )

    await worker.tick()

    # Fila marcada como CONCLUIDO (IGNORADA fecha a fila sem erro)
    item_atualizado = fila.buscar(item.id)
    assert item_atualizado is not None
    assert item_atualizado.status == "CONCLUIDO", (
        f"esperava status 'CONCLUIDO' (IGNORADA), obteve '{item_atualizado.status}'"
    )

    # Nada salvo e nada enviado
    assert repo.salvos == [], f"esperava nada salvo, obteve {repo.salvos}"
    assert telegram.enviados == [], (
        f"esperava silêncio no Telegram para IGNORADA, obteve {telegram.enviados}"
    )


# ---------------------------------------------------------------------------
# INT-W-04 — soft-match → transação salva com possivel_duplicata=True, botões "mesma/nova"
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_INT_W_04_soft_match_possivel_duplicata():
    """INT-W-04: transação similar recente no repo (3 min antes); após tick():
    - repo.salvos tem 1 item com possivel_duplicata=True
    - 1 mensagem enviada com botões 'mesma:<hash>' e 'nova:<hash>'
    """
    # Transação similar: mesmo valor e estabelecimento, 3 min antes de _POSTED_AT (dentro da janela de 10 min)
    similar = TransacaoSimilar(
        valor=Decimal("50.00"),
        estabelecimento="Loja Teste",
        data_hora=datetime(2026, 6, 21, 9, 57, 0),  # 3 min antes de _POSTED_AT
    )
    repo = FakeTransacaoRepo(
        transacoes_por_usuario={_USUARIO_ID: [similar]}
    )
    principal = FakeLLM(transacao=_transacao_extraida_valida())
    fila, worker, telegram = _montar_pipeline(repo, principal)

    item = fila.enqueue(
        texto_bruto=_TEXTO_VALIDO,
        usuario_id=_USUARIO_ID,
        origem="notificacao",
        package_name=None,
        data_hora=_POSTED_AT,
    )

    await worker.tick()

    # Transação salva com possivel_duplicata=True
    assert len(repo.salvos) == 1, f"esperava 1 salvo, obteve {len(repo.salvos)}"
    _uid, _hash, _transacao, possivel_duplicata = repo.salvos[0]
    assert possivel_duplicata is True, (
        f"esperava possivel_duplicata=True, obteve {possivel_duplicata}"
    )

    # 1 mensagem enviada com botões "mesma:<hash>" e "nova:<hash>"
    assert len(telegram.enviados) == 1, (
        f"esperava 1 envio, obteve {len(telegram.enviados)}"
    )
    _chat_id, _texto, botoes = telegram.enviados[0]
    assert botoes is not None
    hash_esperado = hash_exato(_TEXTO_VALIDO)
    dados_botoes = [data for _label, data in botoes]
    assert any(d == f"mesma:{hash_esperado}" for d in dados_botoes), (
        f"esperava botão 'mesma:{hash_esperado}', recebeu: {dados_botoes}"
    )
    assert any(d == f"nova:{hash_esperado}" for d in dados_botoes), (
        f"esperava botão 'nova:{hash_esperado}', recebeu: {dados_botoes}"
    )
