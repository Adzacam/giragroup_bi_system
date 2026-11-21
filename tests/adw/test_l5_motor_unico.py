"""ADW L5: un solo motor de KPI. Lo que una pantalla de módulo muestra de un KPI es lo que publica el CMI en la misma gestión.

Con PostgreSQL (solo SELECT): contrato por gestión entre `KPIService` y `bi.vw_cmi_valores`.
Sin PostgreSQL: el servicio conserva su cálculo local y lo declara en `fuente`.
"""
import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[2]
for p in (str(ROOT), str(ROOT / "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

from services.kpi_service import KPIService  # noqa: E402


def _pg_url():
    url = os.environ.get("ADW_DB_URL") or os.environ.get("DW_TEST_URL") or os.environ.get("DATABASE_URL", "")
    if "@giragroup_db:" in url:
        url = url.replace("@giragroup_db:5432", "@localhost:5434").replace("@giragroup_db:", "@localhost:5434:")
    return url if url.startswith("postgresql") else None


def _pg_disponible() -> bool:
    url = _pg_url()
    if not url:
        return False
    try:
        with create_engine(url).connect() as c:
            c.execute(text("SELECT 1 FROM bi.vw_cmi_valores LIMIT 1"))
        return True
    except Exception:
        return False


requiere_pg = pytest.mark.skipif(not _pg_disponible(), reason="Requiere PostgreSQL con las vistas bi del CMI")


@pytest.fixture
def db():
    s = sessionmaker(bind=create_engine(_pg_url()))()
    yield s
    s.close()


def _cmi(db, g):
    return {c: (None if v is None else float(v)) for c, v in db.execute(text("SELECT codigo, valor FROM bi.vw_cmi_valores WHERE gestion=:g"), {"g": g})}


def _gestiones(db):
    return [r[0] for r in db.execute(text("SELECT gestion FROM bi.vw_cmi_gestiones ORDER BY gestion"))]


def _igual(a, b):
    return a == b if a is None or b is None else a == pytest.approx(b, abs=0.011)


@requiere_pg
def test_cmi_completo_coincide_con_el_cmi_en_todas_las_gestiones(db):
    for g in _gestiones(db):
        v = _cmi(db, g)
        res = KPIService(db).obtener_perspectivas_cmi_completo(gestion=g)
        f, c, p, a = (res["perspectivas"][k] for k in ("financiera", "cliente_mercado", "procesos_internos", "aprendizaje_crecimiento"))
        assert res["fuente"] == "bi.vw_cmi_valores" and res["filtros"]["gestion"] == g
        esperados = [
            (f["ticket_promedio_bs"], v.get("KPI-01"), "KPI-01"), (f["cumplimiento_metas_mensual_pct"], v.get("KPI-02"), "KPI-02"),
            (f["cumplimiento_metas_anual_pct"], v.get("KPI-13"), "KPI-13"), (f["estudiantes_riesgo_financiero"], v.get("KPI-04"), "KPI-04"),
            (f["mora_total_pct"], v.get("KPI-05"), "KPI-05"), (c["tasa_conversion_admisiones_pct"], v.get("KPI-06"), "KPI-06"),
            (c["total_matricula_acumulada"], v.get("KPI-21"), "KPI-21"), (a["promedio_general_notas"], v.get("KPI-07"), "KPI-07"),
            (a["tasa_aprobacion_pct"], v.get("KPI-08"), "KPI-08"), (a["estudiantes_riesgo_academico"], v.get("KPI-09"), "KPI-09"),
            (p["confianza_media_beto_pct"], v.get("KPI-10"), "KPI-10"), (p["tasa_automatizacion_pct"], v.get("KPI-11"), "KPI-11"),
        ]
        malos = [(cod, pantalla, cmi) for pantalla, cmi, cod in esperados if not _igual(pantalla, cmi)]
        assert not malos, f"gestión {g}: la pantalla difiere del CMI en {malos}"


@requiere_pg
def test_sin_gestion_se_usa_la_ultima_del_cmi_y_no_todas(db):
    ultima = _gestiones(db)[-1]
    sin = KPIService(db).obtener_perspectivas_cmi_completo()
    con = KPIService(db).obtener_perspectivas_cmi_completo(gestion=ultima)
    assert sin["filtros"]["gestion"] == ultima
    assert sin["perspectivas"]["financiera"]["mora_total_pct"] == con["perspectivas"]["financiera"]["mora_total_pct"]


@requiere_pg
def test_kpis_de_modulo_academico_y_financiero_coinciden_con_el_cmi(db):
    for g in _gestiones(db):
        v = _cmi(db, g)
        a = KPIService(db).obtener_kpis_academicos(gestion_filtro=g)
        f = KPIService(db).obtener_kpis_financieros(gestion_filtro=g)
        assert a["gestion"] == f["gestion"] == g
        assert _igual(a["promedio_general_notas"], v.get("KPI-07")) and _igual(a["tasa_aprobacion_pct"], v.get("KPI-08"))
        assert a["estudiantes_en_riesgo_academico"] == (int(v["KPI-09"]) if v.get("KPI-09") is not None else 0)
        assert _igual(f["mora_estudiantes_pct"], v.get("KPI-05")) and _igual(f["cartera_vencida_pct"], v.get("KPI-15"))


@requiere_pg
def test_con_filtro_de_programa_se_declara_que_no_es_el_cmi(db):
    res = KPIService(db).obtener_perspectivas_cmi_completo(programa="DIPLOMADO")
    assert res["fuente"] == "calculo_local (filtro de programa)"


@requiere_pg
def test_calidad_nlp_cuenta_las_entidades_pendientes(db):
    k = KPIService(db).obtener_kpis_pipeline()
    hechos = db.execute(text("SELECT count(*), count(*) FILTER (WHERE requiere_revision) FROM fact_rendimiento_academico")).one()
    pend = db.execute(text("SELECT count(*) FROM stg_entidad_no_resuelta WHERE NOT resuelto")).scalar()
    esperado = round(100.0 - 100.0 * (hechos[1] + pend) / (hechos[0] + pend), 2)
    assert k["tasa_calidad_nlp_pct"] == pytest.approx(esperado, abs=0.01)
    assert k["tasa_calidad_nlp_pct"] < round(100.0 - 100.0 * hechos[1] / hechos[0], 2), "los pendientes deben bajar la tasa"


def test_sin_vistas_bi_el_servicio_conserva_su_calculo_y_lo_declara(dw_sqlite):
    res = KPIService(dw_sqlite).obtener_kpis_financieros()
    assert res["fuente"] == "calculo_local (sin vistas bi)"
    assert "total_recaudado_bs" in res


@requiere_pg
def test_pronostico_financiero_cuenta_todas_las_categorias_igual_que_el_cmi(db):
    """DA8 (Lean): meta y recaudación = PROGRAMAS + TECHOS_CERRADOS, igual que bi.vw_metas_mensual y el KPI-13."""
    from services.forecast_service import obtener_analitica_macro_completa

    c4 = obtener_analitica_macro_completa(db)["caso4_metas_anuales"]
    g = c4["gestion_actual"]
    total = db.execute(text(
        "SELECT SUM(fr.monto_ejecutado), SUM(fr.monto_meta) FROM fact_rentabilidad fr JOIN dim_tiempo t USING(id_tiempo) WHERE t.gestion=:g"),
        {"g": g}).one()
    assert c4["recaudado_acumulado_bs"] == pytest.approx(float(total[0]), abs=0.01)
    assert c4["meta_anual_institucional_bs"] == pytest.approx(float(total[1]), abs=0.01)
    kpi13 = _cmi(db, g).get("KPI-13")
    assert kpi13 is not None and c4["porcentaje_avance_meta"] == pytest.approx(kpi13, abs=0.06)


def test_las_consultas_del_pronostico_ya_no_filtran_por_categoria():
    fuentes = [(ROOT / "backend" / "services" / "forecast_service.py").read_text(encoding="utf-8"),
               (ROOT / "pipeline" / "analytics" / "time_series_extractor.py").read_text(encoding="utf-8")]
    for src in fuentes:
        assert "nombre_categoria = 'PROGRAMAS'" not in src, "una consulta de metas vuelve a filtrar solo PROGRAMAS (DA8)"
