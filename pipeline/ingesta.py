"""
ingesta.py — Sprint 2, Loop 1
Lector universal de archivos heterogéneos.

Arquitectura: registro dinámico de funciones lectoras por extensión.
Para agregar soporte a un nuevo tipo de archivo (ej. .json, .parquet),
basta con definir una función con la firma:

    def leer_mi_formato(ruta: str) -> dict[str, pd.DataFrame]:
        ...

y registrarla:

    LECTORES[".json"] = leer_mi_formato

No se necesita herencia, subclases ni modificar código existente.

Restricción: toda validación se hace contra uploads/data (corpus real).
Queda prohibido usar uploads/test o datos sintéticos preexistentes.
"""

import csv
import logging
import os
from pathlib import Path
from typing import Callable

import pandas as pd

logger = logging.getLogger(__name__)

# ── Tipo de la función lectora ──────────────────────────────────────
# Recibe una ruta, devuelve {nombre_hoja: DataFrame_crudo}.
# Para formatos sin concepto de "hoja" (como CSV), la clave es el
# nombre del archivo sin extensión.
LectorFn = Callable[[str], dict[str, pd.DataFrame]]


# ── Lectores concretos ──────────────────────────────────────────────

def _leer_xlsx(ruta: str) -> dict[str, pd.DataFrame]:
    """
    Lee todas las hojas de un archivo .xlsx/.xls sin procesar nada:
    sin header, sin dropna, sin fillna. Devuelve los DataFrames tal
    cual los entrega pandas/openpyxl.
    """
    try:
        hojas = pd.read_excel(
            ruta,
            sheet_name=None,   # todas las hojas
            header=None,       # no asumir fila de encabezado
            dtype=str,         # todo como texto para no perder datos
        )
    except Exception:
        # Fallback para .xls (xlrd engine)
        try:
            hojas = pd.read_excel(
                ruta,
                sheet_name=None,
                header=None,
                dtype=str,
                engine="xlrd",
            )
        except Exception as e:
            logger.error("No se pudo leer '%s': %s", ruta, e)
            return {}

    logger.info(
        "Archivo '%s': %d hoja(s) leída(s).",
        os.path.basename(ruta), len(hojas),
    )
    return hojas


def _leer_csv(ruta: str) -> dict[str, pd.DataFrame]:
    """
    Lee un archivo CSV completo como una sola "hoja".
    La clave del dict es el nombre del archivo sin extensión.
    """
    nombre = Path(ruta).stem
    try:
        # Detectar delimitador
        with open(ruta, "r", encoding="utf-8", errors="replace") as f:
            muestra = f.read(4096)
        try:
            dialecto = csv.Sniffer().sniff(muestra)
            sep = dialecto.delimiter
        except csv.Error:
            sep = ","

        df = pd.read_csv(ruta, header=None, dtype=str, sep=sep)
        logger.info(
            "Archivo CSV '%s': 1 hoja, %d filas × %d columnas.",
            os.path.basename(ruta), len(df), len(df.columns),
        )
        return {nombre: df}
    except Exception as e:
        logger.error("No se pudo leer CSV '%s': %s", ruta, e)
        return {}


# ── Registro de lectores por extensión ──────────────────────────────
# Para agregar un nuevo formato:
#   from pipeline.ingesta import LECTORES
#   LECTORES[".json"] = mi_funcion_lectora_json
LECTORES: dict[str, LectorFn] = {
    ".xlsx": _leer_xlsx,
    ".xls":  _leer_xlsx,
    ".csv":  _leer_csv,
}


# ── Función pública principal ───────────────────────────────────────

def leer_archivo(ruta: str) -> dict[str, pd.DataFrame]:
    """
    Lee un archivo y devuelve un dict {nombre_hoja: DataFrame_crudo}.

    - Si la extensión no está soportada, loguea un warning y devuelve {}.
    - Si el archivo no existe, loguea un error y devuelve {}.
    - Nunca lanza excepciones: loguea y continúa.
    """
    if not os.path.exists(ruta):
        logger.error("Archivo no encontrado: '%s'", ruta)
        return {}

    ext = Path(ruta).suffix.lower()
    lector = LECTORES.get(ext)

    if lector is None:
        logger.warning(
            "Extensión '%s' no soportada para '%s'. "
            "Extensiones válidas: %s",
            ext, ruta, list(LECTORES.keys()),
        )
        return {}

    return lector(ruta)


def leer_corpus(directorio: str) -> dict[str, dict[str, pd.DataFrame]]:
    """
    Lee todos los archivos soportados dentro de un directorio.
    Devuelve {nombre_archivo: {nombre_hoja: DataFrame}}.

    Nunca se detiene por un archivo corrupto: loguea el error y
    continúa con el siguiente.
    """
    resultados = {}
    ruta_dir = Path(directorio)

    if not ruta_dir.is_dir():
        logger.error("Directorio no encontrado: '%s'", directorio)
        return resultados

    archivos = sorted(
        f for f in ruta_dir.iterdir()
        if f.is_file() and f.suffix.lower() in LECTORES
    )

    logger.info(
        "Corpus '%s': %d archivo(s) soportado(s) encontrado(s).",
        directorio, len(archivos),
    )

    for archivo in archivos:
        hojas = leer_archivo(str(archivo))
        resultados[archivo.name] = hojas

    return resultados
