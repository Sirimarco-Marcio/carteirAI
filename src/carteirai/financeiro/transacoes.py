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
    def buscar_ultima_confirmada(self, usuario_id: str) -> Transacao | None: ...


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
        t = Transacao(
            id=self._gerar_id(),
            conta_id=conta_id,
            usuario_id=usuario_id,
            valor=extraida.valor,
            data_hora=extraida.data_hora,
            estabelecimento=extraida.estabelecimento,
            categoria=extraida.categoria,
            forma=extraida.forma,
            tipo=extraida.tipo,
            parcelas_total=extraida.parcelas_total,
            status="PENDENTE_APROVACAO",
            possivel_duplicata=possivel_duplicata,
        )
        self._transacoes.salvar(t)
        return t

    def confirmar(self, transacao_id: str) -> Transacao:
        """Confirma a transação. Débito/dinheiro: saída debita, entrada credita. Crédito: não mexe
        no saldo (vai p/ fatura). Idempotente (não debita 2×). Contrato: TRANS-02,03,05,06."""
        t = self._transacoes.buscar(transacao_id)
        if t.status == "CONFIRMADA":
            return t
        t.status = "CONFIRMADA"
        if t.forma != "credito":
            conta = self._contas.buscar(t.conta_id)
            if t.tipo == "saida":
                novo_saldo = conta.saldo_atual - t.valor
            else:
                novo_saldo = conta.saldo_atual + t.valor
            self._contas.atualizar_saldo(t.conta_id, novo_saldo)
        self._transacoes.atualizar(t)
        return t

    def ignorar(self, transacao_id: str) -> Transacao:
        """Marca IGNORADA; saldo não muda. Contrato: TRANS-04."""
        t = self._transacoes.buscar(transacao_id)
        t.status = "IGNORADA"
        self._transacoes.atualizar(t)
        return t

    def desfazer_ultima(self, usuario_id: str) -> Transacao | None:
        """Desfaz a última transação CONFIRMADA, voltando para PENDENTE_APROVACAO e revertendo o saldo."""
        t = self._transacoes.buscar_ultima_confirmada(usuario_id)
        if not t:
            return None
        t.status = "PENDENTE_APROVACAO"
        if t.forma != "credito":
            conta = self._contas.buscar(t.conta_id)
            if t.tipo == "saida":
                novo_saldo = conta.saldo_atual + t.valor
            else:
                novo_saldo = conta.saldo_atual - t.valor
            self._contas.atualizar_saldo(t.conta_id, novo_saldo)
        self._transacoes.atualizar(t)
        return t

    def criar_manual(
        self, usuario_id: str, valor: float | str | Decimal, categoria: str, forma: str, descricao: str
    ) -> Transacao:
        """Cria transação manual como PENDENTE_APROVACAO."""
        from datetime import datetime
        t = Transacao(
            id=self._gerar_id(),
            conta_id="default",
            usuario_id=usuario_id,
            valor=Decimal(valor),
            data_hora=datetime.now(),
            estabelecimento=descricao or None,
            categoria=categoria,
            forma=forma, # type: ignore
            tipo="saida",
            status="PENDENTE_APROVACAO",
        )
        self._transacoes.salvar(t)
        return t
