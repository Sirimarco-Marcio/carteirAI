"""Renda — fontes e dias trabalhados (regra pura). Contrato: RENDA-01..07.

Regras (doc 03): padrão = presencial (base + alimentação + transporte).
`remoto` = base + alimentação, **sem** transporte. `falta` = 0.
Fonte `fixo_mensal` rende `valor_base` independente de dias.
Um dia só conta para a fonte se `data.isoweekday() in fonte.dias_semana` (1=seg..7=dom).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from carteirai.dominio.dtos import FonteRenda, RegistroDia


def ganho_do_dia(fonte: FonteRenda, status: str) -> Decimal:
    """Ganho de um único dia conforme o status. Contrato: RENDA-02..04."""
    if status == "presencial":
        return fonte.valor_base + fonte.valor_alimentacao_dia + fonte.valor_transporte_dia
    if status == "remoto":
        return fonte.valor_base + fonte.valor_alimentacao_dia
    # "falta"
    return Decimal("0")


def renda_prevista(
    fonte: FonteRenda,
    dias_uteis: list[date],
    excecoes: list[RegistroDia],
) -> Decimal:
    """Renda prevista da competência para a fonte. Contrato: RENDA-01,05,06,07.
    fixo_mensal → valor_base. por_dia → soma ganho_do_dia sobre os dias_uteis que caem em
    dias_semana, aplicando as exceções (falta/remoto) por data; padrão presencial."""
    if fonte.tipo_calculo == "fixo_mensal":
        return fonte.valor_base

    excecoes_por_data: dict[date, str] = {r.data: r.status for r in excecoes}
    total = Decimal("0")
    for d in dias_uteis:
        if d.isoweekday() in fonte.dias_semana:
            status = excecoes_por_data.get(d, "presencial")
            total += ganho_do_dia(fonte, status)
    return total
