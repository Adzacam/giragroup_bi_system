"""
pipeline/analytics/time_series_extractor.py
-------------------------------------------
GIRA-53: Extractor de series temporales mensuales desde el Data Warehouse (PostgreSQL)
con soporte de fallback directo a fuentes analíticas para entornos de prueba.

Extrae 5 series temporales canónicas indexadas por Period('M') o año:
1. ALUMNOS_GLOBAL: Inscripciones totales mensuales.
2. ALUMNOS_DIPLOMADO: Inscripciones mensuales en Diplomados.
3. ALUMNOS_CURSO: Inscripciones mensuales en Cursos.
4. ALUMNOS_EXPERTO: Inscripciones mensuales en Programas Expertos.
5. META_MENSUAL_PROGRAMAS: Monto ejecutado / meta mensual en Programas regulares.
6. META_ANUAL: Serie anual de recaudación ejecutada (2023-2025).
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

from pipeline.config import DATA_DIR

logger = logging.getLogger("time_series_extractor")


QUERIES = {
    "ALUMNOS_GLOBAL": """
        SELECT 
            dt.periodo_mes,
            COALESCE(SUM(fm.inscritos), 0)::numeric AS valor
        FROM public.dim_tiempo dt
        LEFT JOIN public.fact_marketing fm ON dt.id_tiempo = fm.id_tiempo
        WHERE dt.fecha >= '2022-11-01' AND dt.fecha <= '2026-05-31'
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
          AND dt.fecha >= '2022-11-01' AND dt.fecha <= '2026-05-31'
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
          AND dt.fecha >= '2022-11-01' AND dt.fecha <= '2026-05-31'
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
          AND dt.fecha >= '2022-11-01' AND dt.fecha <= '2026-05-31'
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
          AND dt.gestion IN (2023, 2024, 2025)
        GROUP BY dt.gestion
        ORDER BY dt.gestion;
    """
}


import time

_DB_FAIL_UNTIL: float = 0.0
_EXCEL_CACHE: Dict[str, pd.DataFrame] = {}


def _extraer_desde_archivos(caso_uso: str, data_dir: Optional[Path] = None) -> pd.Series:
    """Extrae series de fallback directamente de los Excel de uploads/data/ con cache en memoria."""
    dir_datos = data_dir or DATA_DIR
    caso_upper = caso_uso.upper()

    if "ALUMNOS" in caso_upper:
        archivo = dir_datos / "TBL_INSCRITOS.xlsx"
        if not archivo.exists():
            raise FileNotFoundError(f"Archivo requerido no encontrado: {archivo}")

        if "TBL_INSCRITOS" not in _EXCEL_CACHE:
            df = pd.read_excel(archivo, sheet_name="TBL_INSCRITOS")
            df["MARCA TEMPORAL"] = pd.to_datetime(df["MARCA TEMPORAL"], errors="coerce")
            df = df.dropna(subset=["MARCA TEMPORAL"])
            df["periodo_mes"] = df["MARCA TEMPORAL"].dt.to_period("M")
            _EXCEL_CACHE["TBL_INSCRITOS"] = df
        else:
            df = _EXCEL_CACHE["TBL_INSCRITOS"]

        if caso_upper == "ALUMNOS_GLOBAL":
            serie = df.groupby("periodo_mes").size()
        elif caso_upper == "ALUMNOS_DIPLOMADO":
            sub = df[df["NOMBRE DEL PROGRAMA"].str.upper().str.contains("DIPLOMADO", na=False)]
            serie = sub.groupby("periodo_mes").size()
        elif caso_upper == "ALUMNOS_CURSO":
            sub = df[df["NOMBRE DEL PROGRAMA"].str.upper().str.contains("CURSO", na=False)]
            serie = sub.groupby("periodo_mes").size()
        elif caso_upper == "ALUMNOS_EXPERTO":
            sub = df[df["NOMBRE DEL PROGRAMA"].str.upper().str.contains("EXPERTO", na=False)]
            serie = sub.groupby("periodo_mes").size()
        else:
            serie = df.groupby("periodo_mes").size()

        serie = serie.sort_index().astype(float)
        serie.name = caso_upper
        return serie

    elif caso_upper in ("META_MENSUAL_PROGRAMAS", "META_ANUAL"):
        archivo = dir_datos / "EJECUTADO VS META.xlsx"
        if not archivo.exists():
            raise FileNotFoundError(f"Archivo requerido no encontrado: {archivo}")

        if "EJECUTADO" not in _EXCEL_CACHE:
            df = pd.read_excel(archivo, sheet_name="EJECUTADO")
            _EXCEL_CACHE["EJECUTADO"] = df
        else:
            df = _EXCEL_CACHE["EJECUTADO"]

        df_prog = df[df["CATEGORIA"].astype(str).str.upper().str.contains("PROGRAMAS", na=False)].copy()
        
        if caso_upper == "META_MENSUAL_PROGRAMAS":
            records = []
            for _, row in df_prog.iterrows():
                mes_num = int(row["MES NUMERICO"])
                for anio, col in [(2023, "EJECUTADO 2023"), (2024, "EJECUTADO 2024"), (2025, "EJECUTADO 2025")]:
                    val = row.get(col)
                    if pd.notna(val) and isinstance(val, (int, float)) and val > 0:
                        records.append({
                            "periodo_mes": pd.Period(f"{anio}-{mes_num:02d}", freq="M"),
                            "valor": float(val)
                        })
            res_df = pd.DataFrame(records).sort_values("periodo_mes")
            serie = pd.Series(res_df["valor"].values, index=res_df["periodo_mes"], name=caso_upper)
            return serie

        elif caso_upper == "META_ANUAL":
            anios = [2023, 2024, 2025]
            totales = []
            for anio in anios:
                col = f"EJECUTADO {anio}"
                tot = df_prog[col].apply(lambda x: float(x) if pd.notna(x) and isinstance(x, (int, float)) else 0.0).sum()
                totales.append(tot)
            serie = pd.Series(totales, index=anios, name="META_ANUAL", dtype=float)
            return serie

    raise ValueError(f"Caso de uso no reconocido: {caso_uso}")


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

    # Fallback automático y veloz
    serie = _extraer_desde_archivos(caso_norm, data_dir=data_dir)
    return serie
