"""
dispatcher.py — GIRA-8
Punto de entrada único del pipeline de ingestión.
Detecta el tipo de archivo por extensión y nombre, y enruta al lector correcto.
No sabe nada de IA — solo enruta.
"""

import os
from pathlib import Path
from datetime import datetime, timezone

from pipeline.ingestion.sheet_reader import leer_xlsx
from pipeline.ingestion.moodle_reader import leer_moodle_export
from pipeline.ingestion.forms_reader import leer_forms_csv


# Palabras clave en el nombre del archivo para distinguir CSV de Moodle vs Forms
_MOODLE_KEYWORDS = ["moodle", "calificaciones", "gradebook", "grades"]
_FORMS_KEYWORDS  = ["forms", "formulario", "encuesta", "inscripcion", "respuestas"]


def procesar_documento(file_path: str) -> dict:
    """
    Punto de entrada único del pipeline de ingestión.
    Detecta el tipo de archivo y llama al lector correcto.
    Devuelve siempre el mismo contrato de salida:

    {
        "texto_plano": str,
        "fuente_tipo": "SHEET" | "MOODLE" | "FORM",
        "nombre_archivo": str,
        "filas_raw": list[dict],
        "procesado_en": str  (ISO timestamp)
    }

    LÍMITE: No soporta PDF ni DOCX (fuera del alcance del sprint).
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {file_path}")

    ext = path.suffix.lower()
    nombre = path.stem.lower()
    
    # Extraer los componentes de la ruta en minúsculas
    partes_ruta = [p.lower() for p in path.parts]

    # Bloqueo explícito de formatos fuera de alcance
    if ext in (".pdf", ".docx", ".doc"):
        raise NotImplementedError(
            f"Formato {ext} no soportado en este sprint. "
            "Solo se procesan: XLSX, XLS, CSV (Moodle/Forms)."
        )
    if "finanzas" in partes_ruta:
        return leer_xlsx(file_path)

    # Ruteo por extensión
    if ext in (".xlsx", ".xls"):
        # XLSX puede ser acta de notas o export de Moodle
        if any(kw in nombre for kw in _MOODLE_KEYWORDS):
            return leer_moodle_export(file_path)
        return leer_xlsx(file_path)

    if ext == ".csv":
        if any(kw in nombre for kw in _MOODLE_KEYWORDS):
            return leer_moodle_export(file_path)
        if any(kw in nombre for kw in _FORMS_KEYWORDS):
            return leer_forms_csv(file_path)
        # Si no tiene keywords, intentar Forms por defecto (el más común)
        return leer_forms_csv(file_path)

    raise ValueError(
        f"Extensión '{ext}' no reconocida. "
        "Formatos válidos: .xlsx, .xls, .csv"
    )


# ── Prueba local ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    import json

    archivo = sys.argv[1] if len(sys.argv) > 1 else "uploads/prueba.xlsx"
    resultado = procesar_documento(archivo)

    print(f"\nFuente:   {resultado['fuente_tipo']}")
    print(f"Archivo:  {resultado['nombre_archivo']}")
    print(f"Filas:    {len(resultado['filas_raw'])}")
    print(f"\n--- Texto plano (primeras 500 chars) ---")
    print(resultado["texto_plano"][:500])
