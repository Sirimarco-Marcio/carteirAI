"""
Repositórios Reais usando SQLAlchemy (Bloco 4).
Implementam a persistência diretamente no banco de dados,
mapeando os resultados de consultas SQL puras para os DTOs do domínio.
"""

import uuid
import json
import calendar
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from carteirai.dominio.dtos import (
    Conta,
    Transacao,
    Fatura,
    FonteRenda,
    RegistroDia
)

class SqlAlchemyContaRepo:
    def __init__(self, session: Session):
        self.session = session

    def buscar(self, conta_id: str) -> Optional[Conta]:
        query = text(
            "SELECT id, tipo, saldo_atual, limite, dia_fechamento, dia_vencimento "
            "FROM contas WHERE id = :id"
        )
        row = self.session.execute(query, {"id": conta_id}).fetchone()
        if not row:
            return None
        
        return Conta(
            id=str(row[0]),
            tipo=str(row[1]),
            saldo_atual=Decimal(str(row[2])),
            limite=Decimal(str(row[3])) if row[3] is not None else None,
            dia_fechamento=row[4],
            dia_vencimento=row[5]
        )

    def atualizar_saldo(self, conta_id: str, novo_saldo: Decimal) -> None:
        query = text("UPDATE contas SET saldo_atual = :saldo WHERE id = :id")
        self.session.execute(query, {"saldo": float(novo_saldo), "id": conta_id})
        self.session.commit()


class SqlAlchemyTransacaoRepo:
    def __init__(self, session: Session):
        self.session = session

    def salvar(self, transacao: Transacao) -> None:
        query = text(
            "INSERT INTO transacoes (id_hash, conta_id, usuario_id, valor, data_hora, "
            "estabelecimento, tipo, forma, status, origem, fatura_id, parcela_atual, "
            "parcelas_total, possivel_duplicata) "
            "VALUES (:id, :conta_id, :usuario_id, :valor, :data_hora, :estabelecimento, "
            ":tipo, :forma, :status, 'manual', :fatura_id, :parcela_atual, "
            ":parcelas_total, :possivel_duplicata)"
        )
        
        # Converte o datetime para string se vier assim, garantindo compatibilidade SQLite/Postgres
        dh = transacao.data_hora
        if isinstance(dh, datetime):
            dh = str(dh)
            
        self.session.execute(query, {
            "id": transacao.id,
            "conta_id": transacao.conta_id,
            "usuario_id": transacao.usuario_id,
            "valor": float(transacao.valor),
            "data_hora": dh,
            "estabelecimento": transacao.estabelecimento,
            "tipo": transacao.tipo,
            "forma": transacao.forma,
            "status": transacao.status,
            "fatura_id": transacao.fatura_id,
            "parcela_atual": transacao.parcela_atual,
            "parcelas_total": transacao.parcelas_total,
            "possivel_duplicata": transacao.possivel_duplicata
        })
        self.session.commit()

    def buscar(self, id_hash: str) -> Optional[Transacao]:
        query = text(
            "SELECT id_hash, conta_id, usuario_id, valor, data_hora, "
            "estabelecimento, tipo, forma, status, fatura_id, "
            "parcela_atual, parcelas_total, possivel_duplicata "
            "FROM transacoes WHERE id_hash = :id_hash"
        )
        row = self.session.execute(query, {"id_hash": id_hash}).fetchone()
        if not row:
            return None
        return self._map_row(row)

    def atualizar(self, transacao: Transacao) -> None:
        query = text("UPDATE transacoes SET status = :status WHERE id_hash = :id_hash")
        self.session.execute(query, {"status": transacao.status, "id_hash": transacao.id})
        self.session.commit()

    def buscar_ultima_confirmada(self, usuario_id: str) -> Optional[Transacao]:
        query = text(
            "SELECT id_hash, conta_id, usuario_id, valor, data_hora, "
            "estabelecimento, tipo, forma, status, fatura_id, "
            "parcela_atual, parcelas_total, possivel_duplicata "
            "FROM transacoes WHERE usuario_id = :usuario_id AND status = 'CONFIRMADA' "
            "ORDER BY data_hora DESC LIMIT 1"
        )
        row = self.session.execute(query, {"usuario_id": usuario_id}).fetchone()
        if not row:
            return None
        return self._map_row(row)

    def pendentes(self) -> List[Transacao]:
        query = text(
            "SELECT id_hash, conta_id, usuario_id, valor, data_hora, "
            "estabelecimento, tipo, forma, status, fatura_id, "
            "parcela_atual, parcelas_total, possivel_duplicata "
            "FROM transacoes WHERE status = 'PENDENTE_APROVACAO'"
        )
        rows = self.session.execute(query).fetchall()
        return [self._map_row(r) for r in rows]

    def _map_row(self, row) -> Transacao:
        dh = row[4]
        if isinstance(dh, str):
            try:
                dh = datetime.fromisoformat(dh.replace('Z', '+00:00'))
            except ValueError:
                # fallback para formato padrão sem tz/iso
                dh = datetime.strptime(dh, "%Y-%m-%d %H:%M:%S")

        return Transacao(
            id=str(row[0]),
            conta_id=str(row[1]) if row[1] else "",
            usuario_id=str(row[2]),
            valor=Decimal(str(row[3])),
            data_hora=dh,
            estabelecimento=str(row[5]) if row[5] else None,
            tipo=str(row[6]),  # type: ignore
            forma=str(row[7]),  # type: ignore
            status=str(row[8]),  # type: ignore
            categoria="Outros", # Campo simplificado sem JOIN na tabela categorias
            fatura_id=str(row[9]) if row[9] else None,
            parcela_atual=row[10] if row[10] else 1,
            parcelas_total=row[11] if row[11] else 1,
            possivel_duplicata=bool(row[12]) if row[12] is not None else False
        )


class SqlAlchemyFaturaRepo:
    def __init__(self, session: Session):
        self.session = session

    def buscar_aberta(self, conta_id: str, mes: int, ano: int) -> Optional[Fatura]:
        query = text(
            "SELECT id, conta_id, mes, ano, valor_total, vencimento, status "
            "FROM faturas WHERE conta_id = :conta_id AND mes = :mes AND ano = :ano AND status = 'ABERTA' "
            "LIMIT 1"
        )
        row = self.session.execute(query, {"conta_id": conta_id, "mes": mes, "ano": ano}).fetchone()
        if not row:
            return None
        return self._map_row(row)

    def criar(self, conta_id: str, mes: int, ano: int) -> Fatura:
        fat_id = str(uuid.uuid4())
        query = text(
            "INSERT INTO faturas (id, conta_id, mes, ano, valor_total, status) "
            "VALUES (:id, :conta_id, :mes, :ano, 0, 'ABERTA')"
        )
        self.session.execute(query, {"id": fat_id, "conta_id": conta_id, "mes": mes, "ano": ano})
        self.session.commit()
        return Fatura(id=fat_id, conta_id=conta_id, mes=mes, ano=ano)

    def atualizar(self, fatura: Fatura) -> None:
        query = text(
            "UPDATE faturas SET valor_total = :valor, status = :status "
            "WHERE id = :id"
        )
        self.session.execute(query, {"valor": float(fatura.valor_total), "status": fatura.status, "id": fatura.id})
        self.session.commit()

    def faturas_abertas(self, usuario_id: str) -> List[Fatura]:
        query = text(
            "SELECT f.id, f.conta_id, f.mes, f.ano, f.valor_total, f.vencimento, f.status "
            "FROM faturas f "
            "JOIN contas c ON f.conta_id = c.id "
            "WHERE c.usuario_id = :usuario_id AND f.status = 'ABERTA'"
        )
        rows = self.session.execute(query, {"usuario_id": usuario_id}).fetchall()
        return [self._map_row(r) for r in rows]

    def _map_row(self, row) -> Fatura:
        venc = row[5]
        if isinstance(venc, str) and venc:
            try:
                venc = date.fromisoformat(venc)
            except ValueError:
                pass

        return Fatura(
            id=str(row[0]),
            conta_id=str(row[1]),
            mes=row[2],
            ano=row[3],
            valor_total=Decimal(str(row[4])),
            vencimento=venc if venc else None,
            status=str(row[6])  # type: ignore
        )


class SqlAlchemyFonteRepo:
    def __init__(self, session: Session):
        self.session = session

    def ativas(self, usuario_id: str) -> List[FonteRenda]:
        query = text(
            "SELECT id, usuario_id, nome, tipo_calculo, valor_base, "
            "valor_alimentacao_dia, valor_transporte_dia, dias_semana, ativa "
            "FROM fontes_renda WHERE usuario_id = :usuario_id AND ativa = :ativa"
        )
        rows = self.session.execute(query, {"usuario_id": usuario_id, "ativa": True}).fetchall()
        
        fontes = []
        for r in rows:
            ds = r[7]
            if isinstance(ds, str):
                try:
                    ds = json.loads(ds)
                except Exception:
                    ds = []
            if not isinstance(ds, list):
                ds = []
            
            fontes.append(FonteRenda(
                id=str(r[0]),
                usuario_id=str(r[1]),
                nome=str(r[2]),
                tipo_calculo=str(r[3]),  # type: ignore
                valor_base=Decimal(str(r[4])),
                valor_alimentacao_dia=Decimal(str(r[5])),
                valor_transporte_dia=Decimal(str(r[6])),
                dias_semana=ds,
                ativa=bool(r[8])
            ))
        return fontes


class SqlAlchemyRegistroDiaRepo:
    def __init__(self, session: Session):
        self.session = session

    def registrar_dia(self, fonte_renda_id: str, data: date, status: str) -> None:
        reg_id = str(uuid.uuid4())
        
        # Realiza UPSERT compatível com SQLite e Postgres através do ON CONFLICT
        query = text("""
            INSERT INTO registro_dias (id, fonte_renda_id, data, status) 
            VALUES (:id, :fonte_renda_id, :data, :status)
            ON CONFLICT (fonte_renda_id, data) DO UPDATE SET status = excluded.status
        """)
        self.session.execute(query, {
            "id": reg_id,
            "fonte_renda_id": fonte_renda_id,
            "data": data.isoformat(),
            "status": status
        })
        self.session.commit()

    def do_mes(self, fonte_id: str, mes: int, ano: int) -> List[RegistroDia]:
        start_date = date(ano, mes, 1)
        end_date = date(ano, mes, calendar.monthrange(ano, mes)[1])
        
        query = text(
            "SELECT fonte_renda_id, data, status "
            "FROM registro_dias "
            "WHERE fonte_renda_id = :id AND data >= :start AND data <= :end"
        )
        rows = self.session.execute(query, {
            "id": fonte_id, 
            "start": start_date.isoformat(), 
            "end": end_date.isoformat()
        }).fetchall()
        
        registros = []
        for r in rows:
            dt = r[1]
            if isinstance(dt, str):
                dt = date.fromisoformat(dt)
            registros.append(RegistroDia(
                fonte_renda_id=str(r[0]),
                data=dt,
                status=str(r[2])  # type: ignore
            ))
        return registros
