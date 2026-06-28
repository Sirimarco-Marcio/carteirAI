"""Adapter real do TelegramPort — envia mensagens via Bot API (httpx).

Implementa a porta usada por `ServicoAprovacao` (telegram.enviar(chat_id, texto, botoes)).
`botoes` é uma lista de (label, callback_data) → vira um inline_keyboard (uma linha).
Nos testes usa-se o FakeTelegram; este é o adapter de produção (precisa do token do bot).
"""

from __future__ import annotations

import httpx


class TelegramPortHttpx:
    def __init__(self, token: str, timeout: float = 20.0) -> None:
        self._base = f"https://api.telegram.org/bot{token}"
        self._timeout = timeout

    def enviar(
        self, chat_id: str, texto: str, botoes: list[tuple[str, str]] | None = None
    ) -> None:
        payload: dict = {"chat_id": chat_id, "text": texto}
        if botoes:
            payload["reply_markup"] = {
                "inline_keyboard": [[{"text": label, "callback_data": data} for label, data in botoes]]
            }
        # Falha de envio não deve derrubar o worker; loga via exceção do httpx se ocorrer.
        httpx.post(f"{self._base}/sendMessage", json=payload, timeout=self._timeout)
