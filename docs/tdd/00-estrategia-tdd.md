# TDD — Estratégia e protocolo entre agentes

Este conjunto de docs é o **contrato de TDD** do worker (Python, no Pi). O objetivo
é permitir que **um agente escreva os testes ANTES** de outro agente escrever o código.

## 1. Protocolo de colaboração entre agentes

```
Contrato (estes .md)
        │
        ▼
[Agente de Testes] ── escreve testes que FALHAM (RED) ──► commit "test: ..."
        │
        ▼
[Agente de Código] ── implementa até PASSAR (GREEN) ──► commit "feat: ..."
        │
        ▼
[Refactor] ── melhora sem quebrar testes ──► commit "refactor: ..."
```

Regras invioláveis:
- O **agente de testes não lê implementação** (ela não existe) — só este contrato.
- O **agente de código não altera os testes** para fazê-los passar; se um teste estiver
  errado, abre questão e corrige o contrato primeiro.
- Cada contrato abaixo tem **ID** (ex: `FILA-01`). Cada teste referencia o ID no nome:
  `test_fila_01_enqueue_persiste_pendente`.
- Um contrato só é "pronto" quando todos os seus casos estão verdes.

## 2. Pirâmide de testes
- **Fase 1 — Unitários (AGORA):** cada módulo isolado, sem rede/DB real. Usa *fakes*.
- **Fase 2 — Integração (DEPOIS):** SQLite real + branch de teste no Neon + fakes de
  borda (Telegram, LLM). Ver `04-plano-integracao.md`.
- Sem testes E2E reais contra Telegram/Gemini no CI (só manual/sandbox).

## 3. Stack de teste
- `pytest` + `pytest-asyncio` (código é async no FastAPI).
- `pytest-cov` para cobertura.
- Sem libs de mock mágicas onde um *fake* explícito serve melhor (ver §4).
- Estrutura: `tests/unit/<dominio>/test_*.py`, `tests/integration/...`.

## 4. Dublês de teste (fakes) — contratos obrigatórios
Para os unitários rodarem sem rede, o agente de testes cria estes fakes:

| Fake | Substitui | Comportamento |
| --- | --- | --- |
| `FakeLLM(BaseLLM)` | Gemini/Local | retorna resposta(s) pré-programada(s) — uma fixa OU uma **sequência por chamada** (p/ testar reflexão); registra `chamadas` e o último `feedback` recebido; permite simular erro/timeout (`LLMError`) |
| `FakeFilaRepo` / SQLite `:memory:` | fila SQLite | guarda itens em memória |
| `FakeTransacaoRepo` | Neon | guarda transações em dict; consulta hash/soft-match |
| `FakeTelegram` | Bot API | captura mensagens "enviadas" e injeta callbacks |
| `RelogioFake` | tempo | `agora()` controlável (datas determinísticas nos testes) |

> **Determinismo:** nenhum teste depende de `datetime.now()` real nem de aleatoriedade.
> Datas/IDs entram por parâmetro ou pelo `RelogioFake`.

## 5. Convenções
- Arrange-Act-Assert explícito.
- Um comportamento por teste; nome descreve o comportamento, não a função.
- Casos de borda são testes próprios (não asserts extras num teste feliz).
- Valores monetários: `Decimal`, nunca `float`.
- Cobertura-alvo Fase 1: ≥ 90% nos módulos de regra de negócio (dedup, auditor,
  cartão/fatura, renda/competência).

## 6. Tipos de domínio compartilhados (DTOs)
Referenciados pelos contratos. São estruturas de dados (Pydantic), não regra:

```
TransacaoExtraida:
  valor: Decimal
  data_hora: datetime
  estabelecimento: str
  categoria: str            # deve pertencer à lista autorizada (doc 03)
  forma: "debito|credito|pix|dinheiro"
  tipo: "entrada|saida"
  parcelas_total: int = 1

ResultadoProcessamento:
  status: "DUPLICADA|ERRO|PENDENTE_APROVACAO|IGNORADA"
  possivel_duplicata: bool = False
  transacao: TransacaoExtraida | None
  motivo_erro: str | None
  tentativas: int = 1        # nº de chamadas ao LLM até decidir (observabilidade; reflexão/fallback)
```
> `IGNORADA` = não é transação (auditor reprovou por **ausência de valor** no texto). Processada sem
> ação e **sem incomodar o humano** — diferente de `ERRO` (que vai pra confirmação/lançamento manual).

## 7. Índice de contratos
- `01-contratos-ingestao-ia.md` — fila, dedup, BaseLLM, auditor, orquestração
- `02-contratos-financeiro.md` — transações, cartão/fatura, renda/competência
- `03-contratos-telegram.md` — comandos, callbacks, roteamento de aprovação
- `04-plano-integracao.md` — Fase 2 (integração)
