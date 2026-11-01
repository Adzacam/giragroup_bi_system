"""
moodle_adapter.py
-----------------
Lector y adaptador especializado para reportes exportados de Moodle (CSV y XLSX).
Normaliza cabeceras características de Moodle (p. ej. 'First name', 'Surname', 'Grade/100.00', etc.)
y las transforma hacia el contrato de salida estandarizado.
"""

import os
import re
import csv
import logging
from typing import Any
try:
    import pandas as pd
except ImportError:
    pd = None

logger = logging.getLogger(__name__)

# Mapeo de cabeceras Moodle típicas a nombres canónicos canónicos
MOODLE_HEADER_MAP = {
    "first name": "nombre",
    "nombre": "nombre",
    "surname": "apellido",
    "apellido(s)": "apellido",
    "apellidos": "apellido",
    "id number": "ci_estudiante",
    "número de id": "ci_estudiante",
    "numero de id": "ci_estudiante",
    "institution": "institucion",
    "institución": "institucion",
    "department": "departamento",
    "email address": "email",
    "dirección de correo": "email",
    "correo electrónico": "email",
    "course": "modulo",
    "curso": "modulo",
    "grade": "nota_final",
    "calificación": "nota_final",
    "calificacion": "nota_final",
    "final grade": "nota_final",
    "status": "estado_moodle",
    "last downloaded from this course": "fecha_descarga",
}

def es_reporte_moodle(df: pd.DataFrame, nombre_archivo: str = "") -> bool:
    """
    Determina si un DataFrame proviene de una exportación de Moodle
    analizando el nombre del archivo o las primeras filas de encabezado.
    """
    nombre_lower = nombre_archivo.lower()
    if any(k in nombre_lower for k in ["moodle", "calificaciones", "grades", "participacion"]):
        return True

    # Revisar las primeras filas en busca de cabeceras Moodle
    if df is not None and not df.empty:
        filas_muestra = df.iloc[:3].values.flatten()
        for celda in filas_muestra:
            if pd.notna(celda):
                texto = str(celda).strip().lower()
                if any(h in texto for h in ["first name", "surname", "id number", "dirección de correo", "calificación/"]):
                    return True
    return False

def adaptar_moodle_df(df: Any) -> Any:
    """
    Limpia y normaliza un DataFrame exportado de Moodle:
    - Encuentra la fila real de cabeceras
    - Mapea las cabeceras Moodle a nombres canónicos
    - Descarta filas de resumen como 'Promedio general' o 'Overall average'
    """
    if df is None or getattr(df, "empty", True):
        return df

    def _notna(v: Any) -> bool:
        if pd is not None:
            return bool(pd.notna(v))
        return v is not None and str(v) != "nan" and str(v) != "None"

    # Buscar la fila de cabeceras (inspeccionar hasta 12 filas)
    header_idx = -1
    for idx in range(min(12, len(df))):
        fila = [str(x).strip().lower() for x in df.iloc[idx] if _notna(x)]
        matches = sum(1 for celda in fila if any(k in celda for k in ["first name", "surname", "nombre", "apellido", "email", "id", "grade", "calificación", "course"]))
        if matches >= 2:
            header_idx = idx
            break

    if header_idx != -1:
        # Extraer cabeceras
        headers = [str(col).strip() if _notna(col) else f"col_{i}" for i, col in enumerate(df.iloc[header_idx])]
        df_clean = df.iloc[header_idx + 1:].copy().reset_index(drop=True)
        df_clean.columns = headers
    else:
        df_clean = df.copy()

    # Descartar filas de agregación/resumen de Moodle
    if len(df_clean) > 0 and len(df_clean.columns) > 0:
        primera_col = df_clean.columns[0]
        descartar_patron = "overall average|promedio general|media del curso|total general|course total|subtotal|firma"
        df_clean = df_clean[~df_clean[primera_col].astype(str).str.lower().str.contains(descartar_patron, na=False)]

    return df_clean
