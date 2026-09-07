"""
pipeline/config.py
------------------
Configuración centralizada para el pipeline de Procesamiento de Lenguaje Natural (PLN)
y normalización semántica del sistema GiraGroup BI.

Define umbrales únicos de confianza, rutas de modelos y directorios del proyecto.
"""

from pathlib import Path

# Directorio raíz del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent

# Rutas de datos
DATA_DIR = BASE_DIR / "uploads" / "data"
OUTPUT_DIR = BASE_DIR / "output"
DB_DIR = BASE_DIR / "db"
SEEDS_DIR = DB_DIR / "seeds"

# Archivos de entrada y salida estándar
SPRINT2_DOCS_PATH = OUTPUT_DIR / "sprint2_documentos.jsonl"
SEED_CATALOGOS_SQL_PATH = SEEDS_DIR / "seed_catalogos.sql"
INCONSISTENCIAS_LOG_PATH = OUTPUT_DIR / "inconsistencias_sprint3.jsonl"

# Configuración de Modelos NLP
MODELO_BETO_BASE = "dccuchile/bert-base-spanish-wwm-cased"
MODELO_BETO_NER = "mrm8488/bert-spanish-cased-finetuned-ner"
MODELO_BETO_NOMBRE = MODELO_BETO_NER  # Por defecto usar el fine-tuned para NER en español
MODELO_BETO_CACHE_DIR = BASE_DIR / "pipeline" / "semantic" / "beto_local"


# Umbrales únicos de confianza probabilística
# REGLA: No duplicar ni hardcodear estos valores en otros módulos.
UMBRAL_CONFIANZA_ALTO = 0.85     # Aceptación automática directa
UMBRAL_CONFIANZA = UMBRAL_CONFIANZA_ALTO  # Alias canónico
UMBRAL_CONFIANZA_MEDIO = 0.60    # Requiere revisión / flag activo
UMBRAL_CONFIANZA_BAJO = 0.40     # Descarte o staging no resuelto

# Parámetros de inferencia
DEFAULT_BATCH_SIZE = 16
MAX_TOKEN_LENGTH = 512

# Asegurar directorios requeridos
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
MODELO_BETO_CACHE_DIR.mkdir(parents=True, exist_ok=True)
