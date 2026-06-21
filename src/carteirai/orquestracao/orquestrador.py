"""Orquestração (LangGraph na implementação final) — fluxo A+B com reflexão + fallback.
Contrato: ORQ-01..13 (docs/tdd/01-contratos-ingestao-ia.md).

Amarra: dedup exato → (LLM extrai → auditor confere)* com reflexão → fallback de provider → decisão.
O provider (Gemini/local) é transparente via `BaseLLM`.
"""

from __future__ import annotations

from typing import Protocol

from carteirai.dedup.dedup import Deduplicador, TransacaoSimilar
from carteirai.dominio.dtos import ItemFila, ResultadoProcessamento, TransacaoExtraida
from carteirai.ia.base_llm import BaseLLM


class RepoTransacoes(Protocol):
    """Porta de persistência/consulta de transações (real = Neon; testes = fake)."""

    def hash_existe(self, hash: str) -> bool: ...
    def transacoes(self, usuario_id: str) -> list[TransacaoSimilar]: ...
    def salvar(
        self,
        usuario_id: str,
        hash: str,
        transacao: TransacaoExtraida,
        possivel_duplicata: bool,
    ) -> None: ...


class Orquestrador:
    def __init__(
        self,
        fila,
        transacao_repo: RepoTransacoes,
        llm_principal: BaseLLM,
        llm_fallback: BaseLLM | None = None,
        max_tentativas: int = 2,
    ) -> None:
        self._fila = fila
        self._repo = transacao_repo
        self._dedup = Deduplicador(transacao_repo)
        self._principal = llm_principal
        self._fallback = llm_fallback
        self._max_tentativas = max_tentativas

    async def processar(self, item: ItemFila) -> ResultadoProcessamento:
        """Processa um item da fila. Ver o laço documentado no contrato (ORQ-01..13):
        dedup exato → reflexão (até max_tentativas) → fallback de provider → IGNORADA/ERRO/PENDENTE_APROVACAO,
        sempre marcando a fila (CONCLUIDO/DUPLICADA/ERRO)."""
        raise NotImplementedError("Implementar ORQ-01..13")
