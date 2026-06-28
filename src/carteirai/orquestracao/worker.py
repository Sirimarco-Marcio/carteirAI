"""Worker de Ingestão — loop de drenagem + reaper.

Contratos: WORKER-01..06. Referência: docs/tdd/09-contratos-worker.md.

O `tick()` drena a fila (claim → processar → notificar) e, ao fim,
chama `recuperar_orfaos()` uma única vez. Exceções por item são capturadas,
marcam o item como ERRO e não interrompem o ciclo.
"""

from __future__ import annotations

from carteirai.dominio.dtos import ResultadoProcessamento
from carteirai.fila.fila_ingestao import FilaIngestao, ItemFilaIngestao


class WorkerIngestao:
    """Worker responsável por drenar a fila de ingestão e recuperar órfãos.

    Args:
        fila: instância de FilaIngestao (claim/marcar/recuperar_orfaos).
        orquestrador: porta assíncrona com ``async processar(item) -> ResultadoProcessamento``.
        notificador: porta síncrona com ``notificar(resultado, item) -> None``.
    """

    def __init__(
        self,
        fila: FilaIngestao,
        orquestrador,
        notificador,
    ) -> None:
        self._fila = fila
        self._orquestrador = orquestrador
        self._notificador = notificador

    async def tick(self) -> None:
        """Executa um ciclo completo: drena todos os itens PENDENTE e, ao fim, recupera órfãos.

        Ordem exata (conforme contrato WORKER-01..06):
        1. Drena: laço claim() → processar → notificar (exceção → marca ERRO, continua).
        2. Ao fim do laço: recuperar_orfaos() uma única vez.
        """
        # 1. Drenagem
        while (item := self._fila.claim()) is not None:
            try:
                resultado: ResultadoProcessamento = await self._orquestrador.processar(item)
                self._notificador.notificar(resultado, item)
            except Exception:
                self._fila.marcar(item.id, "ERRO")
                # continua o laço — um item ruim não derruba o ciclo

        # 2. Reaper — chamado exatamente uma vez, depois da drenagem
        self._fila.recuperar_orfaos()
