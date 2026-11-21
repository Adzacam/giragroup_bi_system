"""
FU-L5: migración 025 (bi.vw_cmi_valores: KPI-19 y KPI-20 cuentan solo puntuacion en [1, escala_max]) contra la PostgreSQL tmpfs aislada.

Aplica la migración dentro de una transacción que SIEMPRE se revierte (nunca la DW viva ni el snapshot) y comprueba que:
- se puede aplicar dos veces (idempotente) y no cambia el número de tablas ni de vistas bi (51 + 10: sin esquema nuevo);
- KPI-19 (docente) y KPI-20 (institucional) promedian solo las respuestas con 1 <= puntuacion <= escala_max: un 0, un valor fuera
  de escala, una respuesta sin escala y un comentario sin puntuación no suman al numerador ni al denominador;
- el NPS (0-10) no entra en ninguno de los dos; una gestión sin respuestas válidas queda sin valor (NULL / sin fila), nunca 0.
Se omite si la copia tmpfs no está disponible. URL por defecto: la de `fu_l5_pg_tmpfs` (127.0.0.1:55440), con FU_L5_PG_URL.
La migración parte de la definición de la 024 (que parte de la 022): requiere la 022, la 023 y la 024 aplicadas antes.
"""

import os
import re
from pathlib import Path

import pytest

psycopg2 = pytest.importorskip("psycopg2")

RAIZ = Path(__file__).resolve().parents[2]
URL = os.environ.get("FU_L5_PG_URL", "postgresql://giragroup_user:tmpfs_local@127.0.0.1:55440/giragroup_db")
MIGRACION = RAIZ / "backend" / "scripts" / "migrations" / "025_fu_l5_encuestas_escala_da1.sql"


def _aislada(url: str) -> bool:
    return bool(re.search(r"@(127\.0\.0\.1|localhost):554\d\d/", url))


@pytest.fixture
def cur():
    if not _aislada(URL):
        pytest.skip("FU_L5_PG_URL no apunta a una copia tmpfs aislada (127.0.0.1:554xx)")
    try:
        con = psycopg2.connect(URL, connect_timeout=3)
    except Exception:
        pytest.skip("copia tmpfs de PostgreSQL no disponible")
    con.autocommit = False
    c = con.cursor()
    try:
        c.execute("SELECT to_regclass('bi.vw_cmi_valores') IS NOT NULL AND EXISTS (SELECT 1 FROM information_schema.columns "
                  "WHERE table_name = 'fact_rendimiento_academico' AND column_name = 'resultado')")
        if not c.fetchone()[0]:
            pytest.skip("la copia tmpfs no tiene aplicadas las migraciones 022 a 024")
        yield c
    finally:
        con.rollback()   # nada de lo que escribe esta prueba se conserva
        con.close()


def _aplicar(c):
    sql = MIGRACION.read_text(encoding="utf-8")
    c.execute(sql.replace("\nBEGIN;", "\n").replace("\nCOMMIT;", "\n"))


def _tiempo(c, gestion):
    idt = gestion * 10000 + 101
    c.execute("INSERT INTO dim_tiempo (id_tiempo, gestion, semestre, mes, nombre_mes, periodo_mes, fecha, trimestre, "
              "semana_iso, dia_mes, dia_semana, nombre_dia, es_fin_semana) "
              "VALUES (%s, %s, 1, 1, 'Enero', %s, %s, 1, 1, 1, 4, 'Jueves', FALSE) ON CONFLICT (id_tiempo) DO NOTHING",
              (idt, gestion, f"{gestion}-01", f"{gestion}-01-01"))
    return idt


def _modulo(c):
    c.execute("INSERT INTO dim_modulo (nombre_modulo, programa) VALUES ('MODULO FICTICIO ENCUESTA', 'P') RETURNING id_modulo")
    return c.fetchone()[0]


_n = [0]


def _resp(c, mod, idt, tipo, puntuacion, escala, comentario=None):
    _n[0] += 1
    c.execute("INSERT INTO fact_evaluacion_docente (id_modulo, id_tiempo, pregunta_bloque, puntuacion, comentario, tipo_pregunta, "
              "escala_max, clave_respuesta) VALUES (%s, %s, 'PREGUNTA FICTICIA', %s, %s, %s, %s, %s)",
              (mod, idt, puntuacion, comentario, tipo, escala, f"fu_l5_test_{_n[0]:06d}"))


def _kpi(c, gestion, codigo):
    c.execute("SELECT valor FROM bi.vw_cmi_valores WHERE gestion = %s AND codigo = %s", (gestion, codigo))
    fila = c.fetchone()
    return None if fila is None or fila[0] is None else float(fila[0])


def _conteos(c):
    c.execute("SELECT (SELECT count(*) FROM information_schema.tables WHERE table_schema IN ('public', 'bi') AND table_type = 'BASE TABLE'), "
              "(SELECT count(*) FROM information_schema.views WHERE table_schema = 'bi')")
    return c.fetchone()


def test_la_migracion_es_idempotente_y_no_cambia_el_esquema(cur):
    antes = _conteos(cur)
    _aplicar(cur)
    _aplicar(cur)
    assert _conteos(cur) == antes                                                   # sin tablas ni vistas nuevas


def test_kpi19_y_kpi20_cuentan_solo_puntuacion_entre_1_y_escala_max(cur):
    _aplicar(cur)
    idt, mod = _tiempo(cur, 2095), _modulo(cur)
    # docente (escala 5): 5 y 4 valen; 0, 8 (fuera de escala), sin escala y un comentario sin puntuación no cuentan
    for p, e in ((5, 5), (4, 5), (0, 5), (8, 5), (3, None)):
        _resp(cur, mod, idt, "DOCENTE", p, e)
    _resp(cur, mod, idt, "DOCENTE", None, None, comentario="comentario ficticio")
    # institucional (escala 10): 10 y 8 valen; 0 y 11 no
    for p, e in ((10, 10), (8, 10), (0, 10), (11, 10)):
        _resp(cur, mod, idt, "INSTITUCIONAL", p, e)
    # NPS: ni siquiera su 0 válido entra en KPI-19 ni en KPI-20
    for p in (0, 9, 10):
        _resp(cur, mod, idt, "NPS", p, 10)
    assert _kpi(cur, 2095, "KPI-19") == pytest.approx(90.0)                          # (100 + 80) / 2
    assert _kpi(cur, 2095, "KPI-20") == pytest.approx(90.0)                          # (100 + 80) / 2


def test_una_gestion_sin_respuestas_validas_no_tiene_valor_no_cero(cur):
    _aplicar(cur)
    idt, mod = _tiempo(cur, 2096), _modulo(cur)
    for p, e in ((0, 5), (9, 5), (0, 10)):
        _resp(cur, mod, idt, "DOCENTE", p, e)
        _resp(cur, mod, idt, "INSTITUCIONAL", p, e)
    assert _kpi(cur, 2096, "KPI-19") is None
    assert _kpi(cur, 2096, "KPI-20") is None


def test_el_denominador_no_incluye_los_valores_descartados(cur):
    """Antes de la 025 un 0 con escala 5 promediaba como 0 %: 5, 4 y 0 daban 60 %; ahora 5 y 4 dan 90 %."""
    _aplicar(cur)
    idt, mod = _tiempo(cur, 2097), _modulo(cur)
    for p in (5, 4, 0):
        _resp(cur, mod, idt, "DOCENTE", p, 5)
    assert _kpi(cur, 2097, "KPI-19") == pytest.approx(90.0)
