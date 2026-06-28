"""Testes RED para a Fila de Ingestão (Neon/SQLAlchemy). Contratos: FILA-N-01..10.
Referência: docs/tdd/08-contratos-fila-ingestao.md"""

from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import create_engine

from carteirai.fila.fila_ingestao import FilaIngestao
from tests.fakes import RelogioFake

# ---------------------------------------------------------------------------
# Constantes e fixtures
# ---------------------------------------------------------------------------

TEMPO_FIXO = datetime(2025, 1, 15, 9, 0, 0)
TEMPO_INICIO = datetime(2025, 1, 15, 8, 0, 0)


@pytest.fixture
def relogio() -> RelogioFake:
    return RelogioFake(TEMPO_FIXO)


@pytest.fixture
def engine():
    """Engine SQLite em memória — isola cada teste."""
    return create_engine("sqlite://")


@pytest.fixture
def fila(engine, relogio: RelogioFake) -> FilaIngestao:
    return FilaIngestao(engine, relogio=relogio)


# ---------------------------------------------------------------------------
# FILA-N-01: enqueue insere PENDENTE
# ---------------------------------------------------------------------------


def test_fila_n_01_enqueue_insere_pendente(
    fila: FilaIngestao, relogio: RelogioFake
) -> None:
    """enqueue() cria item com status PENDENTE, tentativas=0,
    criada_em=relogio(), claimed_em/processada_em=None, e retorna o item com id."""
    # Arrange
    tempo_esperado = relogio.agora()
    data_hora_transacao = datetime(2025, 1, 15, 8, 30, 0)

    # Act
    item = fila.enqueue(
        texto_bruto="pagamento R$50 no Mercado",
        usuario_id="u1",
        origem="notificacao",
        package_name="br.com.banco",
        data_hora=data_hora_transacao,
        client_msg_id="msg-001",
    )

    # Assert
    assert item.id is not None
    assert item.id > 0
    assert item.status == "PENDENTE"
    assert item.texto_bruto == "pagamento R$50 no Mercado"
    assert item.usuario_id == "u1"
    assert item.origem == "notificacao"
    assert item.tentativas == 0
    assert item.criada_em == tempo_esperado
    assert item.claimed_em is None
    assert item.processada_em is None


# ---------------------------------------------------------------------------
# FILA-N-02: enqueue idempotente por client_msg_id
# ---------------------------------------------------------------------------


def test_fila_n_02_enqueue_idempotente_por_client_msg_id(
    fila: FilaIngestao, relogio: RelogioFake
) -> None:
    """Reenviar o mesmo client_msg_id não duplica — retorna o item já existente."""
    # Arrange
    data_hora = datetime(2025, 1, 15, 8, 30, 0)

    # Act — duas chamadas com o mesmo client_msg_id
    item_1 = fila.enqueue(
        texto_bruto="pagamento R$50",
        usuario_id="u1",
        origem="notificacao",
        package_name=None,
        data_hora=data_hora,
        client_msg_id="msg-duplicada",
    )
    item_2 = fila.enqueue(
        texto_bruto="pagamento R$50 (repetido)",
        usuario_id="u1",
        origem="notificacao",
        package_name=None,
        data_hora=data_hora,
        client_msg_id="msg-duplicada",
    )

    # Assert — mesmo id, sem duplicação
    assert item_1.id == item_2.id


def test_fila_n_02_client_msg_id_none_nunca_colide(
    fila: FilaIngestao,
) -> None:
    """client_msg_id=None nunca causa conflito — insere dois itens distintos."""
    # Arrange
    data_hora = datetime(2025, 1, 15, 8, 30, 0)

    # Act — dois enqueues sem client_msg_id
    item_1 = fila.enqueue(
        texto_bruto="compra R$10",
        usuario_id="u1",
        origem="manual",
        package_name=None,
        data_hora=data_hora,
        client_msg_id=None,
    )
    item_2 = fila.enqueue(
        texto_bruto="compra R$20",
        usuario_id="u1",
        origem="manual",
        package_name=None,
        data_hora=data_hora,
        client_msg_id=None,
    )

    # Assert — ids diferentes, ambos inseridos
    assert item_1.id != item_2.id


# ---------------------------------------------------------------------------
# FILA-N-03: claim FIFO
# ---------------------------------------------------------------------------


def test_fila_n_03_claim_fifo_retorna_mais_antigo(
    fila: FilaIngestao, relogio: RelogioFake
) -> None:
    """claim() pega o PENDENTE mais antigo (ordem por id), marca PROCESSANDO
    e seta claimed_em = relogio()."""
    # Arrange
    data_hora = datetime(2025, 1, 15, 8, 30, 0)
    item_a = fila.enqueue("primeiro R$10", "u1", "notificacao", None, data_hora)
    relogio.avancar(segundos=1)
    fila.enqueue("segundo R$20", "u1", "notificacao", None, data_hora)

    # Act
    tempo_claim = relogio.agora()
    item_claimado = fila.claim()

    # Assert — o mais antigo (menor id) é retornado
    assert item_claimado is not None
    assert item_claimado.id == item_a.id
    assert item_claimado.status == "PROCESSANDO"
    assert item_claimado.claimed_em == tempo_claim


# ---------------------------------------------------------------------------
# FILA-N-04: claim atômico
# ---------------------------------------------------------------------------


def test_fila_n_04_claim_atomico_duas_chamadas_nao_retornam_mesmo_item(
    fila: FilaIngestao,
) -> None:
    """Duas chamadas consecutivas de claim() nunca devolvem o mesmo item:
    a 2ª devolve o próximo PENDENTE ou None."""
    # Arrange — apenas um item na fila
    data_hora = datetime(2025, 1, 15, 8, 30, 0)
    fila.enqueue("compra R$30", "u1", "notificacao", None, data_hora)

    # Act
    resultado_1 = fila.claim()
    resultado_2 = fila.claim()

    # Assert — a 2ª chamada não pode devolver o mesmo item
    assert resultado_1 is not None
    assert resultado_2 is None


def test_fila_n_04_claim_atomico_dois_itens_retornam_itens_distintos(
    fila: FilaIngestao,
) -> None:
    """Com dois itens, as duas chamadas devolvem itens distintos."""
    # Arrange
    data_hora = datetime(2025, 1, 15, 8, 30, 0)
    item_a = fila.enqueue("compra A R$10", "u1", "notificacao", None, data_hora)
    item_b = fila.enqueue("compra B R$20", "u1", "notificacao", None, data_hora)

    # Act
    resultado_1 = fila.claim()
    resultado_2 = fila.claim()

    # Assert — ids distintos e em ordem FIFO
    assert resultado_1 is not None
    assert resultado_2 is not None
    assert resultado_1.id != resultado_2.id
    assert resultado_1.id == item_a.id
    assert resultado_2.id == item_b.id


# ---------------------------------------------------------------------------
# FILA-N-05: claim vazio
# ---------------------------------------------------------------------------


def test_fila_n_05_claim_retorna_none_quando_nao_ha_pendente(
    fila: FilaIngestao,
) -> None:
    """claim() devolve None quando não há PENDENTE."""
    # Arrange — fila vazia

    # Act
    resultado = fila.claim()

    # Assert
    assert resultado is None


# ---------------------------------------------------------------------------
# FILA-N-06: marcar final
# ---------------------------------------------------------------------------


def test_fila_n_06_marcar_concluido_grava_status_e_processada_em(
    fila: FilaIngestao, relogio: RelogioFake
) -> None:
    """marcar(item_id, 'CONCLUIDO') grava status CONCLUIDO e seta processada_em = relogio()."""
    # Arrange
    data_hora = datetime(2025, 1, 15, 8, 30, 0)
    fila.enqueue("compra R$40", "u1", "notificacao", None, data_hora)
    item = fila.claim()
    assert item is not None
    relogio.avancar(minutos=2)
    tempo_conclusao = relogio.agora()

    # Act
    fila.marcar(item.id, "CONCLUIDO")

    # Assert — reclama o próximo PENDENTE (não existe, None confirma que o CONCLUIDO não voltou)
    proximo = fila.claim()
    assert proximo is None

    # Verifica processada_em via buscar (ou inspecionando a fila)
    item_final = fila.buscar(item.id)
    assert item_final is not None
    assert item_final.status == "CONCLUIDO"
    assert item_final.processada_em == tempo_conclusao


def test_fila_n_06_marcar_duplicada_grava_status_e_processada_em(
    fila: FilaIngestao, relogio: RelogioFake
) -> None:
    """marcar(item_id, 'DUPLICADA') grava status DUPLICADA e seta processada_em."""
    # Arrange
    data_hora = datetime(2025, 1, 15, 8, 30, 0)
    fila.enqueue("compra R$15", "u1", "notificacao", None, data_hora)
    item = fila.claim()
    assert item is not None
    relogio.avancar(minutos=1)
    tempo_marcacao = relogio.agora()

    # Act
    fila.marcar(item.id, "DUPLICADA")

    # Assert
    item_final = fila.buscar(item.id)
    assert item_final is not None
    assert item_final.status == "DUPLICADA"
    assert item_final.processada_em == tempo_marcacao


def test_fila_n_06_marcar_erro_grava_status_e_processada_em(
    fila: FilaIngestao, relogio: RelogioFake
) -> None:
    """marcar(item_id, 'ERRO') grava status ERRO e seta processada_em."""
    # Arrange
    data_hora = datetime(2025, 1, 15, 8, 30, 0)
    fila.enqueue("compra R$99", "u1", "notificacao", None, data_hora)
    item = fila.claim()
    assert item is not None
    relogio.avancar(minutos=3)
    tempo_marcacao = relogio.agora()

    # Act
    fila.marcar(item.id, "ERRO")

    # Assert
    item_final = fila.buscar(item.id)
    assert item_final is not None
    assert item_final.status == "ERRO"
    assert item_final.processada_em == tempo_marcacao


# ---------------------------------------------------------------------------
# FILA-N-07: reaper recupera órfãos
# ---------------------------------------------------------------------------


def test_fila_n_07_reaper_recupera_orfaos_apos_visibility_timeout(
    fila: FilaIngestao, relogio: RelogioFake
) -> None:
    """recuperar_orfaos() devolve a PENDENTE todo item PROCESSANDO com claimed_em
    mais antigo que visibility_timeout_min (30 min), incrementa tentativas
    e zera claimed_em. Retorna a quantidade recuperada."""
    # Arrange — enfileira e clama um item
    data_hora = datetime(2025, 1, 15, 8, 30, 0)
    fila.enqueue("transação órfã R$60", "u1", "notificacao", None, data_hora)
    item = fila.claim()
    assert item is not None
    tentativas_antes = item.tentativas

    # Avança o relógio além do timeout (30 min + 1 seg)
    relogio.avancar(minutos=31)

    # Act
    quantidade = fila.recuperar_orfaos()

    # Assert
    assert quantidade == 1

    item_recuperado = fila.buscar(item.id)
    assert item_recuperado is not None
    assert item_recuperado.status == "PENDENTE"
    assert item_recuperado.tentativas == tentativas_antes + 1
    assert item_recuperado.claimed_em is None


# ---------------------------------------------------------------------------
# FILA-N-08: reaper preserva recentes
# ---------------------------------------------------------------------------


def test_fila_n_08_reaper_preserva_itens_dentro_da_janela(
    fila: FilaIngestao, relogio: RelogioFake
) -> None:
    """Itens PROCESSANDO com claimed_em dentro da janela (< 30 min)
    não são tocados por recuperar_orfaos()."""
    # Arrange — enfileira e clama
    data_hora = datetime(2025, 1, 15, 8, 30, 0)
    fila.enqueue("transação recente R$25", "u1", "notificacao", None, data_hora)
    item = fila.claim()
    assert item is not None

    # Avança apenas 10 minutos (dentro da janela de 30)
    relogio.avancar(minutos=10)

    # Act
    quantidade = fila.recuperar_orfaos()

    # Assert — nada foi tocado
    assert quantidade == 0

    item_preservado = fila.buscar(item.id)
    assert item_preservado is not None
    assert item_preservado.status == "PROCESSANDO"


# ---------------------------------------------------------------------------
# FILA-N-09: DLQ após max_tentativas
# ---------------------------------------------------------------------------


def test_fila_n_09_dlq_apos_max_tentativas_vira_erro(
    engine, relogio: RelogioFake
) -> None:
    """No recuperar_orfaos(), item órfão que já atingiu max_tentativas (5)
    vai para status='ERRO' (dead-letter) em vez de voltar a PENDENTE."""
    # Arrange — fila com max_tentativas=5
    fila = FilaIngestao(engine, relogio=relogio, max_tentativas=5)
    data_hora = datetime(2025, 1, 15, 8, 30, 0)
    fila.enqueue("transação dlq R$70", "u1", "notificacao", None, data_hora)

    # Simula 5 ciclos: claim → timeout → recuperar_orfaos (4 vezes chegando a 5 tentativas)
    for ciclo in range(5):
        item = fila.claim()
        assert item is not None, f"claim falhou no ciclo {ciclo}"
        relogio.avancar(minutos=31)
        recuperados = fila.recuperar_orfaos()
        # Nos primeiros 4 ciclos o item deve voltar a PENDENTE;
        # no 5º deve ir para ERRO
        if ciclo < 4:
            assert recuperados == 1, f"ciclo {ciclo}: esperava 1 recuperado"
        else:
            # No 5º ciclo, tentativas == 5 → vai para ERRO
            assert recuperados == 0, "5º ciclo: nenhum deve voltar para PENDENTE"

    # Assert — item deve estar em ERRO (DLQ)
    # Buscamos o único item da fila
    item_dlq = fila.claim()
    assert item_dlq is None  # não há PENDENTE

    # Verifica via buscar pelo id do primeiro item
    # (sabemos que o id era o retornado no primeiro claim)
    # Nota: reclama todos os ERRO — método auxiliar ou scan
    itens_erro = fila.listar_por_status("ERRO")
    assert len(itens_erro) == 1
    assert itens_erro[0].status == "ERRO"


def test_fila_n_09_dlq_nao_afeta_itens_com_menos_tentativas(
    engine, relogio: RelogioFake
) -> None:
    """Item com tentativas < max_tentativas continua voltando para PENDENTE."""
    # Arrange
    fila = FilaIngestao(engine, relogio=relogio, max_tentativas=5)
    data_hora = datetime(2025, 1, 15, 8, 30, 0)
    fila.enqueue("transação sem dlq R$80", "u1", "notificacao", None, data_hora)

    # Simula apenas 3 ciclos (< max_tentativas)
    for ciclo in range(3):
        item = fila.claim()
        assert item is not None
        relogio.avancar(minutos=31)
        recuperados = fila.recuperar_orfaos()
        assert recuperados == 1, f"ciclo {ciclo}: esperava recuperar 1"

    # Act — mais um cycle; ainda < 5 tentativas
    item_4 = fila.claim()

    # Assert — ainda é PROCESSANDO (não foi para ERRO)
    assert item_4 is not None
    assert item_4.status == "PROCESSANDO"
    assert item_4.tentativas == 3


# ---------------------------------------------------------------------------
# FILA-N-10: relógio determinístico
# ---------------------------------------------------------------------------


def test_fila_n_10_relogio_deterministico_criada_em(
    fila: FilaIngestao, relogio: RelogioFake
) -> None:
    """Com relogio fixo injetado, criada_em é exatamente o valor do relógio
    (sem chamar datetime.now())."""
    # Arrange
    tempo_exato = relogio.agora()
    data_hora = datetime(2025, 1, 15, 8, 30, 0)

    # Act
    item = fila.enqueue("compra det R$5", "u1", "manual", None, data_hora)

    # Assert
    assert item.criada_em == tempo_exato


def test_fila_n_10_relogio_deterministico_claimed_em(
    fila: FilaIngestao, relogio: RelogioFake
) -> None:
    """Com relogio fixo injetado, claimed_em é exatamente o valor do relógio no momento do claim."""
    # Arrange
    data_hora = datetime(2025, 1, 15, 8, 30, 0)
    fila.enqueue("compra det claim R$5", "u1", "manual", None, data_hora)
    relogio.avancar(minutos=5)
    tempo_claim = relogio.agora()

    # Act
    item = fila.claim()

    # Assert
    assert item is not None
    assert item.claimed_em == tempo_claim


def test_fila_n_10_relogio_deterministico_processada_em(
    fila: FilaIngestao, relogio: RelogioFake
) -> None:
    """Com relogio fixo injetado, processada_em é exatamente o valor do relógio no marcar()."""
    # Arrange
    data_hora = datetime(2025, 1, 15, 8, 30, 0)
    fila.enqueue("compra det proc R$5", "u1", "manual", None, data_hora)
    item = fila.claim()
    assert item is not None
    relogio.avancar(minutos=10)
    tempo_conclusao = relogio.agora()

    # Act
    fila.marcar(item.id, "CONCLUIDO")

    # Assert
    item_final = fila.buscar(item.id)
    assert item_final is not None
    assert item_final.processada_em == tempo_conclusao
