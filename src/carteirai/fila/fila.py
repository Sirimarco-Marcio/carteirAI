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
        agora = self._agora()
        cur = self._con.execute(
            """
            INSERT INTO fila (texto_bruto, usuario_id, origem, status, criada_em, processada_em)
            VALUES (?, ?, ?, 'PENDENTE', ?, NULL)
            """,
            (texto_bruto, usuario_id, origem, agora.isoformat()),
        )
        self._con.commit()
        return ItemFila(
            id=cur.lastrowid,
            texto_bruto=texto_bruto,
            usuario_id=usuario_id,
            origem=origem,
            status="PENDENTE",
            criada_em=agora,
            processada_em=None,
        )

    def fetch_next(self) -> ItemFila | None:
        """Pega 1 PENDENTE (FIFO) e marca PROCESSANDO atomicamente; None se vazia.
        Claim atômico (FILA-05/07): nunca devolve item já em PROCESSANDO nem o mesmo a 2 chamadas."""
        cur = self._con.execute(
            """
            UPDATE fila SET status='PROCESSANDO'
            WHERE id = (SELECT id FROM fila WHERE status='PENDENTE' ORDER BY id LIMIT 1)
            RETURNING *
            """
        )
        row = cur.fetchone()
        self._con.commit()
        if row is None:
            return None
        return self._row_to_item(row)

    def marcar(self, item_id: int, status: str) -> None:
        """Marca status final (CONCLUIDO|DUPLICADA|ERRO) e seta processada_em. Contrato: FILA-06."""
        agora = self._agora()
        self._con.execute(
            "UPDATE fila SET status=?, processada_em=? WHERE id=?",
            (status, agora.isoformat(), item_id),
        )
        self._con.commit()

    def _row_to_item(self, row: sqlite3.Row) -> ItemFila:
        """Converte linha SQLite em ItemFila, parseando datas ISO."""
        criada_em = datetime.fromisoformat(row["criada_em"])
        processada_em = (
            datetime.fromisoformat(row["processada_em"])
            if row["processada_em"] is not None
            else None
        )
        return ItemFila(
            id=row["id"],
            texto_bruto=row["texto_bruto"],
            usuario_id=row["usuario_id"],
            origem=row["origem"],
            status=row["status"],
            criada_em=criada_em,
            processada_em=processada_em,
        )
