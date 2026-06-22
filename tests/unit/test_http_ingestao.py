"""Testes RED — Transporte HTTP App→Pi. Contratos ING-HTTP-01..06.

Referência: docs/tdd/05-contratos-http-ingestao.md §Contratos do RoteadorIngestao.

Estratégia:
  - O app FastAPI é montado via `carteirai.ingestao.app.criar_app(fila=...)`.
  - A Fila real (`:memory:`) é injetada — evita mockar o contrato interno da Fila.
  - httpx.AsyncClient com ASGITransport testa o FastAPI sem abrir socket real.
  - Cada teste nomeia o contrato (ING-HTTP-XX) e segue Arrange / Act / Assert.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
import httpx
from httpx import AsyncClient, ASGITransport

from carteirai.fila.fila import Fila
from carteirai.ingestao.app import criar_app  # módulo a ser criado pelo agente de implementação

# ---------------------------------------------------------------------------
# Payload de referência (válido, completo)
# ---------------------------------------------------------------------------

PAYLOAD_VALIDO = {
    "usuario_id": "550e8400-e29b-41d4-a716-446655440000",
    "package_name": "com.mercadopago.wallet",
    "title": "MercadoPago",
    "text": "Você pagou R$ 22,90",
    "posted_at": 1750546601000,   # 2026-06-21T21:56:41 UTC em ms
    "hash": "abc123def456abc123def456abc123def456abc123def456abc123def456abc1",
    "latitude": -23.5505,
    "longitude": -46.6333,
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fila() -> Fila:
    """Fila em memória — isolamento total entre testes."""
    return Fila(":memory:")


@pytest_asyncio.fixture
async def cliente(fila: Fila) -> AsyncClient:
    """AsyncClient apontando para o FastAPI com a Fila fake injetada."""
    app = criar_app(fila=fila)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as cli:
        yield cli


# ---------------------------------------------------------------------------
# ING-HTTP-01 — Recebe payload válido e encola
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ing_http_01_payload_valido_retorna_202_e_encola(cliente: AsyncClient, fila: Fila):
    """Dado payload completo e válido, espera HTTP 202 e item na Fila."""
    # Act
    resposta = await cliente.post("/ingestao", json=PAYLOAD_VALIDO)

    # Assert — status HTTP
    assert resposta.status_code == 202

    corpo = resposta.json()
    assert corpo["status"] == "enfileirado"
    assert isinstance(corpo["fila_id"], int)
    assert corpo["fila_id"] >= 1

    # Assert — item realmente enfileirado
    item = fila.fetch_next()
    assert item is not None
    # texto_bruto = title + " " + text (ambos presentes)
    assert item.texto_bruto == "MercadoPago Você pagou R$ 22,90"
    assert item.usuario_id == PAYLOAD_VALIDO["usuario_id"]
    assert item.origem == "notificacao"
    assert item.status == "PROCESSANDO"   # fetch_next marca PROCESSANDO


# ---------------------------------------------------------------------------
# ING-HTTP-02 — Rejeita payload sem title E sem text
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ing_http_02_sem_title_e_sem_text_retorna_422(cliente: AsyncClient):
    """Dado title=null e text=null, espera HTTP 422 com mensagem de erro."""
    payload = {**PAYLOAD_VALIDO, "title": None, "text": None}

    resposta = await cliente.post("/ingestao", json=payload)

    assert resposta.status_code == 422
    corpo = resposta.json()
    assert "erro" in corpo
    assert "ausentes" in corpo["erro"].lower() or "title" in corpo["erro"].lower()


@pytest.mark.asyncio
async def test_ing_http_02_title_vazio_e_text_vazio_retorna_422(cliente: AsyncClient):
    """Ambos em branco ("") também deve ser rejeitado com 422."""
    payload = {**PAYLOAD_VALIDO, "title": "", "text": ""}

    resposta = await cliente.post("/ingestao", json=payload)

    assert resposta.status_code == 422


# ---------------------------------------------------------------------------
# ING-HTTP-03 — Aceita text sem title (e vice-versa)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ing_http_03_apenas_text_sem_title_retorna_202(cliente: AsyncClient, fila: Fila):
    """Dado title=null, text preenchido → aceita e texto_bruto = text."""
    payload = {**PAYLOAD_VALIDO, "title": None, "text": "Você pagou R$ 22,90"}

    resposta = await cliente.post("/ingestao", json=payload)

    assert resposta.status_code == 202

    item = fila.fetch_next()
    assert item is not None
    assert item.texto_bruto == "Você pagou R$ 22,90"


@pytest.mark.asyncio
async def test_ing_http_03_apenas_title_sem_text_retorna_202(cliente: AsyncClient, fila: Fila):
    """Dado title preenchido, text=null → aceita e texto_bruto = title."""
    payload = {**PAYLOAD_VALIDO, "title": "MercadoPago", "text": None}

    resposta = await cliente.post("/ingestao", json=payload)

    assert resposta.status_code == 202

    item = fila.fetch_next()
    assert item is not None
    assert item.texto_bruto == "MercadoPago"


# ---------------------------------------------------------------------------
# ING-HTTP-04 — posted_at em milissegundos → criada_em setado pela Fila
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ing_http_04_posted_at_ms_aceito_e_criada_em_vem_da_fila(
    cliente: AsyncClient, fila: Fila
):
    """posted_at em ms não substitui criada_em — a Fila usa seu próprio relógio.

    Verificamos que criada_em é um datetime válido (não None) e que o campo
    posted_at não causou erro de parsing — o contrato não exige igualdade de valor.
    """
    payload = {**PAYLOAD_VALIDO, "posted_at": 1750546601000}

    resposta = await cliente.post("/ingestao", json=payload)

    assert resposta.status_code == 202

    item = fila.fetch_next()
    assert item is not None
    # criada_em deve ser um datetime setado pela Fila (relógio do Pi)
    from datetime import datetime
    assert isinstance(item.criada_em, datetime)


# ---------------------------------------------------------------------------
# ING-HTTP-05 — Latitude/longitude opcionais não quebram
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ing_http_05_lat_long_zero_aceito(cliente: AsyncClient):
    """lat=0.0, long=0.0 (sem GPS disponível) → HTTP 202 normalmente."""
    payload = {**PAYLOAD_VALIDO, "latitude": 0.0, "longitude": 0.0}

    resposta = await cliente.post("/ingestao", json=payload)

    assert resposta.status_code == 202


@pytest.mark.asyncio
async def test_ing_http_05_lat_long_ausentes_aceito(cliente: AsyncClient):
    """lat/long completamente omitidos do payload → HTTP 202 normalmente."""
    payload = {k: v for k, v in PAYLOAD_VALIDO.items() if k not in ("latitude", "longitude")}

    resposta = await cliente.post("/ingestao", json=payload)

    assert resposta.status_code == 202


# ---------------------------------------------------------------------------
# ING-HTTP-06 — Rota de healthcheck
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ing_http_06_healthz_retorna_200_ok(cliente: AsyncClient):
    """GET /healthz deve retornar HTTP 200 com body {\"status\": \"ok\"}."""
    resposta = await cliente.get("/healthz")

    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok"}
