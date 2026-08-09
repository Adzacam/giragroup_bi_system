"""
normalizer.py — GIRA-11, GIRA-41
Normalización difusa y matching semántico para resolución
de dimensiones del data warehouse (estudiantes, docentes, módulos).
"""

import logging
from typing import Optional

import pandas as pd
from rapidfuzz import fuzz, process

from pipeline.normalization.text_cleaner import normalizar_nombre

logger = logging.getLogger(__name__)

# Umbral mínimo de similitud fuzzy para considerar un match válido
_UMBRAL_FUZZY_ALTO = 85
_UMBRAL_FUZZY_MINIMO = 60


def asociar_entidad_fuzzy(
    nombre_crudo: str,
    catalogos_maestros: list[str],
    score_cutoff: int = _UMBRAL_FUZZY_MINIMO,
) -> tuple[Optional[str], float]:
    """
    Asocia un nombre crudo al mejor candidato de un catálogo maestro
    utilizando similitud Jaro-Winkler (rapidfuzz).

    Args:
        nombre_crudo: Texto libre a resolver.
        catalogos_maestros: Lista de nombres estándar del catálogo dimensional.
        score_cutoff: Puntaje mínimo para considerar un match.

    Returns:
        (nombre_estandarizado, score) — score normalizado entre 0.0 y 1.0.
        Si no hay match válido, retorna (None, 0.0).
    """
    if not nombre_crudo or not catalogos_maestros:
        return None, 0.0

    nombre_limpio = normalizar_nombre(nombre_crudo)
    if not nombre_limpio:
        return None, 0.0

    resultado = process.extractOne(
        nombre_limpio,
        catalogos_maestros,
        scorer=fuzz.WRatio,
        score_cutoff=score_cutoff,
    )

    if resultado is None:
        return None, 0.0

    nombre_match, score_raw, _idx = resultado
    score_normalizado = round(score_raw / 100.0, 4)

    return nombre_match, score_normalizado


def resolver_dimension_estudiante(
    ci_crudo: Optional[str],
    nombre_crudo: Optional[str],
    catalogo_estudiantes_df: pd.DataFrame,
) -> dict:
    """
    Resuelve la dimensión de estudiante por CI exacto o fuzzy matching sobre nombre.

    Args:
        ci_crudo: Código/CI del estudiante (puede ser None).
        nombre_crudo: Nombre completo del estudiante (puede ser None).
        catalogo_estudiantes_df: DataFrame con columnas:
            id_estudiante, codigo_estudiante, nombre_completo

    Returns:
        dict con: id_resuelto, nombre_estandarizado, distancia_fuzzy_minima, metodo_match
    """
    resultado_vacio = {
        "id_resuelto": None,
        "nombre_estandarizado": None,
        "distancia_fuzzy_minima": 0.0,
        "metodo_match": "NO_MATCH",
    }

    if catalogo_estudiantes_df.empty:
        return resultado_vacio

    # Intento 1: Búsqueda exacta por CI/código interno
    if ci_crudo and str(ci_crudo).strip():
        ci_normalizado = str(ci_crudo).strip()
        match_ci = catalogo_estudiantes_df[
            catalogo_estudiantes_df["codigo_estudiante"].astype(str).str.strip() == ci_normalizado
        ]
        if not match_ci.empty:
            fila = match_ci.iloc[0]
            return {
                "id_resuelto": int(fila["id_estudiante"]),
                "nombre_estandarizado": fila["nombre_completo"],
                "distancia_fuzzy_minima": 1.0,
                "metodo_match": "EXACTO_CI",
            }

    # Intento 2: Fuzzy matching sobre nombre_completo
    if nombre_crudo and str(nombre_crudo).strip():
        catalogos = catalogo_estudiantes_df["nombre_completo"].tolist()
        nombre_match, score = asociar_entidad_fuzzy(nombre_crudo, catalogos)

        if nombre_match is not None:
            fila_match = catalogo_estudiantes_df[
                catalogo_estudiantes_df["nombre_completo"] == nombre_match
            ].iloc[0]

            return {
                "id_resuelto": int(fila_match["id_estudiante"]),
                "nombre_estandarizado": nombre_match,
                "distancia_fuzzy_minima": score,
                "metodo_match": "FUZZY_NOMBRE",
            }

    return resultado_vacio


def resolver_dimension_docente(
    nombre_crudo: Optional[str],
    catalogo_docentes_df: pd.DataFrame,
) -> dict:
    """
    Resuelve la dimensión de docente por fuzzy matching.
    Combina el nombre del programa con el nombre del instructor
    extraído por el motor NER.

    Args:
        nombre_crudo: Nombre del docente (puede venir del NER).
        catalogo_docentes_df: DataFrame con columnas:
            id_docente, nombre_completo

    Returns:
        dict con: id_resuelto, nombre_estandarizado, distancia_fuzzy_minima, metodo_match
    """
    resultado_vacio = {
        "id_resuelto": None,
        "nombre_estandarizado": None,
        "distancia_fuzzy_minima": 0.0,
        "metodo_match": "NO_MATCH",
    }

    if not nombre_crudo or catalogo_docentes_df.empty:
        return resultado_vacio

    catalogos = catalogo_docentes_df["nombre_completo"].tolist()
    nombre_match, score = asociar_entidad_fuzzy(nombre_crudo, catalogos)

    if nombre_match is not None:
        fila_match = catalogo_docentes_df[
            catalogo_docentes_df["nombre_completo"] == nombre_match
        ].iloc[0]

        return {
            "id_resuelto": int(fila_match["id_docente"]),
            "nombre_estandarizado": nombre_match,
            "distancia_fuzzy_minima": score,
            "metodo_match": "FUZZY_NOMBRE",
        }

    return resultado_vacio
