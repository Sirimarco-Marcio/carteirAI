"""LocalSSHAdapter — extração via modelo local na máquina da faculdade (SSH). Implementação
REAL (integração, sem teste unitário com rede)."""

from __future__ import annotations

from carteirai.dominio.dtos import TransacaoExtraida
from carteirai.ia.base_llm import BaseLLM


class LocalSSHAdapter(BaseLLM):
    async def extrair(self, texto: str) -> TransacaoExtraida:
        raise NotImplementedError("Integração: implementar chamada via SSH ao modelo local")
