"""Testes unitários do auditor anti-alucinação. Contratos: AUD-01..06.
Referência: docs/tdd/01-contratos-ingestao-ia.md — bloco AUDITOR."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest

from carteirai.dominio.dtos import ResultadoAuditoria, TransacaoExtraida
from carteirai.ia.auditor import auditar


# ---------------------------------------------------------------------------
# Helper — monta TransacaoExtraida preenchendo campos irrelevantes com defaults
# ---------------------------------------------------------------------------

def _transacao(
    valor: Decimal,
    data_hora: datetime,
    estabelecimento: str = "X",
    categoria: str = "Outros",
    forma: str = "pix",
    tipo: str = "saida",
    parcelas_total: int = 1,
) -> TransacaoExtraida:
    return TransacaoExtraida(
        valor=valor,
        data_hora=data_hora,
        estabelecimento=estabelecimento,
        categoria=categoria,
        forma=forma,  # type: ignore[arg-type]
        tipo=tipo,  # type: ignore[arg-type]
        parcelas_total=parcelas_total,
    )


# ---------------------------------------------------------------------------
# AUD-01 — valor e data presentes no texto → ok=True
# ---------------------------------------------------------------------------

def test_aud_01_valor_e_data_presentes_retorna_ok():
    # Arrange
    texto = "Compra de R$ 49,90 em 20/06"
    extraida = _transacao(valor=Decimal("49.90"), data_hora=datetime(2026, 6, 20))

    # Act
    resultado = auditar(texto, extraida)

    # Assert
    assert isinstance(resultado, ResultadoAuditoria)
    assert resultado.ok is True


# ---------------------------------------------------------------------------
# AUD-02 — valor ausente no texto → ok=False, falha menciona "valor"
# ---------------------------------------------------------------------------

def test_aud_02_valor_ausente_retorna_falha_com_valor():
    # Arrange
    texto = "Compra no supermercado em 20/06"  # sem valor monetário
    extraida = _transacao(valor=Decimal("500.00"), data_hora=datetime(2026, 6, 20))

    # Act
    resultado = auditar(texto, extraida)

    # Assert
    assert resultado.ok is False
    falhas_lower = " ".join(resultado.falhas).lower()
    assert "valor" in falhas_lower, f"Esperava 'valor' nas falhas, obteve: {resultado.falhas}"


# ---------------------------------------------------------------------------
# AUD-03 — data extraída não aparece no texto → ok=False, falha menciona "data"
# ---------------------------------------------------------------------------

def test_aud_03_data_ausente_retorna_falha_com_data():
    # Arrange
    texto = "Compra de R$ 49,90"  # sem data
    extraida = _transacao(valor=Decimal("49.90"), data_hora=datetime(2026, 6, 21))

    # Act
    resultado = auditar(texto, extraida)

    # Assert
    assert resultado.ok is False
    falhas_lower = " ".join(resultado.falhas).lower()
    assert "data" in falhas_lower, f"Esperava 'data' nas falhas, obteve: {resultado.falhas}"


# ---------------------------------------------------------------------------
# AUD-04 — valor no texto como "49.90" (ponto), extraída usa Decimal("49.90") → ok=True
# ---------------------------------------------------------------------------

def test_aud_04_normalizacao_virgula_ponto_retorna_ok():
    # Arrange — o texto usa ponto como separador decimal, não vírgula
    texto = "Pagamento de 49.90 em 20/06"
    extraida = _transacao(valor=Decimal("49.90"), data_hora=datetime(2026, 6, 20))

    # Act
    resultado = auditar(texto, extraida)

    # Assert
    assert resultado.ok is True


# ---------------------------------------------------------------------------
# AUD-05 — valor com separador de milhar "R$ 1.299,00" → ok=True
# ---------------------------------------------------------------------------

def test_aud_05_separador_de_milhar_retorna_ok():
    # Arrange
    texto = "Compra de R$ 1.299,00 em 20/06"
    extraida = _transacao(valor=Decimal("1299.00"), data_hora=datetime(2026, 6, 20))

    # Act
    resultado = auditar(texto, extraida)

    # Assert
    assert resultado.ok is True


# ---------------------------------------------------------------------------
# AUD-06 — texto sem valor algum → ok=False
# ---------------------------------------------------------------------------

def test_aud_06_texto_sem_valor_retorna_falha():
    # Arrange
    texto = "Mensagem sem nenhum dado financeiro"
    extraida = _transacao(valor=Decimal("100.00"), data_hora=datetime(2026, 6, 20))

    # Act
    resultado = auditar(texto, extraida)

    # Assert
    assert resultado.ok is False
