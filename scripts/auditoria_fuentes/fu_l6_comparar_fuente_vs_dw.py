"""
FU-L6 · Compara las metas de los libros con la DW de la copia tmpfs y mide KPI-02, 03, 12, 13 y 14 antes y después.

Salidas (sin datos personales: montos por categoría y mes):
  docs/mediciones/fu_l6_metas_fuente_vs_dw.csv      una fila por serie, categoría, gestión, mes y campo (meta o ejecutado): valor de cada fuente,
                                                    valor esperado por la prioridad del catálogo, granularidad de la fuente y valor en la DW
  docs/mediciones/fu_l6_conflictos_metas.csv        los conflictos entre fuentes resueltos por regla: mes, campo, fuente elegida (por TIPO),
                                                    valor elegido, valor descartado, diferencia y la señal de múltiplo de 100.000
  docs/mediciones/fu_l6_kpi_antes_despues.csv       kpi, gestión: DW viva (solo lectura), copia tmpfs, cálculo independiente sobre la fuente y motivo
  docs/mediciones/fu_l6_resumen.json                conteos de las comparaciones

La FUENTE sale de cada libro con el lector del sistema (hojas usadas, cabecera por contenido) y las reglas del catálogo
(`metas_canonica`, `prioridad_fuentes`): nada depende del nombre del libro ni de la hoja. Los libros que traen metas se reconocen por
contenido (filas con categoría y mes que `registros_rentabilidad` convierte en hechos; informe de metas de planificación).

Uso (host, sin docker; la copia tmpfs ya recargada con los libros):
    FU_L6_VIVA_URL=<url de la DW viva: SOLO LECTURA> python scripts/auditoria_fuentes/fu_l6_comparar_fuente_vs_dw.py \
        --libro "<libro de ejecutado frente a meta>::RENTABILIDAD" --libro "<libro de egresos>::EGRESOS" --libro "<libro de planificación>::PLANIFICACION" \
        --tmpfs postgresql://giragroup_user:tmpfs_local@127.0.0.1:55441/giragroup_db \
        [--inverso postgresql://giragroup_user:tmpfs_local@127.0.0.1:55441/dw_l6_inverso]

Garantías: --tmpfs e --inverso se niegan a correr si el host no es 127.0.0.1/localhost:554xx; la DW viva se abre en una transacción READ ONLY y solo
ejecuta SELECT, con la URL en la variable de entorno FU_L6_VIVA_URL (no se escribe en ningún archivo ni en la salida).
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

RAIZ = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(RAIZ), str(RAIZ / "backend")]
SALIDA = RAIZ / "docs" / "mediciones"
KPIS = ("KPI-02", "KPI-03", "KPI-12", "KPI-13", "KPI-14")
CAMPOS = ("monto_meta", "monto_ejecutado")
TOLERANCIA = 0.02   # centavos de redondeo entre fuentes


def _aislada(url: str) -> bool:
    return bool(re.search(r"@(127\.0\.0\.1|localhost):554\d\d/", url))


# ── Fuente ────────────────────────────────────────────────────────────

def leer_libro(ruta: str, explicito: Optional[str]) -> Dict[str, Any]:
    """Tipo de fuente del libro (el que la ingesta le asignaría) y sus hojas de metas, leídas con el lector y las reglas del sistema."""
    from pipeline.ingesta import detectar_bloques, leer_archivo_con_metadatos
    from services import metas_canonica
    from services.extraccion_por_encabezado import campos_por_encabezado, registros_rentabilidad
    from services.ingestion_service import (IngestionService, detectar_tipo_fuente_por_cabeceras, elegir_tipo_fuente,
                                            normalizar_codigo_tipo_fuente)

    libro = leer_archivo_con_metadatos(ruta)
    lectura = {n: h.df_recortado() for n, h in libro.items() if h.usada}
    tipo = elegir_tipo_fuente(normalizar_codigo_tipo_fuente(explicito), detectar_tipo_fuente_por_cabeceras(lectura, Path(ruta).name))
    hojas = []
    for nombre, h in libro.items():
        if not h.usada:
            continue
        df = h.df_recortado()
        filas = []
        for b in [b for b in detectar_bloques(df, filas_transparentes=set(h.meta.filas_descartadas) or None) if len(b) >= 2]:
            texto = IngestionService.serializar_bloque_con_encabezados(b)
            filas += [campos_por_encabezado([c.strip() for c in l.split("|")]) for l in texto.splitlines() if l.strip()]
        if not any(registros_rentabilidad(c) for c in filas):
            continue   # no es una hoja de metas por categoría y mes (por contenido)
        perfil = metas_canonica.perfilar(filas)
        regs = [r for c in filas for r in registros_rentabilidad(c, perfil)]
        hojas.append({"indice": len(hojas) + 1, "registros": regs})
    return {"tipo": tipo, "hojas": hojas, "libro": libro, "ruta": ruta}


def metas_de_planificacion(info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Metas del informe de gestión de un libro de planificación (las que la ingesta carga en dim_meta)."""
    from services.planificacion_extractor import extraer_libro_planificacion
    excluidas = {n for n, h in info["libro"].items() if not h.usada}
    return extraer_libro_planificacion(info["ruta"], hojas_excluidas=excluidas)["metas"]


def fuente_por_tipo(libros: List[Dict[str, Any]]) -> Dict[str, Dict[Tuple[str, int, int], Dict[str, Any]]]:
    """{tipo de fuente: {(categoría, año, mes): {monto_meta, monto_ejecutado, granularidad}}}."""
    res: Dict[str, Dict[Tuple[str, int, int], Dict[str, Any]]] = defaultdict(dict)
    for info in libros:
        for hoja in info["hojas"]:
            for r in hoja["registros"]:
                clave = (r["categoria_financiera"], r["fecha"].year, r["fecha"].month)
                celda = res[info["tipo"]].setdefault(clave, {"monto_meta": None, "monto_ejecutado": None, "granularidad": None})
                for campo in CAMPOS:
                    if r.get(campo) is not None:
                        celda[campo] = r[campo]
                if r.get("monto_meta") is not None:
                    celda["granularidad"] = r.get("granularidad_meta")
    return res


def esperado(campo: str, por_tipo: Dict[str, Dict[Tuple, Dict[str, Any]]], clave: Tuple) -> Tuple[Optional[float], Optional[str], Optional[str]]:
    """(valor, tipo que lo aporta, granularidad) por la prioridad del catálogo: manda la fuente de mayor prioridad con una cifra; un hueco
    (vacío o 0) lo llena la otra fuente (misma regla que el cargador, así el resultado no depende del orden de llegada)."""
    from services import metas_canonica
    cands = [(metas_canonica.rango_tipo(campo, t) if metas_canonica.rango_tipo(campo, t) is not None else 99, t, d[clave])
             for t, d in por_tipo.items() if clave in d and d[clave][campo] is not None]
    cands.sort(key=lambda x: (x[0], x[1]))
    for _r, t, celda in cands:
        if celda[campo] != 0:
            return celda[campo], t, celda["granularidad"]
    if cands:
        _r, t, celda = cands[0]
        return celda[campo], t, celda["granularidad"]
    return None, None, None


# ── DW ────────────────────────────────────────────────────────────────

def conectar(url: str, solo_lectura: bool):
    import psycopg2
    con = psycopg2.connect(url, connect_timeout=5)
    con.set_session(readonly=solo_lectura, autocommit=False)
    return con


def leer_dw(con) -> Dict[Tuple[str, int, int], Dict[str, Any]]:
    cur = con.cursor()
    cur.execute("SELECT dc.nombre_categoria, dt.gestion, dt.mes, fr.monto_ejecutado, fr.monto_meta, fr.granularidad_meta "
                "FROM fact_rentabilidad fr JOIN dim_tiempo dt ON dt.id_tiempo = fr.id_tiempo "
                "JOIN dim_categoria_financiera dc ON dc.id_categoria = fr.id_categoria WHERE dc.tipo = 'INGRESO'")
    return {(c, int(g), int(m)): {"monto_ejecutado": None if e is None else float(e), "monto_meta": None if mt is None else float(mt),
                                  "granularidad": gr} for c, g, m, e, mt, gr in cur.fetchall()}


def leer_dim_meta(con) -> Dict[Tuple[str, int, int], float]:
    cur = con.cursor()
    cur.execute("SELECT dm.categoria, dt.gestion, dt.mes, dm.monto_meta FROM dim_meta dm JOIN dim_tiempo dt ON dt.id_tiempo = dm.id_tiempo")
    return {(c, int(g), int(m)): float(v) for c, g, m, v in cur.fetchall() if v is not None}


def leer_conflictos(con) -> List[Dict[str, Any]]:
    from services import metas_canonica
    cur = con.cursor()
    cur.execute("SELECT id_tiempo, gestion, mes FROM dim_tiempo")
    tiempo = {int(i): (int(g), int(m)) for i, g, m in cur.fetchall()}
    cur.execute("SELECT estado_resolucion, descripcion, valor_recibido, valor_esperado, campo_afectado FROM log_inconsistencias "
                "WHERE tipo_regla = 'CONFLICTO_FUENTES' ORDER BY id_inconsistencia")
    out = []
    for estado, desc, recibido, esperado_, campo in cur.fetchall():
        d = metas_canonica.leer_conflicto(desc or "")
        if d is None:   # conflicto sin regla (pendiente): el texto es el de la estructura
            out.append({"estado": estado, "categoria": (desc or "").split(" id_tiempo=")[0], "campo": campo.split(".")[-1],
                        "gestion": None, "mes": None, "elegida": "", "descartada": "", "elegido": None, "descartado": None})
            continue
        g, m = tiempo.get(int(d["id_tiempo"]), (None, None))
        out.append({"estado": estado, "categoria": d["categoria"], "campo": d["campo"], "gestion": g, "mes": m,
                    "elegida": d["elegida"], "descartada": d["descartada"], "elegido": float(d["elegido"]), "descartado": float(d["descartado"])})
    return out


def kpis(con) -> Dict[Tuple[str, int], Optional[float]]:
    cur = con.cursor()
    cur.execute("SELECT codigo, gestion, valor FROM bi.vw_cmi_valores WHERE codigo = ANY(%s)", (list(KPIS),))
    return {(c, int(g)): (None if v is None else float(v)) for c, g, v in cur.fetchall()}


# ── KPI independientes sobre la fuente ────────────────────────────────

def kpi_independiente(resuelto: Dict[Tuple[str, int, int], Dict[str, Any]]) -> Dict[Tuple[str, int], Optional[float]]:
    """KPI-02, 03, 12, 13 y 14 por gestión con las reglas de la 026, desde la tabla resuelta de la FUENTE (no de la DW)."""
    ejec: Dict[Tuple[int, int], float] = defaultdict(float)
    meta_m: Dict[Tuple[int, int], float] = defaultdict(float)
    meta_a: Dict[int, float] = defaultdict(float)
    for (cat, g, m), c in resuelto.items():
        ejec[(g, m)] += c["monto_ejecutado"] or 0.0
        if c["monto_meta"] is not None:
            if c["granularidad"] == "ANUAL":
                meta_a[g] += c["monto_meta"]
            else:
                meta_m[(g, m)] += c["monto_meta"]
    corte = max((g * 100 + m for (g, m), v in ejec.items() if v > 0), default=None)
    cerrado = lambda g, m: ejec[(g, m)] > 0 and (g * 100 + m != corte or m == 12)
    res: Dict[Tuple[str, int], Optional[float]] = {}
    for g in sorted({g for g, _ in ejec} | set(meta_a)):
        meses = [m for m in range(1, 13) if (g, m) in ejec]
        cerr = [m for m in meses if cerrado(g, m)]
        e_tot, e_cer = sum(ejec[(g, m)] for m in meses), sum(ejec[(g, m)] for m in cerr)
        meta_anual = sum(meta_m[(g, m)] for m in range(1, 13)) + meta_a[g]
        a_la_fecha = sum(meta_m[(g, m)] for m in cerr) + meta_a[g]
        ult = max(cerr, default=None)
        res[("KPI-02", g)] = (100.0 * ejec[(g, ult)] / meta_m[(g, ult)]) if ult and meta_m[(g, ult)] else None
        res[("KPI-03", g)] = (100.0 * e_cer / a_la_fecha) if a_la_fecha else None
        previos = [m for m in cerr if (g - 1, m) in ejec]
        base = sum(ejec[(g - 1, m)] for m in cerr)
        res[("KPI-12", g)] = (100.0 * (sum(ejec[(g, m)] for m in cerr) / base - 1)) if base and (g - 1) in {x for x, _ in ejec} else None
        res[("KPI-13", g)] = (100.0 * e_tot / meta_anual) if meta_anual else None
        if meta_anual > 0:
            res[("KPI-14", g)] = max(meta_anual - e_tot, 0.0)
    return res


# ── Salidas ───────────────────────────────────────────────────────────

def escribir(nombre: str, cabecera: List[str], filas: List[List[Any]]) -> Path:
    ruta = SALIDA / nombre
    with open(ruta, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cabecera)
        w.writerows(filas)
    return ruta


def num(v: Any) -> Any:
    return "" if v is None else (round(float(v), 2) if isinstance(v, (int, float)) else v)


def main() -> int:
    from services import metas_canonica, metas_cobertura
    ap = argparse.ArgumentParser()
    ap.add_argument("--libro", action="append", required=True, help="<ruta>::<TIPO sugerido> (el tipo final sale del contenido si es genérico)")
    ap.add_argument("--tmpfs", required=True)
    ap.add_argument("--inverso", default=None)
    ap.add_argument("--viva-env", default="FU_L6_VIVA_URL")
    a = ap.parse_args()
    if not _aislada(a.tmpfs) or (a.inverso and not _aislada(a.inverso)):
        raise SystemExit("--tmpfs e --inverso deben apuntar a una copia aislada (127.0.0.1:554xx)")

    # Fuente
    libros, plan = [], []
    for spec in a.libro:
        ruta, _, tipo = spec.partition("::")
        info = leer_libro(ruta, tipo or None)
        if info["hojas"]:
            libros.append(info)
        elif (info["tipo"] or "") == "PLANIFICACION":
            plan.append(info)
    por_tipo = fuente_por_tipo(libros)
    tipos = sorted(por_tipo)
    claves = sorted({c for d in por_tipo.values() for c in d}, key=lambda k: (k[1], k[2], k[0]))

    con = conectar(a.tmpfs, True)
    dw = leer_dw(con)

    # 1. Fuente vs DW (fact_rentabilidad)
    filas, difs, iguales, explicadas = [], 0, 0, 0
    resuelto: Dict[Tuple, Dict[str, Any]] = {}
    for clave in claves:
        cat, g, m = clave
        meta_v, meta_t, meta_g = esperado("monto_meta", por_tipo, clave)
        ejec_v, ejec_t, _ = esperado("monto_ejecutado", por_tipo, clave)
        resuelto[clave] = {"monto_meta": meta_v, "monto_ejecutado": ejec_v, "granularidad": meta_g}
        d = dw.get(clave, {"monto_meta": None, "monto_ejecutado": None, "granularidad": None})
        for campo, valor, tipo_ok, gran in (("monto_meta", meta_v, meta_t, meta_g), ("monto_ejecutado", ejec_v, ejec_t, None)):
            if valor is None and all(por_tipo[t].get(clave, {}).get(campo) is None for t in tipos) and d[campo] is None:
                continue
            vdw = d[campo]
            dif = None if (valor is None or vdw is None) else round(vdw - valor, 2)
            if (valor is None) != (vdw is None):
                dif, estado, expl = None, "DIFERENTE", "falta en la DW o en la fuente"
                difs += 1
            elif dif is not None and abs(dif) <= TOLERANCIA:
                dif, estado = 0.0, "IGUAL"
                expl = ""
                iguales += 1
            else:
                estado, expl = "DIFERENTE", ""
                difs += 1
            valores = {t: por_tipo[t].get(clave, {}).get(campo) for t in tipos}
            distintos = [v for v in valores.values() if v is not None]
            if estado == "IGUAL" and len({round(v, 2) for v in distintos}) > 1:
                explicadas += 1
                expl = f"las fuentes difieren; se carga la de mayor prioridad ({tipo_ok})"
            gdw = d["granularidad"] if campo == "monto_meta" else ""
            if campo == "monto_meta" and valor is not None and gran != gdw:
                estado, expl = "DIFERENTE", "granularidad distinta"
                difs += 1
            filas.append(["fact_rentabilidad", cat, g, m, campo] + [num(valores[t]) for t in tipos] +
                         [tipo_ok or "", num(valor), gran or "" if campo == "monto_meta" else "", num(vdw), gdw or "", "" if dif is None else dif, estado, expl])
    sobrantes = sorted(set(dw) - set(claves), key=lambda k: (k[1], k[2], k[0]))
    for clave in sobrantes:   # filas de la DW que ninguna fuente trae
        difs += 1
        filas.append(["fact_rentabilidad", clave[0], clave[1], clave[2], "(fila)"] + [""] * len(tipos) + ["", "", "", "", "", "", "DIFERENTE", "fila de la DW sin fuente"])
    cab = ["serie", "categoria", "gestion", "mes", "campo"] + [f"valor_fuente_{t}" for t in tipos] + \
          ["fuente_elegida_por_tipo", "valor_esperado", "granularidad_fuente", "valor_dw_tmpfs", "granularidad_dw", "diferencia", "estado", "explicacion"]

    # Metas de planificación (informe de gestión -> dim_meta): una sola fuente, sin prioridad
    plan_metas = [mt for info in plan for mt in metas_de_planificacion(info)]
    if plan_metas:
        dm = leer_dim_meta(con)
        origen: Dict[Tuple[str, int, int], float] = {}
        for mt in plan_metas:
            origen[(mt["categoria"], int(mt["gestion"]), int(mt["mes"]))] = float(mt["monto_meta"])
        meses_por_serie: Dict[Tuple[str, int], int] = defaultdict(int)
        for (c, g, m) in origen:
            meses_por_serie[(c, g)] += 1
        for clave in sorted(origen, key=lambda k: (k[1], k[2], k[0])):
            c, g, m = clave
            gran = "MENSUAL" if meses_por_serie[(c, g)] >= int(metas_canonica._seccion("granularidad").get("min_meses_mensual", 2)) else "ANUAL"
            vdw = dm.get(clave)
            ok = vdw is not None and abs(vdw - origen[clave]) <= TOLERANCIA
            iguales += int(ok)
            difs += int(not ok)
            filas.append(["dim_meta"] + [c, g, m, "monto_meta"] + [""] * len(tipos) +
                         ["PLANIFICACION", num(origen[clave]), gran, num(vdw), "(sin columna: informe mensual)",
                          "" if vdw is None else round(vdw - origen[clave], 2), "IGUAL" if ok else "DIFERENTE", ""])
        extra_dw = len(set(dm) - set(origen))
        if extra_dw:
            difs += extra_dw
            filas.append(["dim_meta", "", "", "", "monto_meta"] + [""] * len(tipos) + ["", "", "", "", "", extra_dw, "DIFERENTE", "metas de la DW que no están en la fuente"])
    escribir("fu_l6_metas_fuente_vs_dw.csv", cab, filas)

    # 2. Conflictos
    conf = leer_conflictos(con)
    inv = None
    if a.inverso:
        con_inv = conectar(a.inverso, True)
        inv = {(c["campo"], c["categoria"], c["gestion"], c["mes"]): (c["elegido"], c["descartado"]) for c in leer_conflictos(con_inv)
               if c["estado"] == "RESUELTO_REGLA"}
        dw_inv = leer_dw(con_inv)
        con_inv.close()
    filas_c = []
    for c in sorted(conf, key=lambda x: (x["gestion"] or 0, x["mes"] or 0, x["campo"], x["categoria"])):
        dif = None if c["elegido"] is None else round(abs(c["elegido"] - c["descartado"]), 2)
        misma = ""
        if inv is not None and c["estado"] == "RESUELTO_REGLA":
            misma = "si" if inv.get((c["campo"], c["categoria"], c["gestion"], c["mes"])) == (c["elegido"], c["descartado"]) else "no"
        filas_c.append([f"{c['gestion']}-{int(c['mes']):02d}" if c["gestion"] else "", c["campo"], c["categoria"], c["elegida"], c["descartada"],
                        num(c["elegido"]), num(c["descartado"]), "" if dif is None else dif,
                        "SI" if (dif is not None and metas_canonica.es_multiplo_de_aviso(dif)) else "NO", c["estado"], misma])
    escribir("fu_l6_conflictos_metas.csv",
             ["mes", "campo", "categoria", "fuente_elegida_por_tipo", "fuente_descartada_por_tipo", "valor_elegido", "valor_descartado", "diferencia",
              "avisar_area_financiera_multiplo_100000", "estado", "mismo_resultado_orden_inverso"], filas_c)

    # Conflictos esperados desde la fuente: pares de tipos distintos con otra cifra (ambas distintas de cero)
    esperados_conf = 0
    for clave in claves:
        for campo in CAMPOS:
            vals = [(t, por_tipo[t][clave][campo]) for t in tipos if clave in por_tipo[t] and por_tipo[t][clave][campo] not in (None, 0)]
            if len(vals) >= 2:
                mayor = max(vals[0][1], vals[1][1])
                if abs(vals[0][1] - vals[1][1]) > max(1.0, 0.01 * abs(mayor)):
                    esperados_conf += 1

    # 3. KPI antes y después
    url_viva = os.environ.get(a.viva_env)
    viva = {}
    if url_viva:
        cv = conectar(url_viva, True)
        viva = kpis(cv)
        cv.rollback()
        cv.close()
    despues = kpis(con)
    indep = kpi_independiente(resuelto)
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    with Session(create_engine(a.tmpfs)) as s:
        filas_k = []
        for kpi in KPIS:
            for g in sorted({g for (k, g) in list(viva) + list(despues) if k == kpi}):
                antes, desp = viva.get((kpi, g)), despues.get((kpi, g))
                nota = ""
                if kpi == "KPI-02" and desp is None:
                    nota = "sin dato: " + (metas_cobertura.motivo_sin_dato_kpi02(s, g) or "")
                dif = None if (antes is None or desp is None) else round(desp - antes, 2)
                filas_k.append([kpi, g, num(antes), num(desp), "" if dif is None else dif, num(indep.get((kpi, g))), nota])
    escribir("fu_l6_kpi_antes_despues.csv", ["kpi", "gestion", "antes_dw_viva", "despues_tmpfs", "diferencia", "fuente_independiente", "nota"], filas_k)

    resumen = {
        "tipos_de_fuente_con_metas": tipos,
        "filas_comparadas_fact_rentabilidad": sum(1 for f in filas if f[0] == "fact_rentabilidad"),
        "filas_comparadas_dim_meta": sum(1 for f in filas if f[0] == "dim_meta"),
        "iguales": iguales, "diferentes": difs, "iguales_con_fuentes_en_conflicto": explicadas,
        "conflictos_esperados_desde_la_fuente": esperados_conf,
        "conflictos_en_la_dw_resueltos_por_regla": sum(1 for c in conf if c["estado"] == "RESUELTO_REGLA"),
        "conflictos_en_la_dw_pendientes": sum(1 for c in conf if c["estado"] == "PENDIENTE"),
        "conflictos_con_diferencia_multiplo_100000": sum(1 for f in filas_c if f[8] == "SI"),
        "orden_inverso": None if inv is None else {
            "mismos_conflictos": sum(1 for f in filas_c if f[10] == "si"), "distintos": sum(1 for f in filas_c if f[10] == "no"),
            "fact_rentabilidad_identica": dw_inv == dw},
    }
    (SALIDA / "fu_l6_resumen.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(resumen, ensure_ascii=False, indent=1))
    con.rollback()
    con.close()
    return 0 if difs == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
