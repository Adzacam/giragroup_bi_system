"""ADW-L6 (PARTE B): Configuración CMI (migración 027 sobre tmpfs).

Verifica:
1. La migración 027_adw_l6_cmi_config.sql es idempotente y no altera el conteo 51 / 10 / 23.
2. KPI-18 se asigna por gestión del dato (no por stg_entidad_no_resuelta.created_at).
3. bi.vw_cmi_gestiones filtra gestiones residuales (ej. 2023) con < 10 KPI con dato o < 5 con umbral.
"""

import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[2]
MIGRACION_027 = ROOT / "backend" / "scripts" / "migrations" / "027_adw_l6_cmi_config.sql"


def _tmpfs_url() -> str | None:
    url = os.environ.get("ADW_TMPFS_URL") or ""
    if not url:
        # Solo tmpfs (nunca DW_TEST_URL / giragroup_db en 5434)
        candidate = "postgresql://giragroup_user:tmpfs_local@localhost:55441/giragroup_db"
        try:
            with create_engine(candidate, connect_args={"connect_timeout": 2}).connect() as c:
                c.execute(text("SELECT 1"))
            return candidate
        except Exception:
            return None
    return url if url.startswith("postgresql") else None


TMPFS_URL = _tmpfs_url()
requiere_tmpfs = pytest.mark.skipif(not TMPFS_URL, reason="Requiere PostgreSQL tmpfs con migraciones 022..027")


def test_migracion_027_existe_y_no_usa_created_at_para_kpi18():
    assert MIGRACION_027.exists(), "Falta 027_adw_l6_cmi_config.sql"
    sql = MIGRACION_027.read_text(encoding="utf-8")
    assert "CREATE OR REPLACE VIEW bi.vw_cmi_valores" in sql
    assert "CREATE OR REPLACE VIEW bi.vw_cmi_gestiones" in sql
    assert "EXTRACT(YEAR FROM created_at)" not in sql
    assert "EXTRACT(YEAR FROM s.created_at)" not in sql
    assert "027_adw_l6_cmi_config.sql" in sql


@requiere_tmpfs
def test_tmpfs_51_tablas_10_vistas_23_kpi():
    eng = create_engine(TMPFS_URL)
    with eng.connect() as c:
        tablas_pub_bi = c.execute(text(
            "SELECT count(*) FROM information_schema.tables "
            "WHERE table_type = 'BASE TABLE' AND table_schema IN ('public', 'bi')"
        )).scalar()
        vistas_bi = c.execute(text(
            "SELECT count(*) FROM information_schema.views WHERE table_schema = 'bi'"
        )).scalar()
        kpis_ref = c.execute(text("SELECT count(*) FROM bi.ref_kpi")).scalar()
        mig = c.execute(text(
            "SELECT count(*) FROM public.schema_migrations WHERE version = '027_adw_l6_cmi_config.sql'"
        )).scalar()

    assert tablas_pub_bi == 51, f"Esperado 51 tablas (public+bi), obtenido {tablas_pub_bi}"
    assert vistas_bi == 10, f"Esperado 10 vistas bi, obtenido {vistas_bi}"
    assert kpis_ref == 23, f"Esperado 23 KPI en bi.ref_kpi, obtenido {kpis_ref}"
    assert mig == 1


@requiere_tmpfs
def test_tmpfs_kpi18_por_gestion_del_dato_y_sin_gestion_2023():
    eng = create_engine(TMPFS_URL)
    with eng.connect() as c:
        gestiones = [r[0] for r in c.execute(text(
            "SELECT gestion FROM bi.vw_cmi_gestiones ORDER BY gestion"
        )).fetchall()]
        kpi18 = dict(c.execute(text(
            "SELECT gestion, valor::int FROM bi.vw_cmi_valores WHERE codigo = 'KPI-18' ORDER BY gestion"
        )).fetchall())
        pendientes_totales = c.execute(text(
            "SELECT count(*) FROM public.stg_entidad_no_resuelta WHERE resuelto = FALSE"
        )).scalar()

    assert 2023 not in gestiones, f"2023 residual no debe aparecer en bi.vw_cmi_gestiones: {gestiones}"
    assert 2024 in gestiones and 2025 in gestiones and 2026 in gestiones
    assert len(kpi18) > 1, f"KPI-18 debe repartirse en múltiples gestiones, no solo en una: {kpi18}"
    assert sum(kpi18.values()) == pendientes_totales
