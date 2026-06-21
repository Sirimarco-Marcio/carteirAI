"""Testes RED para o módulo COMP (competência/fechamento). Contratos COMP-01..06.

Os stubs em financeiro/competencia.py levantam NotImplementedError — portanto
todos estes testes devem FALHAR enquanto a implementação real não existir.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest

from carteirai.dominio.dtos import (
    Competencia,
    Familia,
    FonteRenda,
    Transacao,
)
from carteirai.financeiro.competencia import ServicoCompetencia
from tests.fakes import (
    FakeFamiliaRepo,
    FakeFonteRepo,
    FakeRegistroDiaRepo,
    FakeTransacaoRepoComp,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DT_FIXO = datetime(2025, 5, 15, 10, 0, 0)


def _transacao_saida_confirmada(valor: str, id: str = "t1") -> Transacao:
    """Cria uma Transacao do tipo saida, status CONFIRMADA, para usar em testes."""
    return Transacao(
        id=id,
        conta_id="conta-1",
        usuario_id="user-1",
        valor=Decimal(valor),
        data_hora=_DT_FIXO,
        forma="pix",
        tipo="saida",
        status="CONFIRMADA",
    )


def _fonte_fixo_mensal(nome: str, valor_base: str, id: str = "fonte-1") -> FonteRenda:
    """Cria uma FonteRenda do tipo fixo_mensal — previsto determinístico = valor_base."""
    return FonteRenda(
        id=id,
        usuario_id="user-1",
        nome=nome,
        tipo_calculo="fixo_mensal",
        valor_base=Decimal(valor_base),
        ativa=True,
    )


def _competencia(mes: int = 5, ano: int = 2025, status: str = "ABERTA") -> Competencia:
    """Cria uma Competencia de referência para os testes."""
    return Competencia(
        id="comp-1",
        familia_id="familia-1",
        mes=mes,
        ano=ano,
        status=status,  # type: ignore[arg-type]
    )


def _servico(
    saidas: list | None = None,
    fontes: list | None = None,
    registros: dict | None = None,
    familia: Familia | None = None,
) -> tuple[ServicoCompetencia, FakeFamiliaRepo]:
    """Monta ServicoCompetencia com fakes e devolve (servico, fake_familia_repo)."""
    familia = familia or Familia(
        id="familia-1",
        nome="Família Teste",
        saldo_acumulado=Decimal("0"),
    )
    familia_repo = FakeFamiliaRepo(familia)
    servico = ServicoCompetencia(
        transacao_repo=FakeTransacaoRepoComp(saidas or []),
        fonte_repo=FakeFonteRepo(fontes or []),
        registro_repo=FakeRegistroDiaRepo(registros or {}),
        familia_repo=familia_repo,
    )
    return servico, familia_repo


# ---------------------------------------------------------------------------
# COMP-01 — total_gasto soma apenas saídas CONFIRMADAS (ignora PENDENTE/IGNORADA)
# ---------------------------------------------------------------------------


def test_comp_01_total_gasto_soma_apenas_saidas_confirmadas() -> None:
    """COMP-01: saídas confirmadas 300+200 → total_gasto == 500; PENDENTE é ignorada."""
    # Arrange — o FakeTransacaoRepoComp recebe APENAS as confirmadas (repo real filtraria)
    saida_300 = _transacao_saida_confirmada("300", id="t1")
    saida_200 = _transacao_saida_confirmada("200", id="t2")
    # A PENDENTE não entra no fake porque saidas_confirmadas() já vem filtrada pelo repo;
    # o teste comprova que o serviço soma corretamente o que o repo entrega.
    servico, _ = _servico(saidas=[saida_300, saida_200])

    # Act
    resultado = servico.total_gasto("comp-1")

    # Assert
    assert resultado == Decimal("500")


# ---------------------------------------------------------------------------
# COMP-02 — fechar_mes: renda prevista == realizada, sem inconsistências
# ---------------------------------------------------------------------------


def test_comp_02_fechar_mes_sem_inconsistencias() -> None:
    """COMP-02: prevista 1600, realizada 1600, gasto 500 → sobra=1100, sem inconsistências."""
    # Arrange
    fonte = _fonte_fixo_mensal(nome="Salário", valor_base="1600")
    saidas = [
        _transacao_saida_confirmada("300", id="t1"),
        _transacao_saida_confirmada("200", id="t2"),
    ]
    comp = _competencia()
    servico, _ = _servico(
        saidas=saidas,
        fontes=[fonte],
        familia=Familia(id="familia-1", nome="Fam", saldo_acumulado=Decimal("0")),
    )

    # Act
    relatorio = servico.fechar_mes(
        comp,
        renda_realizada_por_fonte={fonte.id: Decimal("1600")},
    )

    # Assert
    assert relatorio.sobra == Decimal("1100")
    assert relatorio.inconsistencias == []


# ---------------------------------------------------------------------------
# COMP-03 — fechar_mes: realizada != prevista → inconsistência com nome da fonte
# ---------------------------------------------------------------------------


def test_comp_03_fechar_mes_inconsistencia_quando_realizada_difere_de_prevista() -> None:
    """COMP-03: fonte BNDES prevista=1600, realizada=1400 → inconsistência menciona 'BNDES'."""
    # Arrange
    fonte = _fonte_fixo_mensal(nome="BNDES", valor_base="1600")
    comp = _competencia()
    servico, _ = _servico(
        saidas=[],
        fontes=[fonte],
        familia=Familia(id="familia-1", nome="Fam", saldo_acumulado=Decimal("0")),
    )

    # Act
    relatorio = servico.fechar_mes(
        comp,
        renda_realizada_por_fonte={fonte.id: Decimal("1400")},
    )

    # Assert
    assert len(relatorio.inconsistencias) > 0
    assert any("BNDES" in msg for msg in relatorio.inconsistencias)


# ---------------------------------------------------------------------------
# COMP-04 — fechar_mes: saldo_acumulado da família é incrementado com a sobra
# ---------------------------------------------------------------------------


def test_comp_04_fechar_mes_acumula_sobra_no_saldo_da_familia() -> None:
    """COMP-04: saldo inicial 1000, sobra 1100 → saldo_acumulado == 2100."""
    # Arrange
    fonte = _fonte_fixo_mensal(nome="Salário", valor_base="1600")
    saidas = [
        _transacao_saida_confirmada("300", id="t1"),
        _transacao_saida_confirmada("200", id="t2"),
    ]
    familia = Familia(id="familia-1", nome="Fam", saldo_acumulado=Decimal("1000"))
    comp = _competencia()
    servico, familia_repo = _servico(
        saidas=saidas,
        fontes=[fonte],
        familia=familia,
    )

    # Act
    servico.fechar_mes(
        comp,
        renda_realizada_por_fonte={fonte.id: Decimal("1600")},
    )

    # Assert — inspeciona o objeto mutado no FakeFamiliaRepo
    assert familia_repo.familia.saldo_acumulado == Decimal("2100")


# ---------------------------------------------------------------------------
# COMP-05 — fechar_mes em competência já FECHADA levanta ValueError (idempotente)
# ---------------------------------------------------------------------------


def test_comp_05_fechar_mes_em_competencia_ja_fechada_levanta_value_error() -> None:
    """COMP-05: competência status=='FECHADA' → ValueError (não soma sobra 2×)."""
    # Arrange
    fonte = _fonte_fixo_mensal(nome="Salário", valor_base="1600")
    comp = _competencia(status="FECHADA")
    servico, _ = _servico(fontes=[fonte])

    # Act & Assert
    with pytest.raises(ValueError):
        servico.fechar_mes(
            comp,
            renda_realizada_por_fonte={fonte.id: Decimal("1600")},
        )


# ---------------------------------------------------------------------------
# COMP-06 — sobra negativa: saldo acumulado diminui (alerta de coaching implícito)
# ---------------------------------------------------------------------------


def test_comp_06_sobra_negativa_diminui_saldo_acumulado() -> None:
    """COMP-06: realizada=300, gasto=500 → sobra=-200; saldo 1000 → 800."""
    # Arrange
    fonte = _fonte_fixo_mensal(nome="Salário", valor_base="300")
    saidas = [
        _transacao_saida_confirmada("300", id="t1"),
        _transacao_saida_confirmada("200", id="t2"),
    ]
    familia = Familia(id="familia-1", nome="Fam", saldo_acumulado=Decimal("1000"))
    comp = _competencia()
    servico, familia_repo = _servico(
        saidas=saidas,
        fontes=[fonte],
        familia=familia,
    )

    # Act
    relatorio = servico.fechar_mes(
        comp,
        renda_realizada_por_fonte={fonte.id: Decimal("300")},
    )

    # Assert
    assert relatorio.sobra == Decimal("-200")
    assert familia_repo.familia.saldo_acumulado == Decimal("800")
