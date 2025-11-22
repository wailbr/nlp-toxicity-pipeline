FROM python:3.11-slim

# --- Env propres ---
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/cache/huggingface \
    HF_HUB_DISABLE_SYMLINKS_WARNING=1 \
    TRANSFORMERS_CACHE=/cache/huggingface \
    PORT=8000

# Dépendances système minimales
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copie des deps
COPY requirements.txt /app/requirements.txt

# Installer torch CPU et le reste
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch \
 && pip install --no-cache-dir -r requirements.txt

# Copie du code
COPY app /app/app

# Expose le port interne
EXPOSE 8000

# Créer le dossier cache (pour Hugging Face) + volume
RUN mkdir -p /cache/huggingface
VOLUME ["/cache"]

# Démarrage FastAPI (port configurable via $PORT)
ENTRYPOINT ["sh", "-c", "uvicorn app.api:app --host 0.0.0.0 --port ${PORT}"]
