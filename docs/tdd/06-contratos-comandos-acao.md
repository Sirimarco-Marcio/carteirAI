# 06 — Contratos: Comandos de Ação do Bot

> Bloco 3 do roadmap. Expande `DespachanteComandos` com os comandos de mutação:
> `/faltei`, `/lancar`, `/pagar_fatura`, `/desfazer`.
> Contrato complementa CMD-01..07/10 já implementados.

---

## Contexto

O `DespachanteComandos` atual (em `telegram/comandos.py`) cobre apenas consultas.
Os novos comandos precisam de acesso a serviços de escrita:

```python
class DespachanteComandos:
    def __init__(
        self,
        consultas: ConsultaFinanceira,
        renda_svc: RendaService | None = None,      # novo
        transacao_svc: TransacaoService | None = None,  # novo
        faturas_svc: FaturaService | None = None,   # novo
    ) -> None: ...
```

Os services são injetados opcionalmente — se None, o comando responde
"funcionalidade indisponível" (não quebra). Isso permite testes unitários focados.

---

## CMD-04 — /faltei (sem data)

**Dado** `/faltei` (sem argumento), usuário tem fonte BNDES ativa  
**Quando** `processar` é chamado  
**Então**:
- cria `RegistroDia(fonte_renda_id=<BNDES>, data=hoje, status="falta")`
- responde `"✅ Falta registrada para hoje (DD/MM)."`

## CMD-05 — /faltei com data

**Dado** `/faltei 18/06`  
**Então**:
- cria `RegistroDia(data=date(ano_atual, 6, 18), status="falta")`
- responde `"✅ Falta registrada para 18/06."`

## CMD-05b — /faltei com data inválida

**Dado** `/faltei 99/99`  
**Então** responde `"Data inválida. Use: /faltei DD/MM"`

## CMD-06 — /faltei em data já registrada (idempotente)

**Dado** `RegistroDia` já existe para a data  
**Quando** `/faltei` é chamado de novo para a mesma data  
**Então** atualiza (upsert) e responde `"✅ Falta registrada para DD/MM."` (não duplica)

---

## CMD-08 — /desfazer

**Dado** última transação do usuário tem status `CONFIRMADA`  
**Quando** `/desfazer`  
**Então**:
- transação volta para `PENDENTE_APROVACAO` (ou `IGNORADA` → não reverte — só CONFIRMADA)
- efeito no saldo é revertido (saldo volta ao estado anterior)
- responde `"↩️ Última transação desfeita: R$ X,XX em <estabelecimento>."`

## CMD-08b — /desfazer sem transação confirmada

**Dado** usuário não tem nenhuma transação CONFIRMADA  
**Então** responde `"Nenhuma transação para desfazer."`

---

## CMD-09 — /pagar_fatura sem fatura aberta

**Dado** conta de cartão sem nenhuma fatura ABERTA  
**Quando** `/pagar_fatura`  
**Então** responde `"Sem fatura em aberto."`

## CMD-09b — /pagar_fatura com fatura aberta

**Dado** fatura ABERTA de R$ 500,00  
**Quando** `/pagar_fatura`  
**Então**:
- chama `faturas_svc.pagar_fatura(fatura_id, conta_corrente_id)`
- responde `"✅ Fatura de R$ 500,00 paga. Saldo debitado da conta corrente."`

## CMD-09c — /pagar_fatura com múltiplas faturas abertas

**Dado** 2 faturas abertas (dois cartões)  
**Então** lista as faturas com valores e pede confirmação (ex: "Qual fatura pagar? Responda 1 ou 2.")

---

## CMD-11 — /lancar (lançamento manual)

**Dado** `/lancar`  
**Quando** o usuário envia o comando  
**Então** responde com template guiado:
```
📝 Lançamento manual. Responda neste formato:
valor | categoria | forma (debito/credito/pix/dinheiro) | descrição (opcional)
Exemplo: 45.90 | Alimentação | pix | almoço no centro
```

## CMD-11b — /lancar com payload completo

**Dado** `/lancar 45.90 | Alimentação | pix | almoço`  
**Quando** processar  
**Então**:
- cria transação `origem=manual`, `status=PENDENTE_APROVACAO`
- `valor=45.90`, `categoria="Alimentação"`, `forma="pix"`, `estabelecimento="almoço"`
- responde `"✅ Transação criada. Confirme no Telegram."`

## CMD-11c — /lancar com categoria inválida

**Dado** `/lancar 45.90 | CategoriaErrada | pix`  
**Então** responde com lista de categorias válidas

---

## Interface dos Services (injeção no DespachanteComandos)

```python
class RendaService(Protocol):
    def registrar_dia(self, usuario_id: str, data: date, status: StatusDia) -> RegistroDia: ...
    def ultima_fonte_ativa(self, usuario_id: str) -> FonteRenda | None: ...

class TransacaoService(Protocol):
    def desfazer_ultima(self, usuario_id: str) -> Transacao | None: ...
    def criar_manual(self, usuario_id: str, valor: Decimal, categoria: str,
                     forma: str, descricao: str) -> Transacao: ...

class FaturaService(Protocol):
    def faturas_abertas(self, usuario_id: str) -> list[Fatura]: ...
    def pagar(self, fatura_id: str, conta_corrente_id: str) -> Transacao: ...
```

> **Nota**: `RendaService` e `TransacaoService` não são novos serviços — são protocolos
> que as classes existentes `financeiro/renda.py` e `financeiro/transacoes.py` já satisfazem
> (ou satisfarão com métodos adicionais mínimos). Verificar antes de implementar.

---

## Fakes a adicionar em `tests/fakes.py`

```python
class FakeRendaService:
    """Fake de RendaService. Registra chamadas a registrar_dia() em `registros`."""
    registros: list[RegistroDia]
    def registrar_dia(self, usuario_id, data, status) -> RegistroDia: ...
    def ultima_fonte_ativa(self, usuario_id) -> FonteRenda | None: ...

class FakeTransacaoServiceCmd:
    """Fake de TransacaoService para CMD. Permite programar a última transação."""
    def desfazer_ultima(self, usuario_id) -> Transacao | None: ...
    def criar_manual(self, usuario_id, valor, categoria, forma, descricao) -> Transacao: ...

class FakeFaturaServiceCmd:
    """Fake de FaturaService para CMD."""
    def faturas_abertas(self, usuario_id) -> list[Fatura]: ...
    def pagar(self, fatura_id, conta_corrente_id) -> Transacao: ...
```
