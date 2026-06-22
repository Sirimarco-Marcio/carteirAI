"""Lógica de ingestão de notificações (App → Pi).

Classe pura: sem FastAPI, sem I/O de rede — testável em isolamento.
Contratos: ING-HTTP-01 a ING-HTTP-05 (docs/tdd/05-contratos-http-ingestao.md).
"""

from __future__ import annotations

from dataclasses import dataclass

from carteirai.dominio.dtos import ItemFila
from carteirai.fila.fila import Fila


@dataclass
class PayloadIngestao:
    """Representa o JSON recebido do app Android. Todos os campos vêm validados pelo FastAPI."""

    usuario_id: str
    package_name: str
    title: str | None
    text: str | None
    posted_at: int          # Unix timestamp em milissegundos
    hash: str               # SHA-256 hex — o Pi confia no dedup do app
    latitude: float = 0.0
    longitude: float = 0.0


@dataclass
class RespostaIngestao:
    """Resposta retornada pelo roteador após processar o payload."""

    status: str             # "enfileirado"
    fila_id: int


class ErroPayloadInvalido(ValueError):
    """Lançado quando title e text estão ambos ausentes/vazios (ING-HTTP-02)."""


class RoteadorIngestao:
    """Recebe payloads de notificação e os enfileira na Fila SQLite.

    Uso:
        roteador = RoteadorIngestao(fila=fila)
        resposta = roteador.receber(payload)
    """

    def __init__(self, fila: Fila) -> None:
        self._fila = fila

    def receber(self, payload: PayloadIngestao) -> RespostaIngestao:
        """Valida o payload e enfileira na Fila. Contrato: ING-HTTP-01 a ING-HTTP-05.

        Raises:
            ErroPayloadInvalido: se title e text forem ambos nulos/vazios (ING-HTTP-02).
        """
        # Monta texto_bruto: concatena partes não-nulas/não-vazias (ING-HTTP-01/03)
        partes = [p for p in [payload.title, payload.text] if p]
        texto_bruto = " ".join(partes)

        # ING-HTTP-02 — rejeita se não sobrou nenhum conteúdo
        if not texto_bruto:
            raise ErroPayloadInvalido("title e text ambos ausentes")

        # Enfileira com origem fixa "notificacao"
        item: ItemFila = self._fila.enqueue(
            texto_bruto=texto_bruto,
            usuario_id=payload.usuario_id,
            origem="notificacao",
        )

        return RespostaIngestao(status="enfileirado", fila_id=item.id)
