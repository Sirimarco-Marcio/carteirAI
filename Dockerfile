# Imagem base: Python 3.13 slim (aarch64 compatível com Raspberry Pi 3 64-bit)
FROM python:3.13-slim

# Metadados
LABEL maintainer="carteirAI" \
      description="Worker carteirAI: ingestão HTTP + bot Telegram + IA + fila"

# Variáveis de build
ARG DEBIAN_FRONTEND=noninteractive

# Dependências de sistema mínimas (psycopg usa libpq; curl para healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq-dev \
        gcc \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Diretório de trabalho
WORKDIR /app

# Copia dependências primeiro (aproveita cache de camadas)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia código-fonte e scripts
COPY src/ src/
COPY scripts/ scripts/
COPY pyproject.toml .

# Instala o pacote em modo editável (resolve imports carteirai.*)
RUN pip install --no-cache-dir -e .

# Volume para a fila SQLite persistente
VOLUME ["/data"]

# Expõe porta do FastAPI (ingestão HTTP do app Android)
EXPOSE 8000

# Comando padrão: executa o script que sobe o FastAPI + Bot do Telegram
CMD ["./scripts/start-all.sh"]
