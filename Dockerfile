FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

# Installation des dépendances Python (dont playwright)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code source
COPY master.py worker_node.py ./

# Variables d'environnement par défaut
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Exposition des ports
EXPOSE 8000 8001 8002 8003

# Démarrage par défaut
CMD ["python", "master.py"]