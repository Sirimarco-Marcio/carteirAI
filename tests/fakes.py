"""Dublês de teste (fakes) compartilhados entre os testes unitários.
Referência: docs/tdd/00-estrategia-tdd.md §4."""

from __future__ import annotations

from carteirai.dominio.dtos import TransacaoExtraida
from carteirai.ia.base_llm import BaseLLM, LLMError


class FakeLLM(BaseLLM):
    """Fake do BaseLLM para testes unitários.

    Modos:
    - programado com TransacaoExtraida: extrair() retorna a transação e incrementa chamadas.
    - modo_erro=True: extrair() lança LLMError (simula timeout/falha de rede).
    """

    def __init__(
        self,
        transacao: TransacaoExtraida | None = None,
        modo_erro: bool = False,
        mensagem_erro: str = "LLM indisponível (fake)",
    ) -> None:
        self._transacao = transacao
        self._modo_erro = modo_erro
        self._mensagem_erro = mensagem_erro
        self.chamadas: int = 0

    async def extrair(self, texto: str) -> TransacaoExtraida:
        self.chamadas += 1
        if self._modo_erro:
            raise LLMError(self._mensagem_erro)
        if self._transacao is None:
            raise LLMError("FakeLLM sem transação programada")
        return self._transacao
