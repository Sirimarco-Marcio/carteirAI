"""Fase RED: testes da persistência unificada via SQLAlchemy.

Casos PERS-U-01..11 (contrato: docs/tdd/11-contratos-persistencia-unificada.md).
As 3 classes importadas abaixo NÃO existem ainda → ImportError esperado (RED).
"""

from __future__ import annotations

import ast
from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# -----------------------------------------------------------------------
# IMPORTAÇÕES ALVO — ainda não existem → ImportError == RED esperado
# -----------------------------------------------------------------------
from carteirai.infra.sqlalchemy_repos import (
    SqlAlchemyUsuarioRepo,
    SqlAlchemyTransacaoIngestaoRepo,
    SqlAlchemyConsultaFinanceira,
)

from carteirai.dominio.dtos import Transacao, TransacaoExtraida
from carteirai.dedup.dedup import TransacaoSimilar

# -----------------------------------------------------------------------
# SCHEMA SQLite — espelho do SQLITE_SCHEMA em test_sqlalchemy_repos.py
# (tipos complexos de Postgres substituídos por TEXT/REAL/INTEGER nativos)
# -----------------------------------------------------------------------
SQLITE_SCHEMA = """
CREATE TABLE familias (
    id TEXT PRIMARY KEY,
    nome TEXT NOT NULL,
    saldo_acumulado REAL NOT NULL DEFAULT 0
);
CREATE TABLE usuarios (
    id TEXT PRIMARY KEY,
    familia_id TEXT NOT NULL REFERENCES familias(id),
    nome TEXT NOT NULL,
    telegram_chat_id TEXT UNIQUE,
    role TEXT NOT NULL DEFAULT 'membro'
);
CREATE TABLE instituicoes (
    id TEXT PRIMARY KEY,
    nome TEXT NOT NULL,
    tipo TEXT NOT NULL
);
CREATE TABLE contas (
    id TEXT PRIMARY KEY,
    usuario_id TEXT NOT NULL REFERENCES usuarios(id),
    instituicao_id TEXT NOT NULL REFERENCES instituicoes(id),
    tipo TEXT NOT NULL,
    limite REAL,
    saldo_atual REAL NOT NULL DEFAULT 0,
    dia_fechamento INTEGER,
    dia_vencimento INTEGER
);
CREATE TABLE categorias (
    id TEXT PRIMARY KEY,
    nome TEXT NOT NULL UNIQUE,
    tipo TEXT NOT NULL DEFAULT 'despesa'
);
CREATE TABLE faturas (
    id TEXT PRIMARY KEY,
    conta_id TEXT NOT NULL REFERENCES contas(id),
    mes INTEGER NOT NULL,
    ano INTEGER NOT NULL,
    valor_total REAL NOT NULL DEFAULT 0,
    vencimento TEXT,
    status TEXT NOT NULL DEFAULT 'ABERTA'
);
CREATE TABLE competencias (
    id TEXT PRIMARY KEY,
    familia_id TEXT NOT NULL REFERENCES familias(id),
    mes INTEGER NOT NULL,
    ano INTEGER NOT NULL,
    renda_prevista REAL NOT NULL DEFAULT 0,
    renda_realizada REAL,
    total_gasto REAL NOT NULL DEFAULT 0,
    sobra REAL,
    status TEXT NOT NULL DEFAULT 'ABERTA'
);
CREATE TABLE transacoes (
    id_hash TEXT PRIMARY KEY,
    conta_id TEXT REFERENCES contas(id),
    usuario_id TEXT NOT NULL REFERENCES usuarios(id),
    categoria_id TEXT REFERENCES categorias(id),
    fatura_id TEXT REFERENCES faturas(id),
    competencia_id TEXT REFERENCES competencias(id),
    valor REAL NOT NULL,
    data_hora TEXT NOT NULL,
    estabelecimento TEXT,
    tipo TEXT NOT NULL,
    forma TEXT NOT NULL,
    parcela_atual INTEGER NOT NULL DEFAULT 1,
    parcelas_total INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'PENDENTE_APROVACAO',
    possivel_duplicata BOOLEAN NOT NULL DEFAULT 0,
    origem TEXT NOT NULL DEFAULT 'manual',
    criada_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE fontes_renda (
    id TEXT PRIMARY KEY,
    usuario_id TEXT NOT NULL REFERENCES usuarios(id),
    nome TEXT NOT NULL,
    tipo_calculo TEXT NOT NULL,
    valor_base REAL NOT NULL DEFAULT 0,
    valor_alimentacao_dia REAL NOT NULL DEFAULT 0,
    valor_transporte_dia REAL NOT NULL DEFAULT 0,
    dias_semana TEXT NOT NULL DEFAULT '[]',
    ativa BOOLEAN NOT NULL DEFAULT 1
);
CREATE TABLE registro_dias (
    id TEXT PRIMARY KEY,
    fonte_renda_id TEXT NOT NULL REFERENCES fontes_renda(id),
    data TEXT NOT NULL,
    status TEXT NOT NULL,
    UNIQUE (fonte_renda_id, data)
);
"""


# -----------------------------------------------------------------------
# FIXTURES
# -----------------------------------------------------------------------

@pytest.fixture
def session():
    """Banco SQLite em memória com schema simplificado (simula Postgres)."""
    engine = create_engine("sqlite:///:memory:")
    with engine.connect() as conn:
        for stmt in SQLITE_SCHEMA.split(";"):
            if stmt.strip():
                conn.execute(text(stmt))
        conn.commit()

    Session = sessionmaker(bind=engine)
    db_session = Session()
    yield db_session
    db_session.close()


@pytest.fixture
def seed_data(session):
    """Dados base: família, admin com chat, instituição, conta e categoria 'Alimentação'."""
    session.execute(text(
        "INSERT INTO familias (id, nome, saldo_acumulado) VALUES ('fam1', 'Família Teste', 1500.0)"
    ))
    # Usuário admin COM telegram_chat_id
    session.execute(text(
        "INSERT INTO usuarios (id, familia_id, nome, telegram_chat_id, role) "
        "VALUES ('usr_admin', 'fam1', 'Admin Teste', 'chat_admin_99', 'admin')"
    ))
    # Usuário membro SEM telegram_chat_id (usado em PERS-U-02)
    session.execute(text(
        "INSERT INTO usuarios (id, familia_id, nome, telegram_chat_id, role) "
        "VALUES ('usr_membro', 'fam1', 'Membro Sem Chat', NULL, 'membro')"
    ))
    # Instituição e conta vinculada ao admin
    session.execute(text(
        "INSERT INTO instituicoes (id, nome, tipo) VALUES ('inst1', 'Banco Teste', 'banco')"
    ))
    session.execute(text(
        "INSERT INTO contas (id, usuario_id, instituicao_id, tipo, saldo_atual) "
        "VALUES ('conta_A', 'usr_admin', 'inst1', 'corrente', 100.0)"
    ))
    # Categoria 'Alimentação' (necessária para PERS-U-06 e PERS-U-10)
    session.execute(text(
        "INSERT INTO categorias (id, nome, tipo) VALUES ('cat_alim', 'Alimentação', 'despesa')"
    ))
    # Categoria alternativa para PERS-U-10
    session.execute(text(
        "INSERT INTO categorias (id, nome, tipo) VALUES ('cat_trans', 'Transporte', 'despesa')"
    ))
    session.commit()

    return {
        "familia_id": "fam1",
        "usuario_admin_id": "usr_admin",
        "usuario_membro_id": "usr_membro",
        "conta_id": "conta_A",
        "categoria_alim_id": "cat_alim",
        "categoria_trans_id": "cat_trans",
        "chat_admin": "chat_admin_99",
    }


# -----------------------------------------------------------------------
# PERS-U-01 — chat_id_de: usuário com chat próprio devolve o próprio chat
# -----------------------------------------------------------------------

def test_pers_u_01_chat_id_de_usuario_com_chat_proprio(session, seed_data):
    """PERS-U-01: chat_id_de(admin_id) deve devolver o telegram_chat_id do próprio usuário."""
    repo = SqlAlchemyUsuarioRepo(session)
    resultado = repo.chat_id_de(seed_data["usuario_admin_id"])
    assert resultado == seed_data["chat_admin"]


# -----------------------------------------------------------------------
# PERS-U-02 — chat_id_de: membro sem chat → devolve chat do admin da família
# -----------------------------------------------------------------------

def test_pers_u_02_chat_id_de_membro_sem_chat_cai_no_admin(session, seed_data):
    """PERS-U-02: chat_id_de(membro_sem_chat) deve devolver o telegram_chat_id do admin da família."""
    repo = SqlAlchemyUsuarioRepo(session)
    resultado = repo.chat_id_de(seed_data["usuario_membro_id"])
    # O membro não tem chat; o COALESCE deve cair no admin da mesma família
    assert resultado == seed_data["chat_admin"]


# -----------------------------------------------------------------------
# PERS-U-03 — usuario_de_chat: chat conhecido → id; desconhecido → None
# -----------------------------------------------------------------------

def test_pers_u_03_usuario_de_chat_conhecido_e_desconhecido(session, seed_data):
    """PERS-U-03: usuario_de_chat com chat existente retorna o id do usuário; chat inexistente → None."""
    repo = SqlAlchemyUsuarioRepo(session)

    # Chat conhecido → deve retornar o id do usuário admin
    usuario_encontrado = repo.usuario_de_chat(seed_data["chat_admin"])
    assert usuario_encontrado == seed_data["usuario_admin_id"]

    # Chat desconhecido → deve retornar None
    usuario_ausente = repo.usuario_de_chat("chat_que_nao_existe_999")
    assert usuario_ausente is None


# -----------------------------------------------------------------------
# PERS-U-04 — hash_existe: hash presente → True; ausente → False
# -----------------------------------------------------------------------

def test_pers_u_04_hash_existe_presente_e_ausente(session, seed_data):
    """PERS-U-04: hash_existe retorna True para hash registrado e False para hash desconhecido."""
    # Insere uma transação diretamente para simular hash existente
    session.execute(text(
        "INSERT INTO transacoes "
        "(id_hash, usuario_id, valor, data_hora, tipo, forma, status, origem) "
        "VALUES ('hash_existente_abc', 'usr_admin', 10.0, '2026-06-01 10:00:00', "
        "'saida', 'debito', 'PENDENTE_APROVACAO', 'notificacao')"
    ))
    session.commit()

    repo = SqlAlchemyTransacaoIngestaoRepo(session)

    assert repo.hash_existe("hash_existente_abc") is True
    assert repo.hash_existe("hash_que_nao_existe_xyz") is False


# -----------------------------------------------------------------------
# PERS-U-05 — transacoes(usuario_id): devolve similares (valor/estab/data)
# -----------------------------------------------------------------------

def test_pers_u_05_transacoes_do_usuario_devolve_similares(session, seed_data):
    """PERS-U-05: transacoes(usuario_id) devolve lista de TransacaoSimilar com valor/estabelecimento/data_hora."""
    session.execute(text(
        "INSERT INTO transacoes "
        "(id_hash, usuario_id, valor, data_hora, estabelecimento, tipo, forma, status, origem) "
        "VALUES ('hash_sim1', 'usr_admin', 55.0, '2026-06-10 09:00:00', 'Padaria Central', "
        "'saida', 'debito', 'CONFIRMADA', 'notificacao')"
    ))
    session.execute(text(
        "INSERT INTO transacoes "
        "(id_hash, usuario_id, valor, data_hora, estabelecimento, tipo, forma, status, origem) "
        "VALUES ('hash_sim2', 'usr_admin', 120.5, '2026-06-15 14:30:00', 'Supermercado Norte', "
        "'saida', 'pix', 'PENDENTE_APROVACAO', 'notificacao')"
    ))
    session.commit()

    repo = SqlAlchemyTransacaoIngestaoRepo(session)
    similares = repo.transacoes(seed_data["usuario_admin_id"])

    assert len(similares) == 2
    valores = {s.valor for s in similares}
    assert Decimal("55.0") in valores
    assert Decimal("120.5") in valores

    estabelecimentos = {s.estabelecimento for s in similares}
    assert "Padaria Central" in estabelecimentos
    assert "Supermercado Norte" in estabelecimentos

    # Verifica que todos os itens são TransacaoSimilar com os campos esperados
    for s in similares:
        assert isinstance(s, TransacaoSimilar)
        assert hasattr(s, "valor")
        assert hasattr(s, "estabelecimento")
        assert hasattr(s, "data_hora")


# -----------------------------------------------------------------------
# PERS-U-06 — salvar: INSERT com origem='notificacao', PENDENTE_APROVACAO,
#              categoria_id resolvida por nome; mesmo hash não duplica
# -----------------------------------------------------------------------

def test_pers_u_06_salvar_insere_corretamente_e_idempotente(session, seed_data):
    """PERS-U-06: salvar() insere com origem='notificacao', status PENDENTE_APROVACAO e
    categoria_id resolvida por nome 'Alimentação'. Reenviar o mesmo hash não cria 2 linhas."""
    transacao = TransacaoExtraida(
        valor=Decimal("37.50"),
        data_hora=datetime(2026, 6, 20, 12, 0, 0),
        estabelecimento="Restaurante do Zé",
        categoria="Alimentação",
        forma="pix",
        tipo="saida",
        parcelas_total=1,
    )

    repo = SqlAlchemyTransacaoIngestaoRepo(session)
    hash_teste = "hash_salvar_pers_u_06"

    # Primeira chamada — deve inserir
    repo.salvar(
        usuario_id=seed_data["usuario_admin_id"],
        hash=hash_teste,
        transacao=transacao,
        possivel_duplicata=False,
    )

    # Segunda chamada com mesmo hash — não deve duplicar (idempotente)
    repo.salvar(
        usuario_id=seed_data["usuario_admin_id"],
        hash=hash_teste,
        transacao=transacao,
        possivel_duplicata=False,
    )

    # Verifica que existe exatamente 1 linha com esse hash
    contagem = session.execute(
        text("SELECT COUNT(*) FROM transacoes WHERE id_hash = :h"), {"h": hash_teste}
    ).scalar()
    assert contagem == 1

    # Verifica os campos obrigatórios da linha inserida
    linha = session.execute(
        text(
            "SELECT origem, status, categoria_id, possivel_duplicata "
            "FROM transacoes WHERE id_hash = :h"
        ),
        {"h": hash_teste},
    ).fetchone()

    assert linha is not None
    assert linha[0] == "notificacao"
    assert linha[1] == "PENDENTE_APROVACAO"
    # categoria_id deve estar resolvido — deve apontar para 'Alimentação'
    assert linha[2] == seed_data["categoria_alim_id"]
    assert linha[3] == 0 or linha[3] is False  # possivel_duplicata=False


# -----------------------------------------------------------------------
# PERS-U-07 — buscar(hash): devolve Transacao mapeada; inexistente → None
# -----------------------------------------------------------------------

def test_pers_u_07_buscar_hash_existente_e_inexistente(session, seed_data):
    """PERS-U-07: buscar(hash_existente) devolve Transacao corretamente mapeada; hash ausente → None."""
    session.execute(text(
        "INSERT INTO transacoes "
        "(id_hash, usuario_id, valor, data_hora, estabelecimento, tipo, forma, status, origem) "
        "VALUES ('hash_buscar_07', 'usr_admin', 99.99, '2026-06-18 08:30:00', "
        "'Loja XYZ', 'saida', 'credito', 'PENDENTE_APROVACAO', 'notificacao')"
    ))
    session.commit()

    repo = SqlAlchemyTransacaoIngestaoRepo(session)

    # Hash existente → deve retornar Transacao
    transacao = repo.buscar("hash_buscar_07")
    assert transacao is not None
    assert isinstance(transacao, Transacao)
    assert transacao.id == "hash_buscar_07"
    assert transacao.valor == Decimal("99.99")
    assert transacao.usuario_id == "usr_admin"

    # Hash inexistente → deve retornar None
    ausente = repo.buscar("hash_que_nunca_existiu")
    assert ausente is None


# -----------------------------------------------------------------------
# PERS-U-08 — atualizar_status: muda o status no banco
# -----------------------------------------------------------------------

def test_pers_u_08_atualizar_status_persiste_no_banco(session, seed_data):
    """PERS-U-08: atualizar_status(id, status) efetua UPDATE e o novo status é visível no banco."""
    session.execute(text(
        "INSERT INTO transacoes "
        "(id_hash, usuario_id, valor, data_hora, tipo, forma, status, origem) "
        "VALUES ('hash_upd_08', 'usr_admin', 45.0, '2026-06-17 11:00:00', "
        "'saida', 'debito', 'PENDENTE_APROVACAO', 'notificacao')"
    ))
    session.commit()

    repo = SqlAlchemyTransacaoIngestaoRepo(session)
    repo.atualizar_status("hash_upd_08", "CONFIRMADA")

    status_banco = session.execute(
        text("SELECT status FROM transacoes WHERE id_hash = 'hash_upd_08'")
    ).scalar()
    assert status_banco == "CONFIRMADA"


# -----------------------------------------------------------------------
# PERS-U-09 — saldo(): devolve saldo_acumulado da família do usuário
# -----------------------------------------------------------------------

def test_pers_u_09_saldo_da_familia_do_usuario(session, seed_data):
    """PERS-U-09: saldo() retorna familias.saldo_acumulado da família do usuário como Decimal."""
    # O seed_data já inseriu fam1 com saldo_acumulado = 1500.0
    consulta = SqlAlchemyConsultaFinanceira(session, seed_data["usuario_admin_id"])
    resultado = consulta.saldo()

    assert isinstance(resultado, Decimal)
    assert resultado == Decimal("1500.0")


# -----------------------------------------------------------------------
# PERS-U-10 — gastos_por_categoria: soma só CONFIRMADA+saida+categoria+mês corrente
# -----------------------------------------------------------------------

def test_pers_u_10_gastos_por_categoria_so_mes_corrente_e_confirmada(session, seed_data):
    """PERS-U-10: gastos_por_categoria('Alimentação') soma apenas transações CONFIRMADA,
    tipo='saida', categoria=Alimentação DO MÊS CORRENTE. Ignora: outro mês, outra categoria,
    status PENDENTE_APROVACAO."""
    agora = datetime.now()

    # Formato de data_hora como string ISO (SQLite armazena como TEXT)
    def ts(dt: datetime) -> str:
        return dt.isoformat(sep=" ", timespec="seconds")

    # Transação válida: mês corrente, CONFIRMADA, saida, Alimentação — DEVE entrar
    session.execute(text(
        "INSERT INTO transacoes "
        "(id_hash, usuario_id, categoria_id, valor, data_hora, tipo, forma, status, origem) "
        "VALUES ('t_valida_1', 'usr_admin', 'cat_alim', 80.0, :dt, 'saida', 'pix', 'CONFIRMADA', 'notificacao')"
    ), {"dt": ts(agora)})

    # 2ª transação válida do mesmo mês — DEVE entrar (total = 130.0)
    session.execute(text(
        "INSERT INTO transacoes "
        "(id_hash, usuario_id, categoria_id, valor, data_hora, tipo, forma, status, origem) "
        "VALUES ('t_valida_2', 'usr_admin', 'cat_alim', 50.0, :dt, 'saida', 'debito', 'CONFIRMADA', 'notificacao')"
    ), {"dt": ts(agora)})

    # Mês anterior — NÃO deve entrar
    import calendar
    mes_ant = agora.month - 1 if agora.month > 1 else 12
    ano_ant = agora.year if agora.month > 1 else agora.year - 1
    dia_ant = min(agora.day, calendar.monthrange(ano_ant, mes_ant)[1])
    dt_mes_ant = agora.replace(year=ano_ant, month=mes_ant, day=dia_ant)
    session.execute(text(
        "INSERT INTO transacoes "
        "(id_hash, usuario_id, categoria_id, valor, data_hora, tipo, forma, status, origem) "
        "VALUES ('t_mes_ant', 'usr_admin', 'cat_alim', 200.0, :dt, 'saida', 'pix', 'CONFIRMADA', 'notificacao')"
    ), {"dt": ts(dt_mes_ant)})

    # Outra categoria (Transporte) no mês corrente — NÃO deve entrar
    session.execute(text(
        "INSERT INTO transacoes "
        "(id_hash, usuario_id, categoria_id, valor, data_hora, tipo, forma, status, origem) "
        "VALUES ('t_outra_cat', 'usr_admin', 'cat_trans', 60.0, :dt, 'saida', 'debito', 'CONFIRMADA', 'notificacao')"
    ), {"dt": ts(agora)})

    # Status PENDENTE_APROVACAO, mês corrente, Alimentação — NÃO deve entrar
    session.execute(text(
        "INSERT INTO transacoes "
        "(id_hash, usuario_id, categoria_id, valor, data_hora, tipo, forma, status, origem) "
        "VALUES ('t_pendente', 'usr_admin', 'cat_alim', 90.0, :dt, 'saida', 'pix', 'PENDENTE_APROVACAO', 'notificacao')"
    ), {"dt": ts(agora)})

    session.commit()

    consulta = SqlAlchemyConsultaFinanceira(session, seed_data["usuario_admin_id"])
    total = consulta.gastos_por_categoria("Alimentação")

    assert isinstance(total, Decimal)
    # Apenas t_valida_1 (80) + t_valida_2 (50) = 130
    assert total == Decimal("130.0")


# -----------------------------------------------------------------------
# PERS-U-11 — pendentes(): lista só PENDENTE_APROVACAO da família
# -----------------------------------------------------------------------

def test_pers_u_11_pendentes_so_da_familia_e_so_pendentes(session, seed_data):
    """PERS-U-11: pendentes() devolve apenas transações PENDENTE_APROVACAO da família do usuário;
    exclui CONFIRMADA e transações de família diferente."""
    # Pendente da família → DEVE aparecer
    session.execute(text(
        "INSERT INTO transacoes "
        "(id_hash, usuario_id, valor, data_hora, tipo, forma, status, origem) "
        "VALUES ('t_pend_fam1', 'usr_admin', 40.0, '2026-06-25 10:00:00', "
        "'saida', 'debito', 'PENDENTE_APROVACAO', 'notificacao')"
    ))
    # Pendente do membro da mesma família → também DEVE aparecer
    session.execute(text(
        "INSERT INTO transacoes "
        "(id_hash, usuario_id, valor, data_hora, tipo, forma, status, origem) "
        "VALUES ('t_pend_membro', 'usr_membro', 25.0, '2026-06-25 11:00:00', "
        "'saida', 'pix', 'PENDENTE_APROVACAO', 'notificacao')"
    ))
    # Confirmada da família → NÃO deve aparecer
    session.execute(text(
        "INSERT INTO transacoes "
        "(id_hash, usuario_id, valor, data_hora, tipo, forma, status, origem) "
        "VALUES ('t_conf_fam1', 'usr_admin', 70.0, '2026-06-24 09:00:00', "
        "'saida', 'debito', 'CONFIRMADA', 'notificacao')"
    ))

    # Usuário de outra família com transação pendente → NÃO deve aparecer
    session.execute(text(
        "INSERT INTO familias (id, nome, saldo_acumulado) VALUES ('fam_outra', 'Outra Família', 0)"
    ))
    session.execute(text(
        "INSERT INTO usuarios (id, familia_id, nome, role) "
        "VALUES ('usr_outra_fam', 'fam_outra', 'Outro Usuário', 'admin')"
    ))
    session.execute(text(
        "INSERT INTO transacoes "
        "(id_hash, usuario_id, valor, data_hora, tipo, forma, status, origem) "
        "VALUES ('t_pend_outra_fam', 'usr_outra_fam', 55.0, '2026-06-25 12:00:00', "
        "'saida', 'debito', 'PENDENTE_APROVACAO', 'notificacao')"
    ))
    session.commit()

    consulta = SqlAlchemyConsultaFinanceira(session, seed_data["usuario_admin_id"])
    pendentes = consulta.pendentes()

    assert isinstance(pendentes, list)
    ids_pendentes = {t.id for t in pendentes}

    # Pendentes da família devem estar presentes
    assert "t_pend_fam1" in ids_pendentes
    assert "t_pend_membro" in ids_pendentes

    # Confirmada e transação de outra família NÃO devem aparecer
    assert "t_conf_fam1" not in ids_pendentes
    assert "t_pend_outra_fam" not in ids_pendentes

    # Todos os itens devem ser Transacao
    for t in pendentes:
        assert isinstance(t, Transacao)
        assert t.status == "PENDENTE_APROVACAO"
