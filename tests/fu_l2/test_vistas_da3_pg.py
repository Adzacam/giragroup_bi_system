"""
FU-L2: las tres vistas bi aplican la misma regla DA3 (mora = cuotas_impagas >= 2). Prueba contra la PostgreSQL
tmpfs aislada (nunca la DW viva): aplica la migración 022 dentro de una transacción que SIEMPRE se revierte y
escribe filas ficticias de una gestión que no existe (2099).

Se omite si la copia tmpfs no está disponible. URL por defecto: la de `fu_l2_pg_tmpfs` (127.0.0.1:55437);
se cambia con FU_L2_PG_URL. Se niega a correr contra un host que no sea 127.0.0.1/localhost con puerto 554xx.
"""

import os
import re
from pathlib import Path

import pytest

psycopg2 = pytest.importorskip("psycopg2")

RAIZ = Path(__file__).resolve().parents[2]
URL = os.environ.get("FU_L2_PG_URL", "postgresql://giragroup_user:tmpfs_local@127.0.0.1:55437/giragroup_db")
MIGRACION = RAIZ / "backend" / "scripts" / "migrations" / "022_fu_l2_cobranza_mora_da3.sql"


def _aislada(url: str) -> bool:
    return bool(re.search(r"@(127\.0\.0\.1|localhost):554\d\d/", url))


@pytest.fixture
def cur():
    if not _aislada(URL):
        pytest.skip("FU_L2_PG_URL no apunta a una copia tmpfs aislada (127.0.0.1:554xx)")
    try:
        con = psycopg2.connect(URL, connect_timeout=3)
    except Exception:
        pytest.skip("copia tmpfs de PostgreSQL no disponible")
    con.autocommit = False
    c = con.cursor()
    try:
        yield c
    finally:
        con.rollback()   # nada de lo que escribe esta prueba se conserva
        con.close()


def _sembrar(c):
    sql = MIGRACION.read_text(encoding="utf-8")
    c.execute(sql.replace("\nBEGIN;", "\n").replace("\nCOMMIT;", "\n"))
    c.execute("INSERT INTO dim_tiempo (id_tiempo, gestion, semestre, mes, nombre_mes, periodo_mes, fecha, trimestre, "
              "semana_iso, dia_mes, dia_semana, nombre_dia, es_fin_semana) "
              "VALUES (20990101, 2099, 1, 1, 'Enero', '2099-01', '2099-01-01', 1, 1, 1, 4, 'Jueves', FALSE) "
              "ON CONFLICT (id_tiempo) DO NOTHING")
    ids = []
    for n in ("A", "B", "C", "D"):
        c.execute("INSERT INTO dim_estudiante (nombre_completo, ci, deprecado) VALUES (%s, %s, FALSE) RETURNING id_estudiante",
                  (f"ESTUDIANTE FICTICIO {n}", f"99990{n}"))
        ids.append(c.fetchone()[0])
    a, b, c_, d = ids
    # A: 2 cuotas (mora), deuda 100 · B: 1 cuota (no es mora aunque la fuente diga PREVISIONABLE), deuda 50
    # C: solo pagos del mes (cuotas NULL) · D: dos hechos de 1 cuota cada uno (no es mora: se mira cada hecho)
    filas = [(a, 2, 100, 0, "Mora", "CERRADA"), (b, 1, 50, 0, "Vigente", "PREVISIONABLE"),
             (c_, None, None, 30, None, None), (d, 1, 20, 0, "Vigente", "VIGENTE"), (d, 1, 20, 0, "Vigente", "VIGENTE")]
    for k, (est, cuotas, deuda, pagado, estado, fuente) in enumerate(filas):
        c.execute("INSERT INTO dim_modulo (nombre_modulo, programa) VALUES (%s, %s) RETURNING id_modulo",
                  (f"MODULO FICTICIO {k}", "PROGRAMA FICTICIO"))
        mod = c.fetchone()[0]
        c.execute("INSERT INTO fact_situacion_financiera (id_estudiante, id_modulo, id_tiempo, monto_deuda, monto_pagado, "
                  "cuotas_impagas, estado_cartera, estado_cartera_fuente) VALUES (%s,%s,20990101,%s,%s,%s,%s,%s)",
                  (est, mod, deuda, pagado, cuotas, estado, fuente))
    # nota baja para A y B: la regla F del riesgo cruzado solo se enciende para A
    for est in (a, b):
        c.execute("INSERT INTO fact_rendimiento_academico (id_estudiante, id_tiempo, nota_final) VALUES (%s, 20990101, 50)", (est,))
    return ids


def _kpis(c):
    c.execute("SELECT codigo, valor FROM bi.vw_cmi_valores WHERE gestion = 2099")
    return {k: float(v) for k, v in c.fetchall() if v is not None}


def test_kpi_04_05_15_usan_cuotas_ge_2_sobre_estudiantes_con_cartera(cur):
    _sembrar(cur)
    k = _kpis(cur)
    assert k["KPI-04"] == 1                      # solo A
    assert k["KPI-05"] == pytest.approx(100.0 / 3)   # 1 de 3 estudiantes con cartera (A, B, D); C solo paga
    assert k["KPI-15"] == pytest.approx(100.0 * 100 / 190)   # deuda de A sobre la deuda de A + B + D
    assert k["KPI-01"] == pytest.approx(30.0 / 2)  # recaudación 30 entre la matrícula 2099 (A y B tienen hecho académico)


def test_cartera_estado_separa_mora_vigente_y_pagos_del_mes(cur):
    _sembrar(cur)
    cur.execute("SELECT estado_cartera, n_estudiantes, deuda_bs FROM bi.vw_cartera_estado WHERE gestion = 2099")
    por_estado = {e: (int(n), None if d is None else float(d)) for e, n, d in cur.fetchall()}
    assert por_estado["Mora"] == (1, 100.0)
    assert por_estado["Vigente"] == (2, 90.0)      # B y D
    assert por_estado["Pagos del mes"][0] == 1 and por_estado["Pagos del mes"][1] is None


def test_riesgo_estudiante_regla_f_es_la_misma_regla(cur):
    _sembrar(cur)
    cur.execute("SELECT e.ci, r.regla_f_financiero FROM bi.vw_riesgo_estudiante r "
                "JOIN dim_estudiante e ON e.id_estudiante = r.id_estudiante WHERE r.gestion = 2099")
    regla = dict(cur.fetchall())
    assert regla["99990A"] == 1 and regla["99990B"] == 0


def test_migracion_se_puede_aplicar_dos_veces(cur):
    sql = MIGRACION.read_text(encoding="utf-8").replace("\nBEGIN;", "\n").replace("\nCOMMIT;", "\n")
    cur.execute(sql)
    cur.execute(sql)
    cur.execute("SELECT count(*) FROM information_schema.columns WHERE table_name = 'fact_situacion_financiera' "
                "AND column_name IN ('estado_cartera_fuente', 'dias_mora')")
    assert cur.fetchone()[0] == 2
    cur.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE'")
    # el esquema no gana tablas: 49 en public (+2 en bi = 51); el conteo exacto lo fija FU-L9
    assert cur.fetchone()[0] == 49
