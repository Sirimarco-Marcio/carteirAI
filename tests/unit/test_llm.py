"""Testes unitários da porta BaseLLM e factory resolver_llm. Contratos: LLM-01..07.
Referência: docs/tdd/01-contratos-ingestao-ia.md — bloco LLM."""

from __future__ import annotations

import os
from datetime import datetime
from decimal import Decimal

import pytest

from carteirai.dominio.dtos import CATEGORIAS_AUTORIZADAS, TransacaoExtraida
from carteirai.dominio.dtos import normalizar_categoria
from carteirai.ia.base_llm import BaseLLM, LLMError, resolver_llm
from carteirai.ia.gemini_adapter import GeminiAdapter
from carteirai.ia.local_ssh_adapter import LocalSSHAdapter
from tests.fakes import FakeLLM


# ---------------------------------------------------------------------------
# Helper — TransacaoExtraida com valores válidos pré-definidos
# ---------------------------------------------------------------------------

def _transacao_padrao() -> TransacaoExtraida:
    return TransacaoExtraida(
        valor=Decimal("99.90"),
        data_hora=datetime(2026, 6, 20, 14, 30),
        estabelecimento="Padaria Central",
        categoria="Alimentação",
        forma="pix",
        tipo="saida",
        parcelas_total=1,
    )


# ---------------------------------------------------------------------------
# LLM-01 — resolver_llm("gemini") → GeminiAdapter
# ---------------------------------------------------------------------------

def test_llm_01_resolver_gemini_retorna_gemini_adapter():
    # Arrange — garantir que a env var não interfere
    os.environ["LLM_PROVIDER"] = "gemini"

    # Act
    instancia = resolver_llm("gemini")

    # Assert
    assert isinstance(instancia, GeminiAdapter)


# ---------------------------------------------------------------------------
# LLM-02 — resolver_llm("local") → LocalSSHAdapter
# ---------------------------------------------------------------------------

def test_llm_02_resolver_local_retorna_local_ssh_adapter():
    # Arrange
    os.environ["LLM_PROVIDER"] = "local"

    # Act
    instancia = resolver_llm("local")

    # Assert
    assert isinstance(instancia, LocalSSHAdapter)


# ---------------------------------------------------------------------------
# LLM-03 — provider inválido → ValueError
# ---------------------------------------------------------------------------

def test_llm_03_provider_invalido_levanta_value_error():
    # Arrange / Act / Assert
    with pytest.raises(ValueError):
        resolver_llm("x")


# ---------------------------------------------------------------------------
# LLM-04 — FakeLLM programado → extrair devolve TransacaoExtraida preenchida
# ---------------------------------------------------------------------------

async def test_llm_04_fake_programado_retorna_transacao():
    # Arrange
    transacao_esperada = _transacao_padrao()
    fake = FakeLLM(transacao=transacao_esperada)

    # Act
    resultado = await fake.extrair("Compra de R$ 99,90 na Padaria Central")

    # Assert
    assert isinstance(resultado, TransacaoExtraida)
    assert resultado.valor == transacao_esperada.valor
    assert resultado.estabelecimento == transacao_esperada.estabelecimento
    assert resultado.categoria == transacao_esperada.categoria
    assert fake.chamadas == 1


# ---------------------------------------------------------------------------
# LLM-05 — FakeLLM em modo erro → extrair lança LLMError
# ---------------------------------------------------------------------------

async def test_llm_05_fake_modo_erro_levanta_llm_error():
    # Arrange
    fake = FakeLLM(modo_erro=True, mensagem_erro="timeout simulado")

    # Act / Assert
    with pytest.raises(LLMError):
        await fake.extrair("qualquer texto")

    assert fake.chamadas == 1


# ---------------------------------------------------------------------------
# LLM-06 — normalizar_categoria: fora da lista → "Outros"; dentro → permanece
# ---------------------------------------------------------------------------

def test_llm_06_categoria_inexistente_normaliza_para_outros():
    # Arrange / Act
    resultado = normalizar_categoria("Bla inexistente")

    # Assert
    assert resultado == "Outros"


def test_llm_06_categoria_existente_permanece_inalterada():
    # Arrange — "Mercado" está em CATEGORIAS_AUTORIZADAS
    assert "Mercado" in CATEGORIAS_AUTORIZADAS

    # Act
    resultado = normalizar_categoria("Mercado")

    # Assert
    assert resultado == "Mercado"


# ---------------------------------------------------------------------------
# LLM-07 — conformidade: FakeLLM implementa BaseLLM e extrair é awaitable
#           retornando TransacaoExtraida
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("llm_factory", [
    lambda: FakeLLM(transacao=TransacaoExtraida(
        valor=Decimal("10.00"),
        data_hora=datetime(2026, 1, 1),
        estabelecimento="Teste",
        categoria="Outros",
        forma="dinheiro",
        tipo="saida",
    )),
])
async def test_llm_07_conformidade_fake_implementa_base_llm(llm_factory):
    # Arrange
    llm = llm_factory()

    # Assert — isinstance verifica conformidade de interface
    assert isinstance(llm, BaseLLM), "FakeLLM deve ser subclasse de BaseLLM"

    # Act — extrair deve ser awaitable e retornar TransacaoExtraida
    resultado = await llm.extrair("texto qualquer")

    # Assert — resultado deve ser do tipo correto
    assert isinstance(resultado, TransacaoExtraida), (
        f"extrair deve retornar TransacaoExtraida, obteve {type(resultado)}"
    )
