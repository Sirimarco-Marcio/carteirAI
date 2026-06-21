"""Testes RED para deduplicação em dois níveis. Contratos: DEDUP-01..10.
Referência: docs/tdd/01-contratos-ingestao-ia.md §DEDUP."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest

from carteirai.dedup.dedup import Deduplicador, TransacaoSimilar, hash_exato
from tests.fakes import FakeTransacaoRepo

# ---------------------------------------------------------------------------
# Auxiliares de data fixa (determinismo)
# ---------------------------------------------------------------------------

AGORA = datetime(2024, 6, 1, 12, 0, 0)


def minutos_atras(n: int) -> datetime:
    from datetime import timedelta

    return AGORA - timedelta(minutes=n)


# ---------------------------------------------------------------------------
# DEDUP-01: textos idênticos → mesmo hash
# ---------------------------------------------------------------------------


def test_dedup_01_textos_identicos_geram_mesmo_hash() -> None:
    # Arrange
    texto = "Compra no mercado R$50,00"

    # Act
    h1 = hash_exato(texto)
    h2 = hash_exato(texto)

    # Assert
    assert h1 == h2


# ---------------------------------------------------------------------------
# DEDUP-02: textos iguais com espaços/caixa diferentes → mesmo hash (normalização)
# ---------------------------------------------------------------------------


def test_dedup_02_normalizacao_espacos_e_caixa_geram_mesmo_hash() -> None:
    # Arrange
    texto_original = "Compra no Mercado R$50,00"
    texto_variante = "  compra no mercado r$50,00  "  # caixa-baixa e espaços extras

    # Act
    h1 = hash_exato(texto_original)
    h2 = hash_exato(texto_variante)

    # Assert
    assert h1 == h2


# ---------------------------------------------------------------------------
# DEDUP-03: textos diferentes → hashes diferentes
# ---------------------------------------------------------------------------


def test_dedup_03_textos_diferentes_geram_hashes_diferentes() -> None:
    # Arrange
    texto_a = "Compra no mercado R$50,00"
    texto_b = "Compra na farmácia R$30,00"

    # Act
    h1 = hash_exato(texto_a)
    h2 = hash_exato(texto_b)

    # Assert
    assert h1 != h2


# ---------------------------------------------------------------------------
# DEDUP-04: hash já no histórico → ja_processado() retorna True
# ---------------------------------------------------------------------------


def test_dedup_04_hash_no_historico_retorna_true() -> None:
    # Arrange
    hash_conhecido = "abc123"
    repo = FakeTransacaoRepo(hashes={hash_conhecido})
    dedup = Deduplicador(repo)

    # Act
    resultado = dedup.ja_processado(hash_conhecido)

    # Assert
    assert resultado is True


# ---------------------------------------------------------------------------
# DEDUP-05: hash inédito → ja_processado() retorna False
# ---------------------------------------------------------------------------


def test_dedup_05_hash_inedito_retorna_false() -> None:
    # Arrange
    repo = FakeTransacaoRepo(hashes={"hash_existente"})
    dedup = Deduplicador(repo)

    # Act
    resultado = dedup.ja_processado("hash_novo_nunca_visto")

    # Assert
    assert resultado is False


# ---------------------------------------------------------------------------
# DEDUP-06: transação igual há 3 min, janela=10 → soft_match retorna True
# ---------------------------------------------------------------------------


def test_dedup_06_transacao_igual_dentro_da_janela_retorna_true() -> None:
    # Arrange
    transacao_existente = TransacaoSimilar(
        valor=Decimal("50.00"),
        estabelecimento="Mercado Central",
        data_hora=minutos_atras(3),
    )
    repo = FakeTransacaoRepo(
        transacoes_por_usuario={"u1": [transacao_existente]}
    )
    dedup = Deduplicador(repo)

    # Act
    resultado = dedup.soft_match(
        usuario_id="u1",
        valor=Decimal("50.00"),
        estabelecimento="Mercado Central",
        data_hora=AGORA,
        janela_min=10,
    )

    # Assert
    assert resultado is True


# ---------------------------------------------------------------------------
# DEDUP-07: transação igual há 30 min, janela=10 → soft_match retorna False
# ---------------------------------------------------------------------------


def test_dedup_07_transacao_fora_da_janela_retorna_false() -> None:
    # Arrange
    transacao_existente = TransacaoSimilar(
        valor=Decimal("50.00"),
        estabelecimento="Mercado Central",
        data_hora=minutos_atras(30),
    )
    repo = FakeTransacaoRepo(
        transacoes_por_usuario={"u1": [transacao_existente]}
    )
    dedup = Deduplicador(repo)

    # Act
    resultado = dedup.soft_match(
        usuario_id="u1",
        valor=Decimal("50.00"),
        estabelecimento="Mercado Central",
        data_hora=AGORA,
        janela_min=10,
    )

    # Assert
    assert resultado is False


# ---------------------------------------------------------------------------
# DEDUP-08: mesmo valor, estabelecimento diferente → soft_match retorna False
# ---------------------------------------------------------------------------


def test_dedup_08_estabelecimento_diferente_retorna_false() -> None:
    # Arrange
    transacao_existente = TransacaoSimilar(
        valor=Decimal("50.00"),
        estabelecimento="Mercado Central",
        data_hora=minutos_atras(3),
    )
    repo = FakeTransacaoRepo(
        transacoes_por_usuario={"u1": [transacao_existente]}
    )
    dedup = Deduplicador(repo)

    # Act
    resultado = dedup.soft_match(
        usuario_id="u1",
        valor=Decimal("50.00"),
        estabelecimento="Farmácia Popular",  # estabelecimento diferente
        data_hora=AGORA,
        janela_min=10,
    )

    # Assert
    assert resultado is False


# ---------------------------------------------------------------------------
# DEDUP-09: mesmo valor/estab., usuário diferente → soft_match retorna False
# ---------------------------------------------------------------------------


def test_dedup_09_usuario_diferente_retorna_false() -> None:
    # Arrange
    transacao_existente = TransacaoSimilar(
        valor=Decimal("50.00"),
        estabelecimento="Mercado Central",
        data_hora=minutos_atras(3),
    )
    repo = FakeTransacaoRepo(
        transacoes_por_usuario={
            "u1": [transacao_existente],
            "u2": [],  # u2 não tem transações
        }
    )
    dedup = Deduplicador(repo)

    # Act — consulta feita para u2, mas a transação pertence a u1
    resultado = dedup.soft_match(
        usuario_id="u2",
        valor=Decimal("50.00"),
        estabelecimento="Mercado Central",
        data_hora=AGORA,
        janela_min=10,
    )

    # Assert
    assert resultado is False


# ---------------------------------------------------------------------------
# DEDUP-10: Decimal("10.00") vs Decimal("10.0") → comparação numérica → True
# ---------------------------------------------------------------------------


def test_dedup_10_valores_decimais_equivalentes_sao_iguais() -> None:
    # Arrange — valor armazenado como Decimal("10.00"), consultado como Decimal("10.0")
    transacao_existente = TransacaoSimilar(
        valor=Decimal("10.00"),
        estabelecimento="Padaria Boa",
        data_hora=minutos_atras(3),
    )
    repo = FakeTransacaoRepo(
        transacoes_por_usuario={"u1": [transacao_existente]}
    )
    dedup = Deduplicador(repo)

    # Act — valor ligeiramente diferente na representação string, mas igual numericamente
    resultado = dedup.soft_match(
        usuario_id="u1",
        valor=Decimal("10.0"),  # representação diferente, valor idêntico
        estabelecimento="Padaria Boa",
        data_hora=AGORA,
        janela_min=10,
    )

    # Assert
    assert resultado is True
