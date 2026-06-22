"""Cartão de crédito e faturas (modo "real"). Contrato: FAT-01..09.

Crédito não mexe no saldo; entra numa fatura da competência; saldo só cai ao pagar a fatura.
Parcelamento gera N transações em competências consecutivas (ajuste de centavo na última).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal, ROUND_DOWN
from typing import Protocol

from carteirai.dominio.dtos import Conta, Fatura, Transacao


class FaturaRepo(Protocol):
    def buscar(self, fatura_id: str) -> Fatura | None: ...
    def buscar_aberta(self, conta_id: str, mes: int, ano: int) -> Fatura | None: ...
    def criar(self, conta_id: str, mes: int, ano: int) -> Fatura: ...
    def atualizar(self, fatura: Fatura) -> None: ...
    def abertas(self, conta_id: str) -> list[Fatura]: ...
    def abertas_do_usuario(self, usuario_id: str) -> list[Fatura]: ...


class ContaRepoF(Protocol):
    def buscar(self, conta_id: str) -> Conta | None: ...
    def atualizar_saldo(self, conta_id: str, novo_saldo) -> None: ...


class TransacaoRepoF(Protocol):
    def salvar(self, transacao: Transacao) -> None: ...


def _mes_delta(ano: int, mes: int, k: int) -> tuple[int, int]:
    """Dado (ano, mes) e um delta de meses k, retorna (ano2, mes2) com rollover."""
    m0 = (mes - 1) + k
    ano2 = ano + m0 // 12
    mes2 = m0 % 12 + 1
    return ano2, mes2


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

    def faturas_abertas(self, usuario_id: str) -> list[Fatura]:
        """Retorna todas as faturas ABERTAS do usuário."""
        return self._faturas.abertas_do_usuario(usuario_id)

    def alocar_em_fatura(self, transacao: Transacao, data_compra: date) -> Fatura:
        """Acha/cria a fatura da competência (mês corrente se `data_compra.day <= dia_fechamento`
        do cartão, senão mês seguinte) e soma o valor da transação ao `valor_total`. FAT-01,02,03."""
        conta = self._contas.buscar(transacao.conta_id)
        df = conta.dia_fechamento

        if data_compra.day <= df:
            mes = data_compra.month
            ano = data_compra.year
        else:
            ano, mes = _mes_delta(data_compra.year, data_compra.month, 1)

        fatura = self._faturas.buscar_aberta(transacao.conta_id, mes, ano)
        if fatura is None:
            fatura = self._faturas.criar(transacao.conta_id, mes, ano)

        fatura.valor_total += transacao.valor
        self._faturas.atualizar(fatura)
        transacao.fatura_id = fatura.id
        return fatura

    def gerar_parcelas(self, transacao: Transacao, parcelas_total: int) -> list[Transacao]:
        """Divide o valor em N parcelas (ajuste de centavo na última) em N competências
        consecutivas. A soma das parcelas == valor original. FAT-04,05."""
        N = parcelas_total
        vp = (transacao.valor / N).quantize(Decimal("0.01"), rounding=ROUND_DOWN)

        parcelas: list[Transacao] = []
        for i in range(N):
            if i < N - 1:
                valor = vp
            else:
                valor = transacao.valor - vp * (N - 1)

            ano2, mes2 = _mes_delta(transacao.data_hora.year, transacao.data_hora.month, i)
            data_hora = datetime(ano2, mes2, 1)

            parcela = Transacao(
                id=self._gerar_id(),
                conta_id=transacao.conta_id,
                usuario_id=transacao.usuario_id,
                valor=valor,
                data_hora=data_hora,
                estabelecimento=transacao.estabelecimento,
                categoria=transacao.categoria,
                forma="credito",
                tipo=transacao.tipo,
                status="PENDENTE_APROVACAO",
                parcela_atual=i + 1,
                parcelas_total=N,
            )
            parcelas.append(parcela)

        return parcelas

    def pagar_fatura(self, fatura_id: str, conta_corrente_id: str) -> Transacao:
        """Cria uma saída do valor da fatura na conta corrente (debita saldo) e marca a fatura
        PAGA. Idempotente se já PAGA. FAT-06,07."""
        f = self._faturas.buscar(fatura_id)
        if f.status == "PAGA":
            raise ValueError("fatura já paga")

        pagamento = Transacao(
            id=self._gerar_id(),
            conta_id=conta_corrente_id,
            usuario_id="sistema",
            valor=f.valor_total,
            data_hora=datetime(f.ano, f.mes, 1),
            estabelecimento="Pagamento de fatura",
            categoria="Outros",
            forma="debito",
            tipo="saida",
            status="CONFIRMADA",
        )

        conta = self._contas.buscar(conta_corrente_id)
        self._contas.atualizar_saldo(conta_corrente_id, conta.saldo_atual - f.valor_total)

        f.status = "PAGA"
        self._faturas.atualizar(f)
        self._transacoes.salvar(pagamento)
        return pagamento

    def limite_livre(self, conta_cartao_id: str) -> Decimal:
        """Limite do cartão menos a dívida atual (soma das faturas ABERTAS). FAT-08."""
        conta = self._contas.buscar(conta_cartao_id)
        divida = sum(
            (f.valor_total for f in self._faturas.abertas(conta_cartao_id)),
            Decimal("0"),
        )
        return conta.limite - divida

    def excede_limite(self, conta_cartao_id: str, valor: Decimal) -> bool:
        """True se `valor` excede o limite livre (alerta de coaching; não bloqueia). FAT-09."""
        return valor > self.limite_livre(conta_cartao_id)
