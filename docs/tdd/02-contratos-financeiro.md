# Contratos — Domínio Financeiro

Regras de negócio puras (sem rede). Dinheiro sempre em `Decimal`. Datas via `RelogioFake`.

---

## TRANS — Serviço de transações
Responsabilidade: ciclo de vida da transação e efeito no saldo.

Interface:
```
criar_pendente(extraida, conta_id, usuario_id, possivel_duplicata=False) -> Transacao
confirmar(transacao_id) -> Transacao          # status -> CONFIRMADA
ignorar(transacao_id) -> Transacao            # status -> IGNORADA
```

| ID | Given | When | Then |
| --- | --- | --- | --- |
| TRANS-01 | extraída válida | `criar_pendente` | status `PENDENTE_APROVACAO` |
| TRANS-02 | transação pendente, conta corrente, saída | `confirmar` | saldo da conta cai pelo valor |
| TRANS-03 | transação pendente, entrada | `confirmar` | saldo da conta sobe pelo valor |
| TRANS-04 | transação pendente | `ignorar` | status `IGNORADA`, saldo **não** muda |
| TRANS-05 | confirmar transação já confirmada | `confirmar` | erro/idempotente (não debita 2×) |
| TRANS-06 | forma=`credito` | `confirmar` | saldo da conta corrente **não** muda (ver FAT) |

---

## FAT — Cartão de crédito e faturas (modo "real")
Responsabilidade: crédito vira fatura; saldo só cai ao pagar a fatura; parcelamento.

Interface:
```
alocar_em_fatura(transacao, data_compra) -> Fatura     # acha/cria fatura da competência
gerar_parcelas(transacao, parcelas_total: int) -> list[Transacao]
pagar_fatura(fatura_id, conta_corrente_id) -> Transacao  # cria saída e marca PAGA
```

| ID | Given | When | Then |
| --- | --- | --- | --- |
| FAT-01 | compra crédito antes do fechamento | `alocar_em_fatura` | entra na fatura do mês corrente |
| FAT-02 | compra crédito após dia de fechamento | `alocar_em_fatura` | entra na fatura do **mês seguinte** |
| FAT-03 | compra crédito | `confirmar` (TRANS) | saldo corrente inalterado; `fatura.valor_total += valor` |
| FAT-04 | compra em 3× de R$300 | `gerar_parcelas(3)` | 3 transações de R$100 em 3 competências consecutivas |
| FAT-05 | parcelamento R$100 em 3× | soma das parcelas | == R$100 (sem perda de centavo; ajuste na última parcela) |
| FAT-06 | fatura ABERTA com R$500 | `pagar_fatura` | cria saída de R$500 na conta corrente, fatura vira `PAGA` |
| FAT-07 | pagar fatura já PAGA | `pagar_fatura` | erro/idempotente |
| FAT-08 | limite R$1000, dívida atual R$700 | consulta limite livre | retorna R$300 |
| FAT-09 | compra que excede o limite livre | alerta | sinaliza estouro (não bloqueia, mas marca p/ coaching) |

---

## RENDA — Fontes de renda e dias trabalhados
Responsabilidade: calcular renda prevista por competência conforme regras.

Interface:
```
ganho_do_dia(fonte: FonteRenda, status: "presencial|remoto|falta") -> Decimal
renda_prevista(fonte: FonteRenda, dias_uteis: list[date], excecoes: list[RegistroDia]) -> Decimal
```

Regras (doc 03): padrão = presencial. `remoto` = base + alimentação, **sem** transporte.
`falta` = 0.

| ID | Given | When | Then |
| --- | --- | --- | --- |
| RENDA-01 | fonte fixa_mensal R$1500 | `renda_prevista` | R$1500 independente de dias |
| RENDA-02 | fonte por_dia: base 50 + alim 20 + transp 10, dia presencial | `ganho_do_dia(presencial)` | R$80 |
| RENDA-03 | mesmo, dia remoto | `ganho_do_dia(remoto)` | R$70 (sem transporte) |
| RENDA-04 | mesmo, falta | `ganho_do_dia(falta)` | R$0 |
| RENDA-05 | 20 dias úteis, 0 exceções, por_dia R$80 | `renda_prevista` | R$1600 |
| RENDA-06 | 20 dias úteis, 2 faltas, 3 remotos | `renda_prevista` | 15×80 + 3×70 + 2×0 = R$1410 |
| RENDA-07 | dia fora de `dias_semana` da fonte | não conta | ignorado no cálculo |

---

## COMP — Competência mensal e fechamento
Responsabilidade: consolidar mês, comparar previsto×realizado, acumular sobra.

Interface:
```
total_gasto(competencia_id) -> Decimal             # soma saídas CONFIRMADAS do mês
fechar_mes(competencia, renda_realizada_por_fonte: dict) -> RelatorioFechamento
RelatorioFechamento: { renda_prevista, renda_realizada, total_gasto, sobra,
                       inconsistencias: list[str], por_fonte: dict }
```

| ID | Given | When | Then |
| --- | --- | --- | --- |
| COMP-01 | gastos confirmados 300+200 | `total_gasto` | R$500 (ignora PENDENTE/IGNORADA) |
| COMP-02 | renda prevista 1600, realizada 1600, gasto 500 | `fechar_mes` | `sobra=1100`, sem inconsistências |
| COMP-03 | prevista 1600, realizada 1400 (BNDES pagou menos) | `fechar_mes` | inconsistência registrada na fonte BNDES |
| COMP-04 | fechar_mes | efeito no saldo | `saldo_acumulado` da família += sobra |
| COMP-05 | competência já FECHADA | `fechar_mes` | erro/idempotente (não soma sobra 2×) |
| COMP-06 | sobra negativa (gastou mais que ganhou) | `fechar_mes` | `sobra < 0`, saldo acumulado diminui, alerta de coaching |
