# ✅ Decisões pendentes — responda tudo e me manda junto

> Marque/responda cada item. Os que têm **[recomendo: X]** já têm minha sugestão — se concordar,
> só dizer "ok nos recomendados" que eu sigo. Agrupei por urgência.

---

## 🔴 Bloqueiam o teste real / próximos passos

### D1 — Chave do Gemini (estourou cota 429)
A chave atual autentica mas **não tem cota** (429 RESOURCE_EXHAUSTED). Escolha:
- (a) Gerar **API key nova** em aistudio.google.com/apikey (free tier com cota diária) — colar no `segredos.local.md`. **[recomendo]**
- (b) Ativar **billing** no projeto Google atual.
- [X](c) Usar **modelo local como principal** (qwen2.5:3b nas máquinas da faculdade) e Gemini só como fallback — sem custo/cota, mas extrai um pouco pior.

### D2 — Provider principal (`LLM_PROVIDER`)
Qual é o padrão? **[recomendo: `gemini` principal + `local` fallback automático]** — mas se a cota do Gemini for um problema recorrente, invertemos (local principal).
Gemini + local, n precisa inverter, vamos deixar o melhor na frente. vamos ter muitos problemas com ele, mas isso vai se resolver no futuro proximo. com api paga.

### D3 — Transporte App→Telegram (a "pegadinha")
Como a notificação do celular chega no Pi? O bot **não lê as próprias mensagens** via polling. Opções:
- [X](a) App posta num **canal privado do Telegram por pessoa** (você admin do bot no canal); o Pi lê `channel_post`; identidade = qual canal. **[recomendo]** — precisa você criar 2 canais e me dar os IDs.
- (b) App manda **HTTP direto pro Pi** (via VPN/Tailscale) — sem Telegram no transporte; Telegram só pra aprovação/comandos.
- → Se (a): criar os 2 canais (um seu, um da esposa) e me passar os `chat_id` deles. tem q ser programatico tbm, tem q ter um botão pra cadastrar pessoas n sei se na pg q fica na vercel. ou vc esta falando pra eu criar um bot pra casa pessoa ? se for o caso isso n faz sentido. o bot vai receber a mensagem, o pi só precisa olhar via pooling de 20 em 20 min por exemplo. isso n funciona?

---

## 🟡 Configuração dos seus dados reais (pra IA e relatórios fazerem sentido)

### D4 — Suas contas/cartões
Liste: bancos/instituições, contas (corrente/dinheiro) e **cartões de crédito** com **dia de
fechamento, dia de vencimento e limite**. (Itaú, Bradesco, Santander, Mercado Pago já apareceram —
quais são conta e quais são cartão?) 
- Isso deve ser configuravel com o projeto andando, n pode ir hardcoded pro banco de dados.

### D5 — Fontes de renda (pro `/fechar_mes` e renda prevista)
Confirme os valores (do handoff): **UERJ R$300 fixo/mês**, **Convem R$1500 fixo/mês**, **BNDES por
dia** (valor/dia + alimentação/dia + transporte/dia + quais dias da semana trabalha). Preencher os
números reais do BNDES.
- Isso esta certo, mas tem q ter um onboarding de cada usuario para q sejam cadastrados sua familia, renda , dividas, etc. inclusive seria uma feature mais pra frente uma pessoa q esta em uma familia ser um user independente, por exemplo eu e minha esposa, somos user independentes cada um tera sua visão das financas, mas ela pode cadastrar sei la, a mãe dela com um custo q ela tem, e se a mãe dela for cadastrar ela teria como vincular esse user a essa mãe n iria trazer renda, mas teria esse vinculo afetado, se isso for complicado pode ignorar. poderiamos simplificar apenas colocando um app q le notif e envia mensaengs cada um tera um id e poderemos identificar qual a pessoa q enviou a notif pro bot.

### D6 — `telegram_chat_id` de cada pessoa
Seu chat_id e o da sua esposa (a aprovação vai pro chat de quem gastou). O bot mostra o chat_id no
`/start` — me manda os dois. 
- como ela sera uma pessoa da minha familia, sem renda, vai ser td no meu chat e eu confirmo tds as compras, passe a buscar o id direto do app q raspa a notificação. pode usar um header sei la. (453373581)

### D7 — Categorias
A lista atual (14) está boa? Algum ajuste? Ex: **Pix sempre cai em "Transferências"** — ok? Compras
em loja variada (Americanas) caem em "Outros" — ok ou quer mais granularidade?
- Quero q Pix seja uma categoria, seria bom ter o nome da pessoa q esta recebendo, e nas comrpas variadas pode ir pra outros.

---

## 🟢 Podem esperar (mas bom decidir)

### D8 — Quantas tentativas de reflexão (retry corretivo)
**[recomendo: 2 por provider]** (1 original + 1 corrigida), depois fallback de provider. Concorda ou quer 3?
- Quero 3 por provider, 1 original + 2 corrigidas, ou seja se n funcionar manda o erro q achamos e ele tem a chance de corrigir 2x, se n conseguir reinicia e batendo as 2 chances vai pro outro prov ou erro.

### D9 — Quando criar o banco Neon limpo
Você disse que vai recriar. Quando criar, eu rodo `db/apply.sh`. Me avisa quando a connection string
nova estiver no `segredos.local.md`.
- Ok.

### D10 — Deploy no Pi
Posso configurar o Pi (192.168.1.29): `openfortivpn` (VPN da faculdade) + worker em Docker
(sempre-ligado) + ponte SSH→Ollama. Faço quando você autorizar (mexe no Pi via SSH).
- Pode fazer agr.

### D11 — Vercel (painel)
Você criou um projeto "carteirai". **[recomendo: deixar como está]** e ligar 1 projeto ao repo do
painel quando a gente construir o Next.js (passo 3/4). Ok?
- Ok.

### D12 — App da esposa
Quando instalar o notifier no celular dela? (mesmo processo, `scripts/capturar.sh setup`).
- Me ensina como fazer.

### D13 — Ajustes cosméticos da UI do app
Você disse que tem alguns. Liste quando quiser que eu faça.
- seria basicamente deixar um design melhor, n vamos fazer isso agr pq leva tempo preparar um design bom. se vc acahar q consegue pode fazer usando alguam skill, mas me mande o print antes de aplicar, pq atualemtne é um fundo preto e pronto, podia ser melhor, mais fluido, carregar os dados em batch por exemplo pra n ficar uma tela parada sem nada e no nada varios apps.

### D14 — Feature de localização (backlog)
Capturar GPS junto da notificação (lembrar onde foi a compra). Prioridade? (está em `docs/backlog.md`).
- Isso seria bom fazer logo, pegar as permissões quando instala o app, assim q tem como pegar a localização, envia junto na mensagem, de uma forma q seja possivel jogar pro maps por exemplo com um clique.

### D15 — Fechamento de mês (COMP): de onde vem o "previsto por fonte"?
No `/fechar_mes` eu comparo **previsto × realizado por fonte** (ex: BNDES pagou menos → inconsistência).
O `previsto por fonte` precisa vir de algum lugar. Opções: (a) recalcular na hora via RENDA (preciso
dos dias úteis + exceções do mês), ou (b) guardar `renda_prevista_por_fonte` na competência quando
ela é criada. **[recomendo (b)]**. Deixei o módulo RENDA pronto (testado); COMP fica pendente desta decisão.
- Use os dados de RENDA pra calcular na hr, mesmo que seja algo repetitivo, pq uma falta muda a renda da pessoa, um atestado, etc.

---

## 🔐 Ações suas (rotação de segredos — quando der)
- Revogar o **token do bot** no @BotFather (`/revoke`).
- Recriar o **banco Neon** limpo (a connection string antiga vazou no chat).
- Trocar a **chave do Gemini** (ver D1).
- (eventual) rotacionar **senha SSH/VPN** da faculdade.
