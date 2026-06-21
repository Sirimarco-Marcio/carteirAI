"""Orquestração (LangGraph na implementação final) — fluxo A+B com reflexão + fallback.
Contrato: ORQ-01..13 (docs/tdd/01-contratos-ingestao-ia.md).

Amarra: dedup exato → (LLM extrai → auditor confere)* com reflexão → fallback de provider → decisão.
O provider (Gemini/local) é transparente via `BaseLLM`.
"""

from __future__ import annotations

from typing import Protocol

from carteirai.dedup.dedup import Deduplicador, TransacaoSimilar, hash_exato
from carteirai.dominio.dtos import ItemFila, ResultadoProcessamento, TransacaoExtraida
from carteirai.ia.auditor import auditar
from carteirai.ia.base_llm import BaseLLM, LLMError


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
        max_tentativas: int = 3,  # D8: 1 original + 2 corretivas por provider
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
        # 1. Dedup exato
        h = hash_exato(item.texto_bruto)
        if self._repo.hash_existe(h):
            self._fila.marcar(item.id, "DUPLICADA")
            return ResultadoProcessamento(status="DUPLICADA", tentativas=0)

        # 2. Preparação
        chamadas = 0
        falhas: list[str] | None = None

        # 3. Lista de providers
        providers = [self._principal] + ([self._fallback] if self._fallback else [])

        # 4. Loop por provider
        for provider in providers:
            falhas = None  # reinicia feedback ao trocar de provider
            for _ in range(self._max_tentativas):
                try:
                    extraida = await provider.extrair(item.texto_bruto, feedback=falhas)
                    chamadas += 1
                except LLMError:
                    chamadas += 1
                    break  # abandona este provider, vai pro próximo

                # Data programática
                extraida.data_hora = item.criada_em

                # Auditoria
                res = auditar(item.texto_bruto, extraida)
                falhas_valor = [f for f in res.falhas if "valor" in f.lower()]

                # Caso: valor OK
                if not falhas_valor:
                    dup = self._dedup.soft_match(
                        item.usuario_id,
                        extraida.valor,
                        extraida.estabelecimento,
                        item.criada_em,
                    )
                    self._repo.salvar(item.usuario_id, h, extraida, dup)
                    self._fila.marcar(item.id, "CONCLUIDO")
                    return ResultadoProcessamento(
                        status="PENDENTE_APROVACAO",
                        possivel_duplicata=dup,
                        transacao=extraida,
                        tentativas=chamadas,
                    )

                # Caso: não-transação (sem números monetários no texto)
                if any("sem números" in f for f in falhas_valor):
                    self._fila.marcar(item.id, "CONCLUIDO")
                    return ResultadoProcessamento(status="IGNORADA", tentativas=chamadas)

                # Caso: divergência com número — feedback para próxima tentativa
                falhas = falhas_valor

        # 5. Esgotou tudo
        self._fila.marcar(item.id, "ERRO")
        return ResultadoProcessamento(
            status="ERRO",
            motivo_erro="extração reprovada pelo auditor após todas as tentativas",
            tentativas=chamadas,
        )
