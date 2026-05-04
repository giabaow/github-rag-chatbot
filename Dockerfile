# ── Stage 1: builder ──────────────────────────────────────────────────────────
# Install Python deps in an isolated layer so the final image stays lean.
FROM python:3.11-slim AS builder

WORKDIR /install

# System libs needed to compile some pip packages (faiss, chromadb, gitpython)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --prefix=/install/pkg --no-cache-dir -r requirements.txt


# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM python:3.11-slim

# Runtime system deps (git is needed by GitPython at runtime)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install/pkg /usr/local

# Copy application source
COPY . .

# Create data directories (mounted as volumes in compose)
RUN mkdir -p data/repos data/vectors

# GPT4All downloads its model to ~/.cache/gpt4all by default.
# Point it to a volume-friendly path inside /app so the model
# persists across container restarts without re-downloading.
ENV GPT4ALL_MODEL_PATH=/app/data/models
RUN mkdir -p /app/data/models

# Streamlit runs on 8501
EXPOSE 8501

# Health-check: ping Streamlit's built-in health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser /app
USER appuser

CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false"]