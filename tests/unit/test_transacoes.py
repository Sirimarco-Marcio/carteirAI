"""Testes RED para ServicoTransacoes. Contratos: TRANS-01..06.

Referência: docs/tdd/02-contratos-financeiro.md (bloco TRANS).
Cada teste usa AAA (Arrange / Act / Assert) e Decimal para valores monetários.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest

from carteirai.dominio.dtos import Conta, TransacaoExtraida
from carteirai.financeiro.transacoes import ServicoTransacoes
from tests.fakes import FakeContaRepo, FakeTransacaoStore

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DATA_HORA_FIXA = datetime(2024, 3, 15, 10, 0, 0)


def _extraida(
    valor: Decimal = Decimal("30"),
    forma: str = "debito",
    tipo: str = "saida",
) -> TransacaoExtraida:
    """Cria uma TransacaoExtraida parametrizável para os testes TRANS."""
    return TransacaoExtraida(
        valor=valor,
        data_hora=_DATA_HORA_FIXA,
        estabelecimento="Mercado Fake",
        categoria="Mercado",
        forma=forma,  # type: ignore[arg-type]
        tipo=tipo,  # type: ignore[arg-type]
        parcelas_total=1,
    )


def _conta_corrente(saldo: Decimal = Decimal("100")) -> Conta:
    """Cria uma Conta corrente com saldo inicial parametrizável."""
    return Conta(
        id="conta-001",
        tipo="corrente",
        saldo_atual=saldo,
    )


def _servico(conta: Conta) -> tuple[ServicoTransacoes, FakeContaRepo, FakeTransacaoStore]:
    conta_repo = FakeContaRepo(contas=[conta])
    transacao_repo = FakeTransacaoStore()
    id_fixo = iter(["trans-001", "trans-002", "trans-003"])
    servico = ServicoTransacoes(
        conta_repo=conta_repo,
        transacao_repo=transacao_repo,
        gerar_id=lambda: next(id_fixo),
    )
    return servico, conta_repo, transacao_repo


# ---------------------------------------------------------------------------
# TRANS-01 — criar_pendente retorna status PENDENTE_APROVACAO e persiste
# ---------------------------------------------------------------------------


def test_trans_01_criar_pendente_status_e_persistencia() -> None:
    """TRANS-01: criar_pendente deve criar transação com status PENDENTE_APROVACAO
    e a transação deve estar persistida no repositório."""
    # Arrange
    conta = _conta_corrente(saldo=Decimal("100"))
    servico, _, transacao_repo = _servico(conta)
    extraida = _extraida(valor=Decimal("50"), forma="debito", tipo="saida")

    # Act
    resultado = servico.criar_pendente(extraida, conta_id="conta-001", usuario_id="user-1")

    # Assert
    assert resultado.status == "PENDENTE_APROVACAO"
    assert transacao_repo.buscar(resultado.id) is not None


# ---------------------------------------------------------------------------
# TRANS-02 — confirmar saída debita o saldo da conta corrente
# ---------------------------------------------------------------------------


def test_trans_02_confirmar_saida_debita_saldo_conta_corrente() -> None:
    """TRANS-02: conta corrente saldo 100, saída valor 30, após confirmar saldo == 70."""
    # Arrange
    conta = _conta_corrente(saldo=Decimal("100"))
    servico, conta_repo, _ = _servico(conta)
    extraida = _extraida(valor=Decimal("30"), forma="debito", tipo="saida")

    # Act
    transacao = servico.criar_pendente(extraida, conta_id="conta-001", usuario_id="user-1")
    servico.confirmar(transacao.id)

    # Assert
    saldo_atual = conta_repo.buscar("conta-001").saldo_atual
    assert saldo_atual == Decimal("70")


# ---------------------------------------------------------------------------
# TRANS-03 — confirmar entrada credita o saldo da conta corrente
# ---------------------------------------------------------------------------


def test_trans_03_confirmar_entrada_credita_saldo_conta_corrente() -> None:
    """TRANS-03: conta corrente saldo 100, entrada valor 50, após confirmar saldo == 150."""
    # Arrange
    conta = _conta_corrente(saldo=Decimal("100"))
    servico, conta_repo, _ = _servico(conta)
    extraida = _extraida(valor=Decimal("50"), forma="pix", tipo="entrada")

    # Act
    transacao = servico.criar_pendente(extraida, conta_id="conta-001", usuario_id="user-1")
    servico.confirmar(transacao.id)

    # Assert
    saldo_atual = conta_repo.buscar("conta-001").saldo_atual
    assert saldo_atual == Decimal("150")


# ---------------------------------------------------------------------------
# TRANS-04 — ignorar não muda o saldo e muda o status para IGNORADA
# ---------------------------------------------------------------------------


def test_trans_04_ignorar_nao_altera_saldo_e_define_status_ignorada() -> None:
    """TRANS-04: ignorar transação pendente → status IGNORADA; saldo inalterado (100)."""
    # Arrange
    conta = _conta_corrente(saldo=Decimal("100"))
    servico, conta_repo, transacao_repo = _servico(conta)
    extraida = _extraida(valor=Decimal("30"), forma="debito", tipo="saida")

    # Act
    transacao = servico.criar_pendente(extraida, conta_id="conta-001", usuario_id="user-1")
    resultado = servico.ignorar(transacao.id)

    # Assert
    assert resultado.status == "IGNORADA"
    saldo_atual = conta_repo.buscar("conta-001").saldo_atual
    assert saldo_atual == Decimal("100")


# ---------------------------------------------------------------------------
# TRANS-05 — confirmar é idempotente (não debita duas vezes)
# ---------------------------------------------------------------------------


def test_trans_05_confirmar_idempotente_nao_debita_duas_vezes() -> None:
    """TRANS-05: criar+confirmar saída 30 (saldo 100→70); confirmar de novo → saldo ainda 70."""
    # Arrange
    conta = _conta_corrente(saldo=Decimal("100"))
    servico, conta_repo, _ = _servico(conta)
    extraida = _extraida(valor=Decimal("30"), forma="debito", tipo="saida")

    # Act
    transacao = servico.criar_pendente(extraida, conta_id="conta-001", usuario_id="user-1")
    servico.confirmar(transacao.id)
    servico.confirmar(transacao.id)  # segunda chamada — deve ser idempotente

    # Assert
    saldo_atual = conta_repo.buscar("conta-001").saldo_atual
    assert saldo_atual == Decimal("70")


# ---------------------------------------------------------------------------
# TRANS-06 — forma=credito não altera saldo da conta corrente; status CONFIRMADA
# ---------------------------------------------------------------------------


def test_trans_06_credito_nao_altera_saldo_conta_corrente() -> None:
    """TRANS-06: transação forma='credito', saída 30, conta corrente saldo 100.
    Após confirmar → saldo inalterado (100); status == CONFIRMADA."""
    # Arrange
    conta = _conta_corrente(saldo=Decimal("100"))
    servico, conta_repo, _ = _servico(conta)
    extraida = _extraida(valor=Decimal("30"), forma="credito", tipo="saida")

    # Act
    transacao = servico.criar_pendente(extraida, conta_id="conta-001", usuario_id="user-1")
    resultado = servico.confirmar(transacao.id)

    # Assert
    assert resultado.status == "CONFIRMADA"
    saldo_atual = conta_repo.buscar("conta-001").saldo_atual
    assert saldo_atual == Decimal("100")
