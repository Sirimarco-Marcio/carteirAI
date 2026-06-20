# 04 — Operações: Raspberry Pi (worker)

> Segredos (senha SSH, chave Gemini) **não** ficam aqui — estão em `segredos.local.md`
> (ignorado pelo git). Este arquivo descreve só o ambiente e os processos.

## Estado do hardware/SO (levantado em 2026-06-20)
| Item | Valor |
| --- | --- |
| Modelo | Raspberry Pi 3 Model B Rev 1.2 |
| Hostname | `FinancialServer` |
| SO | Debian GNU/Linux 13 (trixie), **aarch64 / 64-bit** |
| Kernel | 6.18.34+rpt-rpi-v8 |
| CPU | 4 núcleos |
| RAM | 905 MiB total (~686 MiB disponível ocioso) |
| Disco | 59 GB (53 GB livres) |
| Usuário | `msiri` (uid 1000) — grupos `docker`, `sudo` (NOPASSWD), `gpio`, `i2c`, `spi` |
| Acesso | SSH em `192.168.1.29:22` (só porta 22 exposta) |

## Software já instalado (não precisa reinstalar)
| Pacote | Versão |
| --- | --- |
| Docker | 29.6.0 |
| Docker Compose | v5.1.4 |
| Python | 3.13.5 |
| git | 2.47.3 |

## Containers
Nenhum container rodando ainda (`docker ps -a` vazio). O `docker-compose.yml` do
worker será adicionado na fase de implementação.

## Arquitetura de execução prevista (a implementar)
- **1 container** para o worker FastAPI (polling Telegram + fila + LangGraph).
- **Fila SQLite** num volume persistente montado no container.
- Variáveis sensíveis via `.env` (montado, não copiado para a imagem).
- `LLM_PROVIDER` controla Gemini vs modelo local por SSH.

## Próximos passos de configuração (quando liberado)
1. Criar diretório do projeto no Pi (ex: `~/carteirAI`).
2. Clonar o repositório.
3. Criar `.env` a partir do `.env.example`.
4. Subir o stack com `docker compose up -d` (após a imagem existir).
5. Definir restart policy (`restart: unless-stopped`) para sobreviver a reboots.

## Limpeza pendente
- Há um `get-docker.sh` em `~msiri/` (script de instalação já usado) — pode ser removido.
