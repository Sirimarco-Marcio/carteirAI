"""Notificador Telegram. Contrato: NOTIF-01..07 (docs/tdd/10-contratos-notificador.md).

Traduz um ResultadoProcessamento em ação no Telegram, reusando ServicoAprovacao.
Apenas PENDENTE_APROVACAO gera envio; os demais status são silenciosos.
"""

from __future__ import annotations

from carteirai.dedup.dedup import hash_exato
from carteirai.dominio.dtos import ResultadoProcessamento, Transacao
from carteirai.fila.fila_ingestao import ItemFilaIngestao
from carteirai.telegram.aprovacao import ServicoAprovacao


class NotificadorTelegram:
    """Notifica o dono da conta no Telegram quando um item da fila requer aprovação."""

    def __init__(self, servico_aprovacao: ServicoAprovacao) -> None:
        self._servico = servico_aprovacao

    def notificar(self, resultado: ResultadoProcessamento, item: ItemFilaIngestao) -> None:
        """Processa o resultado e, se necessário, envia mensagem de aprovação.

        - PENDENTE_APROVACAO: monta Transacao e chama solicitar_aprovacao.
        - IGNORADA / DUPLICADA / ERRO: silêncio total.
        """
        if resultado.status != "PENDENTE_APROVACAO":
            return

        transacao = Transacao(
            id=hash_exato(item.texto_bruto),
            conta_id="",
            usuario_id=item.usuario_id,
            valor=resultado.transacao.valor,
            data_hora=resultado.transacao.data_hora,
            estabelecimento=resultado.transacao.estabelecimento,
            categoria=resultado.transacao.categoria,
            forma=resultado.transacao.forma,
            tipo=resultado.transacao.tipo,
            possivel_duplicata=resultado.possivel_duplicata,
        )

        self._servico.solicitar_aprovacao(transacao)
