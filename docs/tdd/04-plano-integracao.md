# Plano de Testes de Integração (Fase 2)

> Só após os unitários (Fases 1) estarem verdes. Aqui os módulos conversam de verdade,
> com dependências reais controladas. Mantém Telegram e LLM como *fakes de borda*.

## Ambiente
- **SQLite real** (arquivo temporário por teste, não `:memory:`).
- **Neon:** usar um **branch de teste** isolado (criado via Neon, descartável) ou um
  Postgres em container. Nunca o branch de produção.
- **Migrations** aplicadas antes da suíte (schema real do doc 02).
- Telegram e LLM continuam *fakes* (sem custo/rede externa no CI).

## Cenários de integração (alto nível)
| ID | Cenário | Verifica |
| --- | --- | --- |
| INT-01 | Ingestão→fila→orquestração→Neon: mensagem nova vira transação PENDENTE | fila + dedup + LLM(fake) + auditor + repo Neon juntos |
| INT-02 | Mesma notificação 2× | só 1 transação criada (dedup exato real contra histórico no DB) |
| INT-03 | 2 compras iguais legítimas | 2ª entra como `possivel_duplicata` e exige confirmação |
| INT-04 | Aprovação `[Sim]` recalcula saldo | trigger/serviço de saldo no Postgres real |
| INT-05 | Compra crédito + pagar_fatura | fatura no DB, saldo só muda no pagamento |
| INT-06 | Parcelamento em 3× | 3 linhas em competências corretas no DB |
| INT-07 | `/fechar_mes` com renda divergente | relatório + inconsistências + saldo_acumulado atualizado |
| INT-08 | Queda do LLM no meio | item fica recuperável (não some da fila; reprocessa) |
| INT-09 | Troca `LLM_PROVIDER` gemini→local | factory resolve adapter certo (fake nos dois) |

## Resiliência (importante pro caso "sem internet")
| ID | Cenário | Verifica |
| --- | --- | --- |
| RES-01 | Neon indisponível ao confirmar | item permanece na fila; retried depois |
| RES-02 | Reinício do worker com itens PROCESSANDO órfãos | reabilita itens presos (timeout → volta PENDENTE) |
| RES-03 | App Android offline acumula e envia em lote | todos processados, dedup mantém consistência |

## Critérios de pronto (Fase 2)
- Todos INT-* e RES-* verdes contra DB real.
- Nenhum teste depende de Gemini/Telegram reais.
- Rodável em CI com um Postgres efêmero.
