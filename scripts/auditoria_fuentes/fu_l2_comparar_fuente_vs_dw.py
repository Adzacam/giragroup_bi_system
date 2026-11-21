"""
FU-L2 · Compara un libro de cobranza con la DW de la copia tmpfs y mide los KPI antes y después.

Dos salidas, sin datos personales (solo conteos, montos y estados):
  docs/mediciones/fu_l2_cobranza_fuente_vs_dw.csv   metrica, anio, fuente, dw_tmpfs, diferencia, explicacion
  docs/mediciones/fu_l2_kpi_antes_despues.csv       kpi, gestion, antes_dw_viva, despues_tmpfs, diferencia

La columna de la FUENTE se calcula desde el libro con el catálogo de sinónimos (`config/mapeo_fuentes.yaml`),
sin nombres de columna en el código. La columna DW se lee de la base que se indica.

Uso (host, sin docker; la copia tmpfs ya recargada con el libro):
    python scripts/auditoria_fuentes/fu_l2_comparar_fuente_vs_dw.py --libro "<libro.xlsx>" \
        --tmpfs postgresql://giragroup_user:tmpfs_local@127.0.0.1:55437/giragroup_db \
        [--viva <url de la DW viva: SOLO LECTURA>]
Sin --tmpfs (modo --solo-lector) deja solo la columna de la fuente y la del lector canónico, sin tocar ninguna base.

Garantías: --tmpfs se niega a correr si el host no es 127.0.0.1/localhost:554xx; --viva se abre en una
transacción READ ONLY y solo ejecuta SELECT.
"""
from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(RAIZ), str(RAIZ / "backend")]

SALIDA = RAIZ / "docs" / "mediciones"
KPIS = ["KPI-01", "KPI-04", "KPI-05", "KPI-15"]


def _vacia(v) -> bool:
    return v is None or (isinstance(v, str) and not v.strip())


def leer_fuente(libro: str):
    """Columnas por campo canónico y filas del primer libro/hoja de cobranza (la de más filas con campos de cobranza)."""
    import openpyxl
    from services.cobranza_canonica import campo_de_cabecera

    wb = openpyxl.load_workbook(libro, data_only=True, read_only=True)
    mejor = None
    for ws in wb.worksheets:
        if ws.sheet_state != "visible":
            continue
        filas = ws.iter_rows(values_only=True)
        cab = next(filas, None)
        if not cab:
            continue
        cols = collections.defaultdict(list)
        for i, h in enumerate(cab):
            r = campo_de_cabecera(str(h)) if h is not None else None
            if r:
                cols[r[0]].append((i, str(h), r[1], r[2]))
        if "cuotas_en_mora" in cols and "monto_pago_mes" in cols:
            datos = [r for r in filas if any(not _vacia(v) for v in r)]
            if mejor is None or len(datos) > len(mejor[2]):
                mejor = (cab, cols, datos)
    if mejor is None:
        raise SystemExit("El libro no trae una hoja de cobranza por catálogo")
    return mejor


def _num(v):
    from pipeline.normalization.montos import parsear_monto
    return parsear_monto(v) if v is not None else None


def metricas_fuente(libro: str) -> dict:
    from services.cobranza_canonica import leer_cuotas, mes_de_columna, normalizar_estado_cartera
    from services.extraccion_por_encabezado import parsear_fecha

    cab, cols, datos = leer_fuente(libro)

    def primero(campo):
        c = [x for x in cols.get(campo, []) if not x[3]] or cols.get(campo, [])
        return min(c, key=lambda x: x[2])[0] if c else None

    i_cuotas, i_estado, i_ini, i_deuda = (primero(c) for c in ("cuotas_en_mora", "estado_cartera_fuente", "fecha_inicio", "monto_deuda"))
    i_ci = None
    for i, h in enumerate(cab):
        if h is not None and re.fullmatch(r"\s*ci\s*", str(h), re.I):
            i_ci = i
    m = {"filas": len(datos), "pagos": collections.Counter(), "mora_filas": collections.Counter(),
         "mora_est": collections.defaultdict(set), "estado": collections.Counter(), "cuotas_neg": 0, "cuotas_texto": 0,
         "deuda_neg": 0, "cerrada_mora": 0, "sin_fecha_mora": 0}
    for r in datos:
        cuotas, motivo = leer_cuotas(None if r[i_cuotas] is None else str(r[i_cuotas]))
        if motivo == "CUOTAS_NEGATIVAS":
            m["cuotas_neg"] += 1
        elif motivo == "CUOTAS_CON_TEXTO":
            m["cuotas_texto"] += 1
        canon, _ = normalizar_estado_cartera(None if i_estado is None or r[i_estado] is None else str(r[i_estado]))
        m["estado"][canon] += 1
        d = _num(r[i_deuda]) if i_deuda is not None else None
        if d is not None and d < 0:
            m["deuda_neg"] += 1
        f = r[i_ini] if i_ini is not None else None
        f = f.date() if isinstance(f, dt.datetime) else (parsear_fecha(str(f)) if f is not None else None)
        if (cuotas or 0) >= 2:
            if canon == "CERRADA":
                m["cerrada_mora"] += 1
            if f is None:
                m["sin_fecha_mora"] += 1
            else:
                m["mora_filas"][f.year] += 1
                if i_ci is not None:
                    m["mora_est"][f.year].add(str(r[i_ci]).strip())
    for campo_pago in cols.get("monto_pago_mes", []):
        i, h = campo_pago[0], campo_pago[1]
        periodo = mes_de_columna(h)
        if not periodo:
            continue
        for r in datos:
            v = _num(r[i])
            if v:
                m["pagos"][periodo[0]] += v
    return m


def _sql_tmpfs(url: str, consultas: dict) -> dict:
    import psycopg2
    if not re.search(r"@(127\.0\.0\.1|localhost):554\d\d/", url):
        raise SystemExit("--tmpfs debe ser la copia aislada (127.0.0.1:554xx); no se toca otra base")
    con = psycopg2.connect(url, connect_timeout=5)
    con.set_session(readonly=True)
    out = {}
    with con, con.cursor() as cur:
        for k, q in consultas.items():
            cur.execute(q)
            out[k] = cur.fetchall()
    con.close()
    return out


def _sql_viva_solo_lectura(url: str, q: str):
    import psycopg2
    con = psycopg2.connect(url, connect_timeout=5)
    con.set_session(readonly=True, autocommit=False)
    with con.cursor() as cur:
        cur.execute(q)
        filas = cur.fetchall()
    con.rollback()
    con.close()
    return filas


CONSULTAS_DW = {
    "pagos": "SELECT t.gestion, SUM(f.monto_pagado) FROM fact_situacion_financiera f JOIN dim_tiempo t USING (id_tiempo) GROUP BY 1",
    "mora_hechos": "SELECT t.gestion, COUNT(*), COUNT(DISTINCT f.id_estudiante) FROM fact_situacion_financiera f JOIN dim_tiempo t USING (id_tiempo) "
                   "WHERE f.concepto = 'SITUACION_CARTERA' AND f.cuotas_impagas >= 2 GROUP BY 1",
    "estado": "SELECT estado_cartera_fuente, COUNT(*) FROM fact_situacion_financiera WHERE concepto = 'SITUACION_CARTERA' GROUP BY 1",
    "situaciones": "SELECT COUNT(*) FROM fact_situacion_financiera WHERE concepto = 'SITUACION_CARTERA'",
    "cerrada_mora": "SELECT COUNT(*) FROM fact_situacion_financiera WHERE concepto = 'SITUACION_CARTERA' AND estado_cartera_fuente = 'CERRADA' AND cuotas_impagas >= 2",
    "avisos": "SELECT tipo_regla, descripcion FROM log_inconsistencias WHERE tipo_regla IN ('CUOTAS_NEGATIVAS','CUOTAS_CON_TEXTO','SOBREPAGO')",
    "dias_mora": "SELECT COUNT(*) FROM fact_situacion_financiera WHERE dias_mora IS NOT NULL AND dias_mora > 0",
    "mora_estado_legacy": "SELECT COUNT(*) FROM fact_situacion_financiera WHERE estado_cartera = 'Mora'",
}
SQL_KPI = ("SELECT gestion, codigo, valor FROM bi.vw_cmi_valores WHERE codigo IN (" + ",".join(f"'{k}'" for k in KPIS) + ") ORDER BY 2, 1")


def _fila(metrica, anio, fuente, dw, explicacion):
    dif = "" if (fuente in ("", None) or dw in ("", None)) else round(float(dw) - float(fuente), 2)
    return [metrica, anio, "" if fuente is None else fuente, "" if dw is None else dw, dif, explicacion]


def construir_filas(m: dict, dw: dict | None) -> list:
    filas = []
    anios = sorted(set(m["pagos"]) | set(m["mora_filas"]))
    pagos_dw = {int(g): float(s or 0) for g, s in (dw or {}).get("pagos", [])}
    mora_dw = {int(g): (int(n), int(e)) for g, n, e in (dw or {}).get("mora_hechos", [])}
    for a in anios:
        f = round(m["pagos"].get(a, 0), 2)
        filas.append(_fila("pagos_bs_por_mes_de_pago", a, f, round(pagos_dw[a], 2) if dw and a in pagos_dw else (0 if dw else None),
                           "suma de las columnas MONTO <MES> <AÑO> del año, sin las (PRELIMINAR); cada pago va al mes del pago"))
    for a in anios:
        f = m["mora_filas"].get(a, 0)
        filas.append(_fila("filas_con_cuotas_ge_2_por_anio_de_inicio", a, f, mora_dw.get(a, (0, 0))[0] if dw else None,
                           "DA3: cuotas >= 2; el hecho de situación cae en la fecha de inicio. Una fila sin fecha de inicio legible "
                           f"({m['sin_fecha_mora']} en la fuente) se ubica por otra fecha de la fila y no cuenta en el año de la fuente"))
    for a in anios:
        f = len(m["mora_est"].get(a, ()))
        filas.append(_fila("estudiantes_distintos_con_cuotas_ge_2", a, f, mora_dw.get(a, (0, 0))[1] if dw else None,
                           "estudiantes distintos (CI) con al menos un hecho en mora en la gestión"))
    est_dw = {e: int(n) for e, n in (dw or {}).get("estado", [])}
    for e in ("CERRADA", "VIGENTE", "EN MORA", "PREVISIONABLE", "INCOBRABLE", None):
        filas.append(_fila(f"estado_cartera_fuente={e or 'sin estado'}", "", m["estado"].get(e, 0), est_dw.get(e, 0) if dw else None,
                           "TIPO DE CARTERA normalizado por vocabulario; descriptivo (la mora la decide DA3). Dos filas del mismo "
                           "estudiante, programa y fecha de inicio comparten hecho"))
    filas.append(_fila("filas_de_la_fuente_vs_hechos_de_situacion", "", m["filas"], (dw["situaciones"][0][0] if dw else None),
                       "filas con datos de la hoja de cobranza frente a hechos SITUACION_CARTERA (filas sin campo de cobranza no producen hecho de situación)"))
    filas.append(_fila("cerrada_con_cuotas_ge_2", "", m["cerrada_mora"], (dw["cerrada_mora"][0][0] if dw else None),
                       "contradicción interna de la fuente (cartera cerrada con 2 o más cuotas): se documenta, no se corrige; cuenta como mora por DA3"))
    avisos = collections.Counter()
    for tipo, desc in (dw or {}).get("avisos", []):
        mm = re.search(r":\s*(\d+)\s+fila", desc or "")
        avisos[tipo] += int(mm.group(1)) if mm else 1
    filas.append(_fila("cuotas_negativas_a_cero", "", m["cuotas_neg"], avisos["CUOTAS_NEGATIVAS"] if dw else None, "aviso agregado CUOTAS_NEGATIVAS (valor 0)"))
    filas.append(_fila("cuotas_con_texto_a_numero", "", m["cuotas_texto"], avisos["CUOTAS_CON_TEXTO"] if dw else None, "aviso agregado CUOTAS_CON_TEXTO (texto '1s' -> 1)"))
    filas.append(_fila("deuda_negativa_a_cero", "", m["deuda_neg"], avisos["SOBREPAGO"] if dw else None, "aviso agregado SOBREPAGO (deuda 0)"))
    return filas


def kpis(url_viva, url_tmpfs) -> list:
    antes = {(int(g), c): v for g, c, v in _sql_viva_solo_lectura(url_viva, SQL_KPI)} if url_viva else {}
    despues = {(int(g), c): v for g, c, v in _sql_tmpfs(url_tmpfs, {"k": SQL_KPI})["k"]} if url_tmpfs else {}
    filas = []
    for (g, c) in sorted(set(antes) | set(despues), key=lambda x: (x[1], x[0])):
        a, d = antes.get((g, c)), despues.get((g, c))
        filas.append([c, g, "" if a is None else round(float(a), 2), "" if d is None else round(float(d), 2),
                      "" if a is None or d is None else round(float(d) - float(a), 2)])
    return filas


def escribir(ruta: Path, cabecera, filas):
    with open(ruta, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cabecera)
        w.writerows(filas)
    print(f"{ruta}: {len(filas)} filas")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--libro", required=True)
    ap.add_argument("--tmpfs")
    ap.add_argument("--viva")
    ap.add_argument("--solo-lector", action="store_true")
    ap.add_argument("--salida", default=str(SALIDA / "fu_l2_cobranza_fuente_vs_dw.csv"))
    args = ap.parse_args()
    m = metricas_fuente(args.libro)
    if args.solo_lector or not args.tmpfs:
        escribir(Path(args.salida), ["metrica", "anio", "fuente", "dw_tmpfs", "diferencia", "explicacion"], construir_filas(m, None))
        return 0
    dw = _sql_tmpfs(args.tmpfs, CONSULTAS_DW)
    escribir(Path(args.salida), ["metrica", "anio", "fuente", "dw_tmpfs", "diferencia", "explicacion"], construir_filas(m, dw))
    escribir(SALIDA / "fu_l2_kpi_antes_despues.csv", ["kpi", "gestion", "antes_dw_viva", "despues_tmpfs", "diferencia"],
             kpis(args.viva, args.tmpfs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
