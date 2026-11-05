"""
pipeline/analytics/time_series_extractor.py
-------------------------------------------
GIRA-53: Extractor de series temporales mensuales desde el Data Warehouse (PostgreSQL)
sin fallback a archivos: si el DW no tiene datos, la serie se devuelve vacía.

Extrae 5 series temporales canónicas indexadas por Period('M') o año:
1. ALUMNOS_GLOBAL: Inscripciones totales mensuales.
2. ALUMNOS_DIPLOMADO: Inscripciones mensuales en Diplomados.
3. ALUMNOS_CURSO: Inscripciones mensuales en Cursos.
4. ALUMNOS_EXPERTO: Inscripciones mensuales en Programas Expertos.
5. META_MENSUAL_PROGRAMAS: Monto ejecutado / meta mensual en Programas regulares.
6. META_ANUAL: Serie anual de recaudación ejecutada (gestiones cerradas).
"""

import sys
import logging
from pathlib import Path
from typing import Optional, Dict

import pandas as pd
from sqlalchemy import text, Engine

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


logger = logging.getLogger("time_series_extractor")


QUERIES = {
    "ALUMNOS_GLOBAL": """
        SELECT 
            dt.periodo_mes,
            COALESCE(SUM(fm.inscritos), 0)::numeric AS valor
        FROM public.dim_tiempo dt
        LEFT JOIN public.fact_marketing fm ON dt.id_tiempo = fm.id_tiempo
        GROUP BY dt.periodo_mes
        HAVING SUM(fm.inscritos) > 0
        ORDER BY dt.periodo_mes;
    """,
    "ALUMNOS_DIPLOMADO": """
        SELECT 
            dt.periodo_mes,
            COALESCE(SUM(fm.inscritos), 0)::numeric AS valor
        FROM public.dim_tiempo dt
        JOIN public.fact_marketing fm ON dt.id_tiempo = fm.id_tiempo
        JOIN public.dim_modulo dm ON fm.id_modulo = dm.id_modulo
        WHERE dm.programa ILIKE '%DIPLOMADO%'
        GROUP BY dt.periodo_mes
        ORDER BY dt.periodo_mes;
    """,
    "ALUMNOS_CURSO": """
        SELECT 
            dt.periodo_mes,
            COALESCE(SUM(fm.inscritos), 0)::numeric AS valor
        FROM public.dim_tiempo dt
        JOIN public.fact_marketing fm ON dt.id_tiempo = fm.id_tiempo
        JOIN public.dim_modulo dm ON fm.id_modulo = dm.id_modulo
        WHERE dm.programa ILIKE '%CURSO%'
        GROUP BY dt.periodo_mes
        ORDER BY dt.periodo_mes;
    """,
    "ALUMNOS_EXPERTO": """
        SELECT 
            dt.periodo_mes,
            COALESCE(SUM(fm.inscritos), 0)::numeric AS valor
        FROM public.dim_tiempo dt
        JOIN public.fact_marketing fm ON dt.id_tiempo = fm.id_tiempo
        JOIN public.dim_modulo dm ON fm.id_modulo = dm.id_modulo
        WHERE (dm.programa ILIKE '%EXPERTO%' OR dm.programa ILIKE '%PROGRAMA EXPERTO%')
        GROUP BY dt.periodo_mes
        ORDER BY dt.periodo_mes;
    """,
    "META_MENSUAL_PROGRAMAS": """
        SELECT 
            dt.periodo_mes,
            COALESCE(fr.monto_ejecutado, fr.monto_meta)::numeric AS valor
        FROM public.fact_rentabilidad fr
        JOIN public.dim_categoria_financiera dcf ON fr.id_categoria = dcf.id_categoria
        JOIN public.dim_tiempo dt ON fr.id_tiempo = dt.id_tiempo
        WHERE dcf.nombre_categoria = 'PROGRAMAS'
          AND COALESCE(fr.monto_ejecutado, fr.monto_meta) IS NOT NULL
        ORDER BY dt.periodo_mes;
    """,
    "META_ANUAL": """
        SELECT 
            dt.gestion AS anio,
            SUM(fr.monto_ejecutado)::numeric AS valor
        FROM public.fact_rentabilidad fr
        JOIN public.dim_categoria_financiera dcf ON fr.id_categoria = dcf.id_categoria
        JOIN public.dim_tiempo dt ON fr.id_tiempo = dt.id_tiempo
        WHERE dcf.nombre_categoria = 'PROGRAMAS'
          AND fr.monto_ejecutado IS NOT NULL
          AND dt.gestion < EXTRACT(YEAR FROM CURRENT_DATE)
        GROUP BY dt.gestion
        ORDER BY dt.gestion;
    """
}


import time

_DB_FAIL_UNTIL: float = 0.0


def extraer_serie_temporal(
    caso_uso: str, 
    engine: Optional[Engine] = None, 
    data_dir: Optional[Path] = None
) -> pd.Series:
    """
    Punto de entrada principal para extraer una serie temporal.
    Implementa patrón Circuit Breaker para evitar latencias de reconexión.
    """
    global _DB_FAIL_UNTIL
    caso_norm = caso_uso.strip().upper()
    if caso_norm not in QUERIES:
        raise ValueError(f"Caso '{caso_norm}' no es válido. Opciones: {list(QUERIES.keys())}")

    now = time.time()
    # Si la BD no está en periodo de enfriamiento (cooldown), intentar conexión
    if engine is not None and now >= _DB_FAIL_UNTIL:
        try:
            with engine.connect() as conn:
                df = pd.read_sql(text(QUERIES[caso_norm]), conn)
                if not df.empty and len(df) >= 3:
                    if caso_norm == "META_ANUAL":
                        serie = pd.Series(df["valor"].astype(float).values, index=df["anio"].astype(int), name=caso_norm)
                    else:
                        df["periodo_mes"] = pd.PeriodIndex(df["periodo_mes"], freq="M")
                        serie = pd.Series(df["valor"].astype(float).values, index=df["periodo_mes"], name=caso_norm)
                    logger.info(f"Serie '{caso_norm}' extraída exitosamente de PostgreSQL (N={len(serie)}).")
                    return serie
        except Exception as e:
            # Activar Circuit Breaker por 30 segundos
            _DB_FAIL_UNTIL = now + 30.0
            logger.warning(f"Extracción DB falló para '{caso_norm}' ({e}). Activando Circuit Breaker (30s) y fallback...")

    # Sin datos suficientes en el DW: serie vacía. Nunca se leen los Excel crudos
    # de uploads/data, el único origen válido es lo ingestado y aprobado en PostgreSQL.
    logger.info(f"Serie '{caso_norm}' sin datos suficientes en el Data Warehouse.")
    return pd.Series(dtype=float, name=caso_norm)
