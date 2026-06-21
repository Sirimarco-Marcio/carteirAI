"""GeminiAdapter — extração via API do Gemini. Implementação REAL (integração, sem teste
unitário com rede). Só conformidade de interface via FakeLLM nos unitários (LLM-07)."""

from __future__ import annotations

from carteirai.dominio.dtos import TransacaoExtraida
from carteirai.ia.base_llm import BaseLLM


class GeminiAdapter(BaseLLM):
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash") -> None:
        self.api_key = api_key
        self.model = model

    async def extrair(self, texto: str) -> TransacaoExtraida:
        raise NotImplementedError("Integração: implementar chamada à API do Gemini")
