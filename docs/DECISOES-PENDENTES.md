# ✅ Decisões pendentes — responda tudo e me manda junto

> Marque/responda cada item. Os que têm **[recomendo: X]** já têm minha sugestão — se concordar,
> só dizer "ok nos recomendados" que eu sigo. Agrupei por urgência.

---

## 🔴 Bloqueiam o teste real / próximos passos

### D1 — Chave do Gemini (estourou cota 429)
A chave atual autentica mas **não tem cota** (429 RESOURCE_EXHAUSTED). Escolha:
- (a) Gerar **API key nova** em aistudio.google.com/apikey (free tier com cota diária) — colar no `segredos.local.md`. **[recomendo]**
- (b) Ativar **billing** no projeto Google atual.
- (c) Usar **modelo local como principal** (qwen2.5:3b nas máquinas da faculdade) e Gemini só como fallback — sem custo/cota, mas extrai um pouco pior.

### D2 — Provider principal (`LLM_PROVIDER`)
Qual é o padrão? **[recomendo: `gemini` principal + `local` fallback automático]** — mas se a cota do Gemini for um problema recorrente, invertemos (local principal).

### D3 — Transporte App→Telegram (a "pegadinha")
Como a notificação do celular chega no Pi? O bot **não lê as próprias mensagens** via polling. Opções:
- (a) App posta num **canal privado do Telegram por pessoa** (você admin do bot no canal); o Pi lê `channel_post`; identidade = qual canal. **[recomendo]** — precisa você criar 2 canais e me dar os IDs.
- (b) App manda **HTTP direto pro Pi** (via VPN/Tailscale) — sem Telegram no transporte; Telegram só pra aprovação/comandos.
- → Se (a): criar os 2 canais (um seu, um da esposa) e me passar os `chat_id` deles.

---

## 🟡 Configuração dos seus dados reais (pra IA e relatórios fazerem sentido)

### D4 — Suas contas/cartões
Liste: bancos/instituições, contas (corrente/dinheiro) e **cartões de crédito** com **dia de
fechamento, dia de vencimento e limite**. (Itaú, Bradesco, Santander, Mercado Pago já apareceram —
quais são conta e quais são cartão?)

### D5 — Fontes de renda (pro `/fechar_mes` e renda prevista)
Confirme os valores (do handoff): **UERJ R$300 fixo/mês**, **Convem R$1500 fixo/mês**, **BNDES por
dia** (valor/dia + alimentação/dia + transporte/dia + quais dias da semana trabalha). Preencher os
números reais do BNDES.

### D6 — `telegram_chat_id` de cada pessoa
Seu chat_id e o da sua esposa (a aprovação vai pro chat de quem gastou). O bot mostra o chat_id no
`/start` — me manda os dois.

### D7 — Categorias
A lista atual (14) está boa? Algum ajuste? Ex: **Pix sempre cai em "Transferências"** — ok? Compras
em loja variada (Americanas) caem em "Outros" — ok ou quer mais granularidade?

---

## 🟢 Podem esperar (mas bom decidir)

### D8 — Quantas tentativas de reflexão (retry corretivo)
**[recomendo: 2 por provider]** (1 original + 1 corrigida), depois fallback de provider. Concorda ou quer 3?

### D9 — Quando criar o banco Neon limpo
Você disse que vai recriar. Quando criar, eu rodo `db/apply.sh`. Me avisa quando a connection string
nova estiver no `segredos.local.md`.

### D10 — Deploy no Pi
Posso configurar o Pi (192.168.1.29): `openfortivpn` (VPN da faculdade) + worker em Docker
(sempre-ligado) + ponte SSH→Ollama. Faço quando você autorizar (mexe no Pi via SSH).

### D11 — Vercel (painel)
Você criou um projeto "carteirai". **[recomendo: deixar como está]** e ligar 1 projeto ao repo do
painel quando a gente construir o Next.js (passo 3/4). Ok?

### D12 — App da esposa
Quando instalar o notifier no celular dela? (mesmo processo, `scripts/capturar.sh setup`).

### D13 — Ajustes cosméticos da UI do app
Você disse que tem alguns. Liste quando quiser que eu faça.

### D14 — Feature de localização (backlog)
Capturar GPS junto da notificação (lembrar onde foi a compra). Prioridade? (está em `docs/backlog.md`).

---

## 🔐 Ações suas (rotação de segredos — quando der)
- Revogar o **token do bot** no @BotFather (`/revoke`).
- Recriar o **banco Neon** limpo (a connection string antiga vazou no chat).
- Trocar a **chave do Gemini** (ver D1).
- (eventual) rotacionar **senha SSH/VPN** da faculdade.
