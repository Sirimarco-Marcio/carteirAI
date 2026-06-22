import pytest
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from carteirai.dominio.dtos import (
    Conta, Transacao, Fatura, FonteRenda, RegistroDia
)
# Os repositórios reais a serem implementados para satisfazer os testes (dublês já foram testados)
from carteirai.infra.sqlalchemy_repos import (
    SqlAlchemyContaRepo,
    SqlAlchemyTransacaoRepo,
    SqlAlchemyFaturaRepo,
    SqlAlchemyFonteRepo,
    SqlAlchemyRegistroDiaRepo
)

# Esquema SQLite simplificado para simular as tabelas do PostgreSQL em memória para os testes.
# Tipos complexos como uuid, jsonb e timestamptz foram convertidos para TEXT ou numéricos nativos.
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

@pytest.fixture
def session():
    """
    Cria um banco SQLite em memória com schema simplificado que
    simula o Postgres e disponibiliza uma Session do SQLAlchemy limpa.
    """
    engine = create_engine("sqlite:///:memory:")
    with engine.connect() as conn:
        for stmt in SQLITE_SCHEMA.split(';'):
            if stmt.strip():
                conn.execute(text(stmt))
        conn.commit()
    
    Session = sessionmaker(bind=engine)
    db_session = Session()
    yield db_session
    db_session.close()

@pytest.fixture
def seed_data(session):
    """Insere dados básicos necessários para vincular contas, transações, etc."""
    session.execute(text("INSERT INTO familias (id, nome) VALUES ('fam1', 'Familia Teste')"))
    session.execute(text("INSERT INTO usuarios (id, familia_id, nome, role) VALUES ('usr1', 'fam1', 'Usuario Teste', 'admin')"))
    session.execute(text("INSERT INTO instituicoes (id, nome, tipo) VALUES ('inst1', 'Banco Teste', 'banco')"))
    session.execute(text("INSERT INTO contas (id, usuario_id, instituicao_id, tipo, saldo_atual) VALUES ('conta_A', 'usr1', 'inst1', 'corrente', 100.0)"))
    session.execute(text("INSERT INTO categorias (id, nome, tipo) VALUES ('cat1', 'Alimentação', 'despesa')"))
    session.commit()
    
    return {
        "usuario_id": "usr1",
        "conta_id": "conta_A",
    }


# =====================================================================
# CONTA-SQL
# =====================================================================

def test_sql_c1(session, seed_data):
    """SQL-C1: Banco com Conta A e Saldo 100 -> buscar(conta_id) Retorna DTO Conta perfeitamente mapeado."""
    repo = SqlAlchemyContaRepo(session)
    conta = repo.buscar(seed_data['conta_id'])
    
    assert conta is not None
    assert conta.id == seed_data['conta_id']
    assert conta.saldo_atual == Decimal("100.0")

def test_sql_c2(session, seed_data):
    """SQL-C2: Conta A com Saldo 100 -> atualizar_saldo(A, 50). Verifica UPDATE efetuado e commitado na tabela contas."""
    repo = SqlAlchemyContaRepo(session)
    repo.atualizar_saldo(seed_data['conta_id'], Decimal("50.0"))
    
    # Conferindo a persistência via consulta crua direto no banco
    saldo_banco = session.execute(text(f"SELECT saldo_atual FROM contas WHERE id = '{seed_data['conta_id']}'")).scalar()
    assert saldo_banco == 50.0

def test_sql_c3(session):
    """SQL-C3: ID de conta inexistente -> buscar(inexistente) Retorna None."""
    repo = SqlAlchemyContaRepo(session)
    conta = repo.buscar("inexistente")
    assert conta is None


# =====================================================================
# TRANS-SQL
# =====================================================================

def test_sql_t1(session, seed_data):
    """SQL-T1: Transação nova (Pendente) -> salvar(transacao). Ocorre INSERT na tabela e origem é inserida corretamente."""
    repo = SqlAlchemyTransacaoRepo(session)
    
    nova_transacao = Transacao(
        id="hash_123",
        conta_id=seed_data['conta_id'],
        usuario_id=seed_data['usuario_id'],
        valor=Decimal("25.50"),
        data_hora=datetime(2026, 6, 21, 14, 30),
        estabelecimento="Padaria",
        categoria="Alimentação",
        forma="debito",
        tipo="saida",
        status="PENDENTE_APROVACAO"
    )
    
    repo.salvar(nova_transacao)
    
    linha = session.execute(text("SELECT id_hash, origem FROM transacoes WHERE id_hash = 'hash_123'")).fetchone()
    assert linha is not None
    assert linha[0] == "hash_123"
    assert linha[1] in ["manual", "notificacao"]

def test_sql_t2(session, seed_data):
    """SQL-T2: Transação existente -> buscar(id_hash). Retorna DTO Transacao perfeitamente mapeado."""
    session.execute(text("""
        INSERT INTO transacoes (id_hash, conta_id, usuario_id, valor, data_hora, estabelecimento, tipo, forma, status, origem)
        VALUES ('hash_456', 'conta_A', 'usr1', 50.0, '2026-06-21 10:00:00', 'Mercado', 'saida', 'debito', 'PENDENTE_APROVACAO', 'manual')
    """))
    session.commit()
    
    repo = SqlAlchemyTransacaoRepo(session)
    transacao = repo.buscar("hash_456")
    
    assert transacao is not None
    assert transacao.id == "hash_456"
    assert transacao.valor == Decimal("50.0")

def test_sql_t3(session, seed_data):
    """SQL-T3: Transação alterada p/ CONFIRMADA -> atualizar(transacao). UPDATE do status na tabela transacoes."""
    session.execute(text("""
        INSERT INTO transacoes (id_hash, conta_id, usuario_id, valor, data_hora, tipo, forma, status, origem)
        VALUES ('hash_789', 'conta_A', 'usr1', 10.0, '2026-06-21 10:00:00', 'saida', 'debito', 'PENDENTE_APROVACAO', 'manual')
    """))
    session.commit()
    
    repo = SqlAlchemyTransacaoRepo(session)
    transacao = repo.buscar("hash_789")
    transacao.status = "CONFIRMADA"
    
    repo.atualizar(transacao)
    
    status_banco = session.execute(text("SELECT status FROM transacoes WHERE id_hash = 'hash_789'")).scalar()
    assert status_banco == "CONFIRMADA"

def test_sql_t4(session, seed_data):
    """SQL-T4: buscar_ultima_confirmada(user_id) -> Retorna a última transação confirmada ordenada por data_hora DESC."""
    session.execute(text("""
        INSERT INTO transacoes (id_hash, conta_id, usuario_id, valor, data_hora, tipo, forma, status, origem)
        VALUES 
        ('t1_conf', 'conta_A', 'usr1', 10, '2026-06-20 10:00:00', 'saida', 'debito', 'CONFIRMADA', 'manual'),
        ('t2_conf', 'conta_A', 'usr1', 20, '2026-06-21 12:00:00', 'saida', 'debito', 'CONFIRMADA', 'manual'),
        ('t3_pend', 'conta_A', 'usr1', 30, '2026-06-22 10:00:00', 'saida', 'debito', 'PENDENTE_APROVACAO', 'manual')
    """))
    session.commit()
    
    repo = SqlAlchemyTransacaoRepo(session)
    ultima = repo.buscar_ultima_confirmada(seed_data['usuario_id'])
    
    assert ultima is not None
    assert ultima.id == 't2_conf'  # t3 é mais recente mas é pendente

def test_sql_t5(session, seed_data):
    """SQL-T5: pendentes() -> SELECT das transações onde status = 'PENDENTE_APROVACAO'."""
    session.execute(text("""
        INSERT INTO transacoes (id_hash, conta_id, usuario_id, valor, data_hora, tipo, forma, status, origem)
        VALUES 
        ('t_pend1', 'conta_A', 'usr1', 10, '2026-06-20 10:00:00', 'saida', 'debito', 'PENDENTE_APROVACAO', 'manual'),
        ('t_conf1', 'conta_A', 'usr1', 20, '2026-06-21 12:00:00', 'saida', 'debito', 'CONFIRMADA', 'manual')
    """))
    session.commit()
    
    repo = SqlAlchemyTransacaoRepo(session)
    lista_pendentes = repo.pendentes()
    
    assert len(lista_pendentes) >= 1
    ids = [t.id for t in lista_pendentes]
    assert 't_pend1' in ids
    assert 't_conf1' not in ids


# =====================================================================
# FAT-SQL
# =====================================================================

def test_sql_f1(session, seed_data):
    """SQL-F1: Mês sem fatura para o cartão A -> buscar_aberta(A, 06, 2026) Retorna None."""
    repo = SqlAlchemyFaturaRepo(session)
    fatura = repo.buscar_aberta(seed_data['conta_id'], 6, 2026)
    assert fatura is None

def test_sql_f2(session, seed_data):
    """SQL-F2: criar(A, 06, 2026) -> INSERT na tabela faturas, retorna DTO Fatura gerado."""
    repo = SqlAlchemyFaturaRepo(session)
    fatura = repo.criar(seed_data['conta_id'], 6, 2026)
    
    assert fatura is not None
    assert fatura.id is not None
    assert fatura.mes == 6
    assert fatura.ano == 2026
    
    banco_id = session.execute(text(f"SELECT id FROM faturas WHERE conta_id = '{seed_data['conta_id']}' AND mes = 6 AND ano = 2026")).scalar()
    assert banco_id is not None

def test_sql_f3(session, seed_data):
    """SQL-F3: Fatura existente -> atualizar(fatura) faz UPDATE na tabela faturas (atualiza valor_total ou status)."""
    session.execute(text(f"INSERT INTO faturas (id, conta_id, mes, ano, valor_total, status) VALUES ('fat_upd', '{seed_data['conta_id']}', 6, 2026, 0.0, 'ABERTA')"))
    session.commit()
    
    repo = SqlAlchemyFaturaRepo(session)
    fatura = Fatura(id='fat_upd', conta_id=seed_data['conta_id'], mes=6, ano=2026, valor_total=Decimal("250.0"), status='FECHADA')
    repo.atualizar(fatura)
    
    linha = session.execute(text("SELECT valor_total, status FROM faturas WHERE id = 'fat_upd'")).fetchone()
    assert linha[0] == 250.0
    assert linha[1] == 'FECHADA'

def test_sql_f4(session, seed_data):
    """SQL-F4: faturas_abertas(user_id) -> Junta faturas e contas e traz faturas ABERTAS do usuario_id."""
    session.execute(text(f"INSERT INTO faturas (id, conta_id, mes, ano, valor_total, status) VALUES ('fat_aberta', '{seed_data['conta_id']}', 6, 2026, 0.0, 'ABERTA')"))
    session.execute(text(f"INSERT INTO faturas (id, conta_id, mes, ano, valor_total, status) VALUES ('fat_fechada', '{seed_data['conta_id']}', 5, 2026, 100.0, 'FECHADA')"))
    session.commit()
    
    repo = SqlAlchemyFaturaRepo(session)
    abertas = repo.faturas_abertas(seed_data['usuario_id'])
    
    assert len(abertas) == 1
    assert abertas[0].id == 'fat_aberta'


# =====================================================================
# RENDA-SQL
# =====================================================================

def test_sql_r1(session, seed_data):
    """SQL-R1: 2 fontes, 1 ativa, 1 inativa -> ativas(usuario_id) Retorna apenas a Fonte DTO ativa."""
    session.execute(text(f"INSERT INTO fontes_renda (id, usuario_id, nome, tipo_calculo, ativa) VALUES ('fnt_ativa', '{seed_data['usuario_id']}', 'Empresa A', 'fixo_mensal', 1)"))
    session.execute(text(f"INSERT INTO fontes_renda (id, usuario_id, nome, tipo_calculo, ativa) VALUES ('fnt_inativa', '{seed_data['usuario_id']}', 'Empresa B', 'por_dia', 0)"))
    session.commit()
    
    repo = SqlAlchemyFonteRepo(session)
    ativas = repo.ativas(seed_data['usuario_id'])
    
    assert len(ativas) == 1
    assert ativas[0].id == 'fnt_ativa'

def test_sql_r2(session, seed_data):
    """SQL-R2: registrar_dia(fonte, data, status) -> Realiza UPSERT (INSERT ON CONFLICT) na tabela registro_dias."""
    session.execute(text(f"INSERT INTO fontes_renda (id, usuario_id, nome, tipo_calculo, ativa) VALUES ('fnt_dias', '{seed_data['usuario_id']}', 'Job', 'por_dia', 1)"))
    session.commit()
    
    repo = SqlAlchemyRegistroDiaRepo(session)
    
    # Primeiro registro deve fazer INSERT normal
    repo.registrar_dia('fnt_dias', date(2026, 6, 21), 'presencial')
    status_1 = session.execute(text("SELECT status FROM registro_dias WHERE fonte_renda_id = 'fnt_dias' AND data = '2026-06-21'")).scalar()
    assert status_1 == 'presencial'
    
    # Segundo registro para a mesma data deve cair no UPSERT (ON CONFLICT DO UPDATE)
    repo.registrar_dia('fnt_dias', date(2026, 6, 21), 'remoto')
    status_2 = session.execute(text("SELECT status FROM registro_dias WHERE fonte_renda_id = 'fnt_dias' AND data = '2026-06-21'")).scalar()
    assert status_2 == 'remoto'

def test_sql_r3(session, seed_data):
    """SQL-R3: do_mes(fonte_id, mes, ano) -> Retorna lista de RegistroDia daquele mês/ano para a fonte."""
    session.execute(text(f"INSERT INTO fontes_renda (id, usuario_id, nome, tipo_calculo, ativa) VALUES ('fnt_mes', '{seed_data['usuario_id']}', 'Job Mes', 'por_dia', 1)"))
    session.execute(text("INSERT INTO registro_dias (id, fonte_renda_id, data, status) VALUES ('reg_1', 'fnt_mes', '2026-06-05', 'presencial')"))
    session.execute(text("INSERT INTO registro_dias (id, fonte_renda_id, data, status) VALUES ('reg_2', 'fnt_mes', '2026-06-20', 'remoto')"))
    session.execute(text("INSERT INTO registro_dias (id, fonte_renda_id, data, status) VALUES ('reg_3', 'fnt_mes', '2026-07-01', 'presencial')")) # Fora do mês
    session.commit()
    
    repo = SqlAlchemyRegistroDiaRepo(session)
    registros_junho = repo.do_mes('fnt_mes', 6, 2026)
    
    assert len(registros_junho) == 2
    datas = {r.data for r in registros_junho}
    assert date(2026, 6, 5) in datas
    assert date(2026, 6, 20) in datas
