"""
pipeline/analytics/seed_historical_facts.py
-------------------------------------------
GIRA-52b: Ingesta de soporte histórico hacia fact_marketing, fact_rentabilidad y dim_meta.
Puebla el Data Warehouse con las series históricas de:
1. TBL_INSCRITOS.xlsx -> fact_marketing (alumnos inscritos agrupados por periodo y programa)
2. EJECUTADO VS META.xlsx -> fact_rentabilidad y dim_meta (ingresos ejecutados vs metas presupuestarias)
"""

import os
import re
import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any

import pandas as pd
from sqlalchemy import text, Engine

# Añadir raíz al sys.path para imports limpios
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from pipeline.config import DATA_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed_historical_facts")


def obtener_engine() -> Engine:
    """Obtiene el engine del Data Warehouse desde backend.core.database."""
    from backend.core.database import engine
    return engine


def normalizar_tipo_programa(nombre: str) -> str:
    """Extrae el tipo canónico de programa académico."""
    if not isinstance(nombre, str):
        return "OTRO"
    nombre_upper = nombre.upper()
    if "DIPLOMADO" in nombre_upper:
        return "DIPLOMADO"
    if "PROGRAMA EXPERTO" in nombre_upper or "EXPERTO" in nombre_upper:
        return "PROGRAMA EXPERTO"
    if "CURSO" in nombre_upper:
        return "CURSO"
    if "MAESTRIA" in nombre_upper or "MAESTRÍA" in nombre_upper:
        return "MAESTRIA"
    return "OTRO"


def seed_fact_marketing(engine: Engine, data_dir: Optional[Path] = None) -> int:
    """
    Carga TBL_INSCRITOS.xlsx en fact_marketing y dim_modulo.
    Retorna el número de registros insertados/actualizados.
    """
    dir_datos = data_dir or DATA_DIR
    archivo = dir_datos / "TBL_INSCRITOS.xlsx"
    if not archivo.exists():
        logger.warning(f"No se encontró archivo {archivo}. Omitiendo carga de fact_marketing.")
        return 0

    logger.info(f"Procesando {archivo.name}...")
    df = pd.read_excel(archivo, sheet_name="TBL_INSCRITOS")
    df["MARCA TEMPORAL"] = pd.to_datetime(df["MARCA TEMPORAL"], errors="coerce")
    df = df.dropna(subset=["MARCA TEMPORAL"])

    df["anio"] = df["MARCA TEMPORAL"].dt.year
    df["mes"] = df["MARCA TEMPORAL"].dt.month
    df["id_tiempo"] = df["anio"] * 10000 + df["mes"] * 100 + 1  # 1er día del mes
    df["tipo_prog"] = df["NOMBRE DEL PROGRAMA"].apply(normalizar_tipo_programa)
    df["pos_code"] = df["NUMEROPROYECTO"].fillna("POS-GENERICO").astype(str).str.strip()

    # Agrupar por pos_code, tipo_prog, id_tiempo
    agrupado = df.groupby(["pos_code", "tipo_prog", "id_tiempo"]).size().reset_index(name="inscritos")

    with engine.begin() as conn:
        # Asegurar modulos sintéticos por tipo para agregación
        for tipo in ["DIPLOMADO", "PROGRAMA EXPERTO", "CURSO", "MAESTRIA", "OTRO"]:
            conn.execute(
                text("""
                    INSERT INTO public.dim_modulo (nombre_modulo, nombre_institucion, programa, pos_code)
                    SELECT :nombre, 'GiraGroup', :programa, :pos
                    WHERE NOT EXISTS (
                        SELECT 1 FROM public.dim_modulo WHERE pos_code = :pos
                    )
                """),
                {"nombre": f"Modulo Consolidado {tipo}", "programa": tipo, "pos": f"CANONICAL-{tipo}"}
            )

        # Mapear id_modulo por pos_code
        res = conn.execute(text("SELECT id_modulo, programa, pos_code FROM public.dim_modulo"))
        modulos_map = {row.pos_code: row.id_modulo for row in res}
        tipos_map = {row.programa: row.id_modulo for row in res if str(row.pos_code).startswith("CANONICAL-")}

        filas_cargadas = 0
        for _, row in agrupado.iterrows():
            pos = row["pos_code"]
            tipo = row["tipo_prog"]
            id_tiempo = int(row["id_tiempo"])
            inscritos = int(row["inscritos"])

            id_mod = modulos_map.get(pos) or tipos_map.get(tipo)
            if not id_mod:
                # Insertar nuevo módulo si no existe
                ins = conn.execute(
                    text("""
                        INSERT INTO public.dim_modulo (nombre_modulo, nombre_institucion, programa, pos_code)
                        VALUES (:nombre, 'GiraGroup', :prog, :pos)
                        RETURNING id_modulo
                    """),
                    {"nombre": f"Programa {pos}", "prog": tipo, "pos": pos}
                )
                id_mod = ins.scalar_one()
                modulos_map[pos] = id_mod

            # Upsert en fact_marketing
            conn.execute(
                text("""
                    INSERT INTO public.fact_marketing (id_modulo, id_tiempo, inscritos, leads, reservas)
                    VALUES (:id_mod, :id_t, :insc, 0, 0)
                    ON CONFLICT (id_modulo, id_tiempo)
                    DO UPDATE SET inscritos = EXCLUDED.inscritos
                """),
                {"id_mod": id_mod, "id_t": id_tiempo, "insc": inscritos}
            )
            filas_cargadas += 1

    logger.info(f"fact_marketing poblada exitosamente: {filas_cargadas} registros.")
    return filas_cargadas


def seed_fact_rentabilidad_y_metas(engine: Engine, data_dir: Optional[Path] = None) -> int:
    """
    Carga EJECUTADO VS META.xlsx en fact_rentabilidad y dim_meta.
    Retorna el número de periodos mensuales procesados.
    """
    dir_datos = data_dir or DATA_DIR
    archivo = dir_datos / "EJECUTADO VS META.xlsx"
    if not archivo.exists():
        logger.warning(f"No se encontró archivo {archivo}. Omitiendo carga de rentabilidad.")
        return 0

    logger.info(f"Procesando {archivo.name}...")
    df = pd.read_excel(archivo, sheet_name="EJECUTADO")

    with engine.begin() as conn:
        # 1. Asegurar categorías financieras
        cat_map = {}
        for cat in ["PROGRAMAS", "TECHOS_CERRADOS", "FINANCIERO_ANUAL"]:
            conn.execute(
                text("""
                    INSERT INTO public.dim_categoria_financiera (nombre_categoria, tipo)
                    VALUES (:nombre, 'INGRESO')
                    ON CONFLICT (nombre_categoria) DO NOTHING
                """),
                {"nombre": cat}
            )
            cid = conn.execute(
                text("SELECT id_categoria FROM public.dim_categoria_financiera WHERE nombre_categoria = :nombre"),
                {"nombre": cat}
            ).scalar_one()
            cat_map[cat] = cid

        registros = 0
        for _, row in df.iterrows():
            cat_raw = str(row.get("CATEGORIA", "")).strip().upper()
            if "PROGRAMAS" in cat_raw:
                cat_nombre = "PROGRAMAS"
            elif "TECHO" in cat_raw or "CERRADO" in cat_raw:
                cat_nombre = "TECHOS_CERRADOS"
            else:
                continue

            id_cat = cat_map[cat_nombre]
            mes_num = row.get("MES NUMERICO")
            if pd.isna(mes_num):
                continue
            mes_num = int(mes_num)

            # Iterar por años disponibles
            anios_cols = [
                (2023, "EJECUTADO 2023", None),
                (2024, "EJECUTADO 2024", "META POR CATEGORIA 2024"),
                (2025, "EJECUTADO 2025", "META POR CATEGORIA 2025"),
                (2026, "EJECUTADO 2026", "META POR CATEGORIA 2026"),
            ]

            for anio, col_ejec, col_meta in anios_cols:
                id_tiempo = anio * 10000 + mes_num * 100 + 1
                ejec = row.get(col_ejec)
                meta = row.get(col_meta) if col_meta else None

                val_ejec = float(ejec) if pd.notna(ejec) and isinstance(ejec, (int, float)) else None
                val_meta = float(meta) if pd.notna(meta) and isinstance(meta, (int, float)) else None

                if val_ejec is None and val_meta is None:
                    continue

                # Cargar en fact_rentabilidad
                conn.execute(
                    text("""
                        INSERT INTO public.fact_rentabilidad (id_categoria, id_tiempo, monto_ejecutado, monto_meta)
                        VALUES (:id_cat, :id_t, :ejec, :meta)
                        ON CONFLICT (id_categoria, id_tiempo)
                        DO UPDATE SET 
                            monto_ejecutado = COALESCE(EXCLUDED.monto_ejecutado, public.fact_rentabilidad.monto_ejecutado),
                            monto_meta = COALESCE(EXCLUDED.monto_meta, public.fact_rentabilidad.monto_meta)
                    """),
                    {"id_cat": id_cat, "id_t": id_tiempo, "ejec": val_ejec, "meta": val_meta}
                )

                # Cargar en dim_meta si hay monto objetivo
                if val_meta is not None:
                    conn.execute(
                        text("""
                            INSERT INTO public.dim_meta (categoria, id_tiempo, monto_meta, tipo_programa)
                            VALUES (:cat, :id_t, :meta, NULL)
                        """),
                        {"cat": cat_nombre, "id_t": id_tiempo, "meta": val_meta}
                    )
                registros += 1

    logger.info(f"fact_rentabilidad y dim_meta pobladas exitosamente: {registros} entradas.")
    return registros


def ejecutar_seeding() -> None:
    """Función principal de ejecución del seeding histórico."""
    logger.info("Iniciando GIRA-52b: Ingesta de soporte histórico...")
    try:
        eng = obtener_engine()
        # Verificar conexión
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Conexión a base de datos PostgreSQL exitosa.")
        seed_fact_marketing(eng)
        seed_fact_rentabilidad_y_metas(eng)
        logger.info("GIRA-52b finalizado con éxito.")
    except Exception as e:
        logger.error(f"Error durante el seeding: {e}")
        raise


if __name__ == "__main__":
    ejecutar_seeding()
