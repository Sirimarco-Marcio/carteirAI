"""Testes unitários do Orquestrador — extensão tipo/forma (RED). Contratos: ORQ-14..17.
Referência: docs/tdd/01-contratos-ingestao-ia.md — bloco ORQ, casos novos.

Por que é RED: o Orquestrador atual só reage a falhas de "valor" (ignora tipo/forma).
Portanto ORQ-14 e ORQ-15 NÃO vão refletir (chamadas==1, feedback None → falha o assert),
ORQ-16 NÃO vai dar ERRO (vai aceitar o tipo errado → PENDENTE_APROVACAO) e
ORQ-17 provavelmente já passa (a extensão ausente não introduz falso positivo no caso atual).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest

from carteirai.dominio.dtos import ItemFila, TransacaoExtraida
from carteirai.orquestracao.orquestrador import Orquestrador
from tests.fakes import FakeFila, FakeLLM, FakeTransacaoRepo


# ---------------------------------------------------------------------------
# Helpers locais (copiados/adaptados de test_orquestrador.py para isolamento)
# ---------------------------------------------------------------------------

# Data fixa que aparece nos textos como "21/06" (determinismo).
_DATA_FIXA = datetime(2026, 6, 21, 10, 0, 0)


def _item_fila(
    texto_bruto: str,
    usuario_id: str = "usuario-teste",
    id: int = 1,
) -> ItemFila:
    """Monta um ItemFila com status PROCESSANDO e criada_em fixo."""
    return ItemFila(
        id=id,
        texto_bruto=texto_bruto,
        usuario_id=usuario_id,
        origem="manual",
        status="PROCESSANDO",
        criada_em=_DATA_FIXA,
    )


def _transacao(
    tipo: str = "saida",
    forma: str = "pix",
    valor: Decimal = Decimal("50.00"),
) -> TransacaoExtraida:
    """Monta uma TransacaoExtraida com tipo/forma/valor parametrizáveis.

    data_hora é sempre _DATA_FIXA (21/06/2026) para que o auditor encontre
    "21/06" nos textos e não acuse falha de data (que o orquestrador ignora
    de qualquer forma, mas mantemos coerente para isolar a divergência
    em tipo/forma).
    """
    return TransacaoExtraida(
        valor=valor,
        data_hora=_DATA_FIXA,
        estabelecimento="Loja Teste",
        categoria="Alimentação",
        forma=forma,  # type: ignore[arg-type]
        tipo=tipo,    # type: ignore[arg-type]
        parcelas_total=1,
    )


def _orquestrador(
    fila: FakeFila,
    repo: FakeTransacaoRepo,
    principal: FakeLLM,
    fallback: FakeLLM | None = None,
    max_tentativas: int = 2,
) -> Orquestrador:
    return Orquestrador(
        fila=fila,
        transacao_repo=repo,
        llm_principal=principal,
        llm_fallback=fallback,
        max_tentativas=max_tentativas,
    )


# ---------------------------------------------------------------------------
# ORQ-14 — reflexão por tipo: texto evidencia entrada; 1ª extração diz saida;
#           2ª diz entrada → PENDENTE_APROVACAO; chamadas==2; feedback contém "tipo"
# ---------------------------------------------------------------------------

async def test_orq_14_reflexao_por_tipo_entrada_acerta_na_segunda():
    # Arrange
    # Texto evidencia tipo=entrada ("você recebeu") com valor R$ 50,00 e data 21/06.
    texto = "você recebeu R$ 50,00 em 21/06"
    item = _item_fila(texto)
    repo = FakeTransacaoRepo()
    fila = FakeFila()
    principal = FakeLLM(respostas=[
        _transacao(tipo="saida",   forma="pix", valor=Decimal("50.00")),  # 1ª: tipo errado
        _transacao(tipo="entrada", forma="pix", valor=Decimal("50.00")),  # 2ª: tipo correto
    ])
    orq = _orquestrador(fila, repo, principal, max_tentativas=2)

    # Act
    resultado = await orq.processar(item)

    # Assert
    assert resultado.status == "PENDENTE_APROVACAO", (
        f"esperado PENDENTE_APROVACAO, obtido {resultado.status}"
    )
    assert principal.chamadas == 2, (
        f"esperado 2 chamadas (reflexão), obtido {principal.chamadas}"
    )
    assert principal.ultimo_feedback is not None, (
        "esperado feedback não-nulo na 2ª chamada (reflexão deve ter ocorrido)"
    )
    feedback_texto = " ".join(principal.ultimo_feedback).lower()
    assert "tipo" in feedback_texto, (
        f"esperado 'tipo' no feedback da reflexão, obtido: {principal.ultimo_feedback}"
    )


# ---------------------------------------------------------------------------
# ORQ-15 — reflexão por forma: texto evidencia credito; 1ª extração diz debito;
#           2ª diz credito → PENDENTE_APROVACAO; chamadas==2; feedback contém "forma"
# ---------------------------------------------------------------------------

async def test_orq_15_reflexao_por_forma_credito_acerta_na_segunda():
    # Arrange
    # Texto evidencia forma=credito ("compra no crédito") e tipo=saida ("compra").
    texto = "compra no crédito de R$ 50,00 em 21/06"
    item = _item_fila(texto)
    repo = FakeTransacaoRepo()
    fila = FakeFila()
    principal = FakeLLM(respostas=[
        _transacao(tipo="saida", forma="debito",  valor=Decimal("50.00")),  # 1ª: forma errada
        _transacao(tipo="saida", forma="credito", valor=Decimal("50.00")),  # 2ª: forma correta
    ])
    orq = _orquestrador(fila, repo, principal, max_tentativas=2)

    # Act
    resultado = await orq.processar(item)

    # Assert
    assert resultado.status == "PENDENTE_APROVACAO", (
        f"esperado PENDENTE_APROVACAO, obtido {resultado.status}"
    )
    assert principal.chamadas == 2, (
        f"esperado 2 chamadas (reflexão), obtido {principal.chamadas}"
    )
    assert principal.ultimo_feedback is not None, (
        "esperado feedback não-nulo na 2ª chamada (reflexão deve ter ocorrido)"
    )
    feedback_texto = " ".join(principal.ultimo_feedback).lower()
    assert "forma" in feedback_texto, (
        f"esperado 'forma' no feedback da reflexão, obtido: {principal.ultimo_feedback}"
    )


# ---------------------------------------------------------------------------
# ORQ-16 — divergência de tipo persiste → ERRO; transação não persistida
# ---------------------------------------------------------------------------

async def test_orq_16_divergencia_de_tipo_persiste_retorna_erro():
    # Arrange
    # Texto evidencia tipo=entrada ("você recebeu"); principal SEMPRE extrai tipo=saida.
    texto = "você recebeu R$ 50,00 em 21/06"
    item = _item_fila(texto)
    repo = FakeTransacaoRepo()
    fila = FakeFila()
    # transacao fixa: tipo=saida (diverge do texto que evidencia entrada)
    principal = FakeLLM(transacao=_transacao(tipo="saida", forma="pix", valor=Decimal("50.00")))
    orq = _orquestrador(fila, repo, principal, fallback=None, max_tentativas=2)

    # Act
    resultado = await orq.processar(item)

    # Assert
    assert resultado.status == "ERRO", (
        f"esperado ERRO (divergência de tipo persistente), obtido {resultado.status}"
    )
    assert len(repo.salvos) == 0, (
        f"esperado 0 transações persistidas, obtido {len(repo.salvos)}"
    )


# ---------------------------------------------------------------------------
# ORQ-17 — sem falso positivo: texto sem pista de tipo/forma; extração ok
#           → PENDENTE_APROVACAO (a extensão não acusa nada quando não há pista)
# ---------------------------------------------------------------------------

async def test_orq_17_sem_pista_de_tipo_forma_nao_introduce_falso_positivo():
    # Arrange
    # Texto "Lançamento" não contém pista de tipo nem de forma.
    texto = "Lançamento R$ 50,00 em 21/06"
    item = _item_fila(texto)
    repo = FakeTransacaoRepo()
    fila = FakeFila()
    # Extração: valor bate (50,00), tipo=saida, forma=pix — sem contradição no texto.
    principal = FakeLLM(transacao=_transacao(tipo="saida", forma="pix", valor=Decimal("50.00")))
    orq = _orquestrador(fila, repo, principal, max_tentativas=2)

    # Act
    resultado = await orq.processar(item)

    # Assert
    assert resultado.status == "PENDENTE_APROVACAO", (
        f"esperado PENDENTE_APROVACAO (sem pista → sem falso positivo), "
        f"obtido {resultado.status}"
    )
