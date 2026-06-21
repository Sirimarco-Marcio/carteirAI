"""Serviço de transações — ciclo de vida e efeito no saldo. Contrato: TRANS-01..06.

Regra do cartão (modo real): compra no crédito NÃO mexe no saldo da conta corrente ao confirmar
(entra na fatura — ver FAT). Débito/dinheiro: saída debita, entrada credita. Confirmar é idempotente.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from carteirai.dominio.dtos import Conta, Transacao, TransacaoExtraida


class ContaRepo(Protocol):
    def buscar(self, conta_id: str) -> Conta | None: ...
    def atualizar_saldo(self, conta_id: str, novo_saldo) -> None: ...


class TransacaoRepo(Protocol):
    def salvar(self, transacao: Transacao) -> None: ...
    def buscar(self, transacao_id: str) -> Transacao | None: ...
    def atualizar(self, transacao: Transacao) -> None: ...


class ServicoTransacoes:
    def __init__(
        self,
        conta_repo: ContaRepo,
        transacao_repo: TransacaoRepo,
        gerar_id: Callable[[], str] | None = None,
    ) -> None:
        self._contas = conta_repo
        self._transacoes = transacao_repo
        import uuid

        self._gerar_id = gerar_id or (lambda: uuid.uuid4().hex)

    def criar_pendente(
        self,
        extraida: TransacaoExtraida,
        conta_id: str,
        usuario_id: str,
        possivel_duplicata: bool = False,
    ) -> Transacao:
        """Cria a transação como PENDENTE_APROVACAO (não mexe no saldo). Contrato: TRANS-01."""
        raise NotImplementedError("Implementar TRANS-01")

    def confirmar(self, transacao_id: str) -> Transacao:
        """Confirma a transação. Débito/dinheiro: saída debita, entrada credita. Crédito: não mexe
        no saldo (vai p/ fatura). Idempotente (não debita 2×). Contrato: TRANS-02,03,05,06."""
        raise NotImplementedError("Implementar TRANS-02,03,05,06")

    def ignorar(self, transacao_id: str) -> Transacao:
        """Marca IGNORADA; saldo não muda. Contrato: TRANS-04."""
        raise NotImplementedError("Implementar TRANS-04")
