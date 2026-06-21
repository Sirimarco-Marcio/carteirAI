"""Auditor anti-alucinação (RegEx): garante que valor e data extraídos existem
literalmente no texto bruto. Este é o "checker" sobre a saída do LLM. Contrato: AUD-01..06."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from carteirai.dominio.dtos import ResultadoAuditoria, TransacaoExtraida


def _extrair_decimais_do_texto(texto: str) -> list[Decimal]:
    """Extrai todos os tokens numéricos monetários do texto e os normaliza para Decimal.

    Regras de normalização (ambiguidade BR/US):
    - tem '.' e ',': '.' é milhar, ',' é decimal  ex: 1.299,00 → 1299.00
    - só ',':         ',' é decimal                ex: 49,90   → 49.90
    - só '.':
        - dígitos após último '.' == 3 (sem vírgula): '.' é milhar  ex: 1.299 → 1299
        - senão:                                      '.' é decimal  ex: 49.90 → 49.90
    """
    # Captura tokens como 1.299,00  |  49,90  |  49.90  |  1.299  |  100
    padrao = re.compile(r'\d[\d.,]*\d|\d')
    tokens = padrao.findall(texto)

    decimais: list[Decimal] = []
    for token in tokens:
        tem_ponto = '.' in token
        tem_virgula = ',' in token

        try:
            if tem_ponto and tem_virgula:
                # BR: 1.299,00 → remover pontos, vírgula vira ponto
                normalizado = token.replace('.', '').replace(',', '.')
            elif tem_virgula:
                # BR decimal: 49,90 → 49.90
                normalizado = token.replace(',', '.')
            elif tem_ponto:
                # Ambíguo: verificar quantos dígitos após o último ponto
                pos_ultimo_ponto = token.rfind('.')
                digitos_apos = token[pos_ultimo_ponto + 1:]
                if len(digitos_apos) == 3:
                    # Trata como milhar: 1.299 → 1299
                    normalizado = token.replace('.', '')
                else:
                    # Trata como decimal: 49.90 → 49.90
                    normalizado = token
            else:
                # Número inteiro: 100
                normalizado = token

            decimais.append(Decimal(normalizado))
        except InvalidOperation:
            # Token malformado — ignora
            continue

    return decimais


def auditar(texto_bruto: str, extraida: TransacaoExtraida) -> ResultadoAuditoria:
    """Confere que `extraida.valor` e `extraida.data_hora` aparecem em `texto_bruto`
    (normalizando vírgula/ponto e separador de milhar). Contrato: AUD-01..06."""
    falhas: list[str] = []

    # --- Verificação de valor ---
    numeros_no_texto = _extrair_decimais_do_texto(texto_bruto)

    if not numeros_no_texto:
        falhas.append("valor não encontrado no texto (sem números monetários)")
    else:
        valor_encontrado = any(n == extraida.valor for n in numeros_no_texto)
        if not valor_encontrado:
            falhas.append(
                f"valor {extraida.valor} não encontrado no texto "
                f"(encontrados: {numeros_no_texto})"
            )

    # --- Verificação de data ---
    data = extraida.data_hora
    representacoes = [
        data.strftime("%d/%m"),
        data.strftime("%d/%m/%Y"),
        data.strftime("%d/%m/%y"),
    ]
    data_encontrada = any(rep in texto_bruto for rep in representacoes)
    if not data_encontrada:
        falhas.append(
            f"data {data.strftime('%d/%m/%Y')} não encontrada no texto"
        )

    return ResultadoAuditoria(ok=len(falhas) == 0, falhas=falhas)
