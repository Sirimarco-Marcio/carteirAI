# 02 — Modelo de Dados (Neon / Postgres)

## 1. Diagrama Entidade-Relacionamento

```mermaid
erDiagram
    FAMILIAS ||--o{ USUARIOS : tem
    FAMILIAS ||--o{ RESERVAS : possui
    FAMILIAS ||--o{ COMPETENCIAS : "fecha mês"
    USUARIOS ||--o{ CONTAS : possui
    USUARIOS ||--o{ FONTES_RENDA : "recebe de"
    USUARIOS ||--o{ DIVIDAS_CREDITOS : gerencia
    INSTITUICOES ||--o{ CONTAS : emite
    CONTAS ||--o{ TRANSACOES : origem
    CONTAS ||--o{ FATURAS : "cartão gera"
    CATEGORIAS ||--o{ TRANSACOES : classifica
    FATURAS ||--o{ TRANSACOES : agrupa
    FONTES_RENDA ||--o{ REGISTRO_DIAS : "exceções de dias"
    COMPETENCIAS ||--o{ TRANSACOES : "pertence a"
    FILA_MENSAGENS ||--o| TRANSACOES : "origina"

    FAMILIAS {
        uuid id PK
        text nome
        numeric saldo_acumulado "patrimônio que vai somando"
    }
    USUARIOS {
        uuid id PK
        uuid familia_id FK
        text nome
        text telegram_chat_id
        text role "admin / membro"
    }
    INSTITUICOES {
        uuid id PK
        text nome
        text tipo "banco / carteira / cartao"
    }
    CONTAS {
        uuid id PK
        uuid usuario_id FK
        uuid instituicao_id FK
        text tipo "corrente / credito / dinheiro"
        numeric limite "só cartão"
        numeric saldo_atual "corrente/dinheiro"
        int dia_fechamento "só cartão"
        int dia_vencimento "só cartão"
    }
    CATEGORIAS {
        uuid id PK
        text nome
        text tipo "despesa / receita"
    }
    TRANSACOES {
        text id_hash PK "dedup"
        uuid conta_id FK
        uuid usuario_id FK
        uuid categoria_id FK
        uuid fatura_id FK "null se não-cartão"
        uuid competencia_id FK
        numeric valor
        timestamptz data_hora
        text estabelecimento
        text tipo "entrada / saida"
        text forma "debito / credito / pix / dinheiro"
        int parcela_atual "ex: 1"
        int parcelas_total "ex: 3"
        text status "PENDENTE_APROVACAO / CONFIRMADA / IGNORADA"
        bool possivel_duplicata "soft-match: vai p/ confirmação especial"
        text origem "notificacao / manual"
    }
    FATURAS {
        uuid id PK
        uuid conta_id FK "cartão"
        int mes
        int ano
        numeric valor_total
        date vencimento
        text status "ABERTA / FECHADA / PAGA"
    }
    FONTES_RENDA {
        uuid id PK
        uuid usuario_id FK
        text nome "UERJ / Convem / BNDES"
        text tipo_calculo "fixo_mensal / por_dia"
        numeric valor_base "mensal OU por dia"
        numeric valor_alimentacao_dia
        numeric valor_transporte_dia
        jsonb dias_semana "[1,2,3,4,5] = seg-sex"
        bool ativa
    }
    REGISTRO_DIAS {
        uuid id PK
        uuid fonte_renda_id FK
        date data
        text status "presencial / remoto / falta"
    }
    COMPETENCIAS {
        uuid id PK
        uuid familia_id FK
        int mes
        int ano
        numeric renda_prevista
        numeric renda_realizada "preenchido no /fechar_mes"
        numeric total_gasto
        numeric sobra
        text status "ABERTA / FECHADA"
    }
    RESERVAS {
        uuid id PK
        uuid familia_id FK
        text nome
        text tipo "reserva / investimento"
        numeric saldo
    }
    DIVIDAS_CREDITOS {
        uuid id PK
        uuid usuario_id FK
        text contraparte_nome
        text tipo "devo / me_devem"
        numeric valor
        date vencimento
        text status "aberta / quitada"
    }
    FILA_MENSAGENS {
        text id_hash PK
        text texto_bruto
        uuid usuario_id FK
        text origem "notificacao / manual"
        text status "PENDENTE / PROCESSANDO / CONCLUIDO / DUPLICADA / ERRO"
        timestamptz criada_em
        timestamptz processada_em
    }
```

## 2. Notas de modelagem

- **`saldo_acumulado` (família):** cresce com a sobra de cada competência fechada.
  Mover para `RESERVAS` é opcional e manual.
- **Cartão de crédito (modo real):** uma compra no crédito **não** mexe no
  `saldo_atual`. Ela entra como `TRANSACAO (forma=credito)` ligada a uma `FATURA`
  da competência correspondente. O `saldo_atual` só cai quando a fatura é paga
  (`/pagar_fatura` → cria uma transação de saída na conta corrente e marca a fatura `PAGA`).
- **Parcelamento:** uma compra em N vezes gera N transações (ou 1 transação +
  N registros de parcela), cada uma na fatura da sua competência. Assim a IA consegue
  alertar "você já comprometeu R$X dos próximos meses".
- **Renda por dia (BNDES):** `REGISTRO_DIAS` guarda só as **exceções**. O padrão é
  presencial nos `dias_semana` da fonte. `falta` = não ganha nada no dia.
  `remoto` = ganha `valor_base` + `valor_alimentacao_dia`, **sem** `valor_transporte_dia`.
- **Dedup (dois níveis):**
  - `id_hash` (PK de `FILA_MENSAGENS`) = hash do **texto bruto normalizado** →
    detecta a *mesma* notificação reenviada (retry) e descarta automaticamente.
  - **Soft-match** sobre `TRANSACOES` = `(usuario_id + valor + estabelecimento)` dentro
    de uma janela de tempo → marca `possivel_duplicata=true` e manda pra **confirmação
    especial** no Telegram. Nunca descarta uma possível 2ª compra legítima sem perguntar.
