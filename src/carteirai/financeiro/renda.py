"""Renda — fontes e dias trabalhados (regra pura). Contrato: RENDA-01..07.

Regras (doc 03): padrão = presencial (base + alimentação + transporte).
`remoto` = base + alimentação, **sem** transporte. `falta` = 0.
Fonte `fixo_mensal` rende `valor_base` independente de dias.
Um dia só conta para a fonte se `data.isoweekday() in fonte.dias_semana` (1=seg..7=dom).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from decimal import Decimal
from typing import Protocol

from carteirai.dominio.dtos import FonteRenda, RegistroDia, StatusDia


# ---------------------------------------------------------------------------
# Protocolos de repositório usados por ServicoRenda
# ---------------------------------------------------------------------------


class FonteRendaRepo(Protocol):
    """Repositório de fontes de renda (leitura)."""

    def ativa_do_usuario(self, usuario_id: str) -> FonteRenda | None: ...


class RegistroDiaRepo(Protocol):
    """Repositório de dias registrados (leitura e escrita)."""

    def salvar(self, registro: RegistroDia) -> None: ...


# ---------------------------------------------------------------------------
# Serviço de renda (satisfaz o protocolo RendaService do contrato CMD)
# ---------------------------------------------------------------------------


class ServicoRenda:
    """Satisfaz o protocolo RendaService (contrato CMD-04..06).

    Permite registrar um dia (falta/presencial/remoto) para a fonte ativa do
    usuário e consultar qual é essa fonte ativa. Os dois repositórios são
    injetados para facilitar testes unitários com fakes.
    """

    def __init__(
        self,
        fonte_repo: FonteRendaRepo,
        registro_repo: RegistroDiaRepo,
        gerar_id: Callable[[], str] | None = None,
    ) -> None:
        self._fontes = fonte_repo
        self._registros = registro_repo
        import uuid
        self._gerar_id = gerar_id or (lambda: uuid.uuid4().hex)

    def ultima_fonte_ativa(self, usuario_id: str) -> FonteRenda | None:
        """Retorna a fonte de renda ativa do usuário, ou None se não houver."""
        return self._fontes.ativa_do_usuario(usuario_id)

    def registrar_dia(
        self, usuario_id: str, data: date, status: StatusDia
    ) -> RegistroDia:
        """Cria/substitui o RegistroDia para (fonte_ativa, data, status).

        Idempotente: se já existe um registro para a data, sobrescreve
        (comportamento de upsert — contrato CMD-06).
        Levanta ValueError se o usuário não tiver fonte ativa.
        """
        fonte = self.ultima_fonte_ativa(usuario_id)
        if fonte is None:
            raise ValueError(f"Usuário {usuario_id!r} sem fonte de renda ativa.")
        registro = RegistroDia(fonte_renda_id=fonte.id, data=data, status=status)
        self._registros.salvar(registro)
        return registro


# ---------------------------------------------------------------------------
# Funções puras (API original — preservadas)
# ---------------------------------------------------------------------------


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
