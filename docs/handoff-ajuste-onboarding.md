# Handoff — Ajuste fino do onboarding (web + Android)

> Documento para um agente (Sonnet) refinar o **fluxo de onboarding** do painel web e garantir
> que ele **combina bem com o app Android**. Auto-contido: leia tudo antes de agir.

## Objetivo
1. Exercitar e **avaliar o fluxo de onboarding** (criar conta: família → membros → contas/bancos →
   renda → revisão), apontando atritos de UX.
2. Avaliar **como o web combina com o app Android** — o app expõe um "Copiar ID" (UUID do
   dispositivo) que deve virar o `usuario_id` do membro admin no onboarding. Hoje há um atrito:
   o usuário precisa do ID do app antes de ter conta (resolver/suavizar isso).
3. **Propor e implementar** melhorias no onboarding (mantendo o design system Warm Ledger) e no
   elo app↔onboarding. Entregar uma comparação com prints. **Não dar push sem o OK do usuário.**

## Estado atual (o que já existe)
- **Painel web** em `painel/` (Next.js 15 App Router + TS + Tailwind). No ar em
  **https://carteir-ai.vercel.app** (abre no `/login`; dashboard em `/inicio`; onboarding em `/onboarding`).
  - Onboarding wizard: `painel/app/onboarding/page.tsx` (client) — passos família/membros, contas,
    renda, dívidas, revisão. O membro admin tem campo "ID do app (opcional)".
  - API que persiste: `painel/app/api/onboarding/route.ts` — POST cria família + usuários +
    instituições/contas + fontes_renda + dívidas numa transação (driver `@neondatabase/serverless`).
    Body shape documentado no topo do route. Se `usuario_id` do admin vier vazio, gera UUID.
  - Design system Warm Ledger: `painel/tailwind.config.ts`, `painel/app/globals.css`, e o guia em
    `docs/07-painel-web.md`. Telas de referência do Stitch em `stitch/onboarding/`.
- **App Android** no repo separado `git@github.com:Sirimarco-Marcio/CarteirAINotifier.git`
  (Kotlin, UI em XML/Views, tema Warm Ledger já aplicado). Tela principal (`MainActivity`) mostra
  "SEU ID (PARA CADASTRO)" + botão "Copiar ID" (UUID gerado pelo `IdentidadeStore` na 1ª abertura,
  **independe de ter conta**). O app envia notificações pra `/api/ingestao` (ver `HttpSink`).
- **Backend/worker** em `src/` (Python) roda no Pi; **fora do escopo deste ajuste** (foco no onboarding).
- Modelo de dados: `db/migrations/` (0001 schema, 0002 fila_ingestao, 0003 contas.package_name).

## Ambiente e ferramentas (já disponíveis na máquina)
- **Node 22 + pnpm** + **`google-chrome`** (headless, pra prints). Build do painel: rodar o `next`
  direto evita o gate do pnpm/sharp: `cd painel && ./node_modules/.bin/next build`.
  Dev: `cd painel && ... next dev` (porta 3000+).
- **adb** com o celular real conectado (device `RQCW603P30Y`). Toolchain Android: Java 25,
  `~/Android/Sdk`, gradle wrapper (no clone do app). Build: `./gradlew :app:assembleDebug`.
- **Neon MCP** (ferramentas `mcp__Neon__*`): projeto **`broad-art-08533202`** (nome "CarteirAI",
  Postgres 18). Use `get_connection_string`, `create_branch`, `run_sql`, `delete_branch`.
- **Segredos** (Pi SSH, Telegram, Gemini, URL do Neon de prod): em
  `/home/sirimarco/Documents/carteirAI/segredos.local.md` (NÃO versionar; NÃO colar em arquivos do repo).

## Regras de segurança (IMPORTANTES)
- **NUNCA escreva no branch de produção do Neon.** Crie um **branch de teste** (`create_branch`) e
  use a connection string DELE pra exercitar o onboarding. **Apague o branch** (`delete_branch`) ao terminar.
- **Não dê `git push`** em nenhum repo sem o OK explícito do usuário (deixe os commits/changes locais pra revisão).
- No celular, instale só como **`com.example.carteirainotifier.preview`** (adicione `applicationIdSuffix
  = ".preview"` no `debug { }` do `app/build.gradle.kts` do clone) pra **coexistir sem mexer no app real** do usuário.
- Nada de segredos em arquivos versionados.

## Passo a passo sugerido
1. **Branch de teste no Neon:** `create_branch` no projeto `broad-art-08533202`; pegue a
   connection string (`get_connection_string` com o branchId). Garanta o schema (rode
   `db/migrations/0001..0003` + `db/seed.sql` no branch, se ainda não vier do parent).
2. **Rodar o painel localmente apontando pro branch:**
   `cd painel && DATABASE_URL="<uri-do-branch>" INGEST_SECRET="teste-local" ./node_modules/.bin/next dev`
   (ou `build` + `start`). Suba em background; espere com `curl --retry`.
3. **Exercitar o onboarding (web):** com `google-chrome --headless=new --no-sandbox --window-size=...
   --screenshot=...` capture `localhost:3000/onboarding` em cada passo (desktop e mobile 390px). Crie
   uma conta de teste via a UI e/ou batendo direto no `POST /api/onboarding` (curl) e confira no Neon
   (`run_sql` no branch de teste) que família/usuários/contas/fontes foram criados.
4. **App Android:** clone o repo (`git clone` via SSH), aplique o `applicationIdSuffix ".preview"`,
   `./gradlew :app:assembleDebug`, `adb install -r`, abra (`adb shell am start -W -n
   com.example.carteirainotifier.preview/com.example.carteirainotifier.MainActivity`) e `screencap`
   a tela do "Copiar ID".
5. **Avaliar o elo:** o UUID do app deve casar com o `usuario_id` do admin. Identifique o atrito
   (ex.: usuário não sabe que precisa abrir o app antes; ordem dos passos; campo escondido) e proponha
   o melhor fluxo (ex.: passo dedicado "Conectar o app" com instrução visual; QR/deeplink futuro; ou
   adiar a vinculação com um estado "app não vinculado").
6. **Implementar** as melhorias no `painel/app/onboarding/page.tsx` (+ route se preciso), no estilo
   Warm Ledger, e re-screenshotar pra comprovar. Se mexer no app, faça no clone (sem push).

## Entregável
- Um resumo com **prints** (web passo a passo + Android) e uma **avaliação do fluxo** atual.
- Lista priorizada de **melhorias de UX** do onboarding e do elo app↔conta, com as que você já
  implementou (diffs) e as que dependem de decisão do usuário.
- Confirme que **não tocou em produção** (usou branch de teste) e **não deu push**. Apague o branch de teste.
</content>
