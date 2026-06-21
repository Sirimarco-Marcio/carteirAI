"""Dublês de teste (fakes) compartilhados entre os testes unitários.
Referência: docs/tdd/00-estrategia-tdd.md §4."""

from __future__ import annotations

from datetime import datetime, timedelta

from carteirai.dedup.dedup import HistoricoPort, TransacaoSimilar
from carteirai.dominio.dtos import TransacaoExtraida
from carteirai.ia.base_llm import BaseLLM, LLMError


class RelogioFake:
    """Relógio controlável para testes determinísticos.
    Referência: docs/tdd/00-estrategia-tdd.md §4 (RelogioFake).

    Uso:
        relogio = RelogioFake(datetime(2024, 1, 1, 12, 0, 0))
        relogio.agora()  # datetime(2024, 1, 1, 12, 0, 0)
        relogio.avancar(minutos=5)
        relogio.agora()  # datetime(2024, 1, 1, 12, 5, 0)

    Também é callable: relogio() == relogio.agora()
    """

    def __init__(self, inicio: datetime | None = None) -> None:
        self._agora = inicio or datetime(2024, 1, 1, 12, 0, 0)

    def agora(self) -> datetime:
        return self._agora

    def __call__(self) -> datetime:
        return self._agora

    def avancar(self, segundos: int = 0, minutos: int = 0, horas: int = 0) -> None:
        """Avança o relógio pelo delta especificado."""
        self._agora += timedelta(seconds=segundos, minutes=minutos, hours=horas)

    def definir(self, novo_tempo: datetime) -> None:
        """Define o tempo diretamente."""
        self._agora = novo_tempo


class FakeTransacaoRepo:
    """Implementa HistoricoPort para testes unitários de Deduplicador.
    Referência: docs/tdd/00-estrategia-tdd.md §4 (FakeTransacaoRepo).

    Args:
        hashes: conjunto de hashes já processados.
        transacoes_por_usuario: mapeamento usuario_id -> lista de TransacaoSimilar.
    """

    def __init__(
        self,
        hashes: set[str] | None = None,
        transacoes_por_usuario: dict[str, list[TransacaoSimilar]] | None = None,
    ) -> None:
        self._hashes: set[str] = hashes or set()
        self._transacoes: dict[str, list[TransacaoSimilar]] = (
            transacoes_por_usuario or {}
        )

    def hash_existe(self, hash: str) -> bool:
        return hash in self._hashes

    def transacoes(self, usuario_id: str) -> list[TransacaoSimilar]:
        return self._transacoes.get(usuario_id, [])


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
