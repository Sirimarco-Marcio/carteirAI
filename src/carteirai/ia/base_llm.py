"""Porta `BaseLLM` (Ports & Adapters) + factory por env. Contrato: LLM-01..07."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod

from carteirai.dominio.dtos import TransacaoExtraida


class LLMError(Exception):
    """Falha ao extrair via LLM (timeout, resposta inválida, etc.)."""


class BaseLLM(ABC):
    @abstractmethod
    async def extrair(self, texto: str) -> TransacaoExtraida:
        """Extrai uma TransacaoExtraida de texto livre. Pode lançar LLMError."""
        raise NotImplementedError


def resolver_llm(provider: str | None = None) -> BaseLLM:
    """Factory: escolhe o adapter por `provider` (ou env LLM_PROVIDER).
    `gemini` -> GeminiAdapter; `local` -> LocalSSHAdapter; outro -> ValueError.
    Contrato: LLM-01..03."""
    raise NotImplementedError("Implementar LLM-01..03 (resolver_llm)")
