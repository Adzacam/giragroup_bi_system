"""
FU-L3 · Compara los libros de inscripciones y de captación con la DW de la copia tmpfs y mide KPI-06 y KPI-21 antes y después.

Dos salidas, sin datos personales (solo conteos y cifras por mes y gestión):
  docs/mediciones/fu_l3_inscritos_conversion.csv     metrica, anio_mes, fuente, dw_tmpfs, diferencia, explicacion
  docs/mediciones/fu_l3_kpi_antes_despues.csv        kpi, gestion, antes_dw_viva, despues_tmpfs, diferencia

La columna de la FUENTE sale de los libros con el catálogo de sinónimos (`config/mapeo_fuentes.yaml`), sin nombres
de archivo, de hoja ni de columna en el código: las hojas que se usan las decide el clasificador de FU-L1 y la
deduplicación por programa y mes se calcula aquí aparte de la carga (prioridad: detalle mensual visible).

Uso (host, sin docker; la copia tmpfs ya recargada con los libros):
    python scripts/auditoria_fuentes/fu_l3_comparar_fuente_vs_dw.py \
        --inscripciones "<tabla de inscripciones.xlsx>" --captacion "<libro de planificación.xlsx>" \
        [--captacion "<libro con tabla por programa.xlsx>"] \
        --tmpfs postgresql://giragroup_user:tmpfs_local@127.0.0.1:55438/giragroup_db \
        [--viva <url de la DW viva: SOLO LECTURA>]

Garantías: --tmpfs se niega a correr si el host no es 127.0.0.1/localhost:554xx; --viva se abre en una transacción
READ ONLY y solo ejecuta SELECT. Las URL se reciben por argumento: no se escriben en ningún archivo.
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(RAIZ), str(RAIZ / "backend")]

SALIDA = RAIZ / "docs" / "mediciones"
KPIS = ["KPI-06", "KPI-21"]


def _vacia(v) -> bool:
    return v is None or (isinstance(v, str) and not v.strip()) or (isinstance(v, float) and v != v)


def _texto(v):
    if _vacia(v):
        return None
    if isinstance(v, float) and v == int(v):
        return str(int(v))
    return str(v)


# ── Fuente: inscripciones ────────────────────────────────────────────────────

def _campo_de_tipo(tipo: str, cabecera: str):
    from pipeline.lector_hojas import _coincide, cargar_config, normalizar
    norma = normalizar(cabecera)
    for campo, espec in ((cargar_config()["tipos_fuente"].get(tipo) or {}).get("campos") or {}).items():
        if any(_coincide(norma, s) for s in (espec or {}).get("sinonimos") or []):
            return campo
    return None


def inscripciones_por_anio(libro: str) -> dict:
    """{año: filas} de la hoja de inscripciones (una fila = una inscripción), año de su fecha de inscripción."""
    from pipeline.ingesta import leer_archivo_con_metadatos
    from services.extraccion_por_encabezado import parsear_fecha

    por_anio = collections.Counter()
    sin_fecha = 0
    for hoja in leer_archivo_con_metadatos(libro).values():
        if not hoja.usada or hoja.meta.fila_cabecera is None:
            continue
        cab = [str(c) if not _vacia(c) else "" for c in hoja.df.iloc[hoja.meta.fila_cabecera]]
        col = next((i for i, c in enumerate(cab) if c and _campo_de_tipo("MARKETING", c) == "fecha_inscripcion"), None)
        if col is None:
            continue
        df = hoja.df_recortado().iloc[hoja.meta.fila_cabecera + 1:]
        for v in df.iloc[:, col]:
            if _vacia(v):
                if not df.empty:
                    sin_fecha += 1
                continue
            f = parsear_fecha(str(v)[:10])
            if f:
                por_anio[f.year] += 1
            else:
                sin_fecha += 1
    por_anio["sin_fecha"] = sin_fecha
    return dict(por_anio)


# ── Fuente: captación ────────────────────────────────────────────────────────

def captacion_por_mes(libros: list) -> dict:
    """
    {AAAA-MM: {leads, inscritos, programas, leads_bruto, inscritos_bruto}} de las hojas USADAS de los libros, con la regla DA6:
    solo filas con ambos datos y 0 <= inscritos <= leads; un POS y mes en varias hojas cuenta una vez (menor prioridad;
    desempate por nombre de hoja). `*_bruto` suma todo lo que trae la hoja ganadora sin validar (referencia del plan).
    """
    from pipeline.ingesta import leer_archivo_con_metadatos
    from services import captacion_canonica as capt
    from services.planificacion_extractor import anio_mes_de_hoja

    candidatos = collections.defaultdict(list)       # (pos, mes) -> [(prioridad, hoja, leads, inscritos)]
    brutos = collections.defaultdict(lambda: [0, 0, set()])
    for libro in libros:
        for nombre, hoja in leer_archivo_con_metadatos(libro).items():
            if not hoja.usada or hoja.meta.fila_cabecera is None:
                continue
            cab = [str(c) if not _vacia(c) else f"col_{i}" for i, c in enumerate(hoja.df.iloc[hoja.meta.fila_cabecera])]
            anio_h, mes_h = anio_mes_de_hoja(nombre)
            prioridad = capt.prioridad_de_hoja(hoja.meta.estado, hoja.meta.periodo_dominante)
            for fila in hoja.df_recortado().iloc[hoja.meta.fila_cabecera + 1:].itertuples(index=False):
                campos = {c.upper(): _texto(v) for c, v in zip(cab, fila) if _texto(v)}
                f = capt.leer_fila(campos, anio_h, mes_h)
                if f is None or f.periodo is None or not f.pos:
                    continue
                clave_mes = f.periodo.strftime("%Y-%m")
                if f.leads is not None and f.inscritos is not None:
                    brutos[(clave_mes, prioridad, nombre)][0] += f.leads
                    brutos[(clave_mes, prioridad, nombre)][1] += f.inscritos
                if f.valida:
                    candidatos[(f.pos, clave_mes)].append((prioridad, nombre, int(f.leads), int(f.inscritos)))
    por_mes = collections.defaultdict(lambda: {"leads": 0, "inscritos": 0, "programas": 0, "hojas": set()})
    for (pos, mes), lista in candidatos.items():
        mejor = min((p, h) for p, h, _, _ in lista)
        fila = [(l, i) for p, h, l, i in lista if (p, h) == mejor]
        leads_pm, inscritos_pm = sum(l for l, _ in fila), sum(i for _, i in fila)
        if leads_pm <= 0:       # el KPI-06 (migración 014) pide leads > 0
            continue
        por_mes[mes]["leads"] += leads_pm
        por_mes[mes]["inscritos"] += inscritos_pm
        por_mes[mes]["programas"] += 1
        por_mes[mes]["hojas"].add(mejor[1])
    for (mes, _, _), (l, i, _) in brutos.items():
        por_mes[mes].setdefault("leads_bruto", 0)
        por_mes[mes]["leads_bruto"] = por_mes[mes].get("leads_bruto", 0) + l
        por_mes[mes]["inscritos_bruto"] = por_mes[mes].get("inscritos_bruto", 0) + i
    return {m: {k: (len(v) if k == "hojas" else v) for k, v in d.items()} for m, d in sorted(por_mes.items())}


# ── DW ───────────────────────────────────────────────────────────────────────

def _abrir_tmpfs(url: str):
    import psycopg2
    if not re.search(r"@(127\.0\.0\.1|localhost):554\d\d/", url):
        raise SystemExit("--tmpfs debe ser la copia aislada (127.0.0.1:554xx); no se toca otra base")
    con = psycopg2.connect(url, connect_timeout=5)
    con.set_session(readonly=True)
    return con


def _consulta(con, q, params=None):
    with con.cursor() as cur:
        cur.execute(q, params)
        return cur.fetchall()


SQL_INSCRITOS = ("SELECT t.gestion, SUM(f.inscritos) FROM fact_marketing f JOIN dim_tiempo t USING (id_tiempo) GROUP BY 1")
SQL_CAPTACION_MES = ("SELECT t.periodo_mes, SUM(f.leads_captacion), SUM(f.inscritos_captacion), COUNT(DISTINCT f.id_modulo) "
                     "FROM fact_marketing f JOIN dim_tiempo t USING (id_tiempo) WHERE f.leads_captacion > 0 AND f.inscritos_captacion >= 0 "
                     "AND f.inscritos_captacion <= f.leads_captacion GROUP BY 1 ORDER BY 1")
SQL_KPI = ("SELECT gestion, codigo, valor FROM bi.vw_cmi_valores WHERE codigo IN (" + ",".join(f"'{k}'" for k in KPIS) + ") ORDER BY 2, 1")
SQL_INSCRITOS_MKT = ("SELECT t.gestion, SUM(f.inscritos) FROM public.fact_marketing f JOIN public.dim_tiempo t USING (id_tiempo) GROUP BY 1")
SQL_MODULOS_MKT = "SELECT COUNT(DISTINCT id_modulo) FROM fact_marketing"


def _viva(url: str, consultas: dict) -> dict:
    """Lectura de la DW viva: transacción READ ONLY, solo SELECT, siempre revertida."""
    import psycopg2
    con = psycopg2.connect(url, connect_timeout=5)
    con.set_session(readonly=True, autocommit=False)
    out = {}
    with con.cursor() as cur:
        for k, q in consultas.items():
            cur.execute(q)
            out[k] = cur.fetchall()
    con.rollback()
    con.close()
    return out


def _fila(metrica, clave, fuente, dw, explicacion):
    dif = "" if (fuente in ("", None) or dw in ("", None)) else round(float(dw) - float(fuente), 2)
    return [metrica, clave, "" if fuente is None else fuente, "" if dw is None else dw, dif, explicacion]


def construir(inscr: dict, capt: dict, dw: dict, viva_inscritos: dict | None, base_tmpfs: dict | None = None) -> list:
    filas = []
    dw_ins = {int(g): int(s or 0) for g, s in dw["inscritos"]}
    sin_fecha = inscr.get("sin_fecha", 0)
    for anio in sorted(a for a in inscr if a != "sin_fecha"):
        explic = "una inscripción = 1; sin diferencia" if dw_ins.get(anio) == inscr[anio] else "revisar"
        filas.append(_fila("inscritos_por_anio", anio, inscr[anio], dw_ins.get(anio), explic))
    if viva_inscritos:
        for anio in sorted(viva_inscritos):
            filas.append(_fila("inscritos_dw_viva_antes", anio, inscr.get(anio), viva_inscritos[anio],
                               "DW viva antes de la corrección (duplicados): solo lectura"))
    if base_tmpfs:
        for anio in sorted(base_tmpfs):
            filas.append(_fila("inscritos_tmpfs_codigo_anterior", anio, inscr.get(int(anio)), base_tmpfs[anio],
                               "recarga en la tmpfs con el código de antes de FU-L3 en una DW limpia: 1 por inscripción (no reproduce el ×2); la diferencia son 5 inscripciones con CI incompleta que el código anterior contaba 0 y 1 con marca temporal con milisegundos que quedaba sin mes (id_tiempo vacío)"))
    if sin_fecha:
        filas.append(_fila("inscripciones_sin_fecha_valida", "", sin_fecha, "", "no se pueden ubicar en un año"))
    dw_cap = {m: (int(l), int(i), int(p)) for m, l, i, p in dw["captacion_mes"]}
    gest = collections.defaultdict(lambda: [0, 0, 0, 0, 0, 0])
    for mes in sorted(set(capt) | set(dw_cap)):
        f = capt.get(mes)
        d = dw_cap.get(mes)
        nota = ("misma cifra: ambos datos, 0 <= inscritos <= leads, un POS y mes una sola vez" if f and d and (f["leads"], f["inscritos"]) == d[:2]
                else "revisar")
        filas.append(_fila("leads_captacion", mes, f and f["leads"], d and d[0], nota))
        filas.append(_fila("inscritos_captacion", mes, f and f["inscritos"], d and d[1], nota))
        if f and "leads_bruto" in f:
            filas.append(_fila("referencia_plan_sin_validar_leads", mes, f["leads_bruto"], f["leads"],
                               "suma de la hoja sin la regla DA6; la diferencia son filas sin inscritos o con inscritos > leads"))
            filas.append(_fila("referencia_plan_sin_validar_inscritos", mes, f["inscritos_bruto"], f["inscritos"],
                               "ídem (las filas con inscritos > leads o sin leads no cuentan)"))
        g = int(mes[:4])
        if d:
            gest[g][0] += d[0]
            gest[g][1] += d[1]
            gest[g][2] += 1
        if f:
            gest[g][3] += f["leads"]
            gest[g][4] += f["inscritos"]
            gest[g][5] += 1
    for g in sorted(gest):
        dl, di, dm, fl, fi, fm = gest[g]
        filas.append(_fila("leads_captacion_gestion", g, fl, dl, f"meses con dato: fuente {fm}, DW {dm} de 12"))
        filas.append(_fila("inscritos_captacion_gestion", g, fi, di, f"meses con dato: fuente {fm}, DW {dm} de 12"))
        filas.append(_fila("kpi06_gestion_pct", g, round(100.0 * fi / fl, 2) if fl else "", round(100.0 * di / dl, 2) if dl else "",
                           "Σ inscritos / Σ leads de la gestión (DA6)"))
        filas.append(_fila("cobertura_meses", g, fm, dm, "meses con dato de los 12 de la gestión"))
    kpi06 = {int(g): v for g, c, v in dw["kpi"] if c == "KPI-06"}
    from services import captacion_cobertura as cob
    meses_dw = [{"gestion": int(m[:4]), "mes": int(m[5:]), "periodo_mes": m, "leads": v[0], "inscritos": v[1], "programas": v[2],
                 "conversion_pct": 0.0} for m, v in dw_cap.items()]
    for g in sorted(set(int(a) for a in dw_ins) | set(gest) | {2023, 2024, 2025, 2026}):
        v = kpi06.get(g)
        motivo = "" if v is not None else cob.motivo_sin_dato(meses_dw, g, _plantillas())
        filas.append(_fila("kpi06_cmi_gestion_pct", g, "", round(float(v), 2) if v is not None else "sin dato", motivo))
    filas.append(_fila("programas_distintos_en_fact_marketing", "", "", dw["modulos"][0][0], "programas (módulos) con inscripciones o captación"))
    return filas


def _plantillas():
    from pipeline.lector_hojas import cargar_config
    return (cargar_config().get("captacion") or {}).get("motivos_sin_dato") or {}


NOTAS_KPI = {
    "KPI-06": "Σ inscritos / Σ leads de captación por gestión (DA6); vacío = sin dato (la DW viva no carga leads de planificación)",
    "KPI-21": ("matrícula = estudiantes distintos con rendimiento académico: no lee fact_marketing, así que FU-L3 no la mueve; "
               "la diferencia viene del estado de la copia tmpfs (snapshot) frente a la DW viva"),
    "INSCRITOS-fact_marketing": "Σ fact_marketing.inscritos por gestión (serie Clientes y pronóstico): la DW viva trae el doble; la tmpfs 1 por inscripción",
}


def kpis(url_viva, con_tmpfs) -> list:
    antes = {}
    if url_viva:
        v = _viva(url_viva, {"k": SQL_KPI, "i": SQL_INSCRITOS_MKT})
        antes = {(int(g), c): val for g, c, val in v["k"]}
        antes.update({(int(g), "INSCRITOS-fact_marketing"): val for g, val in v["i"]})
    despues = {(int(g), c): val for g, c, val in _consulta(con_tmpfs, SQL_KPI)}
    despues.update({(int(g), "INSCRITOS-fact_marketing"): val for g, val in _consulta(con_tmpfs, SQL_INSCRITOS_MKT)})
    filas = []
    for (g, c) in sorted(set(antes) | set(despues), key=lambda x: (x[1], x[0])):
        a, d = antes.get((g, c)), despues.get((g, c))
        filas.append([c, g, "" if a is None else round(float(a), 2), "" if d is None else round(float(d), 2),
                      "" if a is None or d is None else round(float(d) - float(a), 2), NOTAS_KPI.get(c, "")])
    return filas


def escribir(ruta: Path, cabecera, filas):
    with open(ruta, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cabecera)
        w.writerows(filas)
    print(f"{ruta}: {len(filas)} filas")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inscripciones", required=True)
    ap.add_argument("--captacion", action="append", required=True)
    ap.add_argument("--tmpfs", required=True)
    ap.add_argument("--viva")
    ap.add_argument("--base-json", help="JSON {año: inscritos} de la recarga con el código anterior (opcional)")
    ap.add_argument("--salida-inscritos", default=str(SALIDA / "fu_l3_inscritos_conversion.csv"))
    ap.add_argument("--salida-kpi", default=str(SALIDA / "fu_l3_kpi_antes_despues.csv"))
    args = ap.parse_args()

    inscr = inscripciones_por_anio(args.inscripciones)
    capt = captacion_por_mes(args.captacion)
    con = _abrir_tmpfs(args.tmpfs)
    dw = {"inscritos": _consulta(con, SQL_INSCRITOS), "captacion_mes": _consulta(con, SQL_CAPTACION_MES),
          "kpi": _consulta(con, SQL_KPI), "modulos": _consulta(con, SQL_MODULOS_MKT)}
    viva_ins = {int(g): int(s or 0) for g, s in _viva(args.viva, {"i": SQL_INSCRITOS_MKT})["i"]} if args.viva else None
    escribir(Path(args.salida_inscritos), ["metrica", "anio_mes", "fuente", "dw_tmpfs", "diferencia", "explicacion"],
             construir(inscr, capt, dw, viva_ins, json.loads(Path(args.base_json).read_text()) if args.base_json else None))
    escribir(Path(args.salida_kpi), ["kpi", "gestion", "antes_dw_viva", "despues_tmpfs", "diferencia", "nota"], kpis(args.viva, con))
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
