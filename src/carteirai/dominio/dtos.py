"""DTOs compartilhados (Pydantic). Estruturas de dados, não regra de negócio.
Referência: docs/tdd/00-estrategia-tdd.md §6 e docs/00-handoff.md (categorias)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

# Lista autorizada de categorias (doc 00/03). Qualquer coisa fora disso → "Outros".
CATEGORIAS_AUTORIZADAS: tuple[str, ...] = (
    "Alimentação",
    "Mercado",
    "Transporte",
    "Moradia",
    "Saúde",
    "Educação",
    "Lazer",
    "Assinaturas",
    "Vestuário",
    "Lanche na rua",
    "Presentes",
    "Pix",
    "Transferências",
    "Investimentos/Reserva",
    "Outros",
)

Forma = Literal["debito", "credito", "pix", "dinheiro"]
Tipo = Literal["entrada", "saida"]


def normalizar_categoria(categoria: str) -> str:
    """Mapeia a categoria para a lista autorizada; fora dela → 'Outros'. Contrato: LLM-06."""
    if categoria in CATEGORIAS_AUTORIZADAS:
        return categoria
    return "Outros"


class TransacaoExtraida(BaseModel):
    valor: Decimal
    data_hora: datetime
    estabelecimento: str
    categoria: str  # deve pertencer a CATEGORIAS_AUTORIZADAS (normalizado pós-LLM)
    forma: Forma
    tipo: Tipo
    parcelas_total: int = 1


class ResultadoAuditoria(BaseModel):
    ok: bool
    falhas: list[str] = []


StatusProcessamento = Literal["DUPLICADA", "ERRO", "PENDENTE_APROVACAO", "IGNORADA"]


class ResultadoProcessamento(BaseModel):
    status: StatusProcessamento
    possivel_duplicata: bool = False
    transacao: TransacaoExtraida | None = None
    motivo_erro: str | None = None
    tentativas: int = 1  # nº de chamadas ao LLM até decidir (reflexão/fallback)


# --- Fila de mensagens (durabilidade) ---
OrigemItem = Literal["notificacao", "manual"]
StatusItem = Literal["PENDENTE", "PROCESSANDO", "CONCLUIDO", "DUPLICADA", "ERRO"]


class ItemFila(BaseModel):
    id: int
    texto_bruto: str
    usuario_id: str
    origem: OrigemItem
    status: StatusItem
    criada_em: datetime
    processada_em: datetime | None = None


# --- Renda (fontes e dias trabalhados) ---
TipoCalculo = Literal["fixo_mensal", "por_dia"]
StatusDia = Literal["presencial", "remoto", "falta"]


class FonteRenda(BaseModel):
    id: str
    usuario_id: str
    nome: str
    tipo_calculo: TipoCalculo
    valor_base: Decimal = Decimal("0")          # mensal (fixo_mensal) OU por dia (por_dia)
    valor_alimentacao_dia: Decimal = Decimal("0")
    valor_transporte_dia: Decimal = Decimal("0")
    dias_semana: list[int] = []                 # ISO weekday: 1=segunda .. 7=domingo ([1,2,3,4,5]=seg-sex)
    ativa: bool = True


class RegistroDia(BaseModel):
    fonte_renda_id: str
    data: date
    status: StatusDia


# --- Contas e transações persistidas ---
TipoConta = Literal["corrente", "credito", "dinheiro"]
StatusTransacao = Literal["PENDENTE_APROVACAO", "CONFIRMADA", "IGNORADA"]


class Conta(BaseModel):
    id: str
    tipo: TipoConta
    saldo_atual: Decimal = Decimal("0")     # corrente/dinheiro
    limite: Decimal | None = None           # só cartão
    dia_fechamento: int | None = None       # só cartão
    dia_vencimento: int | None = None       # só cartão


StatusFatura = Literal["ABERTA", "FECHADA", "PAGA"]


class Fatura(BaseModel):
    id: str
    conta_id: str            # cartão
    mes: int
    ano: int
    valor_total: Decimal = Decimal("0")
    vencimento: date | None = None
    status: StatusFatura = "ABERTA"


class Transacao(BaseModel):
    id: str
    conta_id: str
    usuario_id: str
    valor: Decimal
    data_hora: datetime
    estabelecimento: str | None = None
    categoria: str = "Outros"
    forma: Forma
    tipo: Tipo
    status: StatusTransacao = "PENDENTE_APROVACAO"
    possivel_duplicata: bool = False
    fatura_id: str | None = None
    parcela_atual: int = 1
    parcelas_total: int = 1
