FROM python:3.11-slim

WORKDIR /app

# Installation des dépendances système nécessaires pour exécuter Chromium headless et Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libexpat1 \
    libfontconfig1 \
    libgbm1 \
    libglib2.0-0 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libstdc++6 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext1 \
    libxfixes1 \
    libxi1 \
    libxrandr1 \
    libxrender1 \
    libxtst6 \
    libasound2 \
    libxshmfence1 \
    fonts-liberation \
    && rm -rf /var/lib/apt-get/lists/*

# Installation des dépendances Python (dont playwright)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Installation des binaires du navigateur Chromium (sans les scripts de dépendances obsolètes)
RUN playwright install chromium

# Copie du code source
COPY master.py worker_node.py ./

# Variables d'environnement par défaut
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Exposition des ports
EXPOSE 8000 8001 8002 8003

# Démarrage par défaut
CMD ["python", "master.py"]