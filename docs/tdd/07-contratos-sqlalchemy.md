# Contratos — Implementação Real SQLAlchemy (Bloco 4)

> O domínio já foi coberto por TDD usando dublês (fakes).
> Estes contratos cobrem as implementações REAIS dos repositórios
> usando SQLAlchemy e Postgres (`db/migrations/0001_init.sql`).

---

## 1. Mapeamento Repositório → Tabela(s)

Os repositórios a implementar no módulo `src/carteirai/infra/sqlalchemy_repos.py`:

| Interface Fake (Referência) | Tabela Principal | Repositório Real (SQLAlchemy) |
|---|---|---|
| `FakeContaRepo` | `contas` | `SqlAlchemyContaRepo` |
| `FakeTransacaoStore` (TRANS) | `transacoes` | `SqlAlchemyTransacaoRepo` |
| `FakeFaturaRepo` | `faturas` | `SqlAlchemyFaturaRepo` |
| `FakeFamiliaRepo` | `familias` | `SqlAlchemyFamiliaRepo` |
| `FakeUsuarioRepo` | `usuarios` | `SqlAlchemyUsuarioRepo` |
| `FakeFonteRepo` | `fontes_renda` | `SqlAlchemyFonteRepo` |
| `FakeRegistroDiaRepo` | `registro_dias` | `SqlAlchemyRegistroDiaRepo` |

---

## 2. CONTA-SQL — SqlAlchemyContaRepo

**Responsabilidade**: Saldo de contas correntes e limite de cartões.

| ID | Given | When | Then |
|---|---|---|---|
| SQL-C1 | Banco com Conta A e Saldo 100 | `buscar(conta_id)` | Retorna DTO `Conta(id=A, saldo_atual=100, ...)` |
| SQL-C2 | Conta A com Saldo 100 | `atualizar_saldo(A, 50)` | UPDATE na tabela `contas` setando `saldo_atual = 50`; Commit efetuado |
| SQL-C3 | ID de conta inexistente | `buscar(inexistente)` | Retorna `None` |

---

## 3. TRANS-SQL — SqlAlchemyTransacaoRepo

**Responsabilidade**: Buscar e atualizar Transações.

| ID | Given | When | Then |
|---|---|---|---|
| SQL-T1 | Transação nova (Pendente) | `salvar(transacao)` | INSERT na tabela `transacoes`; `origem` inserida corretamente |
| SQL-T2 | Transação existente | `buscar(id_hash)` | Retorna DTO `Transacao` perfeitamente mapeado |
| SQL-T3 | Transação alterada p/ CONFIRMADA | `atualizar(transacao)` | UPDATE do `status` para `CONFIRMADA` na tabela |
| SQL-T4 | - | `buscar_ultima_confirmada(user_id)`| Retorna a última transação confirmada do usuário ordenada por `data_hora` DESC limit 1 |
| SQL-T5 | Consulta pendentes | `pendentes()` (Cmd) | SELECT das transações onde `status = 'PENDENTE_APROVACAO'` |

---

## 4. FAT-SQL — SqlAlchemyFaturaRepo

**Responsabilidade**: Gerenciamento de faturas (cartões de crédito).

| ID | Given | When | Then |
|---|---|---|---|
| SQL-F1 | Mês sem fatura para o cartão A | `buscar_aberta(A, 06, 2026)` | Retorna `None` |
| SQL-F2 | - | `criar(A, 06, 2026)` | INSERT em `faturas`, retorna DTO `Fatura` com ID UUID gerado |
| SQL-F3 | Fatura existente | `atualizar(fatura)` | UPDATE na tabela `faturas` (atualiza `valor_total` ou `status`) |
| SQL-F4 | Consulta faturas do usuário | `faturas_abertas(user_id)` | Junta `faturas` e `contas` e traz faturas ABERTAS do `usuario_id` |

---

## 5. RENDA-SQL — SQL FonteRenda & RegistroDia

**Responsabilidade**: Rastrear as fontes e marcações de faltas/remoto.

| ID | Given | When | Then |
|---|---|---|---|
| SQL-R1 | 2 fontes, 1 ativa, 1 inativa | `ativas(usuario_id)` | Retorna apenas a Fonte DTO ativa |
| SQL-R2 | - | `registrar_dia(user, data, status)`| Realiza UPSERT (INSERT ON CONFLICT) na tabela `registro_dias` |
| SQL-R3 | Consulta do mês | `do_mes(fonte_id, mes, ano)`| Retorna lista de `RegistroDia` daquele mês/ano para a fonte |

---

## Estratégia de Teste (Integration Tests)

Os testes de repositório **NÃO DEVEM** usar mocks/fakes. Eles devem criar um banco SQLite temporário `sqlite:///:memory:` (ou um PostgreSQL no Docker) e injetar uma `Session` real usando a dependência `sqlalchemy`.

Arquivo sugerido de teste: `tests/integration/test_sqlalchemy_repos.py`.

Cada teste deve inserir dados base (seed) via SQL cru ou DTO, instanciar o Repo Real, rodar o método alvo, e conferir o banco via query ou usando os próprios métodos de busca do Repo.
