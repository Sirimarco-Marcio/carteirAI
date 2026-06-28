"""Testes RED para NotificadorTelegram. Contratos: NOTIF-01..07.

Referência: docs/tdd/10-contratos-notificador.md.
A classe-alvo NÃO existe ainda; o import abaixo levanta ImportError → fase RED.
Cada teste segue AAA (Arrange / Act / Assert).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest

from carteirai.dedup.dedup import hash_exato
from carteirai.dominio.dtos import ResultadoProcessamento, TransacaoExtraida
from carteirai.fila.fila_ingestao import ItemFilaIngestao
from carteirai.telegram.aprovacao import ServicoAprovacao
from tests.fakes import FakeTelegram, FakeUsuarioRepo

# --- classe-alvo (ainda não existe — import falha em RED) ---
from carteirai.telegram.notificador import NotificadorTelegram  # noqa: E402

# ---------------------------------------------------------------------------
# Constantes de teste
# ---------------------------------------------------------------------------

_DATA_HORA_FIXA = datetime(2024, 3, 15, 10, 0, 0)
_TEXTO_BRUTO = "Compra no iFood R$ 45,90"
_USUARIO_ID = "u1"
_CHAT_ID = "chat-99"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _montar_item(texto_bruto: str = _TEXTO_BRUTO) -> ItemFilaIngestao:
    """Cria um ItemFilaIngestao com os campos obrigatórios preenchidos."""
    agora = datetime(2024, 3, 15, 9, 55, 0)
    return ItemFilaIngestao(
        id=1,
        id_hash="hash-item-1",
        texto_bruto=texto_bruto,
        usuario_id=_USUARIO_ID,
        package_name=None,
        origem="notificacao",
        status="PROCESSANDO",
        tentativas=0,
        data_hora=_DATA_HORA_FIXA,
        client_msg_id=None,
        criada_em=agora,
        claimed_em=None,
        processada_em=None,
    )


def _montar_resultado(
    status: str = "PENDENTE_APROVACAO",
    possivel_duplicata: bool = False,
) -> ResultadoProcessamento:
    """Cria um ResultadoProcessamento com uma TransacaoExtraida preenchida."""
    transacao = TransacaoExtraida(
        valor=Decimal("45.90"),
        data_hora=_DATA_HORA_FIXA,
        estabelecimento="iFood",
        categoria="Alimentação",
        forma="credito",
        tipo="saida",
    )
    return ResultadoProcessamento(
        status=status,  # type: ignore[arg-type]
        possivel_duplicata=possivel_duplicata,
        transacao=transacao,
    )


def _montar_notificador() -> tuple[NotificadorTelegram, FakeTelegram]:
    """Instancia NotificadorTelegram com colaboradores fake; devolve (notificador, telegram)."""
    telegram = FakeTelegram()
    usuario_repo = FakeUsuarioRepo({_USUARIO_ID: _CHAT_ID})
    servico_aprovacao = ServicoAprovacao(telegram, usuario_repo, None, None)
    notificador = NotificadorTelegram(servico_aprovacao)
    return notificador, telegram


# ---------------------------------------------------------------------------
# NOTIF-01: aprovação normal → 1 envio ao chat do dono, botão "sim:<hash>"
# ---------------------------------------------------------------------------


def test_NOTIF_01_pendente_aprovacao_envia_mensagem_com_botao_sim():
    """NOTIF-01: status PENDENTE_APROVACAO sem duplicata → exatamente 1 envio
    ao chat do dono e pelo menos um botão cujo callback_data começa com 'sim:'."""
    notificador, telegram = _montar_notificador()
    item = _montar_item()
    resultado = _montar_resultado(status="PENDENTE_APROVACAO", possivel_duplicata=False)

    notificador.notificar(resultado, item)

    assert len(telegram.enviados) == 1
    chat_id_enviado, _texto, botoes = telegram.enviados[0]
    assert chat_id_enviado == _CHAT_ID
    assert botoes is not None
    dados_botoes = [data for _label, data in botoes]
    assert any(d.startswith("sim:") for d in dados_botoes), (
        f"Esperava botão com callback_data 'sim:<hash>', recebeu: {dados_botoes}"
    )


# ---------------------------------------------------------------------------
# NOTIF-02: possível duplicata → botões "mesma:<hash>" e "nova:<hash>"
# ---------------------------------------------------------------------------


def test_NOTIF_02_possivel_duplicata_envia_botoes_mesma_e_nova():
    """NOTIF-02: possivel_duplicata=True → botões 'É a mesma' e 'É nova'
    (callback_data começando com 'mesma:' e 'nova:')."""
    notificador, telegram = _montar_notificador()
    item = _montar_item()
    resultado = _montar_resultado(status="PENDENTE_APROVACAO", possivel_duplicata=True)

    notificador.notificar(resultado, item)

    assert len(telegram.enviados) == 1
    _chat_id, _texto, botoes = telegram.enviados[0]
    assert botoes is not None
    dados_botoes = [data for _label, data in botoes]
    assert any(d.startswith("mesma:") for d in dados_botoes), (
        f"Esperava botão 'mesma:<hash>', recebeu: {dados_botoes}"
    )
    assert any(d.startswith("nova:") for d in dados_botoes), (
        f"Esperava botão 'nova:<hash>', recebeu: {dados_botoes}"
    )


# ---------------------------------------------------------------------------
# NOTIF-03: IGNORADA → silêncio total
# ---------------------------------------------------------------------------


def test_NOTIF_03_ignorada_nao_envia_mensagem():
    """NOTIF-03: status IGNORADA → nenhum envio ao Telegram."""
    notificador, telegram = _montar_notificador()
    item = _montar_item()
    resultado = _montar_resultado(status="IGNORADA")

    notificador.notificar(resultado, item)

    assert telegram.enviados == [], (
        f"Esperava silêncio para IGNORADA, mas houve envios: {telegram.enviados}"
    )


# ---------------------------------------------------------------------------
# NOTIF-04: DUPLICADA → silêncio total
# ---------------------------------------------------------------------------


def test_NOTIF_04_duplicada_nao_envia_mensagem():
    """NOTIF-04: status DUPLICADA → nenhum envio ao Telegram."""
    notificador, telegram = _montar_notificador()
    item = _montar_item()
    resultado = _montar_resultado(status="DUPLICADA")

    notificador.notificar(resultado, item)

    assert telegram.enviados == [], (
        f"Esperava silêncio para DUPLICADA, mas houve envios: {telegram.enviados}"
    )


# ---------------------------------------------------------------------------
# NOTIF-05: ERRO → silêncio total
# ---------------------------------------------------------------------------


def test_NOTIF_05_erro_nao_envia_mensagem():
    """NOTIF-05: status ERRO → nenhum envio ao Telegram."""
    notificador, telegram = _montar_notificador()
    item = _montar_item()
    resultado = _montar_resultado(status="ERRO")

    notificador.notificar(resultado, item)

    assert telegram.enviados == [], (
        f"Esperava silêncio para ERRO, mas houve envios: {telegram.enviados}"
    )


# ---------------------------------------------------------------------------
# NOTIF-06: id nos botões = hash_exato(item.texto_bruto)
# ---------------------------------------------------------------------------


def test_NOTIF_06_id_nos_botoes_e_hash_exato_do_texto_bruto():
    """NOTIF-06: o hash presente no callback_data dos botões deve ser
    exatamente hash_exato(item.texto_bruto)."""
    notificador, telegram = _montar_notificador()
    item = _montar_item()
    resultado = _montar_resultado(status="PENDENTE_APROVACAO", possivel_duplicata=False)

    notificador.notificar(resultado, item)

    hash_esperado = hash_exato(item.texto_bruto)
    _chat_id, _texto, botoes = telegram.enviados[0]
    assert botoes is not None
    dados_botoes = [data for _label, data in botoes]
    assert any(hash_esperado in d for d in dados_botoes), (
        f"Esperava hash '{hash_esperado}' no callback_data dos botões, recebeu: {dados_botoes}"
    )


# ---------------------------------------------------------------------------
# NOTIF-07: envio vai ao chat_id do usuário dono do item
# ---------------------------------------------------------------------------


def test_NOTIF_07_envio_vai_ao_chat_do_dono():
    """NOTIF-07: o envio é direcionado ao chat_id resolvido a partir de
    item.usuario_id (via UsuarioRepo), não a um chat fixo."""
    notificador, telegram = _montar_notificador()
    item = _montar_item()
    resultado = _montar_resultado(status="PENDENTE_APROVACAO", possivel_duplicata=False)

    notificador.notificar(resultado, item)

    assert len(telegram.enviados) == 1
    chat_id_enviado, _texto, _botoes = telegram.enviados[0]
    assert chat_id_enviado == _CHAT_ID, (
        f"Esperava envio para '{_CHAT_ID}' (chat do usuário '{_USUARIO_ID}'), "
        f"mas foi enviado para '{chat_id_enviado}'"
    )
