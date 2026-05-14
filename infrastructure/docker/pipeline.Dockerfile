FROM python:3.12-slim

WORKDIR /app

# Dependencias del sistema para compilar librerías matemáticas y NLP
RUN apt-get update && \
    apt-get install -y build-essential gcc g++ && \
    rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias pesadas del pipeline
COPY pipeline/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código del pipeline
COPY pipeline/ ./pipeline/

# Mantiene el contenedor activo en reposo. 
# Permite entrar a ejecutar scripts (ej: docker exec -it giragroup_pipeline python pipeline/ingestion/sheet_reader.py)
CMD ["tail", "-f", "/dev/null"]