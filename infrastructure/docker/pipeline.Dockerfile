FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias de sistema para compilación y lectura de XML/Excel
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar requerimientos del pipeline
COPY pipeline/requirements.txt /app/pipeline/requirements.txt
RUN pip install --no-cache-dir -r /app/pipeline/requirements.txt

# Copiar el código fuente
COPY . /app

ENV PYTHONPATH=/app

EXPOSE 8006

# Levantar micro-servicio interno de inferencia PyTorch BETO NER en el puerto 8006
CMD ["python", "-m", "pipeline.semantic.inference_server", "--host", "0.0.0.0", "--port", "8006"]