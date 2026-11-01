"""
tests/test_esquema_alineado_ddl.py
----------------------------------
La base en ejecución (create_all, migraciones 002/003, respaldos B0/B1) no coincidía con db/schema.sql:
dim_tiempo admitía NULL y no tenía UNIQUE(fecha), faltaban DEFAULT y ON DELETE, y uq_fact_aca_est_mod
repetía la restricción uq_fact_rendimiento_estudiante_modulo. La migración 005 la alinea en el arranque.
"""

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DDL = (RAIZ / "db" / "schema.sql").read_text(encoding="utf-8")
MIG_005 = (RAIZ / "backend" / "scripts" / "migrations" / "005_alinear_esquema_con_ddl.sql").read_text(encoding="utf-8")


def _sin_comentarios(sql: str) -> str:
    return re.sub(r"--[^\n]*", "", sql)


def test_indice_duplicado_uq_fact_aca_est_mod_eliminado():
    ddl = _sin_comentarios(DDL)
    assert "uq_fact_aca_est_mod" not in ddl
    # La unicidad (id_estudiante, id_modulo) sigue garantizada por la restricción
    assert "uq_fact_rendimiento_estudiante_modulo UNIQUE (id_estudiante, id_modulo)" in ddl
    assert "DROP INDEX IF EXISTS public.uq_fact_aca_est_mod;" in MIG_005
