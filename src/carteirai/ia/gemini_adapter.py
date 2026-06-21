"""GeminiAdapter — extração via API do Gemini. Implementação REAL (integração, sem teste
unitário com rede). Só conformidade de interface via FakeLLM nos unitários (LLM-07).

Usa o SDK novo `google-genai` (google.genai), NÃO o deprecado google.generativeai.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from decimal import Decimal

from carteirai.dominio.dtos import (
    CATEGORIAS_AUTORIZADAS,
    TransacaoExtraida,
    normalizar_categoria,
)
from carteirai.ia.base_llm import BaseLLM, LLMError

_CATEGORIAS_STR = ", ".join(CATEGORIAS_AUTORIZADAS)

_PROMPT_SISTEMA = f"""Você é um extrator de transações financeiras de notificações de bancos brasileiros.

Dada uma notificação de banco, extraia as informações e responda APENAS com um JSON válido, sem texto adicional.

O JSON deve ter EXATAMENTE estas chaves:
- "valor": número (ex: 49.90) — valor da transação
- "estabelecimento": string — nome da loja/contraparte ou "" se não houver
- "categoria": uma das categorias autorizadas abaixo
- "forma": uma de: debito, credito, pix, dinheiro
- "tipo": "entrada" se recebeu/depositou dinheiro, "saida" se pagou/comprou/enviou
- "data_iso": data e hora no formato ISO 8601 SE estiver explícita no texto; caso contrário null

Categorias autorizadas: {_CATEGORIAS_STR}

Responda somente o JSON, sem markdown, sem explicações.
"""


class GeminiAdapter(BaseLLM):
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash") -> None:
        self.api_key = api_key
        self.model = model

    async def extrair(self, texto: str) -> TransacaoExtraida:
        """Extrai TransacaoExtraida de texto bruto usando a API do Gemini.

        Corre a chamada síncrona do SDK em thread separada para não bloquear o loop.
        Lança LLMError em qualquer falha (rede, JSON inválido, campo ausente).
        """
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise LLMError(
                "Pacote google-genai não instalado. Execute: pip install google-genai"
            ) from exc

        client = genai.Client(api_key=self.api_key)
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0,
            system_instruction=_PROMPT_SISTEMA,
        )

        try:
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=self.model,
                contents=texto,
                config=config,
            )
        except Exception as exc:
            raise LLMError(f"Erro ao chamar API do Gemini: {exc}") from exc

        raw_text = getattr(response, "text", None)
        if not raw_text:
            raise LLMError("Gemini retornou resposta vazia ou sem campo 'text'.")

        try:
            j = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise LLMError(
                f"Gemini retornou JSON inválido: {exc}. Resposta bruta: {raw_text!r}"
            ) from exc

        # --- valor ---
        try:
            valor = Decimal(str(j["valor"]))
        except (KeyError, Exception) as exc:
            raise LLMError(f"Campo 'valor' ausente ou inválido no JSON do Gemini: {exc}") from exc

        # --- categoria ---
        categoria = normalizar_categoria(j.get("categoria", ""))

        # --- data_hora ---
        data_iso = j.get("data_iso")
        if data_iso:
            try:
                data_hora = datetime.fromisoformat(str(data_iso))
            except (ValueError, TypeError) as exc:
                # data inválida: usa now() (não é campo rígido)
                data_hora = datetime.now()
        else:
            data_hora = datetime.now()

        # --- forma ---
        formas_validas = {"debito", "credito", "pix", "dinheiro"}
        forma_raw = str(j.get("forma", "")).lower().strip()
        forma = forma_raw if forma_raw in formas_validas else "pix"

        # --- tipo ---
        tipos_validos = {"entrada", "saida"}
        tipo_raw = str(j.get("tipo", "")).lower().strip()
        tipo = tipo_raw if tipo_raw in tipos_validos else "saida"

        # --- estabelecimento ---
        estabelecimento = str(j.get("estabelecimento", "") or "")

        try:
            return TransacaoExtraida(
                valor=valor,
                data_hora=data_hora,
                estabelecimento=estabelecimento,
                categoria=categoria,
                forma=forma,  # type: ignore[arg-type]
                tipo=tipo,  # type: ignore[arg-type]
            )
        except Exception as exc:
            raise LLMError(f"Erro ao montar TransacaoExtraida: {exc}") from exc
