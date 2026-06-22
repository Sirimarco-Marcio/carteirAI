# 05 — Contratos: HTTP Ingestão (App → Pi)

> Bloco 1 do roadmap. O app Android envia o evento via HTTP POST para o Pi.
> O Pi recebe, valida, e coloca na `Fila` SQLite. Sem mudança no orquestrador.

---

## Contexto de arquitetura

```
Android (NotificationIntake)
  └─► HttpSink.enviar(NotificationEvent)
        └─► POST http://<pi>/ingestao
              └─► RoteadorIngestao.receber(payload)
                    └─► Fila.enqueue(texto_bruto, usuario_id, origem="notificacao")
```

- **`HttpSink`** (Kotlin) — nova implementação de `EventSink`. Substitui `LocalOnlySink` na
  `CarteirNotificationListenerService`.
- **`RoteadorIngestao`** (Python/FastAPI) — novo módulo `src/carteirai/ingestao/roteador.py` +
  entrypoint FastAPI em `src/carteirai/ingestao/app.py`.
- A `Fila` existente (`carteirai.fila.fila.Fila`) **não muda**.

---

## Payload JSON (App → Pi)

```json
{
  "usuario_id": "string (UUID — gerado pelo app, fixo por instalação)",
  "package_name": "string (ex: com.mercadopago.wallet)",
  "title": "string | null",
  "text": "string | null",
  "posted_at": 1234567890123,
  "hash": "string (SHA-256 hex do conteúdo, mesmo algoritmo do EventHash.kt)",
  "latitude": 0.0,
  "longitude": 0.0
}
```

Regras:
- `text` ou `title` deve ter valor (não ambos nulos/vazios) — caso contrário 422.
- `posted_at` é Unix timestamp em **milissegundos**.
- `latitude`/`longitude` são opcionais (0.0 = não disponível — aceitar normalmente).
- `usuario_id` é tratado como string opaca; o Pi não valida existência no Neon (isso é
  responsabilidade do Orquestrador mais tarde).
- O Pi **não** re-faz dedup de hash — confia no dedup já feito pelo app Android.

---

## Contratos do RoteadorIngestao (Python)

### ING-HTTP-01 — Recebe payload válido e encola

**Dado** um `POST /ingestao` com payload completo e válido  
**Quando** o roteador processa  
**Então**:
- retorna HTTP 202 `{"status": "enfileirado", "fila_id": <int>}`
- `Fila.enqueue` é chamada com `texto_bruto = "<title> <text>".strip()`, `usuario_id`,
  `origem="notificacao"`

`texto_bruto` é a concatenação de title + " " + text (cada um pode ser null/vazio):
```python
partes = [p for p in [title, text] if p]
texto_bruto = " ".join(partes)
```

### ING-HTTP-02 — Rejeita payload sem title E sem text

**Dado** `title=null` e `text=null` (ou ambos vazios)  
**Então** HTTP 422 com `{"erro": "title e text ambos ausentes"}`

### ING-HTTP-03 — Aceita text sem title (e vice-versa)

**Dado** `title=null`, `text="Você pagou R$ 22,90"`  
**Então** HTTP 202, `texto_bruto = "Você pagou R$ 22,90"`

### ING-HTTP-04 — posted_at em milissegundos → datetime correto na fila

**Dado** `posted_at = 1750546601000` (= 2026-06-21T21:56:41 UTC)  
**Então** o `ItemFila.criada_em` gerado é um datetime próximo ao agora do relógio
(a fila usa seu próprio relógio; `posted_at` é guardado como metadado, não substituído).

> Nota: `posted_at` do Android é salvo na coluna `posted_at_ms` da fila se quisermos
> (não muda o schema atual da `Fila`, adicionar campo extra ao ItemFila é opcional).
> O importante é que `criada_em` seja setado pela `Fila` normalmente.

### ING-HTTP-05 — Latitude/longitude opcionais não quebram

**Dado** `latitude=0.0, longitude=0.0`  
**Então** HTTP 202 normalmente (campos ignorados por ora, backlog de localização)

### ING-HTTP-06 — Rota de healthcheck

**Dado** `GET /healthz`  
**Então** HTTP 200 `{"status": "ok"}`

---

## Contratos do HttpSink (Kotlin)

### SINK-HTTP-01 — Envia POST e retorna Ok em sucesso (HTTP 2xx)

**Dado** servidor mock respondendo 202  
**Quando** `HttpSink.enviar(evento)` é chamado  
**Então** retorna `ResultadoEnvio.Ok`; o body enviado contém `usuario_id`, `package_name`,
`title`, `text`, `posted_at`, `hash`

### SINK-HTTP-02 — Retorna Falha em erro de rede

**Dado** servidor inacessível (timeout ou conexão recusada)  
**Quando** `HttpSink.enviar(evento)` é chamado  
**Então** retorna `ResultadoEnvio.Falha(motivo)` sem lançar exceção

### SINK-HTTP-03 — Retorna Falha em HTTP 4xx/5xx

**Dado** servidor respondendo 500  
**Então** retorna `ResultadoEnvio.Falha("HTTP 500")`

### SINK-HTTP-04 — URL configurável via parâmetro do construtor

**Dado** `HttpSink(baseUrl = "http://192.168.1.X:8000")`  
**Então** o POST vai para `http://192.168.1.X:8000/ingestao`

### SINK-HTTP-05 — usuario_id vem do IdentidadeStore

O `HttpSink` recebe `identidadeStore: IdentidadeStore` no construtor.
No `enviar`, lê `identidadeStore.obterOuCriarId()` e inclui no payload.

---

## Estrutura de arquivos a criar

### Python (worker)
```
src/carteirai/ingestao/
  __init__.py
  roteador.py    ← lógica (RoteadorIngestao, sem FastAPI — testável puro)
  app.py         ← monta o FastAPI, injeta Fila real
```

### Kotlin (Android)
```
app/src/main/java/com/example/carteirainotifier/transport/
  HttpSink.kt    ← nova implementação de EventSink
```

`CarteirNotificationListenerService.kt` troca `LocalOnlySink()` por `HttpSink(baseUrl, identidadeStore)`.

---

## Dependências a adicionar

### Python
```
fastapi>=0.111
uvicorn[standard]>=0.29
httpx>=0.27          # para testes do endpoint
```
Adicionar em `requirements.txt`.

### Kotlin / Android
Já tem OkHttp ou Ktor no projeto? Usar o que já existe.
Se não tiver nenhum: adicionar `com.squareup.okhttp3:okhttp:4.12.0` ao `build.gradle.kts` do app.

---

## Wiring final (CarteirNotificationListenerService)

```kotlin
// Antes:
LocalOnlySink()

// Depois:
HttpSink(
    baseUrl = BuildConfig.PI_BASE_URL,   // ex: "http://100.x.x.x:8000" (Tailscale IP)
    identidadeStore = IdentidadeStore(applicationContext),
)
```

`PI_BASE_URL` vem de `local.properties` → `buildConfigField` no `build.gradle.kts`.
