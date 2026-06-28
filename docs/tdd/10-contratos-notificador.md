# 10 — Contratos: Notificador (worker → Telegram)  `NOTIF-*`

> Fonte: `docs/06` (Chunk C). O `WorkerIngestao` chama `notificador.notificar(resultado, item)` para
> cada item processado. O `NotificadorTelegram` traduz o `ResultadoProcessamento` em ação no Telegram,
> **reusando `ServicoAprovacao.solicitar_aprovacao`** (mensagem + botões + roteamento do chat do dono).

## Classe alvo
`carteirai.telegram.notificador.NotificadorTelegram`
- Construtor: `NotificadorTelegram(servico_aprovacao)`.
  - `servico_aprovacao`: instância de `ServicoAprovacao` (já resolve chat do dono e monta os botões).
- Método: `notificar(resultado: ResultadoProcessamento, item) -> None`.
  - `item` é um `ItemFilaIngestao` (tem `texto_bruto`, `usuario_id`, `data_hora`).

## Comportamento
- **`PENDENTE_APROVACAO`:** constrói uma `Transacao` a partir de `resultado.transacao` + `item`
  (`id = hash_exato(item.texto_bruto)`, `usuario_id = item.usuario_id`, `valor/estabelecimento/
  categoria/forma/tipo` de `resultado.transacao`, `data_hora = resultado.transacao.data_hora`,
  `possivel_duplicata = resultado.possivel_duplicata`, `conta_id = ""`) e chama
  `servico_aprovacao.solicitar_aprovacao(transacao)`.
- **`IGNORADA`, `DUPLICADA`, `ERRO`:** **silencioso** (não envia nada). *(Alerta de ERRO/DLQ é
  uma melhoria futura — ver task #9.)*

## Casos
- **NOTIF-01 — aprovação normal.** `status=PENDENTE_APROVACAO`, `possivel_duplicata=False` →
  1 envio ao **chat do dono** (resolvido via `UsuarioRepo`) com botões **Sim/Não/Editar**.
- **NOTIF-02 — possível duplicata.** `possivel_duplicata=True` → mensagem de duplicata com botões
  **"É a mesma"/"É nova"**.
- **NOTIF-03 — IGNORADA → silêncio.** nada é enviado.
- **NOTIF-04 — DUPLICADA → silêncio.** nada é enviado.
- **NOTIF-05 — ERRO → silêncio.** nada é enviado.
- **NOTIF-06 — id nos botões.** O `callback_data` dos botões usa `hash_exato(item.texto_bruto)`
  (o mesmo id com que a transação foi persistida).
- **NOTIF-07 — chat do dono.** O envio vai ao `chat_id` de `item.usuario_id` (via `UsuarioRepo`;
  membro sem chat cai no admin, conforme `chat_id_de`).

## Notas de teste
- Use `ServicoAprovacao(FakeTelegram(), FakeUsuarioRepo({usuario: chat}), None, None)` — `solicitar_aprovacao`
  só usa telegram + usuario_repo. Asserções sobre `FakeTelegram.enviados` (tuplas `(chat_id, texto, botoes)`).
- `item` pode ser um `ItemFilaIngestao` real (engine não é necessário; construa o DTO direto) ou um
  objeto simples com `texto_bruto`/`usuario_id`/`data_hora`.
</content>
