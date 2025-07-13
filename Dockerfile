# syntax=docker/dockerfile:1.7
# --------------------------------------------------------
# Build stage – create an ultralight venv with uv
# --------------------------------------------------------
FROM python:3.12-slim AS builder

# 1️⃣ system deps that uv might need when compiling wheels
RUN apt-get update && apt-get install -y --no-install-recommends --fix-missing \
      build-essential curl git && \
    rm -rf /var/lib/apt/lists/*

# 2️⃣ install uv by copying from the official uv image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# 3️⃣ set environment variables for uv
ENV UV_PROJECT_ENVIRONMENT="/opt/venv" \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# 4️⃣ copy project files
COPY pyproject.toml uv.lock ./
COPY DAPEAgent/ ./DAPEAgent
COPY azure_tools/ ./azure_tools
COPY streamlit_ui.py .

# 5️⃣ sync everything (dependencies + project)
RUN uv sync --frozen

# --------------------------------------------------------
# Runtime stage – copy sources & start the app
# --------------------------------------------------------
FROM python:3.12-slim

# Install nginx, Node.js, npm, and Azure CLI
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    curl \
    ca-certificates \
    gnupg \
    lsb-release && \
    # Install Node.js and npm
    curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - && \
    apt-get install -y nodejs && \
    # Install Azure CLI
    curl -sLS https://packages.microsoft.com/keys/microsoft.asc | \
    gpg --dearmor | \
    tee /etc/apt/trusted.gpg.d/microsoft.gpg > /dev/null && \
    echo "deb [arch=amd64] https://packages.microsoft.com/repos/azure-cli/ $(lsb_release -cs) main" | \
    tee /etc/apt/sources.list.d/azure-cli.list && \
    apt-get update && \
    apt-get install -y azure-cli && \
    rm -rf /var/lib/apt/lists/*

# copy the ready-made venv from builder
COPY --from=builder /opt/venv /opt/venv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# copy *only* the code we need (tests & examples ignored by .dockerignore)
COPY DAPEAgent/ ./DAPEAgent
COPY azure_tools/ ./azure_tools
COPY streamlit_ui.py .
COPY .env .
COPY entry_point.sh .
COPY nginx.conf /etc/nginx/nginx.conf


# (optional) copy any extra config files, nginx conf, prompts, etc.
COPY DAPEAgent/prompts/ ./DAPEAgent/prompts

RUN chmod +x ./entry_point.sh

# App Service looks for exactly one exposed port – pick whichever your
# entrypoint forwards to (e.g. 80 when using NGINX, or 8501 for raw Streamlit)
ENV PORT=80
EXPOSE 80

CMD ["./entry_point.sh"]
