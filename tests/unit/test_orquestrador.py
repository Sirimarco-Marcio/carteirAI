"""Testes unitários do Orquestrador (RED). Contratos: ORQ-01..13.
Referência: docs/tdd/01-contratos-ingestao-ia.md — bloco ORQ.

Fluxo testado: dedup exato → reflexão (até max_tentativas por provider) →
fallback de provider → IGNORADA/ERRO/PENDENTE_APROVACAO, sempre marcando a fila.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest

from carteirai.dedup.dedup import TransacaoSimilar
from carteirai.dedup.dedup import hash_exato
from carteirai.dominio.dtos import ItemFila, TransacaoExtraida
from carteirai.ia.base_llm import LLMError
from carteirai.orquestracao.orquestrador import Orquestrador
from tests.fakes import FakeFila, FakeLLM, FakeTransacaoRepo


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Data fixa para todos os testes (determinismo — sem datetime.now()).
_DATA_FIXA = datetime(2026, 6, 21, 10, 0, 0)


def _item_fila(
    texto_bruto: str,
    usuario_id: str = "usuario-teste",
    id: int = 1,
) -> ItemFila:
    """Monta um ItemFila com status PROCESSANDO e criada_em fixo."""
    return ItemFila(
        id=id,
        texto_bruto=texto_bruto,
        usuario_id=usuario_id,
        origem="manual",
        status="PROCESSANDO",
        criada_em=_DATA_FIXA,
    )


def _transacao_extraida(valor: Decimal = Decimal("50.00")) -> TransacaoExtraida:
    """Monta uma TransacaoExtraida com campos válidos e valor parametrizável.

    ATENÇÃO: data_hora usa _DATA_FIXA para que o auditor passe na verificação
    de data. O texto_bruto "correto" deve conter tanto o valor quanto a data.
    """
    return TransacaoExtraida(
        valor=valor,
        data_hora=_DATA_FIXA,
        estabelecimento="Loja Teste",
        categoria="Alimentação",
        forma="pix",
        tipo="saida",
        parcelas_total=1,
    )


# Textos canônicos:
# - "correto": contém R$ 50,00 e a data 21/06 → auditor aprova valor e ignora data (data é programática)
# - "divergência": contém R$ 50,00 mas a transação extrai valor=999.00 → auditor reprova valor
# - "não-transação": sem número → auditor reporta "sem números"
_TEXTO_CORRETO = "compra R$ 50,00 em 21/06"
_TEXTO_DIVERGENCIA = "compra R$ 50,00 em 21/06"  # mesmo texto; a divergência vem do valor extraído
_TEXTO_SEM_NUMERO = "bom dia, ofertas imperdíveis hoje"


def _hash_de(texto: str) -> str:
    return hash_exato(texto)


def _orquestrador(
    fila: FakeFila,
    repo: FakeTransacaoRepo,
    principal: FakeLLM,
    fallback: FakeLLM | None = None,
    max_tentativas: int = 2,
) -> Orquestrador:
    return Orquestrador(
        fila=fila,
        transacao_repo=repo,
        llm_principal=principal,
        llm_fallback=fallback,
        max_tentativas=max_tentativas,
    )


# ---------------------------------------------------------------------------
# ORQ-01 — hash já processado → DUPLICADA; LLM nunca chamado; fila DUPLICADA
# ---------------------------------------------------------------------------

async def test_orq_01_dedup_exato_retorna_duplicada_sem_chamar_llm():
    # Arrange
    item = _item_fila(_TEXTO_CORRETO)
    hash_item = _hash_de(_TEXTO_CORRETO)
    repo = FakeTransacaoRepo(hashes={hash_item})
    fila = FakeFila()
    principal = FakeLLM(transacao=_transacao_extraida())
    orq = _orquestrador(fila, repo, principal)

    # Act
    resultado = await orq.processar(item)

    # Assert
    assert resultado.status == "DUPLICADA"
    assert principal.chamadas == 0
    assert any(status == "DUPLICADA" for _, status in fila.marcacoes)


# ---------------------------------------------------------------------------
# ORQ-02 — hash novo, LLM acerta na 1ª, sem soft-match → PENDENTE_APROVACAO
# ---------------------------------------------------------------------------

async def test_orq_02_conteudo_novo_llm_acerta_sem_soft_match():
    # Arrange
    item = _item_fila(_TEXTO_CORRETO)
    repo = FakeTransacaoRepo()  # nenhum hash e nenhuma transação similar
    fila = FakeFila()
    principal = FakeLLM(transacao=_transacao_extraida(Decimal("50.00")))
    orq = _orquestrador(fila, repo, principal)

    # Act
    resultado = await orq.processar(item)

    # Assert
    assert resultado.status == "PENDENTE_APROVACAO"
    assert resultado.possivel_duplicata is False
    assert resultado.tentativas == 1
    assert len(repo.salvos) == 1


# ---------------------------------------------------------------------------
# ORQ-03 — soft-match positivo → PENDENTE_APROVACAO com possivel_duplicata=True
# ---------------------------------------------------------------------------

async def test_orq_03_soft_match_positivo_marca_possivel_duplicata():
    # Arrange
    item = _item_fila(_TEXTO_CORRETO, usuario_id="usuario-abc")
    # Transação similar: mesmo valor e estab., criada 3 min antes (dentro da janela de 10 min)
    similar = TransacaoSimilar(
        valor=Decimal("50.00"),
        estabelecimento="Loja Teste",
        data_hora=datetime(2026, 6, 21, 9, 57, 0),  # 3 min antes de _DATA_FIXA
    )
    repo = FakeTransacaoRepo(
        transacoes_por_usuario={"usuario-abc": [similar]}
    )
    fila = FakeFila()
    principal = FakeLLM(transacao=_transacao_extraida(Decimal("50.00")))
    orq = _orquestrador(fila, repo, principal)

    # Act
    resultado = await orq.processar(item)

    # Assert
    assert resultado.status == "PENDENTE_APROVACAO"
    assert resultado.possivel_duplicata is True


# ---------------------------------------------------------------------------
# ORQ-04 — LLMError em TODOS os providers → ERRO; motivo_erro preenchido; fila ERRO
# ---------------------------------------------------------------------------

async def test_orq_04_llm_error_em_todos_providers_retorna_erro():
    # Arrange
    item = _item_fila(_TEXTO_CORRETO)
    repo = FakeTransacaoRepo()
    fila = FakeFila()
    principal = FakeLLM(modo_erro=True)
    fallback = FakeLLM(modo_erro=True)
    orq = _orquestrador(fila, repo, principal, fallback=fallback)

    # Act
    resultado = await orq.processar(item)

    # Assert
    assert resultado.status == "ERRO"
    assert resultado.motivo_erro is not None
    assert any(status == "ERRO" for _, status in fila.marcacoes)


# ---------------------------------------------------------------------------
# ORQ-05 — divergência persiste em todos os providers → ERRO; não persiste
# ---------------------------------------------------------------------------

async def test_orq_05_divergencia_esgota_todos_providers_retorna_erro():
    # Arrange — ambos os providers sempre retornam valor que não está no texto
    item = _item_fila(_TEXTO_DIVERGENCIA)
    repo = FakeTransacaoRepo()
    fila = FakeFila()
    # Valor 999.00 não está no texto "compra R$ 50,00 em 21/06" → divergência
    transacao_errada = _transacao_extraida(Decimal("999.00"))
    principal = FakeLLM(transacao=transacao_errada)
    fallback = FakeLLM(transacao=transacao_errada)
    orq = _orquestrador(fila, repo, principal, fallback=fallback, max_tentativas=2)

    # Act
    resultado = await orq.processar(item)

    # Assert
    assert resultado.status == "ERRO"
    assert len(repo.salvos) == 0


# ---------------------------------------------------------------------------
# ORQ-06 — sucesso → fila marcada CONCLUIDO
# ---------------------------------------------------------------------------

async def test_orq_06_sucesso_marca_fila_concluido():
    # Arrange
    item = _item_fila(_TEXTO_CORRETO)
    repo = FakeTransacaoRepo()
    fila = FakeFila()
    principal = FakeLLM(transacao=_transacao_extraida(Decimal("50.00")))
    orq = _orquestrador(fila, repo, principal)

    # Act
    await orq.processar(item)

    # Assert
    assert any(status == "CONCLUIDO" for _, status in fila.marcacoes)


# ---------------------------------------------------------------------------
# ORQ-07 — duplicata exata → fila marcada DUPLICADA
# ---------------------------------------------------------------------------

async def test_orq_07_duplicata_exata_marca_fila_duplicada():
    # Arrange
    item = _item_fila(_TEXTO_CORRETO)
    hash_item = _hash_de(_TEXTO_CORRETO)
    repo = FakeTransacaoRepo(hashes={hash_item})
    fila = FakeFila()
    principal = FakeLLM(transacao=_transacao_extraida())
    orq = _orquestrador(fila, repo, principal)

    # Act
    await orq.processar(item)

    # Assert
    assert any(status == "DUPLICADA" for _, status in fila.marcacoes)


# ---------------------------------------------------------------------------
# ORQ-08 — dedup exato → LLM nunca chamado (principal.chamadas == 0)
# ---------------------------------------------------------------------------

async def test_orq_08_dedup_exato_llm_nunca_chamado():
    # Arrange
    item = _item_fila(_TEXTO_CORRETO)
    hash_item = _hash_de(_TEXTO_CORRETO)
    repo = FakeTransacaoRepo(hashes={hash_item})
    fila = FakeFila()
    principal = FakeLLM(transacao=_transacao_extraida())
    orq = _orquestrador(fila, repo, principal)

    # Act
    await orq.processar(item)

    # Assert
    assert principal.chamadas == 0


# ---------------------------------------------------------------------------
# ORQ-09 — reflexão: principal erra na 1ª, acerta na 2ª com feedback
# ---------------------------------------------------------------------------

async def test_orq_09_reflexao_principal_erra_acerta_com_feedback():
    # Arrange
    item = _item_fila(_TEXTO_CORRETO)
    repo = FakeTransacaoRepo()
    fila = FakeFila()
    # Sequência: 1ª chamada retorna valor divergente; 2ª retorna valor correto
    principal = FakeLLM(respostas=[
        _transacao_extraida(Decimal("999.00")),   # valor não está no texto → divergência
        _transacao_extraida(Decimal("50.00")),    # valor correto → auditor aprova
    ])
    orq = _orquestrador(fila, repo, principal, max_tentativas=2)

    # Act
    resultado = await orq.processar(item)

    # Assert
    assert resultado.status == "PENDENTE_APROVACAO"
    assert principal.chamadas == 2
    # A 2ª chamada deve ter recebido feedback com as falhas do auditor da 1ª tentativa
    assert principal.ultimo_feedback is not None
    assert len(principal.ultimo_feedback) > 0


# ---------------------------------------------------------------------------
# ORQ-10 — fallback por divergência: principal esgota, fallback acerta
# ---------------------------------------------------------------------------

async def test_orq_10_fallback_por_divergencia_principal_esgota_fallback_acerta():
    # Arrange
    item = _item_fila(_TEXTO_CORRETO)
    repo = FakeTransacaoRepo()
    fila = FakeFila()
    # Principal sempre diverge (max_tentativas=2 → 2 chamadas divergentes)
    transacao_errada = _transacao_extraida(Decimal("999.00"))
    principal = FakeLLM(transacao=transacao_errada)
    fallback = FakeLLM(transacao=_transacao_extraida(Decimal("50.00")))
    orq = _orquestrador(fila, repo, principal, fallback=fallback, max_tentativas=2)

    # Act
    resultado = await orq.processar(item)

    # Assert
    assert resultado.status == "PENDENTE_APROVACAO"
    assert principal.chamadas == 2
    assert fallback.chamadas >= 1


# ---------------------------------------------------------------------------
# ORQ-11 — fallback por erro: principal lança LLMError; fallback acerta
# ---------------------------------------------------------------------------

async def test_orq_11_fallback_por_llm_error_fallback_acerta():
    # Arrange
    item = _item_fila(_TEXTO_CORRETO)
    repo = FakeTransacaoRepo()
    fila = FakeFila()
    principal = FakeLLM(respostas=[LLMError("timeout simulado")])
    fallback = FakeLLM(transacao=_transacao_extraida(Decimal("50.00")))
    orq = _orquestrador(fila, repo, principal, fallback=fallback, max_tentativas=2)

    # Act
    resultado = await orq.processar(item)

    # Assert
    assert resultado.status == "PENDENTE_APROVACAO"
    # Principal foi chamado 1× e abandonado (não esgotou max_tentativas)
    assert principal.chamadas == 1
    assert fallback.chamadas >= 1


# ---------------------------------------------------------------------------
# ORQ-12 — texto sem valor (não é transação) → IGNORADA; sem retry; fila CONCLUIDO
# ---------------------------------------------------------------------------

async def test_orq_12_texto_sem_numero_retorna_ignorada_sem_retry():
    # Arrange
    item = _item_fila(_TEXTO_SEM_NUMERO)
    repo = FakeTransacaoRepo()
    fila = FakeFila()
    # LLM extrai qualquer valor — o auditor reprovará por "sem números" no texto
    principal = FakeLLM(transacao=_transacao_extraida(Decimal("50.00")))
    orq = _orquestrador(fila, repo, principal)

    # Act
    resultado = await orq.processar(item)

    # Assert
    assert resultado.status == "IGNORADA"
    assert principal.chamadas == 1          # sem retry
    assert len(repo.salvos) == 0            # não persistiu
    assert any(status == "CONCLUIDO" for _, status in fila.marcacoes)


# ---------------------------------------------------------------------------
# ORQ-13 — max_tentativas=1; divergência; sem fallback → ERRO na 1ª falha
# ---------------------------------------------------------------------------

async def test_orq_13_max_tentativas_1_divergencia_sem_fallback_retorna_erro():
    # Arrange
    item = _item_fila(_TEXTO_DIVERGENCIA)
    repo = FakeTransacaoRepo()
    fila = FakeFila()
    # Valor divergente: não está no texto
    principal = FakeLLM(transacao=_transacao_extraida(Decimal("999.00")))
    orq = _orquestrador(fila, repo, principal, max_tentativas=1)

    # Act
    resultado = await orq.processar(item)

    # Assert
    assert resultado.status == "ERRO"
