"""Aprovação Human-in-the-Loop. Contrato: APROV-01..09 (docs/tdd/03-contratos-telegram.md).

Manda a confirmação pro chat de QUEM fez o gasto (dono da conta). Trata o clique nos botões
([Sim]/[Não]/[Editar] ou, para possível duplicata, [É a mesma]/[É nova]) e confirma/ignora a
transação reusando o ServicoTransacoes. Rejeita callback de quem não é o dono. Idempotente.
"""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel

from carteirai.dominio.dtos import Transacao


class TelegramPort(Protocol):
    """Saída p/ o Telegram (real = Bot API; testes = FakeTelegram que captura envios)."""

    def enviar(
        self, chat_id: str, texto: str, botoes: list[tuple[str, str]] | None = None
    ) -> None: ...


class UsuarioRepo(Protocol):
    def chat_id_de(self, usuario_id: str) -> str | None: ...
    def usuario_de_chat(self, chat_id: str) -> str | None: ...


class TransacaoRepoAprov(Protocol):
    def buscar(self, transacao_id: str) -> Transacao | None: ...


class Callback(BaseModel):
    transacao_id: str
    acao: str          # "sim" | "nao" | "editar" | "mesma" | "nova"
    chat_id: str


class ResultadoCallback(BaseModel):
    tratado: bool
    status: str | None = None     # status final da transação, se mudou
    mensagem: str = ""


class ServicoAprovacao:
    def __init__(
        self,
        telegram: TelegramPort,
        usuario_repo: UsuarioRepo,
        transacao_repo: TransacaoRepoAprov,
        servico_transacoes,
    ) -> None:
        self._tg = telegram
        self._usuarios = usuario_repo
        self._repo = transacao_repo
        self._servico = servico_transacoes

    def solicitar_aprovacao(self, transacao: Transacao) -> None:
        """Envia a mensagem de confirmação ao chat do dono. Teclado normal [Sim][Não][Editar];
        se `possivel_duplicata`, mensagem e teclado de duplicata [É a mesma][É nova]. APROV-01,02,03."""
        raise NotImplementedError("Implementar APROV-01,02,03")

    def tratar_callback(self, callback: Callback) -> ResultadoCallback:
        """Trata o clique. Valida que o chat é o dono (APROV-09); se já resolvida → 'já tratada'
        (APROV-08); senão confirma (sim/nova) ou ignora (não/mesma). APROV-04..07."""
        raise NotImplementedError("Implementar APROV-04..09")
