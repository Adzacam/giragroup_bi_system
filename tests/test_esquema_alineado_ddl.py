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


def test_ddl_no_repite_indices_de_claves_primarias_ni_unicas():
    ddl = _sin_comentarios(DDL)
    for repetido in ("idx_dim_tiempo_fecha", "idx_dim_est_id", "idx_log_auditoria_nlp_id",
                     "idx_fact_rendimiento_aca_id", "idx_fact_cobro_id"):
        assert repetido not in ddl


def test_005_deja_dim_tiempo_como_el_ddl():
    mig = _sin_comentarios(MIG_005)
    for col in ("fecha", "gestion", "semestre", "trimestre", "mes", "nombre_mes", "semana_iso", "dia_mes",
                "dia_semana", "nombre_dia", "es_fin_semana", "periodo_mes"):
        assert f"ALTER COLUMN {col} SET NOT NULL" in mig
    assert "UNIQUE (fecha)" in mig
    assert "ALTER COLUMN id_tiempo DROP DEFAULT" in mig      # clave YYYYMMDD, sin secuencia
    assert "ALTER COLUMN gestion DROP DEFAULT" in mig        # sin relleno 2026 / mayo
    assert "ALTER COLUMN mes DROP DEFAULT" in mig


def test_005_fk_con_on_delete_del_ddl():
    mig = _sin_comentarios(MIG_005)
    for tabla, columna, accion in (("dim_estudiante", "fusionado_en", "SET NULL"),
                                   ("dim_estudiante", "id_institucion", "SET NULL"),
                                   ("fact_situacion_financiera", "id_modulo", "SET NULL"),
                                   ("dim_categoria_financiera", "id_cat_categoria_fin", "SET NULL"),
                                   ("stg_entidad_no_resuelta", "registro_origen_id", "CASCADE")):
        assert re.search(rf"\('{tabla}',\s*'{columna}',.*'{accion}'\)", mig), (tabla, columna)
        assert re.search(rf"{columna}[^\n]*ON DELETE {accion}", _sin_comentarios(DDL)), (tabla, columna)


def test_005_es_idempotente_y_queda_registrada():
    mig = _sin_comentarios(MIG_005)
    assert "CREATE INDEX IF NOT EXISTS" in mig and "CREATE INDEX idx" not in mig
    assert "IF NOT EXISTS (SELECT 1 FROM pg_constraint" in mig
    assert "'005_alinear_esquema_con_ddl.sql'" in mig and "ON CONFLICT (version)" in mig


def test_indices_declarados_en_ddl_y_en_005_coinciden():
    patron = r"CREATE INDEX (?:IF NOT EXISTS )?(\w+) ON public\.(\w+) ?\(([^)]*)\)"
    en_ddl = {(n, t, c.replace(" ", "")) for n, t, c in re.findall(patron, DDL)}
    en_005 = {(n, t, c.replace(" ", "")) for n, t, c in re.findall(patron, MIG_005)}
    assert en_005 <= en_ddl, en_005 - en_ddl


def test_ddl_declara_catalogos_de_docente_y_modulo_con_sus_fk():
    """Sin cat_docente/cat_modulo en el DDL, las FK de dim_docente y dim_modulo no podían declararse."""
    ddl = _sin_comentarios(DDL)
    assert ddl.index("CREATE TABLE public.cat_docente") < ddl.index("CREATE TABLE public.dim_docente")
    assert ddl.index("CREATE TABLE public.cat_modulo") < ddl.index("CREATE TABLE public.dim_modulo")
    assert "id_cat_docente INT REFERENCES public.cat_docente(id_docente) ON DELETE SET NULL" in ddl
    assert "id_cat_modulo INT REFERENCES public.cat_modulo(id_modulo) ON DELETE SET NULL" in ddl
    assert "'cat_docente', 'cat_modulo'" in _sin_comentarios(MIG_005)  # RLS y políticas también en esas tablas
