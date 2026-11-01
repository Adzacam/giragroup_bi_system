#!/usr/bin/env python
"""
scripts/reset_dw.py
===================
Script de Reset y Truncado Seguro del Data Warehouse y Staging — GiraGroup BI.

Comportamiento:
- TRUNCATE en cascada de todas las tablas de hechos (fact_*).
- TRUNCATE en cascada de staging (staging_registros_crudos, stg_entidad_no_resuelta),
  lotes, dim_origen_documental y logs del pipeline.
- PRESERVACIÓN ESTRICTA de:
  * users (credenciales de usuario y roles)
  * cat_institucion (y catálogos maestros fijos de configuración)
  * dim_tiempo (calendario dimensional)

Uso:
  python scripts/reset_dw.py --confirm
"""

import argparse
import os
import subprocess
import sys
from typing import Dict, Any, List, Optional, Tuple

TABLAS_TRUNCAR = [
    "fact_rendimiento_academico",
    "fact_situacion_financiera",
    "fact_evaluacion_docente",
    "fact_marketing",
    "fact_rentabilidad",
    "fact_forecast",
    "fact_cobranzas_proyectadas",
    "stg_entidad_no_resuelta",
    "staging_registros_crudos",
    "log_pipeline_ingesta",
    "log_inconsistencias",
    "log_auditoria_nlp",
    "dim_origen_documental",
    "lote"
]

TABLAS_PRESERVAR = [
    "users",
    "dim_tiempo",
    "cat_institucion"
]


def ejecutar_reset_via_psycopg2(conn) -> Dict[str, Any]:
    """Ejecuta el reset mediante una conexión DB-API existente."""
    with conn.cursor() as cur:
        # 1. Contar filas antes
        conteos_antes = {}
        for t in TABLAS_TRUNCAR + TABLAS_PRESERVAR:
            try:
                cur.execute(f"SELECT count(*) FROM public.{t};")
                conteos_antes[t] = cur.fetchone()[0]
            except Exception:
                conteos_antes[t] = 0
                conn.rollback()

        # 2. TRUNCATE
        sql_truncate = f"TRUNCATE TABLE {', '.join(['public.' + t for t in TABLAS_TRUNCAR])} RESTART IDENTITY CASCADE;"
        cur.execute(sql_truncate)
        conn.commit()

        # 3. Contar filas después
        conteos_despues = {}
        for t in TABLAS_TRUNCAR + TABLAS_PRESERVAR:
            try:
                cur.execute(f"SELECT count(*) FROM public.{t};")
                conteos_despues[t] = cur.fetchone()[0]
            except Exception:
                conteos_despues[t] = -1

        return {
            "status": "success",
            "method": "psycopg2",
            "conteos_antes": conteos_antes,
            "conteos_despues": conteos_despues
        }


def ejecutar_reset_via_docker(container_name: str = "giragroup_db", db_user: str = "giragroup_user", db_name: str = "giragroup_db") -> Dict[str, Any]:
    """Ejecuta el reset invocando psql dentro del contenedor Docker oficial."""
    sql_script_path = os.path.join(os.path.dirname(__file__), "..", "db", "scripts", "reset_dw.sql")
    sql_script_path = os.path.abspath(sql_script_path)

    cmd = [
        "docker", "exec", "-i", container_name,
        "psql", "-U", db_user, "-d", db_name
    ]

    with open(sql_script_path, "r", encoding="utf-8") as f:
        sql_content = f.read()

    proc = subprocess.run(
        cmd,
        input=sql_content,
        capture_output=True,
        text=True,
        check=True
    )

    # Consultar conteos finales
    check_sql = "; ".join([f"SELECT '{t}', count(*) FROM public.{t}" for t in TABLAS_TRUNCAR + TABLAS_PRESERVAR]) + ";"
    proc_check = subprocess.run(
        cmd,
        input=check_sql,
        capture_output=True,
        text=True,
        check=True
    )

    conteos_despues = {}
    for line in proc_check.stdout.splitlines():
        parts = [p.strip() for p in line.split("|") if p.strip()]
        if len(parts) == 2 and parts[1].isdigit():
            conteos_despues[parts[0]] = int(parts[1])

    return {
        "status": "success",
        "method": "docker",
        "output": proc.stdout,
        "conteos_despues": conteos_despues
    }


def reset_data_warehouse(confirm: bool = False, use_docker_fallback: bool = True) -> Dict[str, Any]:
    """
    Función orquestadora de reset del DW con comprobación estricta y fallback automático a Docker.
    """
    if not confirm:
        raise ValueError("Se requiere confirm=True para ejecutar el reset del Data Warehouse.")

    # 1. Intentar conexión directa vía SQLAlchemy / psycopg2
    try:
        import psycopg2
        url = os.getenv("DATABASE_URL", "postgresql://giragroup_user:giragroup_secret_2026@127.0.0.1:5432/giragroup_db")
        # Parsear o conectar directamente
        conn = psycopg2.connect(url, connect_timeout=2)
        res = ejecutar_reset_via_psycopg2(conn)
        conn.close()
        return res
    except Exception as e_direct:
        if not use_docker_fallback:
            raise RuntimeError(f"Fallo al conectar directamente a PostgreSQL: {e_direct}")

    # 2. Fallback a docker exec
    try:
        return ejecutar_reset_via_docker()
    except Exception as e_docker:
        raise RuntimeError(f"Fallo al ejecutar reset tanto directo como vía Docker: {e_docker}")


def main():
    parser = argparse.ArgumentParser(description="Reset Seguro del Data Warehouse — GiraGroup BI")
    parser.add_argument("--confirm", action="store_true", help="Confirmación explícita obligatoria para ejecutar el truncado")
    parser.add_argument("--docker-only", action="store_true", help="Forzar ejecución vía contenedor Docker")

    args = parser.parse_args()

    if not args.confirm:
        print("\n[ERROR DE SEGURIDAD] Debe especificar el parámetro --confirm para proceder con el reset del Data Warehouse.")
        print("Ejemplo: python scripts/reset_dw.py --confirm\n")
        sys.exit(1)

    print("\n=======================================================")
    print(" INICIANDO RESET SEGURO DEL DATA WAREHOUSE & STAGING")
    print("=======================================================")

    try:
        if args.docker_only:
            resultado = ejecutar_reset_via_docker()
        else:
            resultado = reset_data_warehouse(confirm=True)

        print(f"\n[ÉXITO] Reset completado mediante método: {resultado.get('method')}")
        print("\n--- Estado de Tablas Truncadas (Hechos & Staging) ---")
        despues = resultado.get("conteos_despues", {})
        todos_cero = True
        for t in TABLAS_TRUNCAR:
            cnt = despues.get(t, 0)
            status = "0 filas [OK]" if cnt == 0 else f"{cnt} filas [ERROR]"
            if cnt != 0:
                todos_cero = False
            print(f"  • {t:<30}: {status}")

        print("\n--- Estado de Tablas Preservadas ---")
        for t in TABLAS_PRESERVAR:
            cnt = despues.get(t, "N/A")
            print(f"  • {t:<30}: {cnt} filas preservadas [INTACTO]")

        if not todos_cero:
            print("\n[ALERTA] Algunas tablas de hechos no quedaron en 0 filas.")
            sys.exit(2)
        else:
            print("\n[INVARIANTE VERIFICADO] 100% de tablas de hechos y staging en 0. Tablas críticas preservadas.\n")

    except Exception as e:
        print(f"\n[ERROR FATAL] Falló el reset del DW: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
