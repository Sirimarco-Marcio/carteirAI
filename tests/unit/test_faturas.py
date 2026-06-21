"""Testes RED para ServicoFaturas. Contratos: FAT-01..09.

Referência: docs/tdd/02-contratos-financeiro.md (bloco FAT).
Cada teste usa AAA (Arrange / Act / Assert) e Decimal para valores monetários.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest

from carteirai.dominio.dtos import Conta, Fatura, Transacao
from carteirai.financeiro.faturas import ServicoFaturas
from tests.fakes import FakeContaRepo, FakeFaturaRepo, FakeTransacaoStore

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DATA_HORA_BASE = datetime(2024, 6, 1, 10, 0, 0)


def _cartao(
    id: str = "cartao-001",
    limite: Decimal = Decimal("1000"),
    dia_fechamento: int = 20,
) -> Conta:
    return Conta(
        id=id,
        tipo="credito",
        saldo_atual=Decimal("0"),
        limite=limite,
        dia_fechamento=dia_fechamento,
        dia_vencimento=5,
    )


def _corrente(id: str = "corrente-001", saldo: Decimal = Decimal("1000")) -> Conta:
    return Conta(id=id, tipo="corrente", saldo_atual=saldo)


def _transacao(
    id: str = "trans-001",
    conta_id: str = "cartao-001",
    valor: Decimal = Decimal("80"),
    data_hora: datetime = _DATA_HORA_BASE,
    forma: str = "credito",
    tipo: str = "saida",
) -> Transacao:
    return Transacao(
        id=id,
        conta_id=conta_id,
        usuario_id="user-1",
        valor=valor,
        data_hora=data_hora,
        estabelecimento="Loja Fake",
        categoria="Outros",
        forma=forma,  # type: ignore[arg-type]
        tipo=tipo,  # type: ignore[arg-type]
        status="CONFIRMADA",
    )


def _ids(*nomes: str):
    """Gera um iterador de ids fixos para uso como gerar_id."""
    seq = iter(nomes)
    return lambda: next(seq)


def _servico(
    contas: list | None = None,
    faturas: list | None = None,
) -> tuple[ServicoFaturas, FakeFaturaRepo, FakeContaRepo, FakeTransacaoStore]:
    fatura_repo = FakeFaturaRepo(faturas=faturas)
    conta_repo = FakeContaRepo(contas=contas or [])
    transacao_repo = FakeTransacaoStore()
    servico = ServicoFaturas(
        fatura_repo=fatura_repo,
        conta_repo=conta_repo,
        transacao_repo=transacao_repo,
        gerar_id=_ids("t-pag-001", "t-pag-002", "t-pag-003"),
    )
    return servico, fatura_repo, conta_repo, transacao_repo


# ---------------------------------------------------------------------------
# FAT-01 — compra antes do fechamento → fatura do mês corrente
# ---------------------------------------------------------------------------


def test_fat_01_compra_antes_fechamento_entra_fatura_mes_corrente() -> None:
    """FAT-01: cartão dia_fechamento=20; data_compra=2024-06-10 (10 ≤ 20)
    → alocar_em_fatura devolve fatura mes=6 ano=2024."""
    # Arrange
    cartao = _cartao(dia_fechamento=20)
    servico, fatura_repo, _, _ = _servico(contas=[cartao])
    transacao = _transacao(valor=Decimal("100"), data_hora=datetime(2024, 6, 10, 9, 0))
    data_compra = date(2024, 6, 10)

    # Act
    fatura = servico.alocar_em_fatura(transacao, data_compra)

    # Assert
    assert fatura.mes == 6
    assert fatura.ano == 2024


# ---------------------------------------------------------------------------
# FAT-02 — compra após dia de fechamento → fatura do mês seguinte
# ---------------------------------------------------------------------------


def test_fat_02_compra_apos_fechamento_entra_fatura_mes_seguinte() -> None:
    """FAT-02: cartão dia_fechamento=20; data_compra=2024-06-25 (25 > 20)
    → alocar_em_fatura devolve fatura mes=7 ano=2024."""
    # Arrange
    cartao = _cartao(dia_fechamento=20)
    servico, _, _, _ = _servico(contas=[cartao])
    transacao = _transacao(valor=Decimal("100"), data_hora=datetime(2024, 6, 25, 9, 0))
    data_compra = date(2024, 6, 25)

    # Act
    fatura = servico.alocar_em_fatura(transacao, data_compra)

    # Assert
    assert fatura.mes == 7
    assert fatura.ano == 2024


def test_fat_02b_rollover_dezembro_para_janeiro() -> None:
    """FAT-02 (rollover): cartão dia_fechamento=20; data_compra=2024-12-25 (25 > 20)
    → fatura mes=1 ano=2025 (rollover de dezembro para janeiro)."""
    # Arrange
    cartao = _cartao(dia_fechamento=20)
    servico, _, _, _ = _servico(contas=[cartao])
    transacao = _transacao(
        valor=Decimal("100"), data_hora=datetime(2024, 12, 25, 9, 0)
    )
    data_compra = date(2024, 12, 25)

    # Act
    fatura = servico.alocar_em_fatura(transacao, data_compra)

    # Assert
    assert fatura.mes == 1
    assert fatura.ano == 2025


# ---------------------------------------------------------------------------
# FAT-03 — alocar soma o valor ao valor_total da fatura
# ---------------------------------------------------------------------------


def test_fat_03_alocar_soma_valor_ao_total_da_fatura() -> None:
    """FAT-03: alocar transação valor=80 → fatura.valor_total == 80;
    alocar outra transação valor=80 → fatura.valor_total == 160."""
    # Arrange
    cartao = _cartao(dia_fechamento=20)
    servico, fatura_repo, _, _ = _servico(contas=[cartao])
    data_compra = date(2024, 6, 10)
    t1 = _transacao(id="t1", valor=Decimal("80"), data_hora=datetime(2024, 6, 10, 9, 0))
    t2 = _transacao(id="t2", valor=Decimal("80"), data_hora=datetime(2024, 6, 10, 9, 0))

    # Act
    fatura_apos_primeira = servico.alocar_em_fatura(t1, data_compra)
    assert fatura_apos_primeira.valor_total == Decimal("80")

    fatura_apos_segunda = servico.alocar_em_fatura(t2, data_compra)

    # Assert
    assert fatura_apos_segunda.valor_total == Decimal("160")


# ---------------------------------------------------------------------------
# FAT-04 — gerar_parcelas cria N transações em meses consecutivos
# ---------------------------------------------------------------------------


def test_fat_04_gerar_parcelas_divide_em_n_transacoes_meses_consecutivos() -> None:
    """FAT-04: transação valor=300, gerar_parcelas(3) → 3 transações de Decimal('100.00');
    meses consecutivos: jun, jul, ago (base = data_hora da transação original)."""
    # Arrange
    cartao = _cartao()
    servico, _, _, _ = _servico(contas=[cartao])
    transacao = _transacao(valor=Decimal("300"), data_hora=datetime(2024, 6, 1, 10, 0))

    # Act
    parcelas = servico.gerar_parcelas(transacao, 3)

    # Assert
    assert len(parcelas) == 3
    for i, parcela in enumerate(parcelas):
        assert parcela.valor == Decimal("100.00")
        assert parcela.data_hora.month == (6 + i - 1) % 12 + 1 or True  # verificado abaixo
    assert parcelas[0].data_hora.month == 6
    assert parcelas[1].data_hora.month == 7
    assert parcelas[2].data_hora.month == 8


# ---------------------------------------------------------------------------
# FAT-05 — soma das parcelas é igual ao valor original (ajuste de centavo)
# ---------------------------------------------------------------------------


def test_fat_05_soma_parcelas_igual_valor_original_sem_perda_centavo() -> None:
    """FAT-05: transação valor=100, gerar_parcelas(3) → soma das 3 parcelas == Decimal('100.00')
    Parcelas esperadas: 33.33, 33.33, 33.34 (ajuste na última)."""
    # Arrange
    cartao = _cartao()
    servico, _, _, _ = _servico(contas=[cartao])
    transacao = _transacao(valor=Decimal("100"), data_hora=datetime(2024, 6, 1, 10, 0))

    # Act
    parcelas = servico.gerar_parcelas(transacao, 3)

    # Assert
    soma = sum(p.valor for p in parcelas)
    assert soma == Decimal("100")
    # As duas primeiras são truncadas; a última absorve o ajuste.
    assert parcelas[0].valor == Decimal("33.33")
    assert parcelas[1].valor == Decimal("33.33")
    assert parcelas[2].valor == Decimal("33.34")


# ---------------------------------------------------------------------------
# FAT-06 — pagar_fatura debita conta corrente e marca fatura como PAGA
# ---------------------------------------------------------------------------


def test_fat_06_pagar_fatura_debita_corrente_e_marca_paga() -> None:
    """FAT-06: fatura ABERTA valor_total=500; conta corrente saldo=1000.
    pagar_fatura → saldo corrente == 500; fatura.status == 'PAGA';
    retorna Transacao saída de 500."""
    # Arrange
    cartao = _cartao(id="cartao-001")
    corrente = _corrente(id="corrente-001", saldo=Decimal("1000"))
    fatura_existente = Fatura(
        id="fat-001",
        conta_id="cartao-001",
        mes=6,
        ano=2024,
        valor_total=Decimal("500"),
        status="ABERTA",
    )
    servico, fatura_repo, conta_repo, _ = _servico(
        contas=[cartao, corrente],
        faturas=[fatura_existente],
    )

    # Act
    transacao_saida = servico.pagar_fatura("fat-001", "corrente-001")

    # Assert
    saldo_corrente = conta_repo.buscar("corrente-001").saldo_atual
    assert saldo_corrente == Decimal("500")

    fatura_atualizada = fatura_repo.buscar("fat-001")
    assert fatura_atualizada.status == "PAGA"

    assert transacao_saida.tipo == "saida"
    assert transacao_saida.valor == Decimal("500")


# ---------------------------------------------------------------------------
# FAT-07 — pagar fatura já PAGA levanta ValueError (idempotência com erro)
# ---------------------------------------------------------------------------


def test_fat_07_pagar_fatura_ja_paga_levanta_value_error() -> None:
    """FAT-07: fatura com status='PAGA'; pagar_fatura → levanta ValueError."""
    # Arrange
    cartao = _cartao(id="cartao-001")
    corrente = _corrente(id="corrente-001", saldo=Decimal("1000"))
    fatura_paga = Fatura(
        id="fat-002",
        conta_id="cartao-001",
        mes=5,
        ano=2024,
        valor_total=Decimal("300"),
        status="PAGA",
    )
    servico, _, _, _ = _servico(
        contas=[cartao, corrente],
        faturas=[fatura_paga],
    )

    # Act / Assert
    with pytest.raises(ValueError):
        servico.pagar_fatura("fat-002", "corrente-001")


# ---------------------------------------------------------------------------
# FAT-08 — limite_livre = limite - soma das faturas ABERTAS
# ---------------------------------------------------------------------------


def test_fat_08_limite_livre_desconta_faturas_abertas() -> None:
    """FAT-08: cartão limite=1000; faturas abertas somando 700
    → limite_livre(cartao) == Decimal('300')."""
    # Arrange
    cartao = _cartao(id="cartao-001", limite=Decimal("1000"))
    fat1 = Fatura(
        id="fat-a",
        conta_id="cartao-001",
        mes=4,
        ano=2024,
        valor_total=Decimal("400"),
        status="ABERTA",
    )
    fat2 = Fatura(
        id="fat-b",
        conta_id="cartao-001",
        mes=5,
        ano=2024,
        valor_total=Decimal("300"),
        status="ABERTA",
    )
    servico, _, _, _ = _servico(contas=[cartao], faturas=[fat1, fat2])

    # Act
    livre = servico.limite_livre("cartao-001")

    # Assert
    assert livre == Decimal("300")


# ---------------------------------------------------------------------------
# FAT-09 — excede_limite sinaliza estouro (não bloqueia)
# ---------------------------------------------------------------------------


def test_fat_09_excede_limite_sinaliza_estouro_corretamente() -> None:
    """FAT-09: cartão limite=1000, faturas abertas 700 (livre=300).
    excede_limite(Decimal('500')) → True (500 > 300).
    excede_limite(Decimal('100')) → False (100 ≤ 300)."""
    # Arrange
    cartao = _cartao(id="cartao-001", limite=Decimal("1000"))
    fat = Fatura(
        id="fat-c",
        conta_id="cartao-001",
        mes=6,
        ano=2024,
        valor_total=Decimal("700"),
        status="ABERTA",
    )
    servico, _, _, _ = _servico(contas=[cartao], faturas=[fat])

    # Act / Assert
    assert servico.excede_limite("cartao-001", Decimal("500")) is True
    assert servico.excede_limite("cartao-001", Decimal("100")) is False
