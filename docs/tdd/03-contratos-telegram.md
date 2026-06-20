# Contratos — Telegram (comandos, callbacks, aprovação)

Testados com `FakeTelegram` (captura envios, injeta callbacks). Sem rede real.

---

## APROV — Roteamento de aprovação (Human-in-the-Loop)
Responsabilidade: mandar a confirmação pro chat de **quem fez o gasto** (dono da conta).

Interface:
```
solicitar_aprovacao(transacao) -> None   # envia mensagem + inline keyboard ao dono
tratar_callback(callback) -> ResultadoCallback
```

| ID | Given | When | Then |
| --- | --- | --- | --- |
| APROV-01 | transação da conta do usuário A | `solicitar_aprovacao` | mensagem enviada ao `telegram_chat_id` de A |
| APROV-02 | transação normal | `solicitar_aprovacao` | teclado tem `[Sim] [Não] [Editar]` |
| APROV-03 | transação `possivel_duplicata=True` | `solicitar_aprovacao` | mensagem de duplicata + `[É a mesma] [É nova]` |
| APROV-04 | callback `[Sim]` | `tratar_callback` | transação vira `CONFIRMADA` |
| APROV-05 | callback `[Não]` | `tratar_callback` | transação vira `IGNORADA` |
| APROV-06 | callback `[É a mesma]` (duplicata) | `tratar_callback` | transação `IGNORADA` |
| APROV-07 | callback `[É nova]` (duplicata) | `tratar_callback` | transação `CONFIRMADA` |
| APROV-08 | callback de transação já resolvida | `tratar_callback` | responde "já tratada", sem reprocessar |
| APROV-09 | callback de chat que não é o dono | `tratar_callback` | rejeitado (não autorizado) |

---

## CMD — Comandos do bot
Responsabilidade: parsear comando e responder. Lógica de negócio delegada aos serviços.

Interface (cada handler recebe `args`, devolve texto/estrutura de resposta):
```
/saldo /giro /cartao /limite /gastos [categoria] /relatorio
/lancar /faltei [data] /fechar_mes /pagar_fatura /divida /pendentes /desfazer
```

| ID | Given | When | Then |
| --- | --- | --- | --- |
| CMD-01 | usuário com saldo 1234.56 | `/saldo` | resposta contém o saldo formatado em R$ |
| CMD-02 | `/gastos mercado` | mês com 3 compras de mercado | soma só categoria mercado |
| CMD-03 | `/gastos categoria_inexistente` | — | mensagem de categoria inválida (lista autorizada) |
| CMD-04 | `/faltei` sem data | hoje é dia útil | registra falta na data de hoje |
| CMD-05 | `/faltei 18/06` | — | cria `RegistroDia(status=falta, data=18/06)` |
| CMD-06 | `/faltei` em data já registrada | — | atualiza o registro (não duplica) |
| CMD-07 | `/pendentes` com 2 transações PENDENTE | — | lista as 2 |
| CMD-08 | `/desfazer` após uma confirmação | — | reverte a última transação confirmada (volta saldo) |
| CMD-09 | `/pagar_fatura` cartão sem fatura aberta | — | mensagem "sem fatura em aberto" |
| CMD-10 | comando desconhecido `/xyz` | — | mensagem de ajuda com comandos válidos |
| CMD-11 | `/lancar` (manual) | fluxo guiado | cria transação `origem=manual` PENDENTE_APROVACAO |

---

## WEBHOOK/POLL — Recebimento de mensagem bruta
Responsabilidade: transformar update do Telegram em item da fila.

| ID | Given | When | Then |
| --- | --- | --- | --- |
| ING-01 | update de texto (notificação) | handler de ingestão | `enqueue(origem=notificacao)` chamado |
| ING-02 | update que é comando `/saldo` | handler | **não** enfileira; roteia pro CMD |
| ING-03 | update de chat desconhecido (não cadastrado) | handler | ignora (segurança) |
| ING-04 | mesmo update entregue 2× pelo Telegram | handler | dedup exato evita item duplicado na fila |
