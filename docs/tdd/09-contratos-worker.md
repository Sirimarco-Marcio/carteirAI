# 09 — Contratos: Worker de Ingestão  `WORKER-*`

> Fonte: `docs/06-arquitetura-alvo.md` (Chunk C). O worker é um daemon no Pi que, a cada ciclo
> (`tick`, ~10 min), recupera órfãos e drena a `fila_ingestao`, delegando cada item ao Orquestrador
> e notificando o resultado. Aqui testamos a **disciplina do loop** (reaper + drenagem + resiliência
> + notificação), com colaboradores fakes. O roteamento/conteúdo da notificação (chat do dono,
> botões) e a fiação com o Orquestrador real são integração (depois).

## Classe alvo
`carteirai.orquestracao.worker.WorkerIngestao`
- Construtor: `WorkerIngestao(fila, orquestrador, notificador)`.
  - `fila`: a `FilaIngestao` (claim/recuperar_orfaos/marcar) — real (SQLite) nos testes.
  - `orquestrador`: porta com `async processar(item) -> ResultadoProcessamento`. (fake nos testes)
  - `notificador`: porta com `notificar(resultado, item) -> None`. (fake nos testes)
- Método principal: `async tick() -> None`.

## Comportamento do `tick()`
1. **Drena** a fila: em laço, `item = fila.claim()`; se `None`, para. Para cada item:
   - `res = await orquestrador.processar(item)`.
   - `notificador.notificar(res, item)`.
2. Ao **fim**, chama `fila.recuperar_orfaos()` **uma vez**.
   - *Por que no fim, não no início:* um órfão recuperado volta a PENDENTE e só é reprocessado no
     **próximo** tick (~10 min depois) — em vez de ser re-drenado no mesmo ciclo que pode tê-lo
     deixado órfão. Evita reprocessamento imediato de algo que acabou de falhar.
3. **Resiliência:** se `processar` levantar exceção para um item, o worker **marca esse item como
   ERRO** (`fila.marcar(item.id, "ERRO")`) e **continua** com os próximos — um item ruim não derruba
   o ciclo. Não notifica resultado nesse caso (não há `res`).

## Casos
- **WORKER-01 — reaper a cada tick.** `tick()` chama `fila.recuperar_orfaos()` exatamente uma vez.
- **WORKER-02 — drena tudo.** Com N itens PENDENTE, `tick()` chama `processar` N vezes; ao fim, não
  há PENDENTE (a fila esvazia — `claim()` passou a devolver `None`).
- **WORKER-03 — ordem FIFO.** Os itens são processados na ordem de enfileiramento (menor id primeiro).
- **WORKER-04 — fila vazia.** Sem PENDENTE, `tick()` roda o reaper mas **não** chama `processar` nem
  `notificar`.
- **WORKER-05 — notifica cada resultado.** Para cada item processado, `notificador.notificar` é
  chamado uma vez com o `ResultadoProcessamento` e o item correspondentes.
- **WORKER-06 — resiliência a exceção.** Se `processar` levantar exceção em 1 de N itens, esse item
  termina em `ERRO`, os outros N-1 são processados normalmente, e o `tick()` não propaga a exceção.
- **WORKER-07 — fake do orquestrador por sequência.** (apoio) O fake do orquestrador deve permitir
  programar uma sequência de resultados/exceções por item, e registrar os itens recebidos.

## Fora deste contrato (próximos)
- Roteamento da notificação (chat do dono via UsuarioRepo, botões de aprovação/duplicata) → reaproveitar `telegram/aprovacao.py`.
- `data_hora` = `posted_at` do item (ajuste no Orquestrador, ligado a A5/task #10).
- Aviso no Telegram quando item cai na DLQ (ERRO via reaper).
- Fiação real: FilaIngestao + Orquestrador real + adapters de LLM (integração).
</content>
