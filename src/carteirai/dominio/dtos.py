"""DTOs compartilhados (Pydantic). Estruturas de dados, não regra de negócio.
Referência: docs/tdd/00-estrategia-tdd.md §6 e docs/00-handoff.md (categorias)."""

from __future__ import annotations

from datetime import datetime
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
