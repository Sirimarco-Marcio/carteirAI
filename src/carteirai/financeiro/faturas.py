"""Cartão de crédito e faturas (modo "real"). Contrato: FAT-01..09.

Crédito não mexe no saldo; entra numa fatura da competência; saldo só cai ao pagar a fatura.
Parcelamento gera N transações em competências consecutivas (ajuste de centavo na última).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from decimal import Decimal
from typing import Protocol

from carteirai.dominio.dtos import Conta, Fatura, Transacao


class FaturaRepo(Protocol):
    def buscar(self, fatura_id: str) -> Fatura | None: ...
    def buscar_aberta(self, conta_id: str, mes: int, ano: int) -> Fatura | None: ...
    def criar(self, conta_id: str, mes: int, ano: int) -> Fatura: ...
    def atualizar(self, fatura: Fatura) -> None: ...
    def abertas(self, conta_id: str) -> list[Fatura]: ...


class ContaRepoF(Protocol):
    def buscar(self, conta_id: str) -> Conta | None: ...
    def atualizar_saldo(self, conta_id: str, novo_saldo) -> None: ...


class TransacaoRepoF(Protocol):
    def salvar(self, transacao: Transacao) -> None: ...


class ServicoFaturas:
    def __init__(
        self,
        fatura_repo: FaturaRepo,
        conta_repo: ContaRepoF,
        transacao_repo: TransacaoRepoF,
        gerar_id: Callable[[], str] | None = None,
    ) -> None:
        self._faturas = fatura_repo
        self._contas = conta_repo
        self._transacoes = transacao_repo
        import uuid

        self._gerar_id = gerar_id or (lambda: uuid.uuid4().hex)

    def alocar_em_fatura(self, transacao: Transacao, data_compra: date) -> Fatura:
        """Acha/cria a fatura da competência (mês corrente se `data_compra.day <= dia_fechamento`
        do cartão, senão mês seguinte) e soma o valor da transação ao `valor_total`. FAT-01,02,03."""
        raise NotImplementedError("Implementar FAT-01,02,03")

    def gerar_parcelas(self, transacao: Transacao, parcelas_total: int) -> list[Transacao]:
        """Divide o valor em N parcelas (ajuste de centavo na última) em N competências
        consecutivas. A soma das parcelas == valor original. FAT-04,05."""
        raise NotImplementedError("Implementar FAT-04,05")

    def pagar_fatura(self, fatura_id: str, conta_corrente_id: str) -> Transacao:
        """Cria uma saída do valor da fatura na conta corrente (debita saldo) e marca a fatura
        PAGA. Idempotente se já PAGA. FAT-06,07."""
        raise NotImplementedError("Implementar FAT-06,07")

    def limite_livre(self, conta_cartao_id: str) -> Decimal:
        """Limite do cartão menos a dívida atual (soma das faturas ABERTAS). FAT-08."""
        raise NotImplementedError("Implementar FAT-08")

    def excede_limite(self, conta_cartao_id: str, valor: Decimal) -> bool:
        """True se `valor` excede o limite livre (alerta de coaching; não bloqueia). FAT-09."""
        raise NotImplementedError("Implementar FAT-09")
