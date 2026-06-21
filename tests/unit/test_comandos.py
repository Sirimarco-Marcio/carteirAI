"""Testes RED para os comandos de consulta do bot — CMD-01, 02, 03, 07, 10.
Referência: docs/tdd/03-contratos-telegram.md §CMD.
Cada teste falha com NotImplementedError até a implementação de
DespachanteComandos.processar().
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest

from carteirai.dominio.dtos import Transacao
from carteirai.telegram.comandos import DespachanteComandos
from tests.fakes import FakeConsultas


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _transacao(id: str, valor: str, estabelecimento: str) -> Transacao:
    """Cria uma Transacao PENDENTE_APROVACAO mínima para uso nos testes CMD."""
    return Transacao(
        id=id,
        conta_id="conta-1",
        usuario_id="u",
        valor=Decimal(valor),
        data_hora=datetime(2024, 1, 1, 12, 0, 0),
        estabelecimento=estabelecimento,
        categoria="Outros",
        forma="pix",
        tipo="saida",
        status="PENDENTE_APROVACAO",
    )


# ---------------------------------------------------------------------------
# CMD-01 — /saldo → resposta com valor BRL formatado (ponto milhar, vírgula decimal)
# ---------------------------------------------------------------------------


def test_cmd_01_saldo_formata_brl():
    """CMD-01: /saldo com saldo=1234.56 → resposta contém 'R$ 1.234,56'."""
    # Arrange
    fake = FakeConsultas(saldo_val=Decimal("1234.56"))
    despachante = DespachanteComandos(fake)

    # Act
    resposta = despachante.processar("/saldo", "u")

    # Assert
    assert "R$ 1.234,56" in resposta


# ---------------------------------------------------------------------------
# CMD-02 — /gastos <categoria válida> → soma BRL + nome canônico na resposta
# ---------------------------------------------------------------------------


def test_cmd_02_gastos_categoria_valida():
    """CMD-02: /gastos mercado (case-insensitive) → 'R$ 150,00' e 'Mercado'; consulta recebe forma canônica."""
    # Arrange
    fake = FakeConsultas(gastos={"Mercado": Decimal("150.00")})
    despachante = DespachanteComandos(fake)

    # Act
    resposta = despachante.processar("/gastos mercado", "u")

    # Assert — valor e categoria canônica na resposta
    assert "R$ 150,00" in resposta
    assert "Mercado" in resposta
    # Assert — a consulta recebeu a forma canônica (não a forma digitada em minúsculo)
    assert "Mercado" in fake.categorias_consultadas


# ---------------------------------------------------------------------------
# CMD-03 — /gastos <categoria inválida> → indica categoria inválida; NÃO consulta
# ---------------------------------------------------------------------------


def test_cmd_03_gastos_categoria_invalida():
    """CMD-03: /gastos categoria_que_nao_existe → resposta indica inválida; consulta NÃO chamada."""
    # Arrange
    fake = FakeConsultas()
    despachante = DespachanteComandos(fake)

    # Act
    resposta = despachante.processar("/gastos categoria_que_nao_existe", "u")

    # Assert — resposta indica que a categoria é inválida
    assert "inválida" in resposta.lower() or "categoria" in resposta.lower()
    # Assert — a consulta NÃO foi chamada com a categoria inexistente
    assert "categoria_que_nao_existe" not in fake.categorias_consultadas


# ---------------------------------------------------------------------------
# CMD-07 — /pendentes com 2 transações → resposta menciona as 2
# ---------------------------------------------------------------------------


def test_cmd_07_pendentes_lista_duas_transacoes():
    """CMD-07: /pendentes com 2 Transacao pendentes → resposta menciona as 2 (contador ou estabelecimentos)."""
    # Arrange
    t1 = _transacao("t1", "99.90", "Padaria Central")
    t2 = _transacao("t2", "45.50", "Farmácia Saúde")
    fake = FakeConsultas(pendentes_list=[t1, t2])
    despachante = DespachanteComandos(fake)

    # Act
    resposta = despachante.processar("/pendentes", "u")

    # Assert — resposta menciona "2" ou ambos os estabelecimentos
    menciona_contador = "2" in resposta
    menciona_ambos = (
        "Padaria Central" in resposta and "Farmácia Saúde" in resposta
    )
    assert menciona_contador or menciona_ambos, (
        f"Esperava '2' ou ambos os estabelecimentos na resposta; obteve: {resposta!r}"
    )


# ---------------------------------------------------------------------------
# CMD-10 — comando desconhecido → ajuda listando /saldo e /gastos
# ---------------------------------------------------------------------------


def test_cmd_10_comando_desconhecido_retorna_ajuda():
    """CMD-10: /xyz (desconhecido) → resposta de ajuda com '/saldo' e '/gastos'."""
    # Arrange
    fake = FakeConsultas()
    despachante = DespachanteComandos(fake)

    # Act
    resposta = despachante.processar("/xyz", "u")

    # Assert — resposta lista pelo menos /saldo e /gastos
    assert "/saldo" in resposta
    assert "/gastos" in resposta
