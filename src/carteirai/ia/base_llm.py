"""Porta `BaseLLM` (Ports & Adapters) + factory por env. Contrato: LLM-01..07."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod

from carteirai.dominio.dtos import TransacaoExtraida


class LLMError(Exception):
    """Falha ao extrair via LLM (timeout, resposta inválida, etc.)."""


class BaseLLM(ABC):
    @abstractmethod
    async def extrair(self, texto: str, feedback: list[str] | None = None) -> TransacaoExtraida:
        """Extrai uma TransacaoExtraida de texto livre. Pode lançar LLMError.
        `feedback` (reflexão): falhas do auditor da tentativa anterior, p/ o adapter corrigir."""
        raise NotImplementedError


def resolver_llm(provider: str | None = None) -> BaseLLM:
    """Factory: escolhe o adapter por `provider` (ou env LLM_PROVIDER).
    `gemini` -> GeminiAdapter; `local` -> LocalSSHAdapter; outro -> ValueError.
    Contrato: LLM-01..03."""
    if provider is None:
        provider = os.getenv("LLM_PROVIDER")

    if provider == "gemini":
        from carteirai.ia.gemini_adapter import GeminiAdapter  # evita import circular
        return GeminiAdapter(api_key=os.getenv("GEMINI_API_KEY", ""))
    elif provider == "local":
        from carteirai.ia.local_ssh_adapter import LocalSSHAdapter  # evita import circular
        return LocalSSHAdapter()
    else:
        raise ValueError(
            f"Provider LLM inválido: {provider!r}. Use 'gemini' ou 'local'."
        )
