"""Entrypoint FastAPI para ingestão de notificações (App → Pi).

Expõe:
    POST /ingestao  — recebe payload do Android, valida e enfileira
    GET  /healthz   — healthcheck simples

Uso (desenvolvimento):
    uvicorn carteirai.ingestao.app:app --host 0.0.0.0 --port 8000 --reload

Contratos: ING-HTTP-01 a ING-HTTP-06 (docs/tdd/05-contratos-http-ingestao.md).
"""

from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

from carteirai.fila.fila import Fila
from carteirai.ingestao.roteador import (
    ErroPayloadInvalido,
    PayloadIngestao,
    RoteadorIngestao,
)


# ---------------------------------------------------------------------------
# Schema Pydantic para validação automática do corpo da requisição
# ---------------------------------------------------------------------------

class CorpoIngestao(BaseModel):
    """Schema do payload JSON enviado pelo app Android."""

    usuario_id: str
    package_name: str
    title: str | None = None
    text: str | None = None
    posted_at: int                  # Unix timestamp em milissegundos
    hash: str
    latitude: float = 0.0
    longitude: float = 0.0

    @field_validator("usuario_id", "package_name", "hash")
    @classmethod
    def nao_vazio(cls, v: str) -> str:
        """Garante que campos obrigatórios de string não sejam strings vazias."""
        if not v.strip():
            raise ValueError("campo não pode ser vazio")
        return v


# ---------------------------------------------------------------------------
# Fábrica: permite injetar Fila nos testes (ING-HTTP-*)
# ---------------------------------------------------------------------------

def criar_app(fila: Fila | None = None) -> FastAPI:
    """Cria e configura a instância FastAPI com a Fila injetada.

    Em produção, chame sem argumento: `criar_app()` usa `CARTEIRAI_DB`.
    Nos testes, passe uma Fila em memória: `criar_app(Fila(':memory:'))`.
    """
    if fila is None:
        db_path = os.environ.get("FILA_DB_PATH", os.environ.get("CARTEIRAI_DB", "/data/fila.db"))
        fila = Fila(db_path=db_path)

    roteador = RoteadorIngestao(fila=fila)
    _app = FastAPI(title="CarteirAI — Ingestão", version="0.1.0")

    @_app.post("/ingestao", status_code=202)
    async def ingestao(corpo: CorpoIngestao) -> dict:
        """Recebe notificação do app Android e enfileira na Fila SQLite.

        Retorna:
            202 {"status": "enfileirado", "fila_id": <int>}
            422 {"erro": "title e text ambos ausentes"}  se ambos estiverem vazios/nulos
        """
        payload = PayloadIngestao(
            usuario_id=corpo.usuario_id,
            package_name=corpo.package_name,
            title=corpo.title,
            text=corpo.text,
            posted_at=corpo.posted_at,
            hash=corpo.hash,
            latitude=corpo.latitude,
            longitude=corpo.longitude,
        )
        try:
            resposta = roteador.receber(payload)
        except ErroPayloadInvalido as exc:
            # ING-HTTP-02 — title e text ambos ausentes
            return JSONResponse(status_code=422, content={"erro": str(exc)})

        return {"status": resposta.status, "fila_id": resposta.fila_id}

    @_app.get("/healthz")
    async def healthz() -> dict:
        """Healthcheck simples. Contrato: ING-HTTP-06.

        Retorna:
            200 {"status": "ok"}
        """
        return {"status": "ok"}

    @_app.exception_handler(RequestValidationError)
    async def handler_422(request: Request, exc: RequestValidationError) -> JSONResponse:
        """Padroniza erros de validação Pydantic para o formato do contrato."""
        return JSONResponse(status_code=422, content={"detail": exc.errors()})

    return _app


# ---------------------------------------------------------------------------
# Instância global — usada pelo uvicorn em produção
# ---------------------------------------------------------------------------

# Lazy: só cria a Fila ao importar fora de contexto de testes.
# Em testes, importe `criar_app` diretamente e injete a Fila.
import os as _os
_db_env = _os.environ.get("FILA_DB_PATH", _os.environ.get("CARTEIRAI_DB", ""))
if _db_env:
    app = criar_app()
else:
    # Sem variável de ambiente → ambiente de testes ou CI; cria app sem Fila real
    # (testes sempre usam criar_app(fila=Fila(':memory:')) diretamente)
    app = criar_app(Fila(":memory:"))

