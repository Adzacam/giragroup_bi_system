"""Pruebas A-7 para scripts/purgar_cache_beto.py."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from scripts.purgar_cache_beto import purge_entity_cache, validate_target


def test_validate_target_blocks_snapshot_and_live_by_default():
    with pytest.raises(ValueError, match="snapshot"):
        validate_target("postgresql://u:p@127.0.0.1:55632/snapshot_dw_20261110_1201")
    with pytest.raises(ValueError, match="protegido"):
        validate_target("postgresql://u:p@127.0.0.1:5434/giragroup_db")
    info = validate_target("postgresql://usuario_demo:secreto_ficticio_123@127.0.0.1:55632/giragroup_db")
    assert info["database"] == "giragroup_db"
    assert "secreto_ficticio_123" not in json.dumps(info)
    assert "usuario_demo" not in json.dumps(info)


def test_purge_isolated_table_present_empty_and_absent(tmp_path):
    base_url = os.environ.get("F1_TEST_TMPFS_URL", "postgresql://giragroup_user:tmpfs_local@127.0.0.1:55632")
    import psycopg2

    # Verificar que beto_pg_tmpfs esté accesible; si no, omitir prueba de integración
    try:
        conn = psycopg2.connect(f"{base_url}/postgres")
        conn.close()
    except Exception:
        pytest.skip("beto_pg_tmpfs no disponible en 127.0.0.1:55632")

    test_db = "test_f1_a7_purga"
    subprocess.run(
        ["docker", "exec", "beto_pg_tmpfs", "psql", "-U", "giragroup_user", "-d", "postgres",
         "-c", f"DROP DATABASE IF EXISTS {test_db}", "-c", f"CREATE DATABASE {test_db} TEMPLATE dw_vacio"],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        target_url = f"{base_url}/{test_db}"
        with psycopg2.connect(target_url) as c:
            with c.cursor() as cur:
                cur.execute(
                    "CREATE TABLE IF NOT EXISTS public.cache_beto_entidades ("
                    "hash_texto CHAR(64) NOT NULL, configuracion VARCHAR(80) NOT NULL, "
                    "entidades TEXT NOT NULL, creado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP, "
                    "PRIMARY KEY (hash_texto, configuracion))"
                )
                cur.execute(
                    "INSERT INTO public.cache_beto_entidades (hash_texto, configuracion, entidades) "
                    "VALUES (%s, %s, %s), (%s, %s, %s)",
                    ("a" * 64, "cfg1", "[]", "b" * 64, "cfg1", "[]"),
                )
            c.commit()

        r1 = purge_entity_cache(target_url)
        assert r1["tabla_existe"] is True
        assert r1["filas_antes"] == 2
        assert r1["filas_eliminadas"] == 2
        assert r1["filas_despues"] == 0
        assert r1["tablas_ajenas_sin_cambios"] is True

        # Segunda ejecución idempotente sobre tabla vacía
        r2 = purge_entity_cache(target_url)
        assert r2["tabla_existe"] is True
        assert r2["filas_antes"] == 0
        assert r2["filas_eliminadas"] == 0
        assert r2["filas_despues"] == 0
        assert r2["tablas_ajenas_sin_cambios"] is True

        # Tabla ausente
        with psycopg2.connect(target_url) as c:
            with c.cursor() as cur:
                cur.execute("DROP TABLE public.cache_beto_entidades")
            c.commit()
        r3 = purge_entity_cache(target_url)
        assert r3["tabla_existe"] is False
        assert r3["filas_antes"] == 0
        assert r3["filas_despues"] == 0
        assert r3["tablas_ajenas_sin_cambios"] is True
    finally:
        subprocess.run(
            ["docker", "exec", "beto_pg_tmpfs", "psql", "-U", "giragroup_user", "-d", "postgres",
             "-c", f"DROP DATABASE IF EXISTS {test_db}"],
            check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
