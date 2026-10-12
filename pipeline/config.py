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


# Umbrales únicos de lectura base y de índice del registro (#3, #6)
# REGLA: No duplicar ni hardcodear estos valores en otros módulos.
COMPUERTA_LECTURA_MODELO = 0.70        # Compuerta mínima de lectura base por entidad para recibir bonos
COMPUERTA_LECTURA_MODELO_PCT = 70      # Compuerta en escala 0-100
UMBRAL_INDICE_REGISTRO = 85            # Umbral de corte del índice final del registro (0-100) para pase directo al DW
UMBRAL_INDICE_REGISTRO_DEC = 0.85      # Umbral de corte en escala 0-1
TOPE_INDICE_BONIFICADO = 99            # Tope máximo para índice con bonos acumulativos (0-100)
TOPE_INDICE_BONIFICADO_DEC = 0.99      # Tope máximo en escala 0-1

UMBRAL_CONFIANZA_ALTO = 0.85     # Aceptación automática directa
UMBRAL_CONFIANZA = UMBRAL_CONFIANZA_ALTO  # Alias canónico
UMBRAL_CONFIANZA_MEDIO = 0.60    # Requiere revisión / flag activo
UMBRAL_CONFIANZA_BAJO = 0.40     # Descarte o staging no resuelto

# Umbrales de activación de revisión humana y calidad (GIRA-27: corte estricto en 0.85)
UMBRAL_REVISION_BETO = 0.85      # Inferencia BETO < 0.85 activa requiere_revision (Nivel MEDIA o BAJA)
UMBRAL_REVISION_FUZZY = 0.80     # Similitud RapidFuzz < 80% activa requiere_revision
RAPIDFUZZ_HIGH = 85.0
RAPIDFUZZ_LOW = 60.0

# Rangos y umbrales de dominio académico
NOTA_MINIMA_VALIDA = 0.0
NOTA_MAXIMA_VALIDA = 100.0
NOTA_APROBACION_MINIMA = 51.0
ASISTENCIA_MINIMA_VALIDA = 0.0
ASISTENCIA_MAXIMA_VALIDA = 100.0
UMBRAL_DESERCION_INCUMPLIMIENTO_PCT = 30.0

# Rangos y umbrales de dominio financiero
UMBRAL_RIESGO_CUOTAS_IMPAGAS = 2
ESTADOS_CARTERA_VALIDOS = ("Vigente", "Mora", "Previsionable")

# Parámetros de inferencia
DEFAULT_BATCH_SIZE = 16
MAX_TOKEN_LENGTH = 512

# ── Constantes y Expresiones Regulares de Dominio Centralizadas ──────
import re

# Códigos POS (4000 a 7000 en GiraGroup)
PATRON_POS_GENERAL = re.compile(r'\b(?:POS[-_ ]?)?(\d{4,5})\b', re.IGNORECASE)
PATRON_POS_STRICT = re.compile(r'\bPOS-(\d{4,5})\b', re.IGNORECASE)

# Cédula de Identidad boliviana
PATRON_CI_BOLIVIA = re.compile(r'^\d{5,9}(?:-[0-9A-Za-z]{1,3})?$', re.IGNORECASE)

# Prefijos y títulos profesionales para desambiguación y normalización
PREFIJOS_TITULOS = re.compile(
    r'\b(?:lic(?:\.|enciad[oa])?|dr(?:\.|a\.)?|ing(?:\.|enier[oa])?|msc(?:\.)?|'
    r'mag[ií]ster|mtr(?:\.)?|ph\.?d\.?|prof(?:\.|esor[a]?)?|docente)\b',
    re.IGNORECASE
)
TITULOS_PERSONA_TUPLA = (
    "docente", "profesor", "profesora", "facilitador", "facilitadora",
    "lic.", "lic", "licenciado", "licenciada",
    "ing.", "ing", "ingeniero", "ingeniera",
    "dr.", "dr", "dra.", "dra", "doctor", "doctora",
    "msc.", "msc", "magister", "máster", "master", "phd", "ph.d."
)

# Asegurar directorios requeridos
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
MODELO_BETO_CACHE_DIR.mkdir(parents=True, exist_ok=True)
