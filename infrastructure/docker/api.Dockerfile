FROM python:3.12-slim

WORKDIR /app

# Dependencias del sistema operativo para compilar psycopg2 (PostgreSQL)
RUN apt-get update && \
    apt-get install -y build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias de la API
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente
COPY backend/ .

EXPOSE 8000

# Ejecutar Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]