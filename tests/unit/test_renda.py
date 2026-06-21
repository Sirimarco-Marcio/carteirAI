"""Testes RED para o módulo RENDA. Contratos RENDA-01..07.

Os stubs em renda.py levantam NotImplementedError — portanto todos estes
testes devem FALHAR (ERROR) enquanto a implementação real não existir.
"""

from datetime import date
from decimal import Decimal

from carteirai.dominio.dtos import FonteRenda, RegistroDia
from carteirai.financeiro.renda import ganho_do_dia, renda_prevista

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _fonte(
    tipo_calculo: str = "por_dia",
    valor_base: str = "50",
    valor_alimentacao_dia: str = "20",
    valor_transporte_dia: str = "10",
    dias_semana: list[int] | None = None,
) -> FonteRenda:
    """Constrói uma FonteRenda com valores padrão para os testes."""
    return FonteRenda(
        id="fonte-test",
        usuario_id="user-test",
        nome="Salário Teste",
        tipo_calculo=tipo_calculo,  # type: ignore[arg-type]
        valor_base=Decimal(valor_base),
        valor_alimentacao_dia=Decimal(valor_alimentacao_dia),
        valor_transporte_dia=Decimal(valor_transporte_dia),
        dias_semana=dias_semana if dias_semana is not None else [1, 2, 3, 4, 5],
        ativa=True,
    )


# 20 dias úteis (seg–sex) a partir de 2024-06-03.
# Todos têm isoweekday in [1,2,3,4,5].
DIAS_UTEIS_20: list[date] = [
    date(2024, 6, 3),   # seg=1
    date(2024, 6, 4),   # ter=2
    date(2024, 6, 5),   # qua=3
    date(2024, 6, 6),   # qui=4
    date(2024, 6, 7),   # sex=5
    date(2024, 6, 10),  # seg=1
    date(2024, 6, 11),  # ter=2
    date(2024, 6, 12),  # qua=3
    date(2024, 6, 13),  # qui=4
    date(2024, 6, 14),  # sex=5
    date(2024, 6, 17),  # seg=1
    date(2024, 6, 18),  # ter=2
    date(2024, 6, 19),  # qua=3
    date(2024, 6, 20),  # qui=4
    date(2024, 6, 21),  # sex=5
    date(2024, 6, 24),  # seg=1
    date(2024, 6, 25),  # ter=2
    date(2024, 6, 26),  # qua=3
    date(2024, 6, 27),  # qui=4
    date(2024, 6, 28),  # sex=5
]

# Sábado — fora de dias_semana=[1..5]
SABADO_FORA: date = date(2024, 6, 8)  # isoweekday=6


# ---------------------------------------------------------------------------
# RENDA-01 — fixo_mensal retorna valor_base independente dos dias
# ---------------------------------------------------------------------------

def test_renda_01_fixo_mensal_ignora_lista_de_dias() -> None:
    """RENDA-01: fonte fixo_mensal R$1500 → renda_prevista == Decimal('1500') para qualquer lista de dias."""
    # Arrange
    fonte = _fonte(tipo_calculo="fixo_mensal", valor_base="1500")

    # Act
    result = renda_prevista(fonte, DIAS_UTEIS_20, [])

    # Assert
    assert result == Decimal("1500")


# ---------------------------------------------------------------------------
# RENDA-02 — ganho_do_dia presencial = base + alimentacao + transporte
# ---------------------------------------------------------------------------

def test_renda_02_ganho_dia_presencial() -> None:
    """RENDA-02: por_dia base=50, alim=20, transp=10, presencial → R$80."""
    # Arrange
    fonte = _fonte(valor_base="50", valor_alimentacao_dia="20", valor_transporte_dia="10")

    # Act
    result = ganho_do_dia(fonte, "presencial")

    # Assert
    assert result == Decimal("80")


# ---------------------------------------------------------------------------
# RENDA-03 — ganho_do_dia remoto = base + alimentacao (sem transporte)
# ---------------------------------------------------------------------------

def test_renda_03_ganho_dia_remoto() -> None:
    """RENDA-03: por_dia base=50, alim=20, transp=10, remoto → R$70 (sem transporte)."""
    # Arrange
    fonte = _fonte(valor_base="50", valor_alimentacao_dia="20", valor_transporte_dia="10")

    # Act
    result = ganho_do_dia(fonte, "remoto")

    # Assert
    assert result == Decimal("70")


# ---------------------------------------------------------------------------
# RENDA-04 — ganho_do_dia falta = 0
# ---------------------------------------------------------------------------

def test_renda_04_ganho_dia_falta() -> None:
    """RENDA-04: falta → R$0."""
    # Arrange
    fonte = _fonte(valor_base="50", valor_alimentacao_dia="20", valor_transporte_dia="10")

    # Act
    result = ganho_do_dia(fonte, "falta")

    # Assert
    assert result == Decimal("0")


# ---------------------------------------------------------------------------
# RENDA-05 — por_dia, 20 dias úteis, 0 exceções → 20 × 80 = 1600
# ---------------------------------------------------------------------------

def test_renda_05_renda_prevista_20_dias_sem_excecoes() -> None:
    """RENDA-05: por_dia R$80/dia, 20 dias úteis, 0 exceções → R$1600."""
    # Arrange — base=50, alim=20, transp=10 → presencial = 80
    fonte = _fonte(valor_base="50", valor_alimentacao_dia="20", valor_transporte_dia="10")

    # Act
    result = renda_prevista(fonte, DIAS_UTEIS_20, [])

    # Assert
    assert result == Decimal("1600")


# ---------------------------------------------------------------------------
# RENDA-06 — por_dia, 20 dias, 2 faltas + 3 remotos → 15×80 + 3×70 + 2×0 = 1410
# ---------------------------------------------------------------------------

def test_renda_06_renda_prevista_com_faltas_e_remotos() -> None:
    """RENDA-06: 20 dias, 2 faltas e 3 remotos via RegistroDia → R$1410."""
    # Arrange
    fonte = _fonte(valor_base="50", valor_alimentacao_dia="20", valor_transporte_dia="10")

    # 2 faltas: primeiros dois dias do período
    faltas = [
        RegistroDia(fonte_renda_id="fonte-test", data=DIAS_UTEIS_20[0], status="falta"),
        RegistroDia(fonte_renda_id="fonte-test", data=DIAS_UTEIS_20[1], status="falta"),
    ]
    # 3 remotos: próximos três dias
    remotos = [
        RegistroDia(fonte_renda_id="fonte-test", data=DIAS_UTEIS_20[2], status="remoto"),
        RegistroDia(fonte_renda_id="fonte-test", data=DIAS_UTEIS_20[3], status="remoto"),
        RegistroDia(fonte_renda_id="fonte-test", data=DIAS_UTEIS_20[4], status="remoto"),
    ]
    excecoes = faltas + remotos

    # Act
    result = renda_prevista(fonte, DIAS_UTEIS_20, excecoes)

    # Assert
    # 15 presenciais × 80 = 1200
    # 3 remotos      × 70 =  210
    # 2 faltas        × 0 =    0
    # Total                = 1410
    assert result == Decimal("1410")


# ---------------------------------------------------------------------------
# RENDA-07 — dia fora de dias_semana é ignorado
# ---------------------------------------------------------------------------

def test_renda_07_dia_fora_de_dias_semana_e_ignorado() -> None:
    """RENDA-07: sábado não está em dias_semana=[1..5] — não altera o total."""
    # Arrange
    fonte = _fonte(valor_base="50", valor_alimentacao_dia="20", valor_transporte_dia="10")

    # Garantias sobre as datas utilizadas
    assert SABADO_FORA.isoweekday() == 6, "Deve ser sábado"
    assert 6 not in fonte.dias_semana, "Sábado fora de dias_semana"

    # dias_uteis com 20 dias válidos + 1 sábado que deve ser ignorado
    dias_com_sabado = DIAS_UTEIS_20 + [SABADO_FORA]

    # Act
    result = renda_prevista(fonte, dias_com_sabado, [])

    # Assert — o sábado é ignorado; total idêntico aos 20 dias úteis
    assert result == Decimal("1600")
