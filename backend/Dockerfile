FROM python:3.11-slim

# System deps:
#  - build-essential, curl: compiled Python wheels (lxml, chromadb)
#  - nodejs, npm: Gmail MCP server runs as a Node subprocess via npx
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        nodejs \
        npm \
    && rm -rf /var/lib/apt/lists/* \
    && npm install -g @gongrzhe/server-gmail-autoauth-mcp@latest

# Install uv (pinned for reproducibility)
COPY --from=ghcr.io/astral-sh/uv:0.5.4 /uv /usr/local/bin/uv

# HF Spaces runs containers as a non-root user with UID 1000
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/home/user/.cache/huggingface \
    SENTENCE_TRANSFORMERS_HOME=/home/user/.cache/sentence-transformers

WORKDIR /app

# Copy dependency manifests first for layer caching
COPY --chown=user:user pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Pre-download the embedding model into the image so cold starts skip the download
RUN uv run python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

# Copy application code last (changes most often)
COPY --chown=user:user . .

EXPOSE 7860

# Entrypoint materializes Gmail OAuth credentials from env vars before starting
# uvicorn. Credentials are stored in ~/.gmail-mcp/ where the gongrzhe MCP server
# expects them. Without those env vars set, the dispatcher's MCP-skip path
# (services/approvals/dispatcher.py) handles the absence gracefully.
CMD ["sh", "/app/scripts/entrypoint.sh"]
