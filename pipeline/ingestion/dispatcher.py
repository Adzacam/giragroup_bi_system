"""
dispatcher.py — GIRA-8 (Sprint 2 — refactorizado)
Punto de entrada único del pipeline de ingestión.
Detecta el tipo de archivo, enruta al lector correcto, clasifica hojas
por familia y retorna resultados segmentados con auditoría trazable.

Contrato de salida enriquecido que segmenta hojas en:
- texto_libre → insumo para BETO/NER
- estructurado_relacional → llaves para matching
- financiero → no entra a NLP
- descartable → log de auditoría con razón explícita
"""

import os
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from pipeline.ingestion.sheet_reader import leer_xlsx_multihoja, leer_xlsx
from pipeline.ingestion.moodle_reader import leer_moodle_export
from pipeline.ingestion.forms_reader import leer_forms_csv
from pipeline.ingestion.canonical_mapper import CanonicalMapper

logger = logging.getLogger(__name__)

# Palabras clave en el nombre del archivo para distinguir CSV de Moodle vs Forms
_MOODLE_KEYWORDS = ["moodle", "calificaciones", "gradebook", "grades"]
_FORMS_KEYWORDS  = ["forms", "formulario", "encuesta", "inscripcion", "respuestas"]


def _crear_mapper() -> Optional[CanonicalMapper]:
    """Crea una instancia del mapper canónico, tolerante a fallos."""
    try:
        return CanonicalMapper()
    except FileNotFoundError:
        logger.warning(
            "Diccionario canónico no encontrado. "
            "Operando sin mapeo de columnas."
        )
        return None


def procesar_documento(file_path: str) -> dict:
    """
    Punto de entrada único del pipeline de ingestión (retrocompatible).
    Detecta el tipo de archivo y llama al lector correcto.
    Devuelve siempre el mismo contrato de salida legacy:

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


def procesar_documento_completo(file_path: str) -> dict:
    """
    Punto de entrada NUEVO del pipeline de ingestión Sprint 2.
    Procesa TODAS las hojas del archivo, clasificándolas por familia,
    mapeando columnas canónicamente y descartando hojas basura
    con trazabilidad.

    Args:
        file_path: Ruta al archivo a procesar.

    Returns:
        {
            "nombre_archivo": str,
            "procesado_en": str (ISO),
            "fuente_tipo": "SHEET" | "MOODLE" | "FORM",

            "hojas_texto_libre": list[dict],
                # Cada dict: {nombre_hoja, data: DataFrame, columnas_texto_libre,
                #              mapeo_columnas, columnas_no_mapeadas, n_filas, ...}

            "hojas_estructuradas": list[dict],
                # Datos académicos/administrativos para matching/cruce

            "hojas_financieras": list[dict],
                # Datos financieros (no NLP)

            "hojas_descartadas": list[dict],
                # {nombre_hoja, razon} — auditoría trazable

            "estadisticas": {
                "total_hojas": int,
                "hojas_texto_libre": int,
                "hojas_estructuradas": int,
                "hojas_financieras": int,
                "hojas_descartadas": int,
            },

            "auditoria": {
                "columnas_no_mapeadas_global": list[dict],
            },
        }
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {file_path}")

    ext = path.suffix.lower()
    nombre = path.stem.lower()

    # Bloqueo explícito de formatos fuera de alcance
    if ext in (".pdf", ".docx", ".doc"):
        raise NotImplementedError(
            f"Formato {ext} no soportado en este sprint. "
            "Solo se procesan: XLSX, XLS, CSV (Moodle/Forms)."
        )

    # Determinar tipo de fuente
    if ext == ".csv":
        if any(kw in nombre for kw in _MOODLE_KEYWORDS):
            fuente_tipo = "MOODLE"
        elif any(kw in nombre for kw in _FORMS_KEYWORDS):
            fuente_tipo = "FORM"
        else:
            fuente_tipo = "FORM"
    else:
        if any(kw in nombre for kw in _MOODLE_KEYWORDS):
            fuente_tipo = "MOODLE"
        else:
            fuente_tipo = "SHEET"

    # ── Lectura multi-hoja con perfilado ──────────────────────────────
    mapper = _crear_mapper()
    resultado_raw = leer_xlsx_multihoja(file_path, mapper=mapper)

    # ── Segmentar hojas por familia ───────────────────────────────────
    hojas_texto_libre = []
    hojas_estructuradas = []
    hojas_financieras = []
    columnas_no_mapeadas_global = []

    for hoja in resultado_raw["hojas"]:
        familia = hoja["familia"]

        # Acumular columnas no mapeadas para auditoría global
        for col_info in hoja.get("columnas_no_mapeadas", []):
            col_info["hoja"] = hoja["nombre_hoja"]
            columnas_no_mapeadas_global.append(col_info)

        if familia == "texto_libre":
            hojas_texto_libre.append(hoja)
        elif familia == "financiero":
            hojas_financieras.append(hoja)
        else:
            # estructurado_relacional o cualquier otro
            hojas_estructuradas.append(hoja)

    logger.info(
        "Archivo '%s' procesado: %d texto_libre, %d estructuradas, "
        "%d financieras, %d descartadas",
        resultado_raw["nombre_archivo"],
        len(hojas_texto_libre),
        len(hojas_estructuradas),
        len(hojas_financieras),
        len(resultado_raw["hojas_descartadas"]),
    )

    return {
        "nombre_archivo": resultado_raw["nombre_archivo"],
        "procesado_en": resultado_raw["procesado_en"],
        "fuente_tipo": fuente_tipo,
        "hojas_texto_libre": hojas_texto_libre,
        "hojas_estructuradas": hojas_estructuradas,
        "hojas_financieras": hojas_financieras,
        "hojas_descartadas": resultado_raw["hojas_descartadas"],
        "estadisticas": {
            "total_hojas": resultado_raw["estadisticas"]["total_hojas"],
            "hojas_texto_libre": len(hojas_texto_libre),
            "hojas_estructuradas": len(hojas_estructuradas),
            "hojas_financieras": len(hojas_financieras),
            "hojas_descartadas": len(resultado_raw["hojas_descartadas"]),
        },
        "auditoria": {
            "columnas_no_mapeadas_global": columnas_no_mapeadas_global,
        },
    }


# ── Prueba local ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    import json

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    archivo = sys.argv[1] if len(sys.argv) > 1 else "uploads/prueba.xlsx"

    print("\n=== Modo completo (Sprint 2) ===")
    resultado = procesar_documento_completo(archivo)

    print(f"\nArchivo:  {resultado['nombre_archivo']}")
    print(f"Fuente:   {resultado['fuente_tipo']}")
    print(f"\nEstadísticas:")
    for k, v in resultado["estadisticas"].items():
        print(f"  {k}: {v}")

    if resultado["hojas_descartadas"]:
        print(f"\nHojas descartadas:")
        for h in resultado["hojas_descartadas"]:
            print(f"  - {h['nombre_hoja']}: {h['razon']}")

    if resultado["hojas_texto_libre"]:
        print(f"\nHojas de texto libre:")
        for h in resultado["hojas_texto_libre"]:
            print(f"  - {h['nombre_hoja']} ({h['n_filas']} filas)")
            print(f"    Columnas texto libre: {h['columnas_texto_libre']}")

    if resultado["auditoria"]["columnas_no_mapeadas_global"]:
        print(f"\nColumnas no mapeadas (auditoría):")
        for c in resultado["auditoria"]["columnas_no_mapeadas_global"][:10]:
            print(f"  - [{c.get('hoja','')}] {c['columna']} "
                  f"(mejor: {c.get('mejor_candidato', '?')}, "
                  f"score: {c.get('mejor_score', 0):.1f}%)")
