"""Competência mensal e fechamento. Contrato: COMP-01..06.

`total_gasto` = soma das saídas CONFIRMADAS do mês. `fechar_mes` compara previsto × realizado
por fonte (previsto **calculado na hora** via RENDA — D15: falta/atestado muda a renda), calcula
a sobra, acumula no saldo da família e marca a competência FECHADA (idempotente).
"""

from __future__ import annotations

import calendar
from datetime import date
from decimal import Decimal
from typing import Protocol

from carteirai.dominio.dtos import (
    Competencia,
    Familia,
    FonteRenda,
    RegistroDia,
    RelatorioFechamento,
    Transacao,
)
from carteirai.financeiro.renda import renda_prevista


class TransacaoRepoComp(Protocol):
    def saidas_confirmadas(self, competencia_id: str) -> list[Transacao]: ...


class FonteRepo(Protocol):
    def ativas(self, familia_id: str) -> list[FonteRenda]: ...


class RegistroDiaRepo(Protocol):
    def do_mes(self, fonte_renda_id: str, mes: int, ano: int) -> list[RegistroDia]: ...


class FamiliaRepo(Protocol):
    def buscar(self, familia_id: str) -> Familia | None: ...
    def atualizar_saldo(self, familia_id: str, novo_saldo: Decimal) -> None: ...


def _dias_do_mes(ano: int, mes: int) -> list[date]:
    n = calendar.monthrange(ano, mes)[1]
    return [date(ano, mes, d) for d in range(1, n + 1)]


class ServicoCompetencia:
    def __init__(
        self,
        transacao_repo: TransacaoRepoComp,
        fonte_repo: FonteRepo,
        registro_repo: RegistroDiaRepo,
        familia_repo: FamiliaRepo,
    ) -> None:
        self._transacoes = transacao_repo
        self._fontes = fonte_repo
        self._registros = registro_repo
        self._familias = familia_repo

    def total_gasto(self, competencia_id: str) -> Decimal:
        """Soma das saídas CONFIRMADAS do mês (ignora PENDENTE/IGNORADA). Contrato: COMP-01."""
        return sum(
            (t.valor for t in self._transacoes.saidas_confirmadas(competencia_id)),
            Decimal("0"),
        )

    def fechar_mes(
        self,
        competencia: Competencia,
        renda_realizada_por_fonte: dict,
    ) -> RelatorioFechamento:
        """Fecha a competência: previsto por fonte (via RENDA, na hora), realizado informado,
        sobra = realizada − gasto, acumula no saldo da família, marca FECHADA. Idempotente.
        Contrato: COMP-02..06."""
        if competencia.status == "FECHADA":
            raise ValueError("competência já fechada")

        dias = _dias_do_mes(competencia.ano, competencia.mes)
        fontes = self._fontes.ativas(competencia.familia_id)

        previsto_por_fonte = {
            f.id: renda_prevista(
                f, dias, self._registros.do_mes(f.id, competencia.mes, competencia.ano)
            )
            for f in fontes
        }

        renda_prevista_total = sum(previsto_por_fonte.values(), Decimal("0"))
        renda_realizada_total = sum(renda_realizada_por_fonte.values(), Decimal("0"))
        tg = self.total_gasto(competencia.id)
        sobra = renda_realizada_total - tg

        inconsistencias: list[str] = []
        por_fonte: dict = {}
        for f in fontes:
            prev = previsto_por_fonte[f.id]
            real = renda_realizada_por_fonte.get(f.id, Decimal("0"))
            por_fonte[f.id] = {"previsto": prev, "realizado": real}
            if real != prev:
                inconsistencias.append(f"{f.nome}: previsto {prev}, realizado {real}")

        familia = self._familias.buscar(competencia.familia_id)
        self._familias.atualizar_saldo(
            competencia.familia_id, familia.saldo_acumulado + sobra
        )

        competencia.status = "FECHADA"
        competencia.renda_prevista = renda_prevista_total
        competencia.renda_realizada = renda_realizada_total
        competencia.total_gasto = tg
        competencia.sobra = sobra

        return RelatorioFechamento(
            renda_prevista=renda_prevista_total,
            renda_realizada=renda_realizada_total,
            total_gasto=tg,
            sobra=sobra,
            inconsistencias=inconsistencias,
            por_fonte=por_fonte,
        )
