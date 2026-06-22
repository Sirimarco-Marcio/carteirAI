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


def _brl(v: Decimal) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


class DespachanteComandos:
    def __init__(self, consultas: ConsultaFinanceira) -> None:
        self._consultas = consultas

    def _ajuda(self) -> str:
        return "Comandos: " + ", ".join(COMANDOS_VALIDOS)

    def processar(self, texto: str, usuario_id: str) -> str:
        """Parseia `texto` (ex: '/gastos mercado') e devolve a resposta. Contrato:
        CMD-01 (/saldo), CMD-02/03 (/gastos [categoria]), CMD-07 (/pendentes), CMD-10 (desconhecido→ajuda)."""
        partes = texto.strip().split()
        if not partes:
            return self._ajuda()
        comando = partes[0].lower()
        args = partes[1:]
        if comando == "/saldo":
            return f"💰 Saldo: {_brl(self._consultas.saldo())}"
        if comando == "/gastos":
            if not args:
                return "Use: /gastos <categoria>"
            alvo = " ".join(args)
            canonica = next((c for c in CATEGORIAS_AUTORIZADAS if c.lower() == alvo.lower()), None)
            if canonica is None:
                return f"Categoria inválida. Use uma de: {', '.join(CATEGORIAS_AUTORIZADAS)}"
            v = self._consultas.gastos_por_categoria(canonica)
            return f"Gastos em {canonica}: {_brl(v)}"
        if comando == "/pendentes":
            lista = self._consultas.pendentes()
            if not lista:
                return "Nenhuma transação pendente."
            linhas = [f"- {_brl(t.valor)} em {t.estabelecimento or '—'}" for t in lista]
            return f"{len(lista)} pendente(s):\n" + "\n".join(linhas)
        return self._ajuda()
