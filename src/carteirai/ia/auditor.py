"""Auditor anti-alucinação (RegEx): garante que valor e data extraídos existem
literalmente no texto bruto. Este é o "checker" sobre a saída do LLM. Contrato: AUD-01..06."""

from __future__ import annotations

from carteirai.dominio.dtos import ResultadoAuditoria, TransacaoExtraida


def auditar(texto_bruto: str, extraida: TransacaoExtraida) -> ResultadoAuditoria:
    """Confere que `extraida.valor` e `extraida.data_hora` aparecem em `texto_bruto`
    (normalizando vírgula/ponto e separador de milhar). Contrato: AUD-01..06."""
    raise NotImplementedError("Implementar AUD-01..06 (auditar)")
