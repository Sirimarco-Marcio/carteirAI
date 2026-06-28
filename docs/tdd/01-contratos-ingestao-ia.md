# Contratos — Ingestão & IA

Cada bloco: **interface** (contrato, não implementação) + **casos de teste** com ID.

---

## FILA — Fila de mensagens (SQLite)
Responsabilidade: durabilidade e estados da mensagem bruta.

Interface:
```
enqueue(texto_bruto: str, usuario_id: str, origem: "notificacao|manual") -> Item
fetch_next() -> Item | None        # pega 1 PENDENTE e marca PROCESSANDO (atômico)
marcar(item_id, status: "CONCLUIDO|DUPLICADA|ERRO") -> None
Item: { id, texto_bruto, usuario_id, origem, status, criada_em, processada_em }
```

| ID | Given | When | Then |
| --- | --- | --- | --- |
| FILA-01 | fila vazia | `enqueue("compra R$10")` | item criado com status `PENDENTE` e `criada_em` setado |
| FILA-02 | 1 item PENDENTE | `fetch_next()` | retorna o item e seu status vira `PROCESSANDO` |
| FILA-03 | fila vazia | `fetch_next()` | retorna `None` |
| FILA-04 | 2 itens PENDENTE | `fetch_next()` 2× | retorna em ordem de chegada (FIFO) |
| FILA-05 | item em PROCESSANDO | `fetch_next()` | **não** retorna o mesmo item (sem reprocessar) |
| FILA-06 | item PROCESSANDO | `marcar(id, "CONCLUIDO")` | status `CONCLUIDO`, `processada_em` setado |
| FILA-07 | 2 workers chamam `fetch_next()` no mesmo item | concorrência | só **um** recebe o item (claim atômico) |

---

## DEDUP — Deduplicação em dois níveis
Responsabilidade: distinguir notificação repetida de 2ª compra legítima.

Interface:
```
hash_exato(texto_bruto: str) -> str           # normaliza (trim, espaços, caixa) e faz hash
ja_processado(hash: str) -> bool               # consulta histórico de hashes
soft_match(usuario_id, valor: Decimal, estabelecimento: str,
           data_hora: datetime, janela_min: int = 10) -> bool
```

| ID | Given | When | Then |
| --- | --- | --- | --- |
| DEDUP-01 | dois textos idênticos | `hash_exato` em ambos | mesmo hash |
| DEDUP-02 | textos iguais com espaços/caixa diferentes | `hash_exato` | mesmo hash (normalização) |
| DEDUP-03 | textos diferentes | `hash_exato` | hashes diferentes |
| DEDUP-04 | hash já no histórico | `ja_processado(hash)` | `True` (duplicata exata → descarte) |
| DEDUP-05 | hash inédito | `ja_processado(hash)` | `False` |
| DEDUP-06 | transação igual (mesmo usuário+valor+estab.) há 3 min | `soft_match(janela=10)` | `True` (possível duplicata) |
| DEDUP-07 | transação igual há 30 min | `soft_match(janela=10)` | `False` (fora da janela) |
| DEDUP-08 | mesmo valor, **estabelecimento diferente** | `soft_match` | `False` |
| DEDUP-09 | mesmo valor/estab., **usuário diferente** | `soft_match` | `False` |
| DEDUP-10 | valores `10.00` vs `10.0` (Decimal) | `soft_match` | `True` (comparação numérica, não string) |

---

## LLM — Adapter `BaseLLM` (Ports & Adapters)
Responsabilidade: extrair `TransacaoExtraida` de texto livre. Trocável por env.

Interface:
```
class BaseLLM(ABC):
    async def extrair(texto: str, feedback: list[str] | None = None) -> TransacaoExtraida   # pode lançar LLMError
resolver_llm(provider: "gemini|local") -> BaseLLM        # factory por env LLM_PROVIDER
```
> `feedback` (reflexão): na 1ª tentativa é `None`. Quando o auditor reprova por **divergência**,
> a orquestração rechama `extrair` passando as falhas do auditor como `feedback`; o adapter as
> injeta no prompt ("o valor X que você extraiu não aparece no texto; os valores presentes são [...]; corrija").
> O adapter real (integração) incorpora o feedback no prompt; o `FakeLLM` apenas **registra** o
> feedback recebido (para os testes de ORQ verificarem que a reflexão aconteceu).

| ID | Given | When | Then |
| --- | --- | --- | --- |
| LLM-01 | `LLM_PROVIDER=gemini` | `resolver_llm()` | retorna instância de `GeminiAdapter` |
| LLM-02 | `LLM_PROVIDER=local` | `resolver_llm()` | retorna instância de `LocalSSHAdapter` |
| LLM-03 | provider inválido | `resolver_llm("x")` | lança `ValueError` |
| LLM-04 | `FakeLLM` programado p/ retornar transação | `extrair(texto)` | devolve `TransacaoExtraida` com campos preenchidos |
| LLM-05 | `FakeLLM` simulando timeout | `extrair` | lança `LLMError` (orquestração trata, ver ORQ) |
| LLM-06 | resposta com categoria fora da lista autorizada | `extrair` | categoria cai em `Outros` (normalização pós-LLM) |
| LLM-07 | (contrato comum) ambos adapters | implementam a interface `BaseLLM` | teste de conformidade roda igual nos dois via FakeLLM |

> Adapters reais (Gemini/SSH) **não** têm teste unitário com rede — só conformidade de
> interface via fake + teste de integração (Fase 2).

---

## AUDITOR — Validação anti-alucinação (RegEx)
Responsabilidade: garantir que valor e data extraídos **existem literalmente** no texto.

Interface:
```
auditar(texto_bruto: str, extraida: TransacaoExtraida) -> ResultadoAuditoria
ResultadoAuditoria: { ok: bool, falhas: list[str] }
```

| ID | Given | When | Then |
| --- | --- | --- | --- |
| AUD-01 | texto "R$ 49,90 em 20/06" e extraída valor=49.90 data=20/06 | `auditar` | `ok=True` |
| AUD-02 | extraída valor=**500.00** ausente no texto | `auditar` | `ok=False`, falha menciona "valor" |
| AUD-03 | data extraída não aparece no texto | `auditar` | `ok=False`, falha menciona "data" |
| AUD-04 | valor no texto como `49.90` e extraída `49,90` | `auditar` | `ok=True` (normaliza vírgula/ponto) |
| AUD-05 | valor com separador de milhar `1.299,00` | `auditar` | `ok=True` |
| AUD-06 | texto sem valor algum | `auditar` | `ok=False` |

### Extensão: confirmação de `tipo` e `forma` por regex (AUD-07..13)
> Decisão Chunk B (`docs/06`): a IA extrai `tipo`/`forma`, mas um **regex determinístico** confirma.
> **Conservador:** só acusa falha quando o texto evidencia **exatamente uma** categoria e ela
> **contradiz** a extraída. Texto sem pista (ou ambíguo, com pistas de +de uma) → **não acusa**
> (confia na IA). Não altera o comportamento de valor/data (AUD-01..06 seguem válidos).

Palavras-chave (case-insensitive), por categoria evidenciada no texto:
- **tipo=entrada:** "você recebeu", "recebeu", "recebido", "recebida", "depósito", "deposito",
  "creditado", "crédito em conta", "entrada de".
- **tipo=saida:** "compra", "você pagou", "pagou", "pagamento", "saque", "você enviou", "enviou",
  "débito de", "debitado", "gasto".
- **forma=credito:** "no crédito", "cartão de crédito", "compra no crédito", "parcelado",
  "parcelas", "fatura". *(NÃO usar "crédito" sozinho — colide com "crédito em conta", que é entrada.)*
- **forma=debito:** "no débito", "cartão de débito", "débito automático", "compra no débito".
- **forma=pix:** "pix".
- **forma=dinheiro:** "dinheiro", "espécie", "especie".

Regra: para `tipo` (e idem `forma`), monte o conjunto de categorias evidenciadas. Se houver
**exatamente uma** e ela for **diferente** da extraída → falha mencionando "tipo" (ou "forma").
Zero ou mais de uma categoria evidenciada → sem falha.

| ID | Given | When | Then |
| --- | --- | --- | --- |
| AUD-07 | texto "você recebeu R$ 100 em 20/06" (entrada), extraída `tipo=saida` | `auditar` | `ok=False`, falha menciona "tipo" |
| AUD-08 | texto "Compra de R$ 50 em 20/06" (saida), extraída `tipo=entrada` | `auditar` | `ok=False`, falha menciona "tipo" |
| AUD-09 | texto sem pista de tipo ("Lançamento R$ 50 em 20/06"), extraída `tipo=saida` | `auditar` | sem falha de "tipo" |
| AUD-10 | texto "compra no crédito R$ 50 em 20/06", extraída `forma=debito` | `auditar` | `ok=False`, falha menciona "forma" |
| AUD-11 | texto "Pix de R$ 50 em 20/06", extraída `forma=credito` | `auditar` | `ok=False`, falha menciona "forma" |
| AUD-12 | texto sem pista de forma, extraída `forma=pix` | `auditar` | sem falha de "forma" |
| AUD-13 | texto "compra no crédito de R$ 50 em 20/06", extraída `tipo=saida` `forma=credito` | `auditar` | `ok=True` (tudo confere) |

---

## ORQ — Orquestração (LangGraph) — fluxo A+B end-to-end (com fakes)
Responsabilidade: amarrar dedup → LLM → auditor → decisão de status.

Interface:
```
class Orquestrador:
    def __init__(self, fila, transacao_repo,
                 llm_principal: BaseLLM, llm_fallback: BaseLLM | None = None,
                 max_tentativas: int = 3): ...   # D8: 1 original + 2 corretivas por provider
    async def processar(item: Item) -> ResultadoProcessamento
```

**Laço de extração (reflexão + fallback de provider) — o "agente de leitura":**
1. **Dedup exato:** `ja_processado(hash)` → se sim, `DUPLICADA` (LLM nunca é chamado).
2. Para cada provider em `[principal] (+ [fallback] se houver)`:
   - repetir até `max_tentativas` vezes:
     - `extraida = await provider.extrair(texto, feedback=falhas)` — na 1ª, `feedback=None`.
       - se lançar `LLMError` → **abandona este provider** e vai pro próximo (não conta como divergência).
     - `res = auditar(texto, extraida)`. **Falhas de "data" são ignoradas** (a `data_hora` vem do
       `posted_at`, não do texto — ver `docs/06` A.4). Considere só as **falhas relevantes**
       (valor, tipo, forma):
       - **sem falhas relevantes** → soft-match? define `possivel_duplicata`; persiste
         `PENDENTE_APROVACAO`; fila `CONCLUIDO`. **Fim.**
       - falha por **ausência de número** (não é transação) → `IGNORADA` na hora (**não** retenta,
         **não** chama outro provider); fila `CONCLUIDO`. **Fim.**
       - falha por **divergência** (valor que não bate, **ou** `tipo`/`forma` que o texto contradiz)
         → guarda as falhas relevantes como `feedback` e repete (reflexão).
3. Esgotou todos os providers/tentativas → `ERRO` (`motivo_erro` preenchido), **não persiste** transação; fila `ERRO`; vai pro humano.

> Teto de custo: ≤ `max_tentativas` chamadas por provider. `IGNORADA` e `DUPLICADA` nunca gastam retry.
> `tentativas` no `ResultadoProcessamento` registra quantas chamadas ao LLM ocorreram (observabilidade).

| ID | Given | When | Then |
| --- | --- | --- | --- |
| ORQ-01 | hash já processado | `processar(item)` | status `DUPLICADA`, sem chamar LLM |
| ORQ-02 | conteúdo novo, LLM ok na 1ª, auditor ok, sem soft-match | `processar` | `PENDENTE_APROVACAO`, `possivel_duplicata=False`, `tentativas==1` |
| ORQ-03 | conteúdo novo, soft-match positivo | `processar` | `PENDENTE_APROVACAO`, `possivel_duplicata=True` |
| ORQ-04 | `LLMError` em TODOS os providers | `processar` | status `ERRO`, `motivo_erro` preenchido, **fila `ERRO`** (não CONCLUIDO) |
| ORQ-05 | divergência persiste e **esgota** as tentativas em todos os providers | `processar` | status `ERRO`, **não persiste** transação |
| ORQ-06 | sucesso | `processar` | item da fila marcado `CONCLUIDO` |
| ORQ-07 | duplicata exata | `processar` | item da fila marcado `DUPLICADA` |
| ORQ-08 | dedup exato dispara | `processar` | `FakeLLM.chamadas == 0` (LLM nunca chamado) |
| ORQ-09 | **reflexão**: principal erra o valor na 1ª, acerta na 2ª (com feedback) | `processar` | `PENDENTE_APROVACAO`; `FakeLLM.chamadas == 2`; a 2ª chamada recebeu `feedback` não-vazio com as falhas do auditor |
| ORQ-10 | **fallback por divergência**: principal sempre diverge (esgota `max_tentativas`), fallback acerta | `processar` | `PENDENTE_APROVACAO`; principal chamado `max_tentativas`×; fallback chamado e usado |
| ORQ-11 | **fallback por erro**: principal lança `LLMError`, fallback acerta na 1ª | `processar` | `PENDENTE_APROVACAO` via fallback; principal não consome todas as tentativas (abandonado no erro) |
| ORQ-12 | texto **sem valor** (não é transação) | `processar` | status `IGNORADA`; `FakeLLM.chamadas == 1` (sem retry); fila `CONCLUIDO`; transação não persistida |
| ORQ-13 | reflexão desligada (`max_tentativas=1`), divergência, sem fallback | `processar` | status `ERRO` na 1ª falha (comportamento legado, sem reflexão) |
| ORQ-14 | texto evidencia `tipo=entrada` ("você recebeu…"); principal extrai `tipo=saida` na 1ª e `tipo=entrada` na 2ª | `processar` | `PENDENTE_APROVACAO`; `chamadas==2`; a 2ª chamada recebeu `feedback` contendo "tipo" |
| ORQ-15 | texto evidencia `forma=credito` ("compra no crédito…"); principal extrai `forma=debito` na 1ª e `forma=credito` na 2ª | `processar` | `PENDENTE_APROVACAO`; `chamadas==2`; `feedback` da 2ª contém "forma" |
| ORQ-16 | divergência de `tipo` persiste e esgota tentativas, sem fallback | `processar` | status `ERRO`, **não persiste** (tipo é tratado como divergência, igual a valor) |
| ORQ-17 | texto sem pista de tipo/forma, valor confere (caso atual) | `processar` | `PENDENTE_APROVACAO` (a extensão de tipo/forma não introduz falsos positivos) |
| ORQ-18 | item possui `data_hora` (posted_at) **≠** `criada_em` | `processar` | a transação salva usa `data_hora` (posted_at) como momento — não `criada_em`. Item sem `data_hora` (legado) usa `criada_em`. |

> **Nota (data):** o auditor ainda reporta falha de "data" (AUD-03), mas o orquestrador a **ignora**
> — a data efetiva vem do `posted_at` do item, não do texto da notificação.
