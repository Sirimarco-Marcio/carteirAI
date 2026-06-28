"""Testes unitários do auditor — extensão de tipo e forma por regex. Contratos: AUD-07..13.
Referência: docs/tdd/01-contratos-ingestao-ia.md — bloco "Extensão: confirmação de tipo e forma".

Estes testes estão na fase RED: a função `auditar` atual não verifica tipo/forma,
portanto os casos de contradição (AUD-07, 08, 10, 11) falham intencionalmente.
Os casos sem pista (AUD-09, 12) e o caso de conformidade (AUD-13) devem passar
já nesta fase, pois a função atual não acusa falhas de tipo/forma em nenhuma situação.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from carteirai.dominio.dtos import ResultadoAuditoria, TransacaoExtraida
from carteirai.ia.auditor import auditar


# ---------------------------------------------------------------------------
# Helper — monta TransacaoExtraida preenchendo campos irrelevantes com defaults
# (idêntico ao helper de test_auditor.py, recriado aqui para isolamento)
# ---------------------------------------------------------------------------

def _transacao(
    valor: Decimal,
    data_hora: datetime,
    estabelecimento: str = "X",
    categoria: str = "Outros",
    forma: str = "pix",
    tipo: str = "saida",
    parcelas_total: int = 1,
) -> TransacaoExtraida:
    return TransacaoExtraida(
        valor=valor,
        data_hora=data_hora,
        estabelecimento=estabelecimento,
        categoria=categoria,
        forma=forma,  # type: ignore[arg-type]
        tipo=tipo,  # type: ignore[arg-type]
        parcelas_total=parcelas_total,
    )


# ---------------------------------------------------------------------------
# AUD-07 — texto evidencia tipo=entrada, extraída diz tipo=saida → ok=False, falha menciona "tipo"
# ---------------------------------------------------------------------------

def test_aud_07_tipo_entrada_no_texto_extraida_saida_falha():
    # Arrange
    # "você recebeu" → pista de entrada; valor R$ 100 em 20/06 presentes para isolar.
    texto = "você recebeu R$ 100,00 em 20/06"
    extraida = _transacao(
        valor=Decimal("100.00"),
        data_hora=datetime(2026, 6, 20),
        tipo="saida",
        forma="pix",
    )

    # Act
    resultado = auditar(texto, extraida)

    # Assert — RED esperado: função atual não verifica tipo, portanto ok=True (falha aqui)
    assert resultado.ok is False, (
        "AUD-07: texto indica 'entrada' mas extraída diz 'saida' — esperava ok=False"
    )
    falhas_lower = " ".join(resultado.falhas).lower()
    assert "tipo" in falhas_lower, (
        f"AUD-07: esperava 'tipo' nas falhas, obteve: {resultado.falhas}"
    )


# ---------------------------------------------------------------------------
# AUD-08 — texto evidencia tipo=saida ("Compra"), extraída diz tipo=entrada → ok=False, falha menciona "tipo"
# ---------------------------------------------------------------------------

def test_aud_08_tipo_saida_no_texto_extraida_entrada_falha():
    # Arrange
    # "Compra" → pista de saida; valor R$ 50 em 20/06 presentes.
    texto = "Compra de R$ 50,00 em 20/06"
    extraida = _transacao(
        valor=Decimal("50.00"),
        data_hora=datetime(2026, 6, 20),
        tipo="entrada",
        forma="pix",
    )

    # Act
    resultado = auditar(texto, extraida)

    # Assert — RED esperado: função atual não verifica tipo
    assert resultado.ok is False, (
        "AUD-08: texto indica 'saida' mas extraída diz 'entrada' — esperava ok=False"
    )
    falhas_lower = " ".join(resultado.falhas).lower()
    assert "tipo" in falhas_lower, (
        f"AUD-08: esperava 'tipo' nas falhas, obteve: {resultado.falhas}"
    )


# ---------------------------------------------------------------------------
# AUD-09 — texto sem pista de tipo ("Lançamento"), extraída tipo=saida → sem falha de "tipo"
# ---------------------------------------------------------------------------

def test_aud_09_texto_sem_pista_de_tipo_nao_acusa_falha_de_tipo():
    # Arrange
    # "Lançamento" não pertence a nenhuma lista de pistas de tipo → ambíguo → sem falha.
    # Valor e data presentes para que não haja outra falha.
    texto = "Lançamento de R$ 50,00 em 20/06"
    extraida = _transacao(
        valor=Decimal("50.00"),
        data_hora=datetime(2026, 6, 20),
        tipo="saida",
        forma="pix",
    )

    # Act
    resultado = auditar(texto, extraida)

    # Assert — deve passar mesmo na fase RED (função atual nunca acusa tipo)
    falhas_lower = " ".join(resultado.falhas).lower()
    assert "tipo" not in falhas_lower, (
        f"AUD-09: texto sem pista de tipo não deve gerar falha de 'tipo', obteve: {resultado.falhas}"
    )


# ---------------------------------------------------------------------------
# AUD-10 — texto evidencia forma=credito ("compra no crédito"), extraída forma=debito → ok=False, falha menciona "forma"
# ---------------------------------------------------------------------------

def test_aud_10_forma_credito_no_texto_extraida_debito_falha():
    # Arrange
    # "compra no crédito" → pista de credito; valor e data presentes.
    texto = "compra no crédito de R$ 50,00 em 20/06"
    extraida = _transacao(
        valor=Decimal("50.00"),
        data_hora=datetime(2026, 6, 20),
        tipo="saida",
        forma="debito",
    )

    # Act
    resultado = auditar(texto, extraida)

    # Assert — RED esperado: função atual não verifica forma
    assert resultado.ok is False, (
        "AUD-10: texto indica forma='credito' mas extraída diz 'debito' — esperava ok=False"
    )
    falhas_lower = " ".join(resultado.falhas).lower()
    assert "forma" in falhas_lower, (
        f"AUD-10: esperava 'forma' nas falhas, obteve: {resultado.falhas}"
    )


# ---------------------------------------------------------------------------
# AUD-11 — texto evidencia forma=pix ("Pix"), extraída forma=credito → ok=False, falha menciona "forma"
# ---------------------------------------------------------------------------

def test_aud_11_forma_pix_no_texto_extraida_credito_falha():
    # Arrange
    # "Pix" → pista de pix; valor e data presentes.
    texto = "Pix de R$ 50,00 em 20/06"
    extraida = _transacao(
        valor=Decimal("50.00"),
        data_hora=datetime(2026, 6, 20),
        tipo="saida",
        forma="credito",
    )

    # Act
    resultado = auditar(texto, extraida)

    # Assert — RED esperado: função atual não verifica forma
    assert resultado.ok is False, (
        "AUD-11: texto indica forma='pix' mas extraída diz 'credito' — esperava ok=False"
    )
    falhas_lower = " ".join(resultado.falhas).lower()
    assert "forma" in falhas_lower, (
        f"AUD-11: esperava 'forma' nas falhas, obteve: {resultado.falhas}"
    )


# ---------------------------------------------------------------------------
# AUD-12 — texto sem pista de forma, extraída forma=pix → sem falha de "forma"
# ---------------------------------------------------------------------------

def test_aud_12_texto_sem_pista_de_forma_nao_acusa_falha_de_forma():
    # Arrange
    # "Débito bancário" não pertence à lista de pistas de forma reconhecidas
    # ("débito de" é pista de TIPO=saida, não de forma; "no débito" seria pista de forma=debito).
    # Aqui usamos texto neutro sem nenhuma palavra-chave de forma.
    texto = "Transferência de R$ 75,00 em 15/06"
    extraida = _transacao(
        valor=Decimal("75.00"),
        data_hora=datetime(2026, 6, 15),
        tipo="saida",
        forma="pix",
    )

    # Act
    resultado = auditar(texto, extraida)

    # Assert — deve passar mesmo na fase RED (função atual nunca acusa forma)
    falhas_lower = " ".join(resultado.falhas).lower()
    assert "forma" not in falhas_lower, (
        f"AUD-12: texto sem pista de forma não deve gerar falha de 'forma', obteve: {resultado.falhas}"
    )


# ---------------------------------------------------------------------------
# AUD-13 — texto "compra no crédito de R$ 50 em 20/06", tipo=saida, forma=credito → ok=True
# ---------------------------------------------------------------------------

def test_aud_13_tipo_e_forma_conferem_retorna_ok():
    # Arrange
    # "compra" → pista de tipo=saida (confere)
    # "no crédito" → pista de forma=credito (confere)
    # Valor e data presentes e coerentes.
    texto = "compra no crédito de R$ 50,00 em 20/06"
    extraida = _transacao(
        valor=Decimal("50.00"),
        data_hora=datetime(2026, 6, 20),
        tipo="saida",
        forma="credito",
    )

    # Act
    resultado = auditar(texto, extraida)

    # Assert — RED esperado apenas se a implementação futura introduzir regressão;
    # a função atual retorna ok=True aqui (valor e data conferem, tipo/forma não são checados ainda),
    # portanto este caso PASSA na fase RED e deve continuar passando na GREEN.
    assert resultado.ok is True, (
        f"AUD-13: tipo e forma conferem — esperava ok=True, obteve falhas: {resultado.falhas}"
    )
