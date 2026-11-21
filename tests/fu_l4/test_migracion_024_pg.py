"""
FU-L4: migración 024 (resultado, estado_de_fuente, bi.vw_cmi_valores con KPI-07, 08 y 16) contra la PostgreSQL tmpfs aislada.

Aplica la migración dentro de una transacción que SIEMPRE se revierte (nunca la DW viva ni el snapshot) y comprueba que:
- se puede aplicar dos veces (idempotente) y solo acepta los cinco resultados canónicos;
- KPI-07: promedio de notas numéricas sin INASISTENCIA, EXIMIDO ni SIN_NOTA; un 0 real entra;
- KPI-08: APROBADO / (APROBADO + REPROBADO + INASISTENCIA); EXIMIDO y SIN_NOTA fuera del denominador; «Aprobó» (texto) cuenta;
- KPI-16: Deserción o Abandono (estado académico o de tutoría, con cualquier mayúscula) sobre la matrícula de la gestión;
  «sin dato» (NULL, nunca 0) si ninguna fuente de la gestión trae el estado; 0 % real si la fuente lo trae y nadie desertó.
Se omite si la copia tmpfs no está disponible. URL por defecto: la de `fu_l4_pg_tmpfs` (127.0.0.1:55439), con FU_L4_PG_URL.
"""

import os
import re
from pathlib import Path

import pytest

psycopg2 = pytest.importorskip("psycopg2")

RAIZ = Path(__file__).resolve().parents[2]
URL = os.environ.get("FU_L4_PG_URL", "postgresql://giragroup_user:tmpfs_local@127.0.0.1:55439/giragroup_db")
MIGRACION = RAIZ / "backend" / "scripts" / "migrations" / "024_fu_l4_actas_resultado_desercion.sql"


def _aislada(url: str) -> bool:
    return bool(re.search(r"@(127\.0\.0\.1|localhost):554\d\d/", url))


@pytest.fixture
def cur():
    if not _aislada(URL):
        pytest.skip("FU_L4_PG_URL no apunta a una copia tmpfs aislada (127.0.0.1:554xx)")
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


def _estudiante(c, n):
    c.execute("INSERT INTO dim_estudiante (nombre_completo, ci_numero) VALUES (%s, %s) RETURNING id_estudiante",
              (f"ESTUDIANTE FICTICIO {n}", f"98{n:05d}"))
    return c.fetchone()[0]


def _modulo(c, n):
    c.execute("INSERT INTO dim_modulo (nombre_modulo, programa) VALUES (%s, 'P') RETURNING id_modulo", (f"MODULO FICTICIO {n}",))
    return c.fetchone()[0]


def _hecho(c, est, mod, idt, nota, resultado, aca=None, tut=None, de_fuente=True):
    c.execute("INSERT INTO fact_rendimiento_academico (id_estudiante, id_modulo, id_tiempo, nota_final, resultado, "
              "estado_academico, estado_tutoria, estado_de_fuente) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
              (est, mod, idt, nota, resultado, aca, tut, de_fuente))


def _kpi(c, gestion, codigo):
    c.execute("SELECT valor FROM bi.vw_cmi_valores WHERE gestion = %s AND codigo = %s", (gestion, codigo))
    fila = c.fetchone()
    return None if fila is None or fila[0] is None else float(fila[0])


def test_la_migracion_es_idempotente_y_solo_acepta_los_cinco_resultados(cur):
    _aplicar(cur)
    _aplicar(cur)
    cur.execute("SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'fact_rendimiento_academico' "
                "AND column_name IN ('resultado', 'estado_de_fuente')")
    assert cur.fetchone()[0] == 2
    idt, est, mod = _tiempo(cur, 2090), _estudiante(cur, 1), _modulo(cur, 1)
    for valido in ("APROBADO", "REPROBADO", "INASISTENCIA", "EXIMIDO", "SIN_NOTA", None):
        _hecho(cur, est, mod, idt, None, valido)
        cur.execute("DELETE FROM fact_rendimiento_academico WHERE id_estudiante = %s", (est,))
    cur.execute("SAVEPOINT s")
    with pytest.raises(psycopg2.errors.CheckViolation):
        _hecho(cur, est, mod, idt, None, "OTRO")
    cur.execute("ROLLBACK TO SAVEPOINT s")


def test_kpi07_y_kpi08_siguen_da_fu2(cur):
    _aplicar(cur)
    idt = _tiempo(cur, 2091)
    est = [_estudiante(cur, 10 + i) for i in range(8)]
    # (nota, resultado): aprobados 85 y 70, texto «Aprobó», reprobado 55, 0 real, inasistencia, eximido, sin nota
    casos = [(85, "APROBADO"), (70, "APROBADO"), (None, "APROBADO"), (55, "REPROBADO"), (0, "REPROBADO"),
             (None, "INASISTENCIA"), (None, "EXIMIDO"), (None, "SIN_NOTA")]
    for e, (nota, res) in zip(est, casos):
        _hecho(cur, e, _modulo(cur, e), idt, nota, res, aca="Aprobado")
    assert _kpi(cur, 2091, "KPI-07") == pytest.approx((85 + 70 + 55 + 0) / 4)               # el 0 real entra; inasistencia, eximido y sin nota no
    assert _kpi(cur, 2091, "KPI-08") == pytest.approx(100.0 * 3 / (3 + 2 + 1))             # 3 aprobados / (3 + 2 reprobados + 1 inasistencia)


def test_una_fila_anterior_a_la_024_sin_resultado_se_deduce_de_la_nota(cur):
    _aplicar(cur)
    idt = _tiempo(cur, 2092)
    for i, nota in enumerate((90, 60)):
        _hecho(cur, _estudiante(cur, 30 + i), _modulo(cur, 30 + i), idt, nota, None, de_fuente=None)
    assert _kpi(cur, 2092, "KPI-08") == pytest.approx(50.0)
    assert _kpi(cur, 2092, "KPI-07") == pytest.approx(75.0)


def test_kpi16_desercion_y_abandono_sobre_la_matricula(cur):
    _aplicar(cur)
    idt = _tiempo(cur, 2093)
    e = [_estudiante(cur, 40 + i) for i in range(5)]
    _hecho(cur, e[0], _modulo(cur, 40), idt, None, "INASISTENCIA", aca="Deserción", tut="Deserción")
    _hecho(cur, e[1], _modulo(cur, 41), idt, 80, "APROBADO", aca="Aprobado", tut="abandono")           # abandono en tutoría, otras mayúsculas
    _hecho(cur, e[2], _modulo(cur, 42), idt, 80, "APROBADO", aca="DESERCION", tut=None)                # sin acento
    _hecho(cur, e[3], _modulo(cur, 43), idt, 80, "APROBADO", aca="Aprobado", tut="Aprobado")
    _hecho(cur, e[4], _modulo(cur, 44), idt, 40, "REPROBADO", aca="Reprobado", tut="Insuficiencia académica")
    _hecho(cur, e[0], _modulo(cur, 45), idt, None, "INASISTENCIA", aca="Deserción", tut="Deserción")    # segundo módulo: el estudiante cuenta una vez
    assert _kpi(cur, 2093, "KPI-16") == pytest.approx(100.0 * 3 / 5)


def test_kpi16_sin_dato_si_ninguna_fuente_trae_el_estado_y_cero_real_si_la_fuente_lo_trae(cur):
    _aplicar(cur)
    sin = _tiempo(cur, 2094)
    for i in range(3):   # estado deducido de la nota por el cargador: no es de la fuente
        _hecho(cur, _estudiante(cur, 50 + i), _modulo(cur, 50 + i), sin, 80, "APROBADO", aca="Aprobado", de_fuente=False)
    assert _kpi(cur, 2094, "KPI-16") is None                      # sin dato, nunca 0
    con = _tiempo(cur, 2095)
    for i in range(3):   # la fuente trae el estado y nadie desertó
        _hecho(cur, _estudiante(cur, 60 + i), _modulo(cur, 60 + i), con, 80, "APROBADO", aca="Aprobado", de_fuente=True)
    assert _kpi(cur, 2095, "KPI-16") == 0.0
