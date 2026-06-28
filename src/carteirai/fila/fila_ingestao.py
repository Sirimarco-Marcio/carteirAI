"""Fila de Ingestão (Neon/SQLAlchemy) — portável SQLite↔Postgres.
Contratos: FILA-N-01..10. Referência: docs/tdd/08-contratos-fila-ingestao.md.

Determinismo: `criada_em`/`claimed_em`/`processada_em` vêm de um `relogio`
injetável (callable `() -> datetime`), nunca de `datetime.now()` direto.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    and_,
    insert,
    select,
    update,
)
from sqlalchemy.engine import Engine


# ---------------------------------------------------------------------------
# DTO de retorno
# ---------------------------------------------------------------------------


class ItemFilaIngestao(BaseModel):
    """DTO que representa um item da fila de ingestão.
    Referência: docs/tdd/08-contratos-fila-ingestao.md §Campos."""

    id: int
    id_hash: str
    texto_bruto: str
    usuario_id: str
    package_name: Optional[str] = None
    origem: str
    status: str
    tentativas: int
    data_hora: datetime
    client_msg_id: Optional[str] = None
    criada_em: datetime
    claimed_em: Optional[datetime] = None
    processada_em: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Fila de Ingestão
# ---------------------------------------------------------------------------


class FilaIngestao:
    """Fila de ingestão persistida no banco (SQLite em testes, Postgres/Neon em produção).

    Args:
        engine: SQLAlchemy Engine (injetável para isolamento de testes).
        relogio: callable `() -> datetime`; padrão `datetime.now`. Nunca use
                 `datetime.now()` diretamente onde o relógio injetado se aplica.
        visibility_timeout_min: minutos até um item PROCESSANDO ser considerado órfão.
        max_tentativas: número máximo de tentativas antes de ir para a DLQ (ERRO).
    """

    def __init__(
        self,
        engine: Engine,
        relogio: Callable[[], datetime] | None = None,
        visibility_timeout_min: int = 30,
        max_tentativas: int = 5,
    ) -> None:
        self._engine = engine
        self._agora: Callable[[], datetime] = relogio or datetime.now
        self._visibility_timeout_min = visibility_timeout_min
        self._max_tentativas = max_tentativas

        # Define a tabela via SQLAlchemy Core (portável SQLite/Postgres)
        self._metadata = MetaData()
        self._tabela = Table(
            "fila_ingestao",
            self._metadata,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("id_hash", String, nullable=False),
            Column("texto_bruto", String, nullable=False),
            Column("usuario_id", String, nullable=False),
            Column("package_name", String, nullable=True),
            Column("origem", String, nullable=False),
            Column("status", String, nullable=False),
            Column("tentativas", Integer, nullable=False, default=0),
            Column("data_hora", DateTime, nullable=False),
            Column("client_msg_id", String, nullable=True, unique=True),
            Column("criada_em", DateTime, nullable=False),
            Column("claimed_em", DateTime, nullable=True),
            Column("processada_em", DateTime, nullable=True),
        )
        self._metadata.create_all(engine)

    # ------------------------------------------------------------------
    # Métodos públicos
    # ------------------------------------------------------------------

    def enqueue(
        self,
        texto_bruto: str,
        usuario_id: str,
        origem: str,
        package_name: Optional[str],
        data_hora: datetime,
        client_msg_id: Optional[str] = None,
    ) -> ItemFilaIngestao:
        """Insere item com status PENDENTE; idempotente via client_msg_id.

        Se `client_msg_id` já existe → NÃO duplica e retorna o item existente.
        `client_msg_id=None` nunca colide (pode inserir múltiplos sem id).
        Contrato: FILA-N-01, FILA-N-02.
        """
        agora = self._agora()
        id_hash = self._calcular_hash(texto_bruto, usuario_id, data_hora)

        # Tenta encontrar item existente quando há client_msg_id
        if client_msg_id is not None:
            item_existente = self._buscar_por_client_msg_id(client_msg_id)
            if item_existente is not None:
                return item_existente

        # Insere novo item
        with self._engine.begin() as conn:
            resultado = conn.execute(
                insert(self._tabela).values(
                    id_hash=id_hash,
                    texto_bruto=texto_bruto,
                    usuario_id=usuario_id,
                    package_name=package_name,
                    origem=origem,
                    status="PENDENTE",
                    tentativas=0,
                    data_hora=data_hora,
                    client_msg_id=client_msg_id,
                    criada_em=agora,
                    claimed_em=None,
                    processada_em=None,
                )
            )
            novo_id = resultado.inserted_primary_key[0]

        return ItemFilaIngestao(
            id=novo_id,
            id_hash=id_hash,
            texto_bruto=texto_bruto,
            usuario_id=usuario_id,
            package_name=package_name,
            origem=origem,
            status="PENDENTE",
            tentativas=0,
            data_hora=data_hora,
            client_msg_id=client_msg_id,
            criada_em=agora,
            claimed_em=None,
            processada_em=None,
        )

    def claim(self) -> ItemFilaIngestao | None:
        """Pega o PENDENTE mais antigo (menor id), marca PROCESSANDO atomicamente.

        Usa UPDATE com subselect para ser portável SQLite↔Postgres.
        Retorna o item ou None se não há PENDENTE. Contrato: FILA-N-03..05.
        """
        agora = self._agora()

        # Subselect para obter o menor id PENDENTE
        subq = (
            select(self._tabela.c.id)
            .where(self._tabela.c.status == "PENDENTE")
            .order_by(self._tabela.c.id)
            .limit(1)
            .scalar_subquery()
        )

        stmt = (
            update(self._tabela)
            .where(self._tabela.c.id == subq)
            .values(status="PROCESSANDO", claimed_em=agora)
            .returning(self._tabela)
        )

        with self._engine.begin() as conn:
            row = conn.execute(stmt).fetchone()

        if row is None:
            return None

        return self._row_para_item(row)

    def marcar(self, item_id: int, status: str) -> None:
        """Grava status final e seta processada_em=relogio().
        Statuses válidos: CONCLUIDO, DUPLICADA, ERRO. Contrato: FILA-N-06.
        """
        agora = self._agora()
        with self._engine.begin() as conn:
            conn.execute(
                update(self._tabela)
                .where(self._tabela.c.id == item_id)
                .values(status=status, processada_em=agora)
            )

    def recuperar_orfaos(self) -> int:
        """Recupera itens PROCESSANDO cujo claimed_em ultrapassou o visibility_timeout.

        Para cada órfão:
        - Incrementa tentativas.
        - Se tentativas >= max_tentativas → status='ERRO' (DLQ, não conta como recuperado).
        - Senão → status='PENDENTE', claimed_em=None (conta como recuperado).

        Retorna a quantidade que voltou para PENDENTE (itens DLQ não entram na contagem).
        Contrato: FILA-N-07, FILA-N-08, FILA-N-09.
        """
        agora = self._agora()
        limite = agora - timedelta(minutes=self._visibility_timeout_min)

        # Busca todos os órfãos (PROCESSANDO com claimed_em anterior ao limite)
        stmt_busca = select(self._tabela).where(
            and_(
                self._tabela.c.status == "PROCESSANDO",
                self._tabela.c.claimed_em < limite,
            )
        )

        recuperados = 0

        with self._engine.begin() as conn:
            orfaos = conn.execute(stmt_busca).fetchall()

            for orfao in orfaos:
                novas_tentativas = orfao.tentativas + 1

                if novas_tentativas >= self._max_tentativas:
                    # DLQ: vai para ERRO
                    conn.execute(
                        update(self._tabela)
                        .where(self._tabela.c.id == orfao.id)
                        .values(status="ERRO", tentativas=novas_tentativas)
                    )
                else:
                    # Volta para PENDENTE
                    conn.execute(
                        update(self._tabela)
                        .where(self._tabela.c.id == orfao.id)
                        .values(
                            status="PENDENTE",
                            tentativas=novas_tentativas,
                            claimed_em=None,
                        )
                    )
                    recuperados += 1

        return recuperados

    def buscar(self, item_id: int) -> ItemFilaIngestao | None:
        """Lê 1 item por id; None se não existe. Contrato: FILA-N-06 (verificação)."""
        stmt = select(self._tabela).where(self._tabela.c.id == item_id)
        with self._engine.connect() as conn:
            row = conn.execute(stmt).fetchone()
        if row is None:
            return None
        return self._row_para_item(row)

    def listar_por_status(self, status: str) -> list[ItemFilaIngestao]:
        """Lista todos os itens com determinado status. Contrato: FILA-N-09."""
        stmt = select(self._tabela).where(self._tabela.c.status == status)
        with self._engine.connect() as conn:
            rows = conn.execute(stmt).fetchall()
        return [self._row_para_item(row) for row in rows]

    # ------------------------------------------------------------------
    # Métodos privados
    # ------------------------------------------------------------------

    def _buscar_por_client_msg_id(self, client_msg_id: str) -> ItemFilaIngestao | None:
        """Busca item pelo client_msg_id; None se não existe."""
        stmt = select(self._tabela).where(
            self._tabela.c.client_msg_id == client_msg_id
        )
        with self._engine.connect() as conn:
            row = conn.execute(stmt).fetchone()
        if row is None:
            return None
        return self._row_para_item(row)

    def _row_para_item(self, row) -> ItemFilaIngestao:
        """Converte Row do SQLAlchemy em ItemFilaIngestao."""
        return ItemFilaIngestao(
            id=row.id,
            id_hash=row.id_hash,
            texto_bruto=row.texto_bruto,
            usuario_id=row.usuario_id,
            package_name=row.package_name,
            origem=row.origem,
            status=row.status,
            tentativas=row.tentativas,
            data_hora=row.data_hora,
            client_msg_id=row.client_msg_id,
            criada_em=row.criada_em,
            claimed_em=row.claimed_em,
            processada_em=row.processada_em,
        )

    @staticmethod
    def _calcular_hash(texto_bruto: str, usuario_id: str, data_hora: datetime) -> str:
        """Gera hash SHA-256 determinístico para o item."""
        conteudo = f"{usuario_id}|{data_hora.isoformat()}|{texto_bruto}"
        return hashlib.sha256(conteudo.encode()).hexdigest()
