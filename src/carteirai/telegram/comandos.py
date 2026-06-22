"""Comandos do bot — parsing e resposta (lógica de negócio delegada aos serviços).
Contrato: CMD (docs/tdd/03). Esta parte cobre as CONSULTAS + ajuda: /saldo, /gastos, /pendentes,
e comando desconhecido → ajuda. Os comandos de ação (/faltei, /desfazer, /pagar_fatura, /lancar)
entram numa etapa seguinte.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Protocol

from carteirai.dominio.dtos import (
    CATEGORIAS_AUTORIZADAS,
    Fatura,
    FonteRenda,
    RegistroDia,
    StatusDia,
    Transacao,
)


COMANDOS_VALIDOS = [
    "/saldo", "/giro", "/cartao", "/limite", "/gastos", "/relatorio",
    "/lancar", "/faltei", "/fechar_mes", "/pagar_fatura", "/divida",
    "/pendentes", "/desfazer",
]


class ConsultaFinanceira(Protocol):
    def saldo(self) -> Decimal: ...
    def gastos_por_categoria(self, categoria: str) -> Decimal: ...
    def pendentes(self) -> list[Transacao]: ...


class RendaService(Protocol):
    def registrar_dia(self, usuario_id: str, data: date, status: StatusDia) -> RegistroDia: ...
    def ultima_fonte_ativa(self, usuario_id: str) -> FonteRenda | None: ...


class TransacaoService(Protocol):
    def desfazer_ultima(self, usuario_id: str) -> Transacao | None: ...
    def criar_manual(self, usuario_id: str, valor: Decimal, categoria: str,
                     forma: str, descricao: str) -> Transacao: ...


class FaturaService(Protocol):
    def faturas_abertas(self, usuario_id: str) -> list[Fatura]: ...
    def pagar_fatura(self, fatura_id: str, conta_corrente_id: str) -> Transacao: ...


def _brl(v: Decimal) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


class DespachanteComandos:
    def __init__(
        self,
        consultas: ConsultaFinanceira,
        renda_svc: RendaService | None = None,
        transacao_svc: TransacaoService | None = None,
        faturas_svc: FaturaService | None = None,
    ) -> None:
        self._consultas = consultas
        self._renda_svc = renda_svc
        self._transacao_svc = transacao_svc
        self._faturas_svc = faturas_svc

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
            
        if comando == "/faltei":
            if not self._renda_svc:
                return "Funcionalidade indisponível."
            fonte = self._renda_svc.ultima_fonte_ativa(usuario_id)
            if not fonte:
                return "Nenhuma fonte de renda ativa encontrada."
            
            if not args:
                d = date.today()
            else:
                try:
                    dia, mes = map(int, args[0].split("/"))
                    d = date(date.today().year, mes, dia)
                except ValueError:
                    return "Data inválida. Use: /faltei DD/MM"
            
            self._renda_svc.registrar_dia(usuario_id, d, "falta")
            if not args:
                return f"✅ Falta registrada para hoje ({d.strftime('%d/%m')})."
            return f"✅ Falta registrada para {d.strftime('%d/%m')}."

        if comando == "/desfazer":
            if not self._transacao_svc:
                return "Funcionalidade indisponível."
            t = self._transacao_svc.desfazer_ultima(usuario_id)
            if not t:
                return "Nenhuma transação para desfazer."
            return f"↩️ Última transação desfeita: {_brl(t.valor)} em {t.estabelecimento or '—'}."

        if comando == "/pagar_fatura":
            if not self._faturas_svc:
                return "Funcionalidade indisponível."
            faturas = self._faturas_svc.faturas_abertas(usuario_id)
            if not faturas:
                return "Sem fatura em aberto."
            if len(faturas) > 1:
                return "Qual fatura pagar? Responda 1 ou 2."
            
            self._faturas_svc.pagar_fatura(faturas[0].id, "default")
            return f"✅ Fatura de {_brl(faturas[0].valor_total)} paga. Saldo debitado da conta corrente."

        if comando == "/lancar":
            if not self._transacao_svc:
                return "Funcionalidade indisponível."
            if not args:
                return (
                    "📝 Lançamento manual. Responda neste formato:\n"
                    "valor | categoria | forma (debito/credito/pix/dinheiro) | descrição (opcional)\n"
                    "Exemplo: 45.90 | Alimentação | pix | almoço no centro"
                )
            
            raw = " ".join(args)
            partes_lancamento = [p.strip() for p in raw.split("|")]
            if len(partes_lancamento) < 3:
                return "Formato inválido. Use: valor | categoria | forma | descrição"
            
            try:
                valor = Decimal(partes_lancamento[0].replace(",", "."))
            except Exception:
                return "Valor inválido."
                
            categoria = partes_lancamento[1]
            canonica = next((c for c in CATEGORIAS_AUTORIZADAS if c.lower() == categoria.lower()), None)
            if not canonica:
                return f"Categoria inválida. Use uma de: {', '.join(CATEGORIAS_AUTORIZADAS)}"
                
            forma = partes_lancamento[2].lower()
            if forma not in ("debito", "credito", "pix", "dinheiro"):
                return "Forma de pagamento inválida. Use: debito, credito, pix ou dinheiro."
                
            descricao = partes_lancamento[3] if len(partes_lancamento) > 3 else ""
            
            self._transacao_svc.criar_manual(usuario_id, valor, canonica, forma, descricao)
            return "✅ Transação criada. Confirme no Telegram."

        return self._ajuda()
