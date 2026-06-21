"""Comandos do bot — parsing e resposta (lógica de negócio delegada aos serviços).
Contrato: CMD (docs/tdd/03). Esta parte cobre as CONSULTAS + ajuda: /saldo, /gastos, /pendentes,
e comando desconhecido → ajuda. Os comandos de ação (/faltei, /desfazer, /pagar_fatura, /lancar)
entram numa etapa seguinte.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Protocol

from carteirai.dominio.dtos import CATEGORIAS_AUTORIZADAS, Transacao


COMANDOS_VALIDOS = [
    "/saldo", "/giro", "/cartao", "/limite", "/gastos", "/relatorio",
    "/lancar", "/faltei", "/fechar_mes", "/pagar_fatura", "/divida",
    "/pendentes", "/desfazer",
]


class ConsultaFinanceira(Protocol):
    def saldo(self) -> Decimal: ...
    def gastos_por_categoria(self, categoria: str) -> Decimal: ...
    def pendentes(self) -> list[Transacao]: ...


class DespachanteComandos:
    def __init__(self, consultas: ConsultaFinanceira) -> None:
        self._consultas = consultas

    def processar(self, texto: str, usuario_id: str) -> str:
        """Parseia `texto` (ex: '/gastos mercado') e devolve a resposta. Contrato:
        CMD-01 (/saldo), CMD-02/03 (/gastos [categoria]), CMD-07 (/pendentes), CMD-10 (desconhecido→ajuda)."""
        raise NotImplementedError("Implementar CMD-01,02,03,07,10")
