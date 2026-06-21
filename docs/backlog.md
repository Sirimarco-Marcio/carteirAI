# Backlog — ideias e melhorias futuras

Itens fora do escopo imediato, anotados para não esquecer.

## Android (app notifier)
- **Enviar localização junto da notificação** 🆕 — capturar a localização (GPS) no momento em
  que a notificação é capturada e anexar ao evento, para ajudar a lembrar **onde/quando** a compra
  foi feita (memória de gasto, contexto no painel).
  - Implica: permissão de localização no app (`ACCESS_FINE/COARSE_LOCATION` — runtime, Android 6+),
    capturar lat/long no `onNotificationPosted` (com cache/última conhecida para não gastar bateria),
    novo campo `latitude/longitude` no `NotificationEvent`/buffer e no modelo de dados (Neon),
    e exibição no painel (ex: mapa/cidade).
  - Decisões em aberto: precisão x bateria; o que fazer quando a localização não está disponível
    (notificação pode chegar muito depois da compra). Provavelmente opcional/best-effort.

## UI (app notifier)
- Ajustes cosméticos diversos (pendentes, o usuário detalha depois).
