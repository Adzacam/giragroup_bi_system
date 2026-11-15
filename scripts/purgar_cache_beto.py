"""A-7: Purga explícita y verificable de public.cache_beto_entidades.

No modifica entidades de negocio, umbrales, inferencia ni snapshot.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import psycopg2


UNRELATED_TABLES = (
    "public.cache_indice_beto",
    "public.dim_estudiante",
    "public.fact_rendimiento_academico",
    "public.stg_entidad_no_resuelta",
    "public.schema_migrations",
)


def redact_target(database_url: str) -> dict:
    parsed = urlparse(database_url)
    return {
        "scheme": parsed.scheme,
        "host": parsed.hostname,
        "port": parsed.port,
        "database": parsed.path.lstrip("/"),
    }


def validate_target(database_url: str, allow_live: bool = False) -> dict:
    info = redact_target(database_url)
    db_name = (info["database"] or "").lower()
    if not db_name:
        raise ValueError("URL de base de datos sin nombre de base")
    if "snapshot" in db_name:
        raise ValueError(f"Destino prohibido: {db_name} es un snapshot inmutable")
    if not allow_live and info["port"] == 5434 and db_name == "giragroup_db":
        raise ValueError("Destino protegido: puerto 5434 corresponde a la DB viva; use copia aislada")
    return info


def _unrelated_counts(cur) -> dict:
    counts = {}
    for tbl in UNRELATED_TABLES:
        cur.execute("SELECT to_regclass(%s) IS NOT NULL", (tbl,))
        exists = bool(cur.fetchone()[0])
        if not exists:
            counts[tbl] = None
        else:
            cur.execute(f"SELECT COUNT(*) FROM {tbl}")
            counts[tbl] = int(cur.fetchone()[0])
    return counts


def purge_entity_cache(database_url: str, *, allow_live: bool = False) -> dict:
    target = validate_target(database_url, allow_live=allow_live)
    conn = psycopg2.connect(database_url)
    try:
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.cache_beto_entidades') IS NOT NULL")
            exists = bool(cur.fetchone()[0])
            unrelated_before = _unrelated_counts(cur)
            if not exists:
                conn.rollback()
                return {
                    "fecha": datetime.now().astimezone().isoformat(),
                    "destino": target,
                    "tabla": "public.cache_beto_entidades",
                    "tabla_existe": False,
                    "filas_antes": 0,
                    "filas_eliminadas": 0,
                    "filas_despues": 0,
                    "tablas_ajenas_antes": unrelated_before,
                    "tablas_ajenas_despues": unrelated_before,
                    "tablas_ajenas_sin_cambios": True,
                }

            cur.execute("SELECT COUNT(*) FROM public.cache_beto_entidades")
            before = int(cur.fetchone()[0])
            cur.execute("DELETE FROM public.cache_beto_entidades")
            deleted = int(cur.rowcount if cur.rowcount is not None and cur.rowcount >= 0 else before)
            cur.execute("SELECT COUNT(*) FROM public.cache_beto_entidades")
            after = int(cur.fetchone()[0])
            unrelated_after = _unrelated_counts(cur)
            if unrelated_before != unrelated_after:
                conn.rollback()
                raise RuntimeError("Se detectó alteración inesperada fuera de cache_beto_entidades")
            conn.commit()
    finally:
        conn.close()

    return {
        "fecha": datetime.now().astimezone().isoformat(),
        "destino": target,
        "tabla": "public.cache_beto_entidades",
        "tabla_existe": True,
        "filas_antes": before,
        "filas_eliminadas": deleted,
        "filas_despues": after,
        "tablas_ajenas_antes": unrelated_before,
        "tablas_ajenas_despues": unrelated_after,
        "tablas_ajenas_sin_cambios": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="A-7: Purga explícita de public.cache_beto_entidades")
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL", ""), help="URL PostgreSQL destino")
    parser.add_argument("--permitir-viva", action="store_true", help="Permite ejecutar sobre puerto 5434 si fue autorizado")
    parser.add_argument("--salida", type=Path, help="Ruta JSON opcional para guardar evidencia")
    args = parser.parse_args(argv)

    if not args.database_url:
        parser.error("Se requiere --database-url o DATABASE_URL")

    report = purge_entity_cache(args.database_url, allow_live=args.permitir_viva)
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.salida:
        args.salida.parent.mkdir(parents=True, exist_ok=True)
        args.salida.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
