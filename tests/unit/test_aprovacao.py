"""Testes RED para ServicoAprovacao. Contratos: APROV-01..09.

Referência: docs/tdd/03-contratos-telegram.md (bloco APROV).
Cada teste usa AAA (Arrange / Act / Assert).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest

from carteirai.dominio.dtos import Conta, Transacao
from carteirai.financeiro.transacoes import ServicoTransacoes
from carteirai.telegram.aprovacao import Callback, ServicoAprovacao
from tests.fakes import FakeContaRepo, FakeTransacaoStore, FakeTelegram, FakeUsuarioRepo

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DATA_HORA_FIXA = datetime(2024, 3, 15, 10, 0, 0)


def _montar_cenario(possivel_duplicata: bool = False):
    """Monta o cenário base reutilizado por todos os testes APROV.

    Retorna (transacao, store, servico_transacoes, usuario_repo, telegram, servico_aprovacao).
    """
    conta = Conta(
        id="conta-1",
        tipo="corrente",
        saldo_atual=Decimal("1000"),
    )
    conta_repo = FakeContaRepo(contas=[conta])

    store = FakeTransacaoStore()
    transacao = Transacao(
        id="t-abc",
        conta_id="conta-1",
        usuario_id="A",
        valor=Decimal("50"),
        data_hora=_DATA_HORA_FIXA,
        estabelecimento="Mercadinho",
        categoria="Mercado",
        forma="debito",
        tipo="saida",
        status="PENDENTE_APROVACAO",
        possivel_duplicata=possivel_duplicata,
    )
    store.salvar(transacao)

    servico_transacoes = ServicoTransacoes(conta_repo, store)
    usuario_repo = FakeUsuarioRepo({"A": "chat-111"})
    telegram = FakeTelegram()
    servico_aprovacao = ServicoAprovacao(telegram, usuario_repo, store, servico_transacoes)

    return transacao, store, servico_transacoes, usuario_repo, telegram, servico_aprovacao


# ---------------------------------------------------------------------------
# APROV-01: solicitar_aprovacao envia ao chat correto do dono
# ---------------------------------------------------------------------------


def test_aprov_01_solicitar_aprovacao_envia_ao_chat_do_dono():
    # Arrange
    transacao, _, _, _, telegram, servico = _montar_cenario()

    # Act
    servico.solicitar_aprovacao(transacao)

    # Assert
    assert len(telegram.enviados) == 1
    chat_id_destino, _, _ = telegram.enviados[0]
    assert chat_id_destino == "chat-111"


# ---------------------------------------------------------------------------
# APROV-02: transação normal → botões [Sim][Não][Editar]
# ---------------------------------------------------------------------------


def test_aprov_02_transacao_normal_botoes_sim_nao_editar():
    # Arrange
    transacao, _, _, _, telegram, servico = _montar_cenario(possivel_duplicata=False)

    # Act
    servico.solicitar_aprovacao(transacao)

    # Assert
    _, _, botoes = telegram.enviados[0]
    rotulos = [rotulo for rotulo, _ in botoes]
    assert "Sim" in rotulos
    assert "Não" in rotulos
    assert "Editar" in rotulos


# ---------------------------------------------------------------------------
# APROV-03: possivel_duplicata=True → botões [É a mesma][É nova]
# ---------------------------------------------------------------------------


def test_aprov_03_possivel_duplicata_botoes_mesma_nova():
    # Arrange
    transacao, _, _, _, telegram, servico = _montar_cenario(possivel_duplicata=True)

    # Act
    servico.solicitar_aprovacao(transacao)

    # Assert
    _, _, botoes = telegram.enviados[0]
    rotulos = [rotulo for rotulo, _ in botoes]
    assert "É a mesma" in rotulos
    assert "É nova" in rotulos


# ---------------------------------------------------------------------------
# APROV-04: callback "sim" (dono) → CONFIRMADA, tratado=True
# ---------------------------------------------------------------------------


def test_aprov_04_callback_sim_confirma_transacao():
    # Arrange
    transacao, store, _, _, _, servico = _montar_cenario()
    callback = Callback(transacao_id="t-abc", acao="sim", chat_id="chat-111")

    # Act
    resultado = servico.tratar_callback(callback)

    # Assert
    assert resultado.tratado is True
    assert store.buscar("t-abc").status == "CONFIRMADA"


# ---------------------------------------------------------------------------
# APROV-05: callback "nao" (dono) → IGNORADA, tratado=True
# ---------------------------------------------------------------------------


def test_aprov_05_callback_nao_ignora_transacao():
    # Arrange
    transacao, store, _, _, _, servico = _montar_cenario()
    callback = Callback(transacao_id="t-abc", acao="nao", chat_id="chat-111")

    # Act
    resultado = servico.tratar_callback(callback)

    # Assert
    assert resultado.tratado is True
    assert store.buscar("t-abc").status == "IGNORADA"


# ---------------------------------------------------------------------------
# APROV-06: possivel_duplicata + "mesma" → IGNORADA
# ---------------------------------------------------------------------------


def test_aprov_06_duplicata_mesma_ignora_transacao():
    # Arrange
    transacao, store, _, _, _, servico = _montar_cenario(possivel_duplicata=True)
    callback = Callback(transacao_id="t-abc", acao="mesma", chat_id="chat-111")

    # Act
    resultado = servico.tratar_callback(callback)

    # Assert
    assert resultado.tratado is True
    assert store.buscar("t-abc").status == "IGNORADA"


# ---------------------------------------------------------------------------
# APROV-07: "nova" → CONFIRMADA
# ---------------------------------------------------------------------------


def test_aprov_07_duplicata_nova_confirma_transacao():
    # Arrange
    transacao, store, _, _, _, servico = _montar_cenario(possivel_duplicata=True)
    callback = Callback(transacao_id="t-abc", acao="nova", chat_id="chat-111")

    # Act
    resultado = servico.tratar_callback(callback)

    # Assert
    assert resultado.tratado is True
    assert store.buscar("t-abc").status == "CONFIRMADA"


# ---------------------------------------------------------------------------
# APROV-08: transação já resolvida → tratado=False, mensagem "já tratada"
# ---------------------------------------------------------------------------


def test_aprov_08_transacao_ja_confirmada_nao_reprocessa():
    # Arrange
    conta = Conta(id="conta-1", tipo="corrente", saldo_atual=Decimal("1000"))
    conta_repo = FakeContaRepo(contas=[conta])
    store = FakeTransacaoStore()
    transacao = Transacao(
        id="t-abc",
        conta_id="conta-1",
        usuario_id="A",
        valor=Decimal("50"),
        data_hora=_DATA_HORA_FIXA,
        estabelecimento="Mercadinho",
        categoria="Mercado",
        forma="debito",
        tipo="saida",
        status="CONFIRMADA",   # já resolvida
        possivel_duplicata=False,
    )
    store.salvar(transacao)
    servico_transacoes = ServicoTransacoes(conta_repo, store)
    usuario_repo = FakeUsuarioRepo({"A": "chat-111"})
    telegram = FakeTelegram()
    servico = ServicoAprovacao(telegram, usuario_repo, store, servico_transacoes)

    callback = Callback(transacao_id="t-abc", acao="sim", chat_id="chat-111")

    # Act
    resultado = servico.tratar_callback(callback)

    # Assert
    assert resultado.tratado is False
    mensagem_lower = resultado.mensagem.lower()
    assert "já" in mensagem_lower or "tratada" in mensagem_lower
    assert store.buscar("t-abc").status == "CONFIRMADA"


# ---------------------------------------------------------------------------
# APROV-09: callback de chat que não é o dono → rejeitado
# ---------------------------------------------------------------------------


def test_aprov_09_callback_de_outro_chat_rejeitado():
    # Arrange
    transacao, store, _, _, _, servico = _montar_cenario()
    callback = Callback(transacao_id="t-abc", acao="sim", chat_id="chat-OUTRO")

    # Act
    resultado = servico.tratar_callback(callback)

    # Assert
    assert resultado.tratado is False
    assert store.buscar("t-abc").status == "PENDENTE_APROVACAO"
