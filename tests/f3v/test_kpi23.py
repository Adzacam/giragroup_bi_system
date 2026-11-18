"""V-4: Pruebas de bi.vw_planificacion_ejecucion_mensual, KPI-23 y /api/v1/cmi/scorecard."""
import os
import sys

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for p in (ROOT, os.path.join(ROOT, "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

from routers.cmi import _scorecard  # noqa: E402


def _pg_url():
    url = os.environ.get("DATABASE_URL", "")
    return url if url.startswith("postgresql") else None


@pytest.mark.skipif(not _pg_url(), reason="Requiere DATABASE_URL PostgreSQL con migraciones 018/019")
def test_scorecard_devuelve_23_kpi_y_kpi23_coincide_con_sql():
    engine = create_engine(_pg_url())
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        ref_count = db.execute(text("SELECT COUNT(*) FROM bi.ref_kpi WHERE activo = TRUE")).scalar()
        assert ref_count == 23

        sc = _scorecard(db, gestion=2026, permitidas=["FINANCIERA", "CLIENTES", "PROCESOS_INTERNOS", "APRENDIZAJE"])
        kpis = [k for p in sc["perspectivas"] for k in p["kpis"]]
        assert len(kpis) == 23
        k23 = next((k for k in kpis if k["codigo"] == "KPI-23"), None)
        assert k23 is not None
        assert k23["perspectiva"] == "PROCESOS_INTERNOS"
        assert k23["meta"] == 85.0
        assert k23["umbral_verde"] == 85.0
        assert k23["umbral_ambar"] == 60.0

        # Verificar la vista mensual y su formula SQL manual en 3 meses con datos
        meses = db.execute(text("""
            SELECT id_tiempo, kpi_23, programas_planificados, programas_iniciados,
                   meta_ingreso_total, ingreso_proyectado_techos, meta_financiera, ejecutado_financiero
            FROM bi.vw_planificacion_ejecucion_mensual
            WHERE programas_planificados > 0
            ORDER BY id_tiempo
            LIMIT 3
        """)).mappings().all()
        for row in meses:
            sql_manual = db.execute(text("""
                WITH por_programa_mes AS (
                    SELECT id_tiempo_plan,
                           COALESCE(NULLIF(upper(btrim(pos_code_fuente)), ''), 'ORIGEN:' || clave_fila_origen) AS programa_mes,
                           bool_or(estado_fuente IN ('Inicio Confirmado', 'En curso', 'Finalizo')) AS iniciado,
                           bool_or(estado_fuente IN ('Por iniciar', 'Inicio Confirmado', 'En curso', 'Finalizo')) AS planificado
                    FROM public.fact_planificacion_programa
                    WHERE id_tiempo_plan = :t
                    GROUP BY id_tiempo_plan, COALESCE(NULLIF(upper(btrim(pos_code_fuente)), ''), 'ORIGEN:' || clave_fila_origen)
                )
                SELECT 100.0 * count(*) FILTER (WHERE iniciado) / NULLIF(count(*) FILTER (WHERE planificado), 0)
                FROM por_programa_mes
            """), {"t": row["id_tiempo"]}).scalar()
            assert abs(float(row["kpi_23"]) - float(sql_manual)) < 1e-6
    finally:
        db.close()
        engine.dispose()
