"""LocalSSHAdapter — extração via Ollama (modelo local na faculdade) por SSH.

A 188 não tem `curl`, então usamos `ollama run <model>` lendo o PROMPT do stdin e capturando só o
STDOUT (o spinner do ollama vai pro stderr, descartado) → JSON limpo. O comando SSH (default
`ssh-188`, que sobe a VPN sozinho) é configurável por `LOCAL_SSH_CMD` (no Pi vira um `ssh` direto).
Mantenha a VPN ligada (vpn-up) pra saída ficar limpa e não re-discar a cada chamada.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
from datetime import datetime
from decimal import Decimal

from carteirai.dominio.dtos import CATEGORIAS_AUTORIZADAS, TransacaoExtraida, normalizar_categoria
from carteirai.ia.base_llm import BaseLLM, LLMError

_CATS = ", ".join(CATEGORIAS_AUTORIZADAS)
_SYSTEM = (
    "Você extrai transações de notificações de bancos brasileiros. Responda APENAS um JSON "
    "(sem markdown) com as chaves: valor (número), estabelecimento (string; no Pix, o nome da "
    f"contraparte), categoria (uma de: {_CATS}; Pix → 'Pix'), "
    "forma (debito, credito, pix ou dinheiro), tipo ('entrada' se a pessoa RECEBEU/depositou, "
    "'saida' se PAGOU/comprou/enviou), parcelas (inteiro; 1 se não disser). NÃO extraia data."
)


class LocalSSHAdapter(BaseLLM):
    def __init__(self, ssh_cmd: str | None = None, model: str | None = None) -> None:
        self.ssh_cmd = ssh_cmd or os.getenv("LOCAL_SSH_CMD", "ssh-188")
        self.model = model or os.getenv("LOCAL_MODEL", "qwen2.5:3b")

    async def extrair(self, texto: str, feedback: list[str] | None = None) -> TransacaoExtraida:
        prompt = f"{_SYSTEM}\n\nNotificação: \"{texto}\""
        if feedback:
            prompt += f"\n\n[CORREÇÃO] Auditor reprovou: {'; '.join(feedback)}. Extraia só o que está no texto."

        def _chamar() -> str:
            proc = subprocess.run(
                [self.ssh_cmd, f"~/ollama/bin/ollama run {self.model}"],
                input=prompt.encode(),
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,  # descarta o spinner do ollama
                timeout=180,
            )
            if proc.returncode != 0:
                raise LLMError(f"SSH/Ollama falhou (rc={proc.returncode})")
            return proc.stdout.decode()

        try:
            saida = await asyncio.to_thread(_chamar)
        except subprocess.TimeoutExpired as exc:
            raise LLMError("timeout no Ollama via SSH") from exc

        # Extrai o 1º objeto JSON do stdout (tolerante a ruído ao redor, ex: banner de VPN).
        try:
            inicio = saida.find("{")
            if inicio < 0:
                raise ValueError("nenhum JSON na saída")
            j, _ = json.JSONDecoder().raw_decode(saida[inicio:])
        except (json.JSONDecodeError, ValueError) as exc:
            raise LLMError(f"resposta do Ollama inválida: {exc}. Bruto: {saida[:200]!r}") from exc

        try:
            valor = Decimal(str(j["valor"]))
        except (KeyError, Exception) as exc:
            raise LLMError(f"'valor' ausente/inválido: {exc}") from exc

        forma = str(j.get("forma", "")).lower().strip()
        forma = forma if forma in {"debito", "credito", "pix", "dinheiro"} else "pix"
        tipo = str(j.get("tipo", "")).lower().strip()
        tipo = tipo if tipo in {"entrada", "saida"} else "saida"
        try:
            parcelas = max(1, int(j.get("parcelas", 1) or 1))
        except (ValueError, TypeError):
            parcelas = 1

        return TransacaoExtraida(
            valor=valor,
            data_hora=datetime.now(),  # placeholder; o pipeline usa o horário real
            estabelecimento=str(j.get("estabelecimento", "") or ""),
            categoria=normalizar_categoria(j.get("categoria", "")),
            forma=forma,  # type: ignore[arg-type]
            tipo=tipo,  # type: ignore[arg-type]
            parcelas_total=parcelas,
        )
