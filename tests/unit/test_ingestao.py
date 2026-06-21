"""Testes RED — Roteamento de ingestão. Contratos ING-01..04.

Referência: docs/tdd/03-contratos-telegram.md §WEBHOOK/POLL.
"""

from tests.fakes import FakeCmd, FakeFilaIngestao, FakeUsuarioRepo
from carteirai.telegram.ingestao import RoteadorIngestao, Update


def _roteador():
    """Monta o conjunto de fakes e retorna (roteador, fila, cmd)."""
    usuario_repo = FakeUsuarioRepo({"A": "chat-1"})
    fila = FakeFilaIngestao()
    cmd = FakeCmd()
    roteador = RoteadorIngestao(usuario_repo, fila, cmd)
    return roteador, fila, cmd


# ---------------------------------------------------------------------------
# ING-01: mensagem de texto comum → enfileirada como notificação
# ---------------------------------------------------------------------------


def test_ing_01_mensagem_texto_enfileira_como_notificacao():
    # Arrange
    roteador, fila, cmd = _roteador()
    update = Update(chat_id="chat-1", texto="compra R$10", update_id=1)

    # Act
    resultado = roteador.processar(update)

    # Assert
    assert resultado == "ENFILEIRADO"
    assert fila.enfileirados == [("compra R$10", "A", "notificacao")]


# ---------------------------------------------------------------------------
# ING-02: comando → roteado pro CMD, não enfileirado
# ---------------------------------------------------------------------------


def test_ing_02_comando_roteia_para_cmd_nao_enfileira():
    # Arrange
    roteador, fila, cmd = _roteador()
    update = Update(chat_id="chat-1", texto="/saldo", update_id=2)

    # Act
    resultado = roteador.processar(update)

    # Assert
    assert resultado == "COMANDO"
    assert len(cmd.recebidos) == 1
    assert fila.enfileirados == []


# ---------------------------------------------------------------------------
# ING-03: chat desconhecido → ignorado por segurança
# ---------------------------------------------------------------------------


def test_ing_03_chat_desconhecido_ignorado():
    # Arrange
    roteador, fila, cmd = _roteador()
    update = Update(chat_id="chat-DESCONHECIDO", texto="oi", update_id=3)

    # Act
    resultado = roteador.processar(update)

    # Assert
    assert resultado == "IGNORADO"
    assert fila.enfileirados == []
    assert cmd.recebidos == []


# ---------------------------------------------------------------------------
# ING-04: mesmo update_id entregue 2× → dedup exato, só 1 item na fila
# ---------------------------------------------------------------------------


def test_ing_04_dedup_mesmo_update_id_nao_enfileira_duas_vezes():
    # Arrange
    roteador, fila, cmd = _roteador()
    update = Update(chat_id="chat-1", texto="compra", update_id=4)

    # Act
    resultado1 = roteador.processar(update)
    resultado2 = roteador.processar(update)

    # Assert
    assert resultado1 == "ENFILEIRADO"
    assert resultado2 == "DUPLICADO"
    assert len(fila.enfileirados) == 1
