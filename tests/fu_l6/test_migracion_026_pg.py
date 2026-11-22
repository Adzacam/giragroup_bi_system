"""
FU-L6: migración 026 (granularidad de la meta, KPI-02/03/12/13/14 y mes parcial) contra la PostgreSQL tmpfs aislada.

Aplica la migración dentro de una transacción que SIEMPRE se revierte (nunca la DW viva ni el snapshot) y comprueba que:
- se puede aplicar dos veces (idempotente) y no cambia el número de tablas ni de vistas bi (51 + 10);
- DA4: KPI-02 solo se calcula con meta MENSUAL: una gestión con una sola celda de meta anual o sin ninguna meta queda sin valor (NULL),
  nunca 6,25 % por poner la meta anual en diciembre; KPI-03, KPI-13 y KPI-14 usan la meta anual;
- mes parcial: el mes de corte de la fuente (el último con ejecutado de toda la tabla) no cuenta en KPI-02, KPI-03 ni KPI-12, salvo diciembre;
- una fila sin bandera (anterior a la 026) se lee como MENSUAL;
- bi.vw_metas_mensual conserva sus columnas, la meta mensual no suma la anual y la anual va en `meta_anual` al final;
- el CHECK de la columna rechaza una granularidad desconocida.
Se omite si la copia tmpfs no está disponible. URL por defecto: la de `fu_l6_pg_tmpfs` (127.0.0.1:55441), con FU_L6_PG_URL.
La migración parte de la definición de la 025 (que parte de la 024 y la 022): requiere la 022 a la 025 aplicadas antes.
"""

import os
import re
from pathlib import Path

import pytest

psycopg2 = pytest.importorskip("psycopg2")

RAIZ = Path(__file__).resolve().parents[2]
URL = os.environ.get("FU_L6_PG_URL", "postgresql://giragroup_user:tmpfs_local@127.0.0.1:55441/giragroup_db")
MIGRACION = RAIZ / "backend" / "scripts" / "migrations" / "026_fu_l6_metas_granularidad.sql"


def _aislada(url: str) -> bool:
    return bool(re.search(r"@(127\.0\.0\.1|localhost):554\d\d/", url))


@pytest.fixture
def cur():
    if not _aislada(URL):
        pytest.skip("FU_L6_PG_URL no apunta a una copia tmpfs aislada (127.0.0.1:554xx)")
    try:
        con = psycopg2.connect(URL, connect_timeout=3)
    except Exception:
        pytest.skip("copia tmpfs de PostgreSQL no disponible")
    con.autocommit = False
    c = con.cursor()
    try:
        c.execute("SELECT to_regclass('bi.vw_cmi_valores') IS NOT NULL AND EXISTS (SELECT 1 FROM information_schema.columns "
                  "WHERE table_name = 'fact_evaluacion_docente' AND column_name = 'escala_max')")
        if not c.fetchone()[0]:
            pytest.skip("la copia tmpfs no tiene aplicadas las migraciones 022 a 025")
        yield c
    finally:
        con.rollback()   # nada de lo que escribe esta prueba se conserva
        con.close()


def _aplicar(c):
    sql = MIGRACION.read_text(encoding="utf-8")
    c.execute(sql.replace("\nBEGIN;", "\n").replace("\nCOMMIT;", "\n"))


MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]


def _tiempo(c, gestion, mes):
    idt = gestion * 10000 + mes * 100 + 1
    c.execute("INSERT INTO dim_tiempo (id_tiempo, gestion, semestre, mes, nombre_mes, periodo_mes, fecha, trimestre, "
              "semana_iso, dia_mes, dia_semana, nombre_dia, es_fin_semana) "
              "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1, 1, 4, 'Jueves', FALSE) ON CONFLICT (id_tiempo) DO NOTHING",
              (idt, gestion, 1 if mes <= 6 else 2, mes, MESES[mes - 1], f"{gestion}-{mes:02d}", f"{gestion}-{mes:02d}-01", (mes - 1) // 3 + 1))
    return idt


def _categoria(c, nombre="CATEGORIA FICTICIA A"):
    c.execute("INSERT INTO dim_categoria_financiera (nombre_categoria, tipo) VALUES (%s, 'INGRESO') RETURNING id_categoria", (nombre,))
    return c.fetchone()[0]


def _rent(c, cat, gestion, mes, ejecutado, meta, gran):
    c.execute("INSERT INTO fact_rentabilidad (id_tiempo, id_categoria, monto_ejecutado, monto_meta, granularidad_meta) VALUES (%s, %s, %s, %s, %s)",
              (_tiempo(c, gestion, mes), cat, ejecutado, meta, gran))


def _kpi(c, gestion, codigo):
    c.execute("SELECT valor FROM bi.vw_cmi_valores WHERE gestion = %s AND codigo = %s", (gestion, codigo))
    fila = c.fetchone()
    return None if fila is None or fila[0] is None else float(fila[0])


def _conteos(c):
    c.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema IN ('public', 'bi') AND table_type = 'BASE TABLE'")
    tablas = c.fetchone()[0]
    c.execute("SELECT count(*) FROM information_schema.views WHERE table_schema = 'bi'")
    return tablas, c.fetchone()[0]


# Gestiones ficticias muy posteriores a los datos reales: el mes de corte de la fuente sale de 2093
G_SIN_META, G_ANUAL, G_MENSUAL, G_PARCIAL = 2090, 2091, 2092, 2093


def _escenario(c):
    cat = _categoria(c)
    for mes in range(1, 13):
        _rent(c, cat, G_SIN_META, mes, 100, None, None)                          # 2090: ejecutado, ninguna meta
        _rent(c, cat, G_ANUAL, mes, 100, 5000 if mes == 12 else None, "ANUAL" if mes == 12 else None)   # 2091: una sola celda anual (diciembre)
        _rent(c, cat, G_MENSUAL, mes, 100 + mes, 120, "MENSUAL")                  # 2092: meta mensual
    for mes in range(1, 6):
        _rent(c, cat, G_PARCIAL, mes, 50 if mes == 5 else 130, 100, "MENSUAL")    # 2093: ejecuta hasta mayo; mayo (corte) es parcial
    for mes in range(6, 13):
        _rent(c, cat, G_PARCIAL, mes, None, 100, "MENSUAL")                       # meta de los meses futuros
    return cat


def test_idempotente_y_sin_esquema_nuevo(cur):
    antes = _conteos(cur)
    _aplicar(cur)
    despues_1 = _conteos(cur)
    _aplicar(cur)
    assert despues_1 == _conteos(cur) == antes == (51, 10)


def test_kpi02_solo_con_meta_mensual(cur):
    _aplicar(cur)
    _escenario(cur)
    assert _kpi(cur, G_ANUAL, "KPI-02") is None        # una sola celda anual en diciembre NO es la meta de diciembre (antes: 5000/ejecutado = 2 %)
    assert _kpi(cur, G_SIN_META, "KPI-02") is None     # sin meta alguna: sin dato
    assert _kpi(cur, G_MENSUAL, "KPI-02") == pytest.approx(100.0 * 112 / 120)            # diciembre: 112 / 120
    # 2093: el mes de corte es mayo (parcial); el último mes cerrado es abril: 130 / 100
    assert _kpi(cur, G_PARCIAL, "KPI-02") == pytest.approx(130.0)


def test_kpi03_13_14_usan_la_meta_anual(cur):
    _aplicar(cur)
    _escenario(cur)
    # 2091: ejecutado 1200 frente a la meta anual de 5000 (una meta anual no se prorratea)
    assert _kpi(cur, G_ANUAL, "KPI-03") == pytest.approx(100.0 * 1200 / 5000)
    assert _kpi(cur, G_ANUAL, "KPI-13") == pytest.approx(100.0 * 1200 / 5000)
    assert _kpi(cur, G_ANUAL, "KPI-14") == pytest.approx(5000 - 1200)
    # 2090 sin meta: KPI-03 y KPI-13 sin dato; KPI-14 no tiene fila (sin meta no hay brecha)
    assert _kpi(cur, G_SIN_META, "KPI-03") is None and _kpi(cur, G_SIN_META, "KPI-13") is None and _kpi(cur, G_SIN_META, "KPI-14") is None
    # 2092 mensual: meta anual = 12 x 120 = 1440; ejecutado = 12 x 100 + (1+...+12)
    ejec = 12 * 100 + 78
    assert _kpi(cur, G_MENSUAL, "KPI-13") == pytest.approx(100.0 * ejec / 1440)
    assert _kpi(cur, G_MENSUAL, "KPI-14") == pytest.approx(max(1440 - ejec, 0))
    assert _kpi(cur, G_MENSUAL, "KPI-03") == pytest.approx(100.0 * ejec / 1440)


def test_mes_parcial_no_cuenta_en_kpi03_ni_kpi12_pero_si_en_13_y_14(cur):
    _aplicar(cur)
    _escenario(cur)
    # 2093: ejecutado total = 4 x 130 + 50 = 570; cerrado (enero a abril) = 520; meta de enero a abril = 400; meta anual = 12 x 100
    assert _kpi(cur, G_PARCIAL, "KPI-03") == pytest.approx(100.0 * 520 / 400)
    assert _kpi(cur, G_PARCIAL, "KPI-13") == pytest.approx(100.0 * 570 / 1200)
    assert _kpi(cur, G_PARCIAL, "KPI-14") == pytest.approx(1200 - 570)
    # KPI-12: enero a abril de 2093 (4 x 130 = 520) frente a enero a abril de 2092 (4 x 100 + 1+2+3+4 = 410)
    assert _kpi(cur, G_PARCIAL, "KPI-12") == pytest.approx(100.0 * (520 / 410 - 1))


def test_el_mes_de_corte_en_diciembre_es_cerrado(cur):
    _aplicar(cur)
    cat = _categoria(cur)
    g = 2095
    for mes in range(1, 13):
        _rent(cur, cat, g, mes, 100, 80, "MENSUAL")
    assert _kpi(cur, g, "KPI-02") == pytest.approx(100.0 * 100 / 80)     # el corte es 2095-12: el año completo, diciembre cuenta
    assert _kpi(cur, g, "KPI-03") == pytest.approx(100.0 * 1200 / 960)


def test_fila_sin_bandera_se_lee_como_mensual(cur):
    _aplicar(cur)
    cat = _categoria(cur)
    g = 2094
    for mes in range(1, 13):
        _rent(cur, cat, g, mes, 100, 80, None)        # filas anteriores a la 026: bandera NULL
    assert _kpi(cur, g, "KPI-02") == pytest.approx(100.0 * 100 / 80)


def test_metas_mensual_conserva_columnas_y_separa_la_anual(cur):
    _aplicar(cur)
    _escenario(cur)
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema = 'bi' AND table_name = 'vw_metas_mensual' "
                "ORDER BY ordinal_position")
    cols = [r[0] for r in cur.fetchall()]
    assert cols == ["gestion", "mes", "nombre_mes", "categoria", "ejecutado", "meta", "fecha_mes", "avance_pct", "ejecutado_anio_ant", "meta_anual"]
    cur.execute("SELECT meta, avance_pct, meta_anual FROM bi.vw_metas_mensual WHERE gestion = %s AND mes = 12", (G_ANUAL,))
    meta, avance, anual = cur.fetchone()
    assert meta is None and avance is None and float(anual) == 5000.0      # la meta anual ya no es la meta de diciembre
    cur.execute("SELECT meta, meta_anual FROM bi.vw_metas_mensual WHERE gestion = %s AND mes = 12", (G_MENSUAL,))
    meta, anual = cur.fetchone()
    assert float(meta) == 120.0 and anual is None


def test_check_de_granularidad_rechaza_valores_desconocidos(cur):
    _aplicar(cur)
    cat = _categoria(cur)
    cur.execute("SAVEPOINT s")
    with pytest.raises(psycopg2.errors.CheckViolation):
        _rent(cur, cat, 2089, 1, 1, 1, "TRIMESTRAL")
    cur.execute("ROLLBACK TO SAVEPOINT s")
