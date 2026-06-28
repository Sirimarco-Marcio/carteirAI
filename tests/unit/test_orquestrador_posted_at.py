"""Teste unitário RED — ORQ-18: Orquestrador deve usar item.data_hora (posted_at)
como momento da transação quando presente, em vez de item.criada_em.

Referência: docs/tdd/01-contratos-ingestao-ia.md — caso ORQ-18.

STATUS: RED — o orquestrador atual seta `extraida.data_hora = item.criada_em`
(linha 77 de orquestrador.py), ignorando o posted_at. O assert falha com:
    AssertionError: datetime(2026,6,28,15,0,0) != datetime(2026,6,21,9,30,0)
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest

from carteirai.fila.fila_ingestao import ItemFilaIngestao
from carteirai.dominio.dtos import TransacaoExtraida
from carteirai.orquestracao.orquestrador import Orquestrador
from tests.fakes import FakeFila, FakeLLM, FakeTransacaoRepo

# Datas distintas para evidenciar o bug:
# posted_at = momento real da transação no celular do usuário
# criada_em = quando o Pi recebeu e gravou o item na fila (diferente!)
POSTED_AT = datetime(2026, 6, 21, 9, 30, 0)
CRIADA_EM = datetime(2026, 6, 28, 15, 0, 0)


def _item_posted_at() -> ItemFilaIngestao:
    """Monta um ItemFilaIngestao com data_hora (posted_at) diferente de criada_em."""
    return ItemFilaIngestao(
        id=1,
        id_hash="abc123",
        texto_bruto="compra R$ 50,00",
        usuario_id="usuario-teste",
        package_name=None,
        origem="notificacao",
        status="PROCESSANDO",
        tentativas=0,
        data_hora=POSTED_AT,
        client_msg_id=None,
        criada_em=CRIADA_EM,
        claimed_em=None,
        processada_em=None,
    )


def _transacao_valida() -> TransacaoExtraida:
    """Transação sem contradição com o texto 'compra R$ 50,00'.
    Sem data no texto — auditor ignora falha de data (posted_at é programático).
    """
    return TransacaoExtraida(
        valor=Decimal("50.00"),
        data_hora=POSTED_AT,   # qualquer datetime; será sobrescrito pelo orquestrador
        estabelecimento="Loja Teste",
        categoria="Alimentação",
        forma="pix",
        tipo="saida",
        parcelas_total=1,
    )


@pytest.mark.asyncio
async def test_orq_18_usa_data_hora_posted_at():
    """ORQ-18: quando item possui data_hora (posted_at) ≠ criada_em,
    a transação salva deve usar data_hora (posted_at) — não criada_em."""
    # Arrange
    item = _item_posted_at()
    repo = FakeTransacaoRepo()   # repositório vazio — sem duplicatas
    fila = FakeFila()
    principal = FakeLLM(transacao=_transacao_valida())
    orq = Orquestrador(
        fila=fila,
        transacao_repo=repo,
        llm_principal=principal,
        llm_fallback=None,
        max_tentativas=2,
    )

    # Act
    resultado = await orq.processar(item)

    # Assert — resultado geral
    assert resultado.status == "PENDENTE_APROVACAO", (
        f"Esperado PENDENTE_APROVACAO, obtido {resultado.status!r}"
    )
    assert len(repo.salvos) == 1, "Esperado exatamente 1 transação salva"

    transacao_salva: TransacaoExtraida = repo.salvos[0][2]

    # Assert principal — ORQ-18: data_hora deve ser o posted_at, não o criada_em
    assert transacao_salva.data_hora == POSTED_AT, (
        f"Esperado posted_at={POSTED_AT}, "
        f"obtido data_hora={transacao_salva.data_hora} "
        f"(criada_em={CRIADA_EM} — se igual, o orquestrador ainda usa criada_em)"
    )
    assert transacao_salva.data_hora != CRIADA_EM, (
        "data_hora não deve ser criada_em — o orquestrador deve usar o posted_at"
    )
