# 00 — Handoff (contexto deste trabalho)

Resumo do que foi decidido na fase de refinamento da spec. Ler junto com 01/02/03.

## Decisões fechadas
- **Arquitetura híbrida:** worker persistente no Raspberry Pi (Docker) + nuvem
  (Neon + Vercel). O Pi é central porque o modelo local exige processo sempre-ligado.
- **Dois LLMs desde o início:** `BaseLLM` com `GeminiAdapter` (padrão) e
  `LocalSSHAdapter` (máquina da faculdade, 6GB VRAM), escolhidos por `LLM_PROVIDER`.
  Evolução desejada: fallback automático local → gemini.
- **Painel acessa o Neon via API Routes da Vercel** (não direto do navegador).
  Vercel serverless É o backend grátis; credencial fica server-side.
- **App Android:** próprio, construído do zero (por segurança). Notificações
  ficam **mockadas** no início (formato dos bancos ainda desconhecido).
- **Aprovação Human-in-the-Loop:** vai pro Telegram de **quem fez o gasto** (dono da conta).
- **Cartão de crédito (modo "real", padrão):** compra no crédito não mexe no saldo;
  entra numa fatura; saldo só cai quando a fatura é paga. Modelo de dados é único;
  o "modo" é só preferência de alerta da IA. Objetivo do usuário: usar só o que ganha,
  à vista, pagar no mês.
- **Categorias:** lista fixa (a confirmar — ver doc 03).

## Renda (caso do usuário)
3 fontes: UERJ (R$300 fixo/mês), Convem (R$1500 fixo/mês), BNDES (valor/dia +
alimentação/dia + transporte/dia, variável por dias trabalhados).
- Padrão = dia presencial. Exceções registradas: `/faltei` (ganha 0) e dia **remoto**
  (ganha dia + alimentação, **sem** transporte).
- Config por fonte: valores e dias da semana de trabalho.
- `/fechar_mes`: usuário informa o recebido; sistema compara previsto × realizado e
  aponta inconsistências.
- **Saldo de giro** mensal; a **sobra acumula** num saldo crescente da família
  (mover para reserva/investimentos é opcional/manual).

## Questões resolvidas
1. **Dedup:** dois níveis. Duplicata exata (mesma notificação reenviada) = descarte
   automático. Possível duplicata semântica (mesmo usuário+valor+estabelecimento na
   janela) = **sempre** vai pra confirmação especial no Telegram — nunca descarta uma
   2ª compra legítima sem perguntar.
2. **Conta conjunta:** fora de escopo. Aprovação sempre vai pra quem fez o gasto.
3. **Categorias (lista autorizada):** Alimentação, Mercado, Transporte, Moradia, Saúde,
   Educação, Lazer, Assinaturas, Vestuário, Lanche na rua, Presentes, Transferências,
   Investimentos/Reserva, Outros.

## Próxima fase
Configurar o Pi (acesso SSH já fornecido — credenciais a rotacionar) e implementar
com **TDD**. Criar doc de operações (mapa do Docker, processos) — segredos só lá,
fora do versionamento.
