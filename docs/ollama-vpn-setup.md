# Guia de Configuração: VPN + Conexão SSH Automática + LLM (Ollama) no Lab

Este documento explica como utilizar os scripts de VPN e SSH configurados para acessar as máquinas do laboratório, além do processo de instalação e execução do Ollama sem acesso root (`sudo`) com aceleração por GPU.

---

## 1. Gerenciamento de VPN (FortiClient)

Para contornar o problema onde o FortiClient no Linux exige uma entrada de terminal interativa (TTY) para a senha e entra em loop infinito nos scripts comuns, foi desenvolvido um utilitário em Python que emula um pseudo-terminal (`pty`).

### Scripts Disponíveis
* **Ligar VPN:** `vpn-up`
  * Comando local: `/home/sirimarco/.local/bin/vpn-up`
  * Funcionalidade: Conecta à VPN usando suas credenciais em segundo plano e monitora o status. Após conectado, ele se desprende (daemoniza) para manter a conexão aberta no sistema.
* **Desligar VPN:** `vpn-down`
  * Comando local: `/home/sirimarco/.local/bin/vpn-down`
  * Funcionalidade: Desconecta a sessão ativa do FortiClient.

---

## 2. Atalhos SSH com VPN Inteligente (`ssh-188` e `ssh-189`)

Os scripts de conexão SSH foram configurados com os IPs externos corretos (`152.92.223.188` e `152.92.223.189`) e com o seu usuário (`sirimarco`). Além disso, eles automatizam o ciclo de vida da VPN:

* **Ao conectar:** O script verifica se a VPN já está ativa. Caso não esteja, ele liga a VPN automaticamente antes do SSH iniciar.
* **Ao desconectar (Sair do SSH):** Se a VPN foi iniciada por aquele script SSH, ele a desliga automaticamente ao fechar o terminal. Se a VPN já estava ligada antes, ele a mantém aberta para não atrapalhar outros trabalhos.
* **Argumentos:** O script suporta passagem de comandos (ex: `ssh-188 "ls -la"`).

### Comandos de Uso

* **Acesso SSH Padrão (Sem Túnel):**
  ```bash
  # Conectar na máquina 188
  ssh-188

  # Conectar na máquina 189
  ssh-189
  ```

* **Acesso SSH com Túnel para OpenCode (Redireciona a porta 11434 para o seu PC local):**
  ```bash
  # Conectar na máquina 188 com túnel Ollama
  ssh-188-tunnel

  # Conectar na máquina 189 com túnel Ollama
  ssh-189-tunnel
  ```
  *Nota: Mantenha esta janela de terminal aberta enquanto estiver utilizando o OpenCode (ou qualquer outro app local de IA). Ao digitar `exit` no terminal SSH, o túnel será desfeito e a VPN será desligada automaticamente (se foi ligada por esse script).*

---

## 3. Ollama no Laboratório (Sem Sudo / Com GPU)

O Ollama foi instalado na máquina **188** (LPG17) de maneira totalmente local no seu usuário.

### Estrutura de Pastas Criada
* Instalação principal: `~/ollama/`
* Executável: `~/ollama/bin/ollama`
* Bibliotecas CUDA (v12 e v13): `~/ollama/lib/ollama/`
* Modelos salvos: `~/.ollama/models/`

### Como rodar o servidor em background
Para manter o servidor rodando na máquina remota mesmo após você deslogar do SSH, o Ollama foi iniciado dentro de uma sessão `screen` desprendida:
```bash
screen -dmS ollama ~/ollama/bin/ollama serve
```

### Comandos de Gerenciamento do Ollama (Na máquina remota)

* **Iniciar Conversa com Modelos Existentes (Já baixados e prontos):**
  ```bash
  # Qwen 2.5 3B Instruct (Altamente recomendado para português)
  ~/ollama/bin/ollama run qwen2.5:3b

  # Llama 3.2 3B Instruct (Excelente para tarefas gerais)
  ~/ollama/bin/ollama run llama3.2

  # Qwen 2.5 0.5b (Super leve para testes rápidos)
  ~/ollama/bin/ollama run qwen2.5:0.5b
  ```

* **Listar Modelos Instalados:**
  ```bash
  ~/ollama/bin/ollama list
  ```

* **Baixar Novos Modelos (Recomendado para GPU 6GB):**
  ```bash
  # DeepSeek R1 (1.5b) - Excelente modelo de raciocínio lógico/raciocínio estruturado
  ~/ollama/bin/ollama pull deepseek-r1:1.5b
  ```

* **Monitorar Logs do Servidor (e verificar uso da GPU):**
  ```bash
  cat ~/ollama/ollama.log | grep -E "inference compute|CUDA"
  ```

---

## 4. Como Limpar / Remover tudo se não for mais usar

Se desejar desativar o serviço e apagar todos os arquivos e modelos baixados para liberar espaço:

1. **Finalizar processos remotos:**
   ```bash
   pkill -f ollama
   screen -XS ollama quit
   ```

2. **Remover pastas de arquivos:**
   ```bash
   rm -rf ~/ollama ~/.ollama
   ```
