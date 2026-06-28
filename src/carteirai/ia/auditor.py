"""Auditor anti-alucinação (RegEx): garante que valor e data extraídos existem
literalmente no texto bruto. Este é o "checker" sobre a saída do LLM. Contrato: AUD-01..13."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from carteirai.dominio.dtos import ResultadoAuditoria, TransacaoExtraida

# ---------------------------------------------------------------------------
# Palavras-chave por categoria — tipo (AUD-07..09)
# ---------------------------------------------------------------------------

_PISTAS_TIPO: dict[str, list[str]] = {
    "entrada": [
        "você recebeu",
        "recebeu",
        "recebido",
        "recebida",
        "depósito",
        "deposito",
        "creditado",
        "crédito em conta",
        "entrada de",
    ],
    "saida": [
        "compra",
        "você pagou",
        "pagou",
        "pagamento",
        "saque",
        "você enviou",
        "enviou",
        "débito de",
        "debitado",
        "gasto",
    ],
}

# ---------------------------------------------------------------------------
# Palavras-chave por categoria — forma (AUD-10..12)
# ATENÇÃO: "crédito" sozinho NÃO está aqui — colide com "crédito em conta" (entrada).
# ---------------------------------------------------------------------------

_PISTAS_FORMA: dict[str, list[str]] = {
    "credito": [
        "no crédito",
        "cartão de crédito",
        "compra no crédito",
        "parcelado",
        "parcelas",
        "fatura",
    ],
    "debito": [
        "no débito",
        "cartão de débito",
        "débito automático",
        "compra no débito",
    ],
    "pix": [
        "pix",
    ],
    "dinheiro": [
        "dinheiro",
        "espécie",
        "especie",
    ],
}


def _categorias_evidenciadas(texto: str, pistas: dict[str, list[str]]) -> set[str]:
    """Retorna o conjunto de categorias cujas palavras-chave aparecem no texto (case-insensitive).

    A busca é por substring e respeita a ordem das pistas dentro de cada categoria
    (mais longas são verificadas antes para evitar falsos positivos via substrings menores).
    """
    texto_lower = texto.lower()
    encontradas: set[str] = set()
    for categoria, palavras in pistas.items():
        for palavra in palavras:
            if palavra.lower() in texto_lower:
                encontradas.add(categoria)
                break  # basta uma pista para confirmar a categoria
    return encontradas


def _categorias_tipo_no_texto(texto: str) -> set[str]:
    """Retorna o conjunto de categorias de tipo (entrada/saida) evidenciadas no texto."""
    return _categorias_evidenciadas(texto, _PISTAS_TIPO)


def _categorias_forma_no_texto(texto: str) -> set[str]:
    """Retorna o conjunto de categorias de forma (credito/debito/pix/dinheiro) evidenciadas."""
    return _categorias_evidenciadas(texto, _PISTAS_FORMA)


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
    """Confere que `extraida.valor`, `extraida.data_hora`, `extraida.tipo` e
    `extraida.forma` são coerentes com `texto_bruto`. Contrato: AUD-01..13.

    Comportamento de tipo/forma (conservador):
    - Monta o conjunto de categorias evidenciadas pelas palavras-chave do contrato.
    - Se **exatamente uma** categoria for evidenciada e ela for **diferente** da extraída
      → acrescenta falha mencionando "tipo" (ou "forma").
    - Zero ou mais de uma categoria evidenciada → não acusa (confia na IA).
    """
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

    # --- Verificação de tipo (AUD-07..09) ---
    categorias_tipo = _categorias_tipo_no_texto(texto_bruto)
    if len(categorias_tipo) == 1:
        categoria_tipo = next(iter(categorias_tipo))
        if categoria_tipo != extraida.tipo:
            falhas.append(
                f"tipo divergente: texto indica '{categoria_tipo}', "
                f"extraída diz '{extraida.tipo}'"
            )

    # --- Verificação de forma (AUD-10..12) ---
    categorias_forma = _categorias_forma_no_texto(texto_bruto)
    if len(categorias_forma) == 1:
        categoria_forma = next(iter(categorias_forma))
        if categoria_forma != extraida.forma:
            falhas.append(
                f"forma divergente: texto indica '{categoria_forma}', "
                f"extraída diz '{extraida.forma}'"
            )

    return ResultadoAuditoria(ok=len(falhas) == 0, falhas=falhas)
