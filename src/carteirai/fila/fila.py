"""Fila de mensagens (durabilidade/estados) — SQLite síncrono. Contrato: FILA-01..07.

Determinismo (docs/tdd/00 §determinismo): `criada_em`/`processada_em` vêm de um `relogio`
injetável (callable que devolve datetime), nunca de `datetime.now()` direto nos testes.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from datetime import datetime

from carteirai.dominio.dtos import ItemFila


class Fila:
    def __init__(
        self,
        db_path: str = ":memory:",
        relogio: Callable[[], datetime] | None = None,
    ) -> None:
        self._agora = relogio or datetime.now
        self._con = sqlite3.connect(db_path)
        self._con.row_factory = sqlite3.Row
        self._con.execute(
            """
            CREATE TABLE IF NOT EXISTS fila (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                texto_bruto   TEXT NOT NULL,
                usuario_id    TEXT NOT NULL,
                origem        TEXT NOT NULL,
                status        TEXT NOT NULL,
                criada_em     TEXT NOT NULL,
                processada_em TEXT
            )
            """
        )
        self._con.commit()

    def enqueue(self, texto_bruto: str, usuario_id: str, origem: str) -> ItemFila:
        """Insere um item com status PENDENTE e criada_em setado. Contrato: FILA-01."""
        raise NotImplementedError("Implementar FILA-01")

    def fetch_next(self) -> ItemFila | None:
        """Pega 1 PENDENTE (FIFO) e marca PROCESSANDO atomicamente; None se vazia.
        Claim atômico (FILA-05/07): nunca devolve item já em PROCESSANDO nem o mesmo a 2 chamadas."""
        raise NotImplementedError("Implementar FILA-02..05,07")

    def marcar(self, item_id: int, status: str) -> None:
        """Marca status final (CONCLUIDO|DUPLICADA|ERRO) e seta processada_em. Contrato: FILA-06."""
        raise NotImplementedError("Implementar FILA-06")
