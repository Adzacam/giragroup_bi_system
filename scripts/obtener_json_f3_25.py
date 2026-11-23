"""
scripts/obtener_json_f3_25.py
-----------------------------
Genera un token JWT administrativo válido y consulta el endpoint
GET /api/v1/forecast/alumnos imprimiendo la respuesta en formato JSON formateado.
"""
import os
import sys
import json
import requests
from datetime import datetime, timedelta, timezone
from jose import jwt
import dotenv

dotenv.load_dotenv(".env")
SECRET_KEY = os.getenv("SECRET_KEY", "dev_secret_key_change_me_in_prod")
ALGORITHM = "HS256"
BASE_URL = os.getenv("API_URL", "http://localhost:8000")

# 1. Generar token de autenticación para ADMIN (usuario 1)
payload = {
    "sub": "1",
    "role": "ADMIN",
    "type": "access",
    "exp": datetime.now(timezone.utc) + timedelta(hours=2)
}
token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

# 2. Consultar el endpoint
headers = {"Authorization": f"Bearer {token}"}
url = f"{BASE_URL}/api/v1/forecast/alumnos?tipo=GLOBAL&horizonte=6"

print(f"--- Consultando {url} ---")
try:
    res = requests.get(url, headers=headers, timeout=10)
    print(f"HTTP Status: {res.status_code}")
    if res.status_code == 200:
        data = res.json()
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print("Error en respuesta:", res.text)
except Exception as e:
    print(f"Error de conexión con la API ({url}): {e}")
