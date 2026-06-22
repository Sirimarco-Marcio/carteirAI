# 📖 Para ler — estado do projeto (resumo de handoff)

> Documento de leitura rápida pra você se situar quando voltar. As decisões que preciso de você
> estão em `docs/DECISOES-PENDENTES.md` (responda tudo de uma vez e me manda).

## Onde está cada coisa
- **App Android** (passo 1): repo separado `github.com/Sirimarco-Marcio/CarteirAINotifier`, local em `~/AndroidStudioProjects/CarteirAINotifier`.
- **Worker (Pi)**: este repo `github.com/Sirimarco-Marcio/carteirAI`, código Python em `src/carteirai/`.
- **Segredos**: `segredos.local.md` + `.env` (ambos ignorados pelo git). Tudo centralizado lá.
- **Contratos de TDD**: `docs/tdd/01..03` (testes antes do código). **Schema do banco**: `db/`.

## ✅ O que já funciona (testado)
1. **App Android** — lê notificações, você escolhe quais apps "Observar" (com busca e seções
   Observados/Ignorados), guarda local com dedup, tela de inspeção com filtros. **Validado no seu
   celular real** (Samsung) — capturou Pix/compras de Itaú, Bradesco, Santander, Mercado Pago.
   Formatos reais salvos em `docs/notificacoes-exemplos.md`.
2. **Worker — núcleo (TDD, 67 testes verdes)**: `auditor` (anti-alucinação), `BaseLLM`/`resolver_llm`/
   `GeminiAdapter`; **FILA** (sqlite, durabilidade), **DEDUP** (hash exato + soft-match),
   **ORQ** (orquestrador com reflexão + fallback de provider), **RENDA** (renda prevista por dia/fonte),
   **TRANS** (ciclo de vida + saldo), **FAT** (cartão: fatura, parcelamento, pagamento, limite).
   Tudo no GitHub, fluxo TDD (test→code) por agentes.
3. **Bot de teste do Telegram** (spike): você cola uma notificação → Gemini extrai → auditor
   confere → bot responde com `[Sim][Não][Editar]`; para crédito, **pergunta as parcelas**.
   Rodável: `PYTHONPATH=src ./.venv/bin/python -m carteirai.bot.teste`.
4. **Schema do banco** (`db/`): 13 tabelas, validado num Postgres descartável. Banco Neon limpo
   nasce pronto com `db/apply.sh`.
5. **LLM local** (máquinas da faculdade): SSH funciona (`ssh-188`/`ssh-189`, sobem a VPN sozinhos);
   **Ollama + modelos (`qwen2.5:3b`, `llama3.2`, `qwen2.5:0.5b`) instalados nas DUAS** (188=LPG17,
   189=LPG16, ambas RTX 2060 6GB). Testado: extrai bem, mas erra mais que o Gemini → **Gemini
   principal, local fallback**.

## Como as coisas funcionam (decisões de design já tomadas)
- **Fluxo**: notificação → (transporte) → Pi: fila → IA (LLM extrai → auditor confere) → Neon →
  aprovação no Telegram de quem gastou.
- **Dedup em 2 níveis**: hash exato (mesma notificação reenviada → descarta) + soft-match
  (mesmo usuário+valor+estab. na janela → pergunta "é a mesma ou nova?").
- **Data é programática**: vem do horário da notificação, **não** da IA (a IA inventava ano errado).
- **Retry tipo "agente de leitura"** (acabei de formalizar): se o auditor reprova o VALOR, o erro
  volta pra IA como feedback e ela tenta de novo (até 2×); se esgota, troca de provider
  (Gemini↔local); se ainda falha, vai pro humano. Não-transação (sem valor) é `IGNORADA` sem retry.
- **Cartão de crédito**: compra não mexe no saldo; entra numa fatura; parcelamento gera N
  transações (uma por mês) → controla limite/saldo futuro. Já mapeado no banco.
- **TDD entre agentes**: eu (gerente) escrevo contrato+stubs; um agente escreve testes (RED);
  outro escreve código (GREEN); eu verifico. Cada iteração vira commits `test:`/`feat:`.

## Como rodar / verificar
```bash
# Worker (testes):
cd ~/Documents/carteirAI && ./.venv/bin/pytest -q
# Bot de teste (Telegram):
PYTHONPATH=src ./.venv/bin/python -m carteirai.bot.teste
# App Android (build + instalar no celular conectado):
cd ~/AndroidStudioProjects/CarteirAINotifier && scripts/capturar.sh setup
# Banco limpo no Neon:
db/apply.sh
# SSH na faculdade:
ssh-188   # ou ssh-189
```

## O que falta (atualizado — 91 testes verdes)
**Feitos (TDD):** FILA, DEDUP, ORQ, auditor, LLM/Gemini, RENDA, TRANS, FAT, COMP, APROV, ING, CMD-consultas (/saldo, /gastos, /pendentes, ajuda). **Falta:**
- **CMD ações:** /faltei, /desfazer, /pagar_fatura, /lancar, /relatorio, /fechar_mes (TDD).
- **Fiação do worker (entrypoint):** loop que liga polling do canal → RoteadorIngestao → Fila → Orquestrador → APROV. Torna o worker executável.
- **Persistência real (Neon):** repos hoje são fakes; falta implementação SQLAlchemy + banco limpo (D9) + chave Gemini com cota (D1).
- **LocalSSHAdapter** (Ollama via SSH) — integração.
- **Deploy no Pi** (openfortivpn + Docker — D10 autorizado, depende do entrypoint).
- **App Android:** TelegramChannelSink (depende do id do canal — D3), localização (D14), app da esposa (D12).
- **Painel Next.js (Vercel)** — passo 3/4.

Para retomar a integração preciso de você: **(a) id do canal** (1 canal, bot admin), **(b) Neon novo**, **(c) chave Gemini com cota**.
Cada módulo é um commit `test:`/`feat:` no GitHub. Decisões respondidas em `DECISOES-PENDENTES.md`.

## ⚠️ Importante (segurança)
Token do bot, connection string do Neon e a chave do Gemini foram colados em texto no chat —
**rotacione** quando puder (estão marcados em `segredos.local.md`). A chave do Gemini atual
**estourou cota (429)** — ver decisões.
