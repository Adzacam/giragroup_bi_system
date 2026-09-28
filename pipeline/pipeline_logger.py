"""
pipeline/pipeline_logger.py
----------------------------
Gestor de logs técnicos del pipeline en disco (logs/pipeline_ejecuciones.log).
Registra en formato estructurado:
- Archivo procesado
- Hoja / Bloque
- Total entidades extraídas
- Nivel de confianza promedio
- Flag requiere_revision
- Latencia en ms
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

PROYECTO_RAIZ = Path(__file__).resolve().parent.parent
LOGS_DIR = PROYECTO_RAIZ / "logs"
LOG_FILE_PATH = LOGS_DIR / "pipeline_ejecuciones.log"

# Asegurar existencia de carpeta logs
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Configurar logger rotativo específico (máx 5 MB, 3 backups)
_logger = logging.getLogger("pipeline_tecnico")
_logger.setLevel(logging.INFO)

if not _logger.handlers:
    file_handler = RotatingFileHandler(
        str(LOG_FILE_PATH),
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8"
    )
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [PIPELINE] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    _logger.addHandler(file_handler)


def registrar_log_ejecucion(
    archivo: str,
    hoja: Optional[str] = None,
    bloque_id: Optional[int] = None,
    total_entidades: int = 0,
    nivel_confianza: float = 0.85,
    requiere_revision: bool = False,
    tiempo_ms: float = 0.0,
    detalles: Optional[str] = None
):
    """Escribe un registro de auditoría técnica en logs/pipeline_ejecuciones.log."""
    mensaje = (
        f"Archivo='{archivo}' | Hoja='{hoja or 'N/A'}' | Bloque={bloque_id if bloque_id is not None else 'N/A'} | "
        f"Entidades={total_entidades} | ConfianzaIA={nivel_confianza:.4f} | "
        f"RequiereRevision={requiere_revision} | Latencia={tiempo_ms:.1f}ms"
    )
    if detalles:
        mensaje += f" | Info='{detalles}'"

    if requiere_revision:
        _logger.warning(mensaje)
    else:
        _logger.info(mensaje)
