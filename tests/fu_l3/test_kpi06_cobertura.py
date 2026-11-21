"""
FU-L3 (DA6): KPI-06 «sin dato» con motivo y cobertura mensual.

- gestiones sin leads (2023, 2024 y el primer semestre de 2025): «sin dato» y el motivo dice desde qué mes hay datos;
- el drill-down muestra la cobertura mensual: meses con dato / meses de la gestión;
- el SQL de lectura corre contra la PostgreSQL tmpfs aislada (nunca la DW viva): siembra una gestión ficticia (2098)
  dentro de una transacción que SIEMPRE se revierte. Se omite si la copia tmpfs no está disponible.
"""

import os
import re

import pytest

from services import captacion_cobertura as cob

MESES = [
    {"gestion": 2025, "mes": m, "periodo_mes": f"2025-{m:02d}", "leads": 100, "inscritos": 5, "programas": 4, "conversion_pct": 5.0}
    for m in range(7, 13)
] + [
    {"gestion": 2026, "mes": m, "periodo_mes": f"2026-{m:02d}", "leads": 200, "inscritos": 10, "programas": 6, "conversion_pct": 5.0}
    for m in range(1, 6)
]


def test_cobertura_cuenta_meses_con_dato_de_los_doce_de_la_gestion():
    c = cob.cobertura(MESES)
    assert c[2025]["meses_con_dato"] == 6 and c[2025]["meses_gestion"] == 12
    assert c[2025]["desde"] == "julio de 2025" and c[2025]["hasta"] == "diciembre de 2025"
    assert c[2026]["meses_con_dato"] == 5 and c[2026]["desde"] == "enero de 2026" and c[2026]["hasta"] == "mayo de 2026"
    assert 2024 not in c


def test_gestion_sin_leads_dice_desde_que_mes_hay_datos():
    motivo = cob.motivo_sin_dato(MESES, 2024)
    assert "desde julio de 2025" in motivo and "Sin leads" in motivo


def test_motivo_usa_la_plantilla_editable_del_catalogo():
    motivo = cob.motivo_sin_dato(MESES, 2023, {"sin_leads": "Nada hasta {desde}."})
    assert motivo == "Nada hasta julio de 2025."


def test_sin_ninguna_fuente_cargada_el_motivo_lo_dice():
    assert "ninguna fuente" in cob.motivo_sin_dato([], 2025)


def test_gestion_con_meses_pero_sin_valor_explica_la_cobertura():
    motivo = cob.motivo_sin_dato(MESES, 2026)
    assert "5 de 12 meses" in motivo


def test_la_plantilla_del_catalogo_esta_en_el_yaml_y_en_el_espejo():
    from pipeline.lector_hojas import cargar_config
    motivos = cargar_config()["captacion"]["motivos_sin_dato"]
    assert "{desde}" in motivos["sin_leads"] and motivos["sin_ninguna"]


# ── SQL contra la PostgreSQL tmpfs (se revierte siempre) ─────────────────────

URL = os.environ.get("FU_L3_PG_URL", "postgresql://giragroup_user:tmpfs_local@127.0.0.1:55438/giragroup_db")


def _aislada(url: str) -> bool:
    return bool(re.search(r"@(127\.0\.0\.1|localhost):554\d\d/", url))


@pytest.fixture
def sesion_pg():
    if not _aislada(URL):
        pytest.skip("FU_L3_PG_URL no apunta a una copia tmpfs aislada (127.0.0.1:554xx)")
    sqlalchemy = pytest.importorskip("sqlalchemy")
    pytest.importorskip("psycopg2")
    from sqlalchemy.orm import sessionmaker
    engine = sqlalchemy.create_engine(URL, connect_args={"connect_timeout": 3})
    try:
        con = engine.connect()
    except Exception:
        pytest.skip("copia tmpfs de PostgreSQL no disponible")
    trans = con.begin()
    s = sessionmaker(bind=con)()
    try:
        yield s
    finally:
        s.close()
        trans.rollback()   # nada de lo que escribe esta prueba se conserva
        con.close()
        engine.dispose()


def test_por_mes_aplica_la_regla_de_la_migracion_014_sobre_fact_marketing(sesion_pg):
    from sqlalchemy import text
    s = sesion_pg
    for id_t, mes in ((20980101, 1), (20980201, 2), (20980301, 3)):
        s.execute(text("INSERT INTO dim_tiempo (id_tiempo, gestion, semestre, mes, nombre_mes, periodo_mes, fecha, trimestre, "
                       "semana_iso, dia_mes, dia_semana, nombre_dia, es_fin_semana) VALUES "
                       "(:i, 2098, 1, :m, 'X', :p, :f, 1, 1, 1, 4, 'Jueves', FALSE) ON CONFLICT (id_tiempo) DO NOTHING"),
                  {"i": id_t, "m": mes, "p": f"2098-{mes:02d}", "f": f"2098-{mes:02d}-01"})
    ids = []
    for k in range(3):
        ids.append(s.execute(text("INSERT INTO dim_modulo (nombre_modulo, programa) VALUES (:n, 'P') RETURNING id_modulo"),
                             {"n": f"MODULO FICTICIO {k}"}).scalar())
    filas = [  # (modulo, tiempo, leads, inscritos): enero válido; febrero con inscritos > leads y sin leads; marzo válido con 0
        (ids[0], 20980101, 100, 10), (ids[1], 20980101, 50, 5),
        (ids[0], 20980201, 10, 20), (ids[1], 20980201, 0, 0),
        (ids[2], 20980301, 40, 0),
    ]
    for mod, t, leads, ins in filas:
        s.execute(text("INSERT INTO fact_marketing (id_modulo, id_tiempo, leads, reservas, inscritos, leads_captacion, "
                       "inscritos_captacion, costo_programa) VALUES (:m, :t, 0, 0, 0, :l, :i, 0)"),
                  {"m": mod, "t": t, "l": leads, "i": ins})
    meses = [m for m in cob.por_mes(s) if m["gestion"] == 2098]
    assert [(m["periodo_mes"], m["leads"], m["inscritos"], m["programas"]) for m in meses] == [
        ("2098-01", 150, 15, 2), ("2098-03", 40, 0, 1)]
    assert meses[0]["conversion_pct"] == 10.0 and meses[1]["conversion_pct"] == 0.0
    assert cob.cobertura(meses)[2098]["meses_con_dato"] == 2


# ── Scorecard: el motivo y la cobertura del KPI-06 llegan por la API sin cambiar su contrato ───────

def _scorecard_con(monkeypatch, gestion, valor_kpi06, meses):
    from routers import cmi

    def filas(db, sql, params=None):
        if "vw_cmi_gestiones" in sql:
            return [{"gestion": g} for g in (2023, 2024, 2025, 2026)]
        if "vw_cmi_perspectiva" in sql:
            return [{"codigo": "CLIENTES", "nombre": "Clientes", "objetivo": "", "pregunta": "", "peso": 1, "orden": 2,
                     "indicadores": 1, "verdes": 0, "ambar": 0, "rojos": 0, "sin_evaluar": 1, "indice": None}]
        if "vw_cmi_scorecard" in sql:
            return [{"perspectiva": "CLIENTES", "codigo": "KPI-06", "nombre": "Conversión", "descripcion": "", "unidad": "%",
                     "sentido": "MAYOR", "valor": valor_kpi06, "valor_anterior": None, "delta": None, "meta": 30,
                     "umbral_verde": 30, "umbral_ambar": 20, "peso": 1, "semaforo": None, "puntaje": None, "tendencia": None}]
        return []

    monkeypatch.setattr(cmi, "_filas", filas)
    monkeypatch.setattr(cob, "por_mes", lambda db, gestion=None: meses)
    return cmi._scorecard(None, gestion, ["CLIENTES"])["perspectivas"][0]["kpis"][0]


def test_scorecard_gestion_sin_leads_trae_motivo_con_el_mes_de_inicio(monkeypatch):
    k = _scorecard_con(monkeypatch, 2024, None, MESES)
    assert k["motivo_sin_dato"].startswith("Sin leads en esta gestión") and "julio de 2025" in k["motivo_sin_dato"]
    assert k["cobertura"] == {"meses_con_dato": 0, "meses_gestion": 12, "desde": None, "hasta": None}


def test_scorecard_gestion_con_datos_trae_la_cobertura_y_ningun_motivo(monkeypatch):
    k = _scorecard_con(monkeypatch, 2025, 5.0, MESES)
    assert k["motivo_sin_dato"] is None
    assert k["cobertura"] == {"meses_con_dato": 6, "meses_gestion": 12, "desde": "julio de 2025", "hasta": "diciembre de 2025"}


def _detalle_clientes(monkeypatch, gestion):
    from types import SimpleNamespace
    from routers import cmi

    def filas(db, sql, params=None):
        if "vw_cmi_gestiones" in sql:
            return [{"gestion": g} for g in (2024, 2025, 2026)]
        return []

    monkeypatch.setattr(cmi, "_filas", filas)
    monkeypatch.setattr(cob, "por_mes", lambda db, gestion=None: MESES)
    db = SimpleNamespace(rollback=lambda: None, execute=lambda *a, **k: [])
    return cmi._detalle_perspectiva(db, "CLIENTES", gestion)


def test_drilldown_clientes_muestra_la_captacion_mensual_y_la_cobertura(monkeypatch):
    d = _detalle_clientes(monkeypatch, 2025)
    assert [m["periodo_mes"] for m in d["series"]["captacion_mensual"]] == [f"2025-{m:02d}" for m in range(7, 13)]
    assert d["series"]["captacion_cobertura"][0]["meses_con_dato"] == 6
    assert any("6 de 12 meses" in a for a in d["avisos"])


def test_drilldown_de_una_gestion_sin_leads_explica_desde_cuando_hay_datos(monkeypatch):
    d = _detalle_clientes(monkeypatch, 2024)
    assert d["series"]["captacion_mensual"] == [] and d["series"]["captacion_cobertura"] == []
    assert any("desde julio de 2025" in a for a in d["avisos"])
