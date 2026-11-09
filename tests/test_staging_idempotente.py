"""Clave de idempotencia de stg_entidad_no_resuelta: mismo archivo, tipo, motivo y valor normalizado => misma clave."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]

from models.staging_entidad import clave_staging


def test_misma_entidad_misma_clave_aunque_cambien_espacios_y_mayusculas():
    assert clave_staging("h1", "ESTUDIANTE", "HOMONIMIA", "Juan  Pérez ") == clave_staging("h1", "ESTUDIANTE", "HOMONIMIA", "juan pérez")


def test_distinto_archivo_tipo_motivo_o_valor_distinta_clave():
    base = clave_staging("h1", "ESTUDIANTE", "HOMONIMIA", "juan perez")
    assert len({base, clave_staging("h2", "ESTUDIANTE", "HOMONIMIA", "juan perez"), clave_staging("h1", "DOCENTE", "HOMONIMIA", "juan perez"),
                clave_staging("h1", "ESTUDIANTE", "BAJA_CONFIANZA_IA", "juan perez"), clave_staging("h1", "ESTUDIANTE", "HOMONIMIA", "juan perea")}) == 5
