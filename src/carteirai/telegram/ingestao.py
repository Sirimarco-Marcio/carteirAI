"""Roteamento de ingestão (webhook/polling). Contrato: ING-01..04 (docs/tdd/03).

Transforma um update do Telegram em item da fila (notificação) OU roteia pro CMD (comando).
Ignora chat desconhecido (segurança). Dedup exato evita item duplicado quando o Telegram
entrega o mesmo update 2× (mesmo `update_id`).
"""

from __future__ import annotations

from typing import Literal, Protocol

from pydantic import BaseModel

from carteirai.telegram.aprovacao import UsuarioRepo


class Update(BaseModel):
    chat_id: str
    texto: str
    update_id: int


ResultadoIngestao = Literal["ENFILEIRADO", "COMANDO", "IGNORADO", "DUPLICADO"]


class FilaPort(Protocol):
    def enqueue(self, texto_bruto: str, usuario_id: str, origem: str): ...


class CmdHandler(Protocol):
    def handle(self, update: Update) -> None: ...


class RoteadorIngestao:
    def __init__(self, usuario_repo: UsuarioRepo, fila: FilaPort, cmd_handler: CmdHandler) -> None:
        self._usuarios = usuario_repo
        self._fila = fila
        self._cmd = cmd_handler
        self._vistos: set[int] = set()

    def processar(self, update: Update) -> ResultadoIngestao:
        """ING-01..04: dedup por update_id → chat conhecido? → comando vs notificação."""
        if update.update_id in self._vistos:
            return "DUPLICADO"
        usuario_id = self._usuarios.usuario_de_chat(update.chat_id)
        if usuario_id is None:
            return "IGNORADO"
        self._vistos.add(update.update_id)
        if update.texto.startswith("/"):
            self._cmd.handle(update)
            return "COMANDO"
        self._fila.enqueue(update.texto, usuario_id, "notificacao")
        return "ENFILEIRADO"
