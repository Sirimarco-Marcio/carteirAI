"""Deduplicação em dois níveis. Contrato: DEDUP-01..10.

- `hash_exato`: identidade da notificação (mesma mensagem reenviada → mesmo hash).
- `ja_processado`: duplicata exata (hash já no histórico) → descarte automático.
- `soft_match`: possível 2ª compra legítima (mesmo usuário+valor+estabelecimento dentro da
  janela) → NUNCA descarta sozinha; marca p/ confirmação especial.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Protocol

from pydantic import BaseModel


class TransacaoSimilar(BaseModel):
    valor: Decimal
    estabelecimento: str
    data_hora: datetime


class HistoricoPort(Protocol):
    """Fonte consultada pelo Deduplicador (real = Neon; testes = FakeTransacaoRepo)."""

    def hash_existe(self, hash: str) -> bool: ...
    def transacoes(self, usuario_id: str) -> list[TransacaoSimilar]: ...


def hash_exato(texto_bruto: str) -> str:
    """Normaliza (trim, colapsa espaços, caixa-baixa) e devolve SHA-256 hex. Contrato: DEDUP-01..03."""
    import hashlib
    import re

    normalizado = re.sub(r"\s+", " ", texto_bruto.strip()).lower()
    return hashlib.sha256(normalizado.encode()).hexdigest()


class Deduplicador:
    def __init__(self, repo: HistoricoPort) -> None:
        self._repo = repo

    def ja_processado(self, hash: str) -> bool:
        """True se o hash já está no histórico (duplicata exata). Contrato: DEDUP-04/05."""
        return self._repo.hash_existe(hash)

    def soft_match(
        self,
        usuario_id: str,
        valor: Decimal,
        estabelecimento: str,
        data_hora: datetime,
        janela_min: int = 10,
    ) -> bool:
        """True se existe transação do MESMO usuário+valor+estabelecimento dentro de `janela_min`
        minutos de `data_hora` (comparação numérica de valor, não string). Contrato: DEDUP-06..10."""
        for t in self._repo.transacoes(usuario_id):
            if (
                t.valor == valor
                and t.estabelecimento == estabelecimento
                and abs((t.data_hora - data_hora).total_seconds()) <= janela_min * 60
            ):
                return True
        return False
