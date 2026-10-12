FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY services/audit-service/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY services/audit-service/ /app/
COPY shared/ /app/shared/

EXPOSE 8004

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8004"]
