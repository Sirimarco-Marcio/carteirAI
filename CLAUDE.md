# carteirAI

Sistema event-driven de gestão financeira pessoal/familiar.
Captura transações via notificações móveis (app Android próprio) + Telegram,
processa com IA (extração + auditoria), consolida no Neon (Postgres) e visualiza
num painel Next.js na Vercel.

## Documentação
- `docs/00-handoff.md` — contexto e decisões (ler primeiro)
- `docs/01-visao-e-arquitetura.md` — arquitetura híbrida + diagrama
- `docs/02-modelo-de-dados.md` — modelo ER (Postgres)
- `docs/03-fluxos.md` — fluxos A–F + comandos do bot
- `docs/04-operacoes-pi.md` — estado e operação do Raspberry Pi
- `docs/tdd/` — estratégia e **contratos de TDD** (testes antes do código)

## Fluxo de TDD entre agentes
Ver `docs/tdd/00-estrategia-tdd.md`. Um agente escreve os testes (RED) a partir dos
contratos `docs/tdd/01..03` ANTES de outro agente implementar (GREEN). Cada caso tem
ID (ex: `FILA-01`) referenciado no nome do teste. Unitários primeiro; integração em
`docs/tdd/04-plano-integracao.md` (Fase 2).

## Arquitetura (resumo)
- **Pi (worker persistente, Docker):** FastAPI + polling Telegram + fila SQLite +
  LangGraph (LLM → Auditor RegEx). Peça central.
- **IA:** `BaseLLM` (Ports & Adapters) com 2 adapters desde o MVP, via `LLM_PROVIDER`:
  `gemini` (API, padrão) ou `local` (SSH → máquina da faculdade, 6GB VRAM).
- **Neon:** single source of truth.
- **Vercel:** painel Next.js + API Routes (credencial do Neon fica server-side;
  o navegador nunca acessa o banco direto).

## Convenções
- Idioma: português (acentuação correta sempre).
- Fase de implementação no Pi: **TDD** (testes primeiro / cobertura ampla).
- Segredos (chave Gemini, SSH do Pi) vão em `.env`/doc de operações fora do versionamento.
