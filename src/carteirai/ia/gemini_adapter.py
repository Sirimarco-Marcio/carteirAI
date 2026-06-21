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
- "parcelas": número inteiro de parcelas SE o texto indicar (ex: "em 3x", "3 vezes", "parcelado em 6"); caso contrário 1

Para transferências Pix: use categoria "Pix" e coloque em "estabelecimento" o NOME da contraparte
(quem enviou/recebeu), quando aparecer no texto.

NÃO extraia data — a data é definida pelo sistema, não por você.

Categorias autorizadas: {_CATEGORIAS_STR}

Responda somente o JSON, sem markdown, sem explicações.
"""


class GeminiAdapter(BaseLLM):
    def __init__(self, api_key: str, model: str = "gemini-flash-latest") -> None:
        self.api_key = api_key
        self.model = model

    async def extrair(self, texto: str, feedback: list[str] | None = None) -> TransacaoExtraida:
        """Extrai TransacaoExtraida de texto bruto usando a API do Gemini.

        Corre a chamada síncrona do SDK em thread separada para não bloquear o loop.
        `feedback` (reflexão): falhas do auditor da tentativa anterior — injetadas no prompt
        para o modelo corrigir (ex: "o valor X que você extraiu não aparece no texto; corrija").
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

        contents = texto
        if feedback:
            correcao = "; ".join(feedback)
            contents = (
                f"{texto}\n\n[CORREÇÃO] A extração anterior foi reprovada pelo auditor: {correcao}. "
                f"Releia o texto com atenção e corrija — extraia SOMENTE valores que aparecem literalmente no texto."
            )

        try:
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=self.model,
                contents=contents,
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

        # --- data_hora: NÃO vem da LLM. Placeholder = now(); o pipeline (bot/worker)
        #     sobrescreve com o horário real do evento (mensagem do chat / postedAt da notificação). ---
        data_hora = datetime.now()

        # --- parcelas ---
        try:
            parcelas_total = int(j.get("parcelas", 1) or 1)
            if parcelas_total < 1:
                parcelas_total = 1
        except (ValueError, TypeError):
            parcelas_total = 1

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
                parcelas_total=parcelas_total,
            )
        except Exception as exc:
            raise LLMError(f"Erro ao montar TransacaoExtraida: {exc}") from exc
