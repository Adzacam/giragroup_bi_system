"""
FU-L4 · Compara el libro de actas con la DW de la copia tmpfs y mide KPI-07, KPI-08 y KPI-16 antes y después.

Dos salidas, sin datos personales (solo conteos y cifras por gestión):
  docs/mediciones/fu_l4_arca_fuente_vs_dw.csv     metrica, anio, fuente, dw_tmpfs, diferencia, explicacion
  docs/mediciones/fu_l4_kpi_antes_despues.csv     kpi, gestion, antes_dw_viva, despues_tmpfs, diferencia, fuente_independiente, nota

La columna de la FUENTE sale del libro con el catálogo de sinónimos (`config/mapeo_fuentes.yaml`): la hoja del acta es la que
trae columnas de nota de módulo y estado académico (se decide por contenido, no por nombre). Los conteos de números y ceros se
calculan aquí aparte de la carga; el texto de las celdas usa el vocabulario del catálogo.

Uso (host, sin docker; la copia tmpfs ya recargada con el libro):
    python scripts/auditoria_fuentes/fu_l4_comparar_fuente_vs_dw.py --acta "<libro de actas.xlsx>" \
        --tmpfs postgresql://giragroup_user:tmpfs_local@127.0.0.1:55439/giragroup_db [--viva <url de la DW viva: SOLO LECTURA>]

Garantías: --tmpfs se niega a correr si el host no es 127.0.0.1/localhost:554xx; --viva se abre en una transacción READ ONLY y
solo ejecuta SELECT. Las URL se reciben por argumento: no se escriben en ningún archivo.
"""
from __future__ import annotations

import argparse
import collections
import csv
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(RAIZ), str(RAIZ / "backend")]
SALIDA = RAIZ / "docs" / "mediciones"


def _vacia(v) -> bool:
    return v is None or (isinstance(v, str) and not v.strip()) or (isinstance(v, float) and v != v)


def _texto(v):
    if _vacia(v):
        return None
    if isinstance(v, float) and v == int(v):
        return str(int(v))
    return str(v).strip()


def leer_filas_acta(ruta: str):
    """[(campos {cabecera normalizada: texto})] de las hojas visibles de la tabla de actas, elegidas por contenido."""
    import openpyxl
    from services import acta_canonica as ac
    from services.extraccion_por_encabezado import normalizar_encabezado
    wb = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
    filas = []
    for ws in wb.worksheets:
        if ws.sheet_state != "visible":
            continue
        datos = list(ws.iter_rows(values_only=True))
        for i in range(min(5, len(datos))):
            cabs = [normalizar_encabezado(str(c)) if c is not None else "" for c in datos[i]]
            mapeadas = [ac.campo_de_cabecera(c) for c in cabs if c]
            if sum(1 for m in mapeadas if m and m[0] == "nota_modulo") >= 3 and any(m and m[0] == "estado_academico" for m in mapeadas):
                for fila in datos[i + 1:]:
                    campos = {c: _texto(v) for c, v in zip(cabs, fila) if c and _texto(v) is not None}
                    if ac.valor_de_campo(campos, "ci") or ac.valor_de_campo(campos, "pos") or campos.get("NOMBRES"):
                        filas.append(campos)
                break
    return filas


def _gestion(campos):
    from services.extraccion_por_encabezado import fecha_de_fila
    f = fecha_de_fila(campos, "academico")
    return f.year if f else None


def _clave_estudiante(campos):
    from services import acta_canonica as ac
    num, _ = ac.separar_ci(ac.valor_de_campo(campos, "ci"))
    if num:
        return "CI:" + num
    nombre = " ".join(" ".join(campos.get(k, "") for k in ("NOMBRES", "APELLIDO PATERNO", "APELLIDO MATERNO")).upper().split())
    return "N:" + nombre if nombre.strip() else "F:" + str(id(campos))


def fuente(filas):
    from services import acta_canonica as ac
    from services.extraccion_por_encabezado import estados_de_fila
    m = collections.Counter()
    ultimo = {}          # (estudiante, pos) -> estados de la última fila (el hecho se reescribe por clave estudiante x módulo)
    est_gestion = collections.defaultdict(set)
    desertores = collections.defaultdict(set)
    desercion_sola = collections.defaultdict(set)
    ci_comp = 0
    celdas_por_par = collections.defaultdict(int)
    for campos in filas:
        anio = _gestion(campos)
        e = estados_de_fila(campos)
        des = ac.es_desercion(e["estado_academico"], e["estado_tutoria"])
        clave = (_clave_estudiante(campos), campos.get("POS - ACTAS") or ac.valor_de_campo(campos, "pos"))
        ultimo[clave] = (anio, e["estado_academico"], e["estado_tutoria"], des)
        est_gestion[anio].add(clave[0])
        if des:
            desertores[anio].add(clave[0])
        if ac.codigo_estado(e["estado_academico"]) == "DESERCION":
            desercion_sola[anio].add(clave[0])
        if ac.separar_ci(ac.valor_de_campo(campos, "ci"))[1]:
            ci_comp += 1
        for n, valor in ac.columnas_modulo(campos).items():
            c = ac.leer_celda(valor)
            if c.clase == "VACIA":
                continue
            m["celdas"] += 1
            celdas_por_par[clave] += 1
            if c.clase == "NUMERO":
                if c.numero == 0 and des:
                    m["ceros_inasistencia"] += 1
                elif c.numero == 0:
                    m["ceros_reales"] += 1
                else:
                    m["numericas_no_cero"] += 1
            elif c.clase == "TEXTO":
                m["texto_" + c.resultado] += 1
            elif c.clase == "FUERA_DE_RANGO":
                m["fuera_de_rango"] += 1
            else:
                m["fuera_de_catalogo"] += 1
    return {"m": m, "ultimo": ultimo, "est_gestion": est_gestion, "desertores": desertores, "desercion_sola": desercion_sola,
            "ci_comp": ci_comp, "n_filas": len(filas), "celdas_por_par": celdas_por_par}


def _conectar(url: str, solo_lectura: bool):
    import psycopg2
    con = psycopg2.connect(url, connect_timeout=5)
    if solo_lectura:
        con.set_session(readonly=True, autocommit=False)
    return con


def _verificar_tmpfs(url: str):
    if not re.search(r"@(127\.0\.0\.1|localhost):554\d\d/", url):
        raise SystemExit("--tmpfs debe apuntar a una copia tmpfs aislada (127.0.0.1:554xx)")


def dw(url: str):
    con = _conectar(url, True)
    cur = con.cursor()
    q = lambda sql, p=None: (cur.execute(sql, p or ()), cur.fetchall())[1]   # noqa: E731
    pos = "split_part(m.pos_code, '-M', 1)"   # programa del módulo (los módulos con nombre de catálogo conservan su pos_code)
    base = (f"FROM fact_rendimiento_academico f LEFT JOIN dim_tiempo t ON t.id_tiempo = f.id_tiempo "
            f"JOIN dim_modulo m ON m.id_modulo = f.id_modulo")
    out = {
        "estados": q(f"SELECT t.gestion, f.estado_academico, COUNT(DISTINCT (f.id_estudiante, {pos})) {base} GROUP BY 1, 2"),
        "tutoria": q(f"SELECT t.gestion, f.estado_tutoria, COUNT(DISTINCT (f.id_estudiante, {pos})) {base} GROUP BY 1, 2"),
        "hechos": q("SELECT COUNT(*) FROM fact_rendimiento_academico")[0][0],
        "resultados": dict(q("SELECT COALESCE(resultado, 'NULO'), COUNT(*) FROM fact_rendimiento_academico GROUP BY 1")),
        "con_nota": q("SELECT COUNT(*) FROM fact_rendimiento_academico WHERE nota_final IS NOT NULL")[0][0],
        "cero_real": q("SELECT COUNT(*) FROM fact_rendimiento_academico WHERE nota_final = 0")[0][0],
        "texto_por_resultado": dict(q("SELECT resultado, COUNT(*) FROM fact_rendimiento_academico WHERE nota_final IS NULL AND resultado IS NOT NULL GROUP BY 1")),
        "inasistencia_total": q("SELECT COUNT(*) FROM fact_rendimiento_academico WHERE resultado = 'INASISTENCIA'")[0][0],
        "avisos": dict(q("SELECT tipo_regla, COALESCE(SUM((regexp_match(descripcion, 'FU-L4: (\\d+) celda'))[1]::int), 0) FROM log_inconsistencias "
                         "WHERE tipo_regla IN ('NOTA_FUERA_DE_RANGO', 'CERO_COMO_INASISTENCIA') OR (tipo_regla = 'VALOR_FUERA_DE_CATALOGO' AND campo_afectado = 'nota_modulo') GROUP BY 1")),
        "est_gestion": dict(q(f"SELECT t.gestion, COUNT(DISTINCT f.id_estudiante) {base} GROUP BY 1")),
        "ci_comp_estudiantes": q("SELECT COUNT(*) FROM dim_estudiante e WHERE e.ci_complemento IS NOT NULL AND EXISTS "
                                 "(SELECT 1 FROM fact_rendimiento_academico f WHERE f.id_estudiante = e.id_estudiante)")[0][0],
        "ci_pegado": q("SELECT COUNT(*) FROM dim_estudiante e WHERE e.ci_numero ~ '^[0-9]{7,9}[A-Za-z]' ")[0][0],
        "hechos_por_par": q(f"SELECT COUNT(*) FROM (SELECT 1 {base} GROUP BY f.id_estudiante, {pos}) x")[0][0],
        "kpi": q("SELECT gestion, codigo, valor FROM bi.vw_cmi_valores WHERE codigo IN ('KPI-07', 'KPI-08', 'KPI-16')"),
    }
    out["staging"] = [r[0] for r in q(
        "SELECT payload_json->>'raw_line' FROM stg_entidad_no_resuelta WHERE payload_json ? 'raw_line' AND id_documento = "
        "(SELECT MAX(id_documento) FROM dim_origen_documental WHERE tipo_fuente = 'ACTA')")]
    norm = lambda col: f"upper(translate(COALESCE(f.{col}, ''), 'ÁÉÍÓÚáéíóú', 'AEIOUaeiou'))"   # noqa: E731
    out["des_todos"] = dict(q(f"SELECT t.gestion, COUNT(DISTINCT f.id_estudiante) {base} WHERE {norm('estado_academico')} IN ('DESERCION', 'ABANDONO') "
                              f"OR {norm('estado_tutoria')} IN ('DESERCION', 'ABANDONO') GROUP BY 1"))
    out["staging_motivos"] = q(
        "SELECT motivo, COUNT(*) FROM stg_entidad_no_resuelta WHERE id_documento = "
        "(SELECT MAX(id_documento) FROM dim_origen_documental WHERE tipo_fuente = 'ACTA') GROUP BY 1 ORDER BY 2 DESC")
    out["des_unicos"] = q(
        f"SELECT t.gestion, COUNT(DISTINCT f.id_estudiante) {base} WHERE upper(translate(COALESCE(f.estado_academico,''), 'ÁÉÍÓÚáéíóú', 'AEIOUaeiou')) = 'DESERCION' GROUP BY 1")
    con.rollback()
    con.close()
    return out


def kpi_vivo(url: str):
    con = _conectar(url, True)
    cur = con.cursor()
    cur.execute("SELECT gestion, codigo, valor FROM bi.vw_cmi_valores WHERE codigo IN ('KPI-07', 'KPI-08', 'KPI-16')")
    filas = cur.fetchall()
    con.rollback()
    con.close()
    return {(int(g), c): (None if v is None else float(v)) for g, c, v in filas}


def _canon(valor):
    from services import acta_canonica as ac
    return ac._normalizar(valor) if valor else None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--acta", required=True)
    ap.add_argument("--tmpfs", required=True)
    ap.add_argument("--viva")
    ap.add_argument("--tmpfs-previos", help="otra copia tmpfs que conserva los estudiantes del snapshot (solo para la tabla de KPI)")
    ap.add_argument("--sufijo", default="", help="sufijo del CSV de comparación (para la copia con estudiantes previos)")
    a = ap.parse_args(argv)
    _verificar_tmpfs(a.tmpfs)
    f = fuente(leer_filas_acta(a.acta))
    d = dw(a.tmpfs)
    m = f["m"]
    from services import acta_canonica as ac
    from services.extraccion_por_encabezado import campos_por_encabezado
    # Filas que el flujo derivó a revisión humana (índice de confianza < 0,60 o identidad no resuelta): están en staging, no en la DW
    en_rev = [c for c in (campos_por_encabezado([x.strip() for x in (ln or "").split("|")]) for ln in d["staging"])
              if ac.columnas_modulo(c) or ac.valor_de_campo(c, "estado_academico")]
    g_rev = fuente(en_rev)
    m_rev = g_rev["m"]
    m_rev["celdas_rev"] = m_rev["celdas"] - m_rev["fuera_de_rango"] - m_rev["fuera_de_catalogo"]
    filas = []

    def fila(metrica, anio, fte, dw_v, expl=""):
        dif = None if (fte is None or dw_v is None) else dw_v - fte
        filas.append([metrica, anio, fte, dw_v, dif, expl])

    # Estados por gestión: pares estudiante-programa (la última fila de un par repetido manda) = DW + filas en revisión humana
    from services.extraccion_por_encabezado import estados_de_fila  # noqa: F401
    por_estado = collections.Counter((u[0], _canon(u[1])) for u in f["ultimo"].values())
    rev_estado = collections.Counter((u[0], _canon(u[1])) for u in g_rev["ultimo"].values())
    dw_estado = collections.Counter()
    for g, e, n in d["estados"]:
        dw_estado[(int(g) if g else None, _canon(e))] += n
    for (g, e) in sorted(set(por_estado) | set(dw_estado), key=lambda x: (str(x[0]), str(x[1]))):
        fte, dwv, rv = por_estado.get((g, e), 0), dw_estado.get((g, e), 0), rev_estado.get((g, e), 0)
        fila(f"estado_academico[{e}]", g, fte, dwv, f"en revisión humana (staging): {rv}; residuo tras sumarlas: {dwv + rv - fte}")
    por_tut = collections.Counter((u[0], _canon(u[2])) for u in f["ultimo"].values())
    rev_tut = collections.Counter((u[0], _canon(u[2])) for u in g_rev["ultimo"].values())
    dw_tut = collections.Counter()
    for g, e, n in d["tutoria"]:
        dw_tut[(int(g) if g else None, _canon(e))] += n
    for (g, e) in sorted(set(por_tut) | set(dw_tut), key=lambda x: (str(x[0]), str(x[1]))):
        fte, dwv, rv = por_tut.get((g, e), 0), dw_tut.get((g, e), 0), rev_tut.get((g, e), 0)
        fila(f"estado_tutoria[{e}]", g, fte, dwv, f"en revisión humana (staging): {rv}; residuo tras sumarlas: {dwv + rv - fte}")
    fila("filas_fuente_vs_pares_estudiante_programa", "todos", f["n_filas"], len(f["ultimo"]),
         "la diferencia son filas repetidas (mismo estudiante y programa): la fuente cuenta filas, la DW un hecho por estudiante y módulo")
    for motivo_stg, n_stg in d["staging_motivos"]:
        fila(f"revision_humana_por_motivo[{motivo_stg}]", "todos", None, n_stg,
             "casos que la cascada de identidad (invariante, sin cambios) no resolvió y dejó en staging; explican el residuo de estados y notas")
    fila("filas_en_revision_humana", "todos", None, len(en_rev), "filas del acta que el flujo dejó en staging (confianza < 0,60 o identidad no resuelta); no están en la DW")

    # Notas y resultados por módulo
    r, t = d["resultados"], d["texto_por_resultado"]
    cero_ina = d["avisos"].get("CERO_COMO_INASISTENCIA", 0)
    ina_texto_dw = t.get("INASISTENCIA", 0) - cero_ina
    def met(nombre, fte_v, dwv, clave_rev, expl):
        rv = m_rev[clave_rev] if isinstance(clave_rev, str) else sum(m_rev[c] for c in clave_rev)
        fila(nombre, "todos", fte_v, dwv, f"{expl}; en revisión humana (staging): {rv}; residuo tras sumarlas: {dwv + rv - fte_v}")
    met("celdas_de_nota_con_valor_sin_dudosas", m["celdas"] - m["fuera_de_rango"] - m["fuera_de_catalogo"], d["hechos"],
        "celdas_rev", "un hecho por celda con nota o resultado; las celdas fuera de rango o de catálogo no generan hecho; en filas repetidas se reescribe (estudiante x módulo único)")
    met("notas_numericas_validas_mayores_de_0", m["numericas_no_cero"], d["con_nota"] - d["cero_real"], "numericas_no_cero", "nota_final no nula sin los ceros reales")
    met("ceros_reales", m["ceros_reales"], d["cero_real"], "ceros_reales", "0 sin estado Deserción ni Abandono: nota_final = 0, REPROBADO")
    met("ceros_como_inasistencia", m["ceros_inasistencia"], cero_ina, "ceros_inasistencia",
        "0 con estado Deserción o Abandono: resultado INASISTENCIA, nota_final NULL (aviso agregado CERO_COMO_INASISTENCIA)")
    met("inasistencia_por_texto", m["texto_INASISTENCIA"], ina_texto_dw, "texto_INASISTENCIA", "«No asistió», «Nunca ingresó», «Faltas y no envió»…")
    met("aprobado_por_texto", m["texto_APROBADO"], t.get("APROBADO", 0), "texto_APROBADO", "«Aprobó»")
    met("eximido", m["texto_EXIMIDO"], t.get("EXIMIDO", 0), "texto_EXIMIDO", "«EXIMIDA»")
    met("sin_nota", m["texto_SIN_NOTA"], t.get("SIN_NOTA", 0), "texto_SIN_NOTA", "«SIN NOTAS EN EL ACTA…» y comentarios equivalentes")
    met("notas_fuera_de_rango_a_revision", m["fuera_de_rango"], d["avisos"].get("NOTA_FUERA_DE_RANGO", 0), "fuera_de_rango",
        "números mayores de 100 (en el acta real son CI pegados): nota NULL, aviso agregado sin el valor")
    met("texto_fuera_de_catalogo_a_revision", m["fuera_de_catalogo"], d["avisos"].get("VALOR_FUERA_DE_CATALOGO", 0), "fuera_de_catalogo",
        "apellidos y comentarios fuera del vocabulario: nota NULL, aviso agregado sin el texto")

    # CI con complemento
    fila("filas_con_ci_con_complemento_o_ciudad", "todos", f["ci_comp"], d["ci_comp_estudiantes"],
         "fuente: filas; DW: estudiantes distintos con ci_complemento (varias filas pueden ser la misma persona)")
    fila("estudiantes_con_complemento_pegado_al_numero", "todos", 0, d["ci_pegado"], "ci_numero con letras pegadas al número (antes: '48920191C')")

    # Matrícula y KPI-16 (independiente de la vista)
    kpi_f = {}
    for g in sorted(k for k in f["est_gestion"] if k):
        mat = len(f["est_gestion"][g])
        des = len(f["desertores"][g])
        solo = len(f["desercion_sola"][g])
        kpi_f[g] = 100.0 * des / mat
        fila("matricula_estudiantes_distintos", g, mat, d["est_gestion"].get(g, 0),
             "estudiantes sin CI se identifican por nombre; las que la cascada no resuelve van a revisión y no entran a la DW")
        fila("desertores_y_abandono_estudiantes_distintos", g, des, d["des_todos"].get(g),
             f"KPI-16 fuente independiente (sobre la matrícula de la fuente) = {100.0 * des / mat:.2f} %")
        fila("solo_desercion_estudiantes_distintos", g, solo, dict(d["des_unicos"]).get(g),
             f"solo el estado académico Deserción (sin Abandono de tutoría): {100.0 * solo / mat:.2f} % de la matrícula de la fuente")

    # KPI antes / después
    vivo = kpi_vivo(a.viva) if a.viva else {}
    despues = {(int(g), c): (None if v is None else float(v)) for g, c, v in d["kpi"]}
    if a.tmpfs_previos:
        _verificar_tmpfs(a.tmpfs_previos)
        previos = {(int(g), c): (None if v is None else float(v)) for g, c, v in dw(a.tmpfs_previos)["kpi"]}
    else:
        previos = {}
    kfilas = []
    for c in ("KPI-07", "KPI-08", "KPI-16"):
        for g in sorted({k[0] for k in list(vivo) + list(despues) if k[1] == c}):
            ant, des = vivo.get((g, c)), despues.get((g, c))
            ind = kpi_f.get(g) if c == "KPI-16" else None
            nota = {"KPI-07": "promedio de notas numéricas (el 0 real entra; inasistencia, eximidos y sin nota no)",
                    "KPI-08": "aprobados / (aprobados + reprobados + inasistencias); eximidos y sin nota fuera",
                    "KPI-16": "estudiantes con Deserción o Abandono / matrícula de la gestión; sin dato si ninguna fuente trae el estado"}[c]
            kfilas.append([c, g, ant, des, None if ant is None or des is None else round(des - ant, 4),
                           None if ind is None else round(ind, 4), previos.get((g, c)), nota])

    SALIDA.mkdir(parents=True, exist_ok=True)
    with open(SALIDA / f"fu_l4_arca_fuente_vs_dw{a.sufijo}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["metrica", "anio", "fuente", "dw_tmpfs", "diferencia", "explicacion"])
        w.writerows(filas)
    if a.sufijo:
        print(f"filas fuente={f['n_filas']} filas csv={len(filas)}")
        return 0
    with open(SALIDA / "fu_l4_kpi_antes_despues.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["kpi", "gestion", "antes_dw_viva", "despues_tmpfs", "diferencia", "fuente_independiente",
                    "despues_tmpfs_con_estudiantes_previos", "nota"])
        w.writerows([[x if x is not None else "" for x in fl] for fl in kfilas])
    print(f"filas fuente={f['n_filas']} filas csv={len(filas)} kpi={len(kfilas)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
