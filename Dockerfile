FROM python:3.11-slim

WORKDIR /app

# Installation des dépendances système nécessaires pour exécuter Chromium headless
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    libglib2.0-0 \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpangocairo-1.0-0 \
    libpango-1.0-0 \
    && rm -rf /var/lib/apt-get/lists/*

# Installation des dépendances Python (dont playwright)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Installation des binaires du navigateur Chromium et de ses dépendances
RUN playwright install chromium
RUN playwright install-deps chromium

# Copie du code source
COPY master.py worker_node.py ./

# Variables d'environnement par défaut
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Exposition des ports
EXPOSE 8000 8001 8002 8003

# Démarrage par défaut
CMD ["python", "master.py"]