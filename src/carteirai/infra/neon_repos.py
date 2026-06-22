"""Repositórios reais ligados ao Neon (psycopg). Implementam as portas usadas pelo
Orquestrador, APROV e CMD. Conexão por chamada (o pooler do Neon dá conta).

Mapeamento de identidade: `usuarios.id` == o UUID que o app Android carimba na notificação.
Aprovação de membro sem chat próprio → cai no chat do admin da família.
"""

from __future__ import annotations

import os
from decimal import Decimal

import psycopg

from carteirai.dedup.dedup import TransacaoSimilar
from carteirai.dominio.dtos import TransacaoExtraida, Transacao


def _dsn(dsn: str | None) -> str:
    return dsn or os.environ["DATABASE_URL"]


class UsuarioRepoNeon:
    """Porta UsuarioRepo (APROV/ING). chat_id_de cai no admin se o usuário não tem chat."""

    def __init__(self, dsn: str | None = None) -> None:
        self._dsn = _dsn(dsn)

    def chat_id_de(self, usuario_id: str) -> str | None:
        sql = """
            SELECT COALESCE(u.telegram_chat_id,
                   (SELECT a.telegram_chat_id FROM usuarios a
                    WHERE a.familia_id = u.familia_id AND a.role = 'admin'
                    ORDER BY a.telegram_chat_id LIMIT 1))
            FROM usuarios u WHERE u.id = %s::uuid
        """
        with psycopg.connect(self._dsn) as c:
            row = c.execute(sql, (usuario_id,)).fetchone()
        return row[0] if row else None

    def usuario_de_chat(self, chat_id: str) -> str | None:
        with psycopg.connect(self._dsn) as c:
            row = c.execute(
                "SELECT id FROM usuarios WHERE telegram_chat_id = %s LIMIT 1", (chat_id,)
            ).fetchone()
        return str(row[0]) if row else None


class TransacaoRepoNeon:
    """Porta RepoTransacoes (Orquestrador) + buscar (APROV). id da transação = id_hash."""

    def __init__(self, dsn: str | None = None) -> None:
        self._dsn = _dsn(dsn)

    def hash_existe(self, hash: str) -> bool:
        with psycopg.connect(self._dsn) as c:
            return c.execute(
                "SELECT 1 FROM transacoes WHERE id_hash = %s LIMIT 1", (hash,)
            ).fetchone() is not None

    def transacoes(self, usuario_id: str) -> list[TransacaoSimilar]:
        with psycopg.connect(self._dsn) as c:
            rows = c.execute(
                "SELECT valor, COALESCE(estabelecimento,''), data_hora "
                "FROM transacoes WHERE usuario_id = %s::uuid", (usuario_id,)
            ).fetchall()
        return [TransacaoSimilar(valor=r[0], estabelecimento=r[1], data_hora=r[2]) for r in rows]

    def salvar(
        self, usuario_id: str, hash: str, transacao: TransacaoExtraida, possivel_duplicata: bool
    ) -> None:
        sql = """
            INSERT INTO transacoes
              (id_hash, usuario_id, categoria_id, valor, data_hora, estabelecimento,
               tipo, forma, parcelas_total, status, possivel_duplicata, origem)
            VALUES (%s, %s::uuid,
                    (SELECT id FROM categorias WHERE nome = %s LIMIT 1),
                    %s, %s, %s, %s, %s, %s, 'PENDENTE_APROVACAO', %s, 'notificacao')
            ON CONFLICT (id_hash) DO NOTHING
        """
        with psycopg.connect(self._dsn) as c:
            c.execute(sql, (
                hash, usuario_id, transacao.categoria, transacao.valor, transacao.data_hora,
                transacao.estabelecimento, transacao.tipo, transacao.forma,
                transacao.parcelas_total, possivel_duplicata,
            ))

    def buscar(self, transacao_id: str) -> Transacao | None:
        """transacao_id == id_hash. Usado pelo APROV.tratar_callback."""
        sql = """
            SELECT id_hash, usuario_id, valor, data_hora, estabelecimento, tipo, forma,
                   status, possivel_duplicata, parcelas_total
            FROM transacoes WHERE id_hash = %s
        """
        with psycopg.connect(self._dsn) as c:
            r = c.execute(sql, (transacao_id,)).fetchone()
        if not r:
            return None
        return Transacao(
            id=r[0], conta_id="", usuario_id=str(r[1]), valor=r[2], data_hora=r[3],
            estabelecimento=r[4], tipo=r[5], forma=r[6], status=r[7],
            possivel_duplicata=r[8], parcelas_total=r[9],
        )

    def atualizar_status(self, transacao_id: str, status: str) -> None:
        with psycopg.connect(self._dsn) as c:
            c.execute("UPDATE transacoes SET status=%s WHERE id_hash=%s", (status, transacao_id))


class ConsultaFinanceiraNeon:
    """Porta ConsultaFinanceira (CMD): saldo, gastos por categoria, pendentes do usuário."""

    def __init__(self, usuario_id: str, dsn: str | None = None) -> None:
        self._dsn = _dsn(dsn)
        self._uid = usuario_id

    def saldo(self) -> Decimal:
        with psycopg.connect(self._dsn) as c:
            row = c.execute(
                "SELECT f.saldo_acumulado FROM familias f "
                "JOIN usuarios u ON u.familia_id = f.id WHERE u.id = %s::uuid", (self._uid,)
            ).fetchone()
        return row[0] if row else Decimal("0")

    def gastos_por_categoria(self, categoria: str) -> Decimal:
        sql = """
            SELECT COALESCE(SUM(t.valor), 0) FROM transacoes t
            JOIN categorias c ON c.id = t.categoria_id
            JOIN usuarios u ON u.id = t.usuario_id
            WHERE u.familia_id = (SELECT familia_id FROM usuarios WHERE id = %s::uuid)
              AND c.nome = %s AND t.status = 'CONFIRMADA' AND t.tipo = 'saida'
              AND date_trunc('month', t.data_hora) = date_trunc('month', now())
        """
        with psycopg.connect(self._dsn) as c:
            row = c.execute(sql, (self._uid, categoria)).fetchone()
        return row[0]

    def pendentes(self) -> list[Transacao]:
        sql = """
            SELECT id_hash, usuario_id, valor, data_hora, estabelecimento, tipo, forma, status
            FROM transacoes t
            WHERE t.usuario_id IN (SELECT id FROM usuarios WHERE familia_id =
                  (SELECT familia_id FROM usuarios WHERE id = %s::uuid))
              AND t.status = 'PENDENTE_APROVACAO'
            ORDER BY t.data_hora DESC
        """
        with psycopg.connect(self._dsn) as c:
            rows = c.execute(sql, (self._uid,)).fetchall()
        return [
            Transacao(id=r[0], conta_id="", usuario_id=str(r[1]), valor=r[2], data_hora=r[3],
                      estabelecimento=r[4], tipo=r[5], forma=r[6], status=r[7])
            for r in rows
        ]
