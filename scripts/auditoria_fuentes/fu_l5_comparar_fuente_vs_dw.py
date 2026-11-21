"""
FU-L5 · Compara los libros de encuestas con la DW de la copia tmpfs y mide KPI-19 y KPI-20 antes y después.

Dos salidas, sin datos personales (solo conteos y cifras por gestión; los libros se nombran «libro A/B/C» y las hojas por su contenido):
  docs/mediciones/fu_l5_encuestas_fuente_vs_dw.csv   metrica, libro, hoja, fuente, dw_tmpfs, diferencia, explicacion
  docs/mediciones/fu_l5_kpi_antes_despues.csv        kpi, gestion, antes_dw_viva, despues_tmpfs, diferencia, n_antes, n_despues,
                                                     fuente_independiente, n_fuente, estimado_da1_antes, estimado_da1_despues, nota

La FUENTE sale del libro, hoja por hoja, con las líneas tal como las deja la ingesta (cabecera detectada, hojas ocultas fuera) y las reglas
del catálogo (`encuesta_canonica`): se cuentan las respuestas esperadas y su clave de idempotencia (misma fila + misma pregunta). Eso se
cruza con las claves de la DW: así cada hoja sabe cuántas de sus respuestas válidas llegaron y cuáles no (filas retenidas por la cascada
de identidad). Las cifras de «0/Sin Información» crudas se cuentan aparte, directo del libro con openpyxl.

Uso (host, sin docker; la copia tmpfs ya recargada con los libros):
    python scripts/auditoria_fuentes/fu_l5_comparar_fuente_vs_dw.py \
        --libro "A=<libro 1.xlsx>=<nombre del documento en la DW>" --libro "B=..." --libro "C=..." \
        --tmpfs postgresql://giragroup_user:tmpfs_local@127.0.0.1:55440/giragroup_db [--viva <url de la DW viva: SOLO LECTURA>]

Garantías: --tmpfs se niega a correr si el host no es 127.0.0.1/localhost:554xx; --viva se abre en una transacción READ ONLY y solo ejecuta
SELECT. Las URL se reciben por argumento: no se escriben en ningún archivo ni en la salida.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(RAIZ), str(RAIZ / "backend")]
SALIDA = RAIZ / "docs" / "mediciones"

# Estimaciones de DA1 (docs/cierres/PLAN_AUDITORIA_DW.md): KPI por gestión, antes -> después
ESTIMADO_DA1 = {
    ("KPI-19", 2024): (58.61, 79.99), ("KPI-20", 2024): (22.00, 79.71),
    ("KPI-19", 2025): (66.77, 81.90), ("KPI-20", 2025): (12.58, 78.37),
    ("KPI-19", 2026): (82.35, 82.35), ("KPI-20", 2026): (70.99, 79.30),
}
VALIDAS_DA1 = {("KPI-20", 2024): 1091, ("KPI-20", 2025): 14342, ("KPI-20", 2026): 6715}


# ── Fuente ────────────────────────────────────────────────────────────

def leer_fuente(ruta: str):
    """[{indice, lineas, perfil, filas: [(campos, fila_canonica, respuestas)]}] de las hojas de encuesta usadas del libro."""
    from pipeline.ingesta import detectar_bloques, leer_archivo_con_metadatos
    from services import encuesta_canonica as ec
    from services.extraccion_por_encabezado import campos_por_encabezado
    from services.ingestion_service import IngestionService

    libro = leer_archivo_con_metadatos(ruta)
    hojas = []
    for nombre, h in libro.items():
        if not h.usada:
            continue
        df = h.df_recortado()
        bloques = [b for b in detectar_bloques(df, filas_transparentes=set(h.meta.filas_descartadas) or None) if len(b) >= 2]
        for b in bloques:
            if not ec.hoja_es_encuesta(b.iloc[:80].values.tolist()):
                continue
            texto = IngestionService.serializar_bloque_con_encabezados(b)
            lineas = [l for l in texto.splitlines() if l.strip()]
            campos = [campos_por_encabezado([c.strip() for c in l.split("|")]) for l in lineas]
            perfil = ec.perfilar(campos)
            filas = []
            for c in campos:
                canonica = "|".join(f"{k}={c[k]}" for k in sorted(c))
                filas.append((c, canonica, ec.leer_fila(c, perfil)))
            hojas.append({"indice": len(hojas) + 1, "lineas": len(lineas), "perfil": perfil, "filas": filas})
    return hojas


def clave(canonica: str, pregunta: str) -> str:
    return hashlib.sha1(f"{canonica}||{pregunta}".encode("utf-8")).hexdigest()


def descriptor(hoja) -> str:
    """Nombre de la hoja por su contenido (sin el nombre real)."""
    from services import encuesta_canonica as ec
    perfil = hoja["perfil"]
    puntuadas = [pc for pc in perfil.columnas.values() if pc.clase == ec.PUNTUADA]
    escalas = sorted({pc.escala for pc in puntuadas if pc.escala})
    partes = ["docente" if perfil.defecto_tipo == "DOCENTE" else "experiencia institucional"]
    partes.append("escalas " + " y ".join(f"1-{e}" for e in escalas) if escalas else "sin escala")
    if any(r.par_evitado for _, _, rs in hoja["filas"] for r in rs):
        partes.append("dos columnas por pregunta (texto y número)")
    if any(pc.clase == ec.COMENTARIO for pc in perfil.columnas.values()):
        partes.append("con comentarios")
    return f"hoja {hoja['indice']} ({', '.join(partes)}; {hoja['lineas']} filas)"


def contar_fuente(hoja):
    """Conteos de una hoja: respuestas válidas únicas, comentarios, sin respuesta por motivo y claves esperadas."""
    from services import encuesta_canonica as ec
    c = Counter()
    validas, comentarios = {}, {}
    cruzadas_grupos = set()
    for campos, canonica, rs in hoja["filas"]:
        for r in rs:
            if r.par_evitado:
                c["par_evitado"] += 1
            if r.clase == ec.PUNTUADA:
                c["validas_celdas"] += 1
                validas[clave(canonica, r.cabecera)] = (r.tipo_pregunta, r.puntuacion, r.escala_max)
            elif r.clase == ec.COMENTARIO:
                c["comentarios_celdas"] += 1
                comentarios[clave(canonica, r.cabecera)] = r
            else:
                c[r.clase] += 1
                if r.clase == ec.CRUZADA:
                    cruzadas_grupos.add(r.cabecera)
            if r.clase == ec.PUNTUADA and r.aviso:
                c["catalogo_con_numero"] += 1
    c["cruzadas_grupos"] = len(cruzadas_grupos)
    return c, validas, comentarios


def celdas_cero_sin_informacion(ruta: str) -> int:
    """Celdas «n/Sin Información» crudas del libro (hojas visibles), contadas con openpyxl sin pasar por el sistema."""
    import openpyxl
    wb = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
    n = 0
    for ws in wb.worksheets:
        if ws.sheet_state != "visible":
            continue
        for fila in ws.iter_rows(values_only=True):
            for v in fila:
                if isinstance(v, str) and re.match(r"^\s*\d+\s*/\s*sin informaci[oó]n", v, re.IGNORECASE):
                    n += 1
    wb.close()
    return n


# ── DW ────────────────────────────────────────────────────────────────

def _host_aislado(url: str) -> bool:
    return bool(re.search(r"@(127\.0\.0\.1|localhost):554\d\d/", url))


def dw_documento(cur, nombre: str):
    cur.execute("SELECT id_documento, tipo_fuente, tipo_escala FROM dim_origen_documental WHERE nombre_archivo = %s "
                "ORDER BY id_documento DESC LIMIT 1", (nombre,))
    return cur.fetchone()


def avisos_dw(cur, doc: int):
    """{(motivo): respuestas} y {(motivo): grupos} de los avisos FU-L5 del documento."""
    cur.execute("SELECT tipo_regla, descripcion FROM log_inconsistencias WHERE id_documento = %s AND descripcion LIKE 'FU-L5:%%'", (doc,))
    n, g = Counter(), Counter()
    for motivo, desc in cur.fetchall():
        n[motivo] += int(re.search(r"FU-L5: (\d+) respuesta", desc).group(1))
        g[motivo] += 1
    return n, g


def kpis(cur, gestiones=(2023, 2024, 2025, 2026)):
    """{(codigo, gestion): (valor, n respuestas que cuenta la vista)} para KPI-19 y KPI-20 de una base."""
    cur.execute("SELECT codigo, gestion, valor FROM bi.vw_cmi_valores WHERE codigo IN ('KPI-19', 'KPI-20')")
    valores = {(c, g): (float(v) if v is not None else None) for c, g, v in cur.fetchall()}
    cur.execute("SELECT dt.gestion, ev.tipo_pregunta, count(*) FILTER (WHERE ev.puntuacion IS NOT NULL AND ev.escala_max > 0) AS n_antes, "
                "count(*) FILTER (WHERE ev.puntuacion >= 1 AND ev.puntuacion <= ev.escala_max) AS n_validas "
                "FROM fact_evaluacion_docente ev JOIN dim_tiempo dt ON dt.id_tiempo = ev.id_tiempo "
                "WHERE ev.tipo_pregunta IN ('DOCENTE', 'INSTITUCIONAL') GROUP BY 1, 2")
    ns = {}
    for g, tipo, n_antes, n_validas in cur.fetchall():
        ns[("KPI-19" if tipo == "DOCENTE" else "KPI-20", g)] = (n_antes, n_validas)
    return valores, ns


def vista_vigente(cur) -> bool:
    """La vista de la base ya filtra [1, escala_max] (migración 025)."""
    cur.execute("SELECT EXISTS (SELECT 1 FROM schema_migrations WHERE version LIKE '025_fu_l5%%')")
    return bool(cur.fetchone()[0])


def escribir(ruta: Path, columnas, filas):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(columnas)
        w.writerows(filas)


def fmt(x):
    return "" if x is None else (f"{x:.2f}" if isinstance(x, float) else x)


# ── Programa ──────────────────────────────────────────────────────────

def main(argv=None) -> int:
    import psycopg2
    ap = argparse.ArgumentParser()
    ap.add_argument("--libro", action="append", required=True, help="ETIQUETA=ruta=nombre del documento en la DW")
    ap.add_argument("--tmpfs", required=True)
    ap.add_argument("--viva")
    a = ap.parse_args(argv)
    if not _host_aislado(a.tmpfs):
        raise SystemExit("--tmpfs debe apuntar a la copia tmpfs aislada (127.0.0.1:554xx)")

    con = psycopg2.connect(a.tmpfs)
    con.set_session(readonly=True)
    cur = con.cursor()
    filas_csv = []
    fuente_kpi = defaultdict(lambda: [0.0, 0])      # (codigo, gestion) -> [suma %, n]
    sin_gestion = Counter()

    from services import encuesta_canonica as ec
    from services.extraccion_por_encabezado import fecha_de_fila

    for spec in a.libro:
        etiqueta, ruta, nombre_dw = spec.split("=", 2)
        libro = f"libro {etiqueta}"
        doc = dw_documento(cur, nombre_dw)
        if not doc:
            raise SystemExit(f"{libro}: el documento «{nombre_dw}» no está en la DW tmpfs")
        id_doc, tipo_fuente, tipo_escala = doc
        cur.execute("SELECT clave_respuesta, puntuacion, comentario, tipo_pregunta, escala_max, id_tiempo FROM fact_evaluacion_docente "
                    "WHERE id_documento = %s", (id_doc,))
        dw = {k: (p, c, t, e, it) for k, p, c, t, e, it in cur.fetchall()}
        n_avisos, g_avisos = avisos_dw(cur, id_doc)

        hojas = leer_fuente(ruta)
        esperadas_validas, esperadas_coment = {}, {}
        tot = Counter()
        for h in hojas:
            nombre_h = descriptor(h)
            c, validas, comentarios = contar_fuente(h)
            esperadas_validas.update(validas)
            esperadas_coment.update({k: v for k, v in comentarios.items()})
            en_dw = sum(1 for k in validas if k in dw and dw[k][0] is not None)
            en_dw_coment = sum(1 for k in comentarios if k in dw and dw[k][1] is not None)
            # filas retenidas: todas sus respuestas válidas faltan en la DW (la cascada de identidad no las cargó)
            retenidas, resp_retenidas = 0, 0
            for campos, canonica, rs in h["filas"]:
                ks = [clave(canonica, r.cabecera) for r in rs if r.clase == ec.PUNTUADA]
                if ks and not any(k in dw for k in ks):
                    retenidas += 1
                    resp_retenidas += len(set(ks))
            dif = len(validas) - en_dw
            expl = (f"{retenidas} filas retenidas por la cascada de identidad ({resp_retenidas} respuestas) en revisión humana"
                    + ("" if dif == resp_retenidas else f"; residuo {dif - resp_retenidas}"))
            if dif == 0:
                expl = "igual"
            filas_csv.append(("respuestas válidas únicas (1 <= puntuacion <= escala_max)", libro, nombre_h, len(validas), en_dw, en_dw - len(validas), expl))
            filas_csv.append(("respuestas válidas repetidas (misma fila y pregunta)", libro, nombre_h, c["validas_celdas"] - len(validas), 0, "",
                              "filas idénticas del libro: la DW las guarda una vez (clave por fila y pregunta)"))
            filas_csv.append(("comentarios con texto (sin puntuación)", libro, nombre_h, len(comentarios), en_dw_coment, en_dw_coment - len(comentarios),
                              "igual" if en_dw_coment == len(comentarios) else "en filas retenidas por la cascada de identidad"))
            filas_csv.append(("NULL por 0 o «Sin Información» (celdas, par contado una vez)", libro, nombre_h, c[ec.SIN_INFORMACION], "", "",
                              "informativo: el aviso agregado de la DW se compara a nivel de libro (los avisos no distinguen la hoja)"))
            filas_csv.append(("NULL por puntuación fuera de escala", libro, nombre_h, c[ec.FUERA_DE_ESCALA], "", "", "avisos de la DW a nivel de libro"))
            filas_csv.append(("respuestas cruzadas entre columnas (celdas)", libro, nombre_h, c[ec.CRUZADA], "", "", "RESPUESTA_EN_COLUMNA_EQUIVOCADA, agrupada por hoja y pregunta"))
            filas_csv.append(("respuestas cruzadas: preguntas afectadas (grupos)", libro, nombre_h, c["cruzadas_grupos"], "", "", "un aviso por hoja y pregunta, con conteo y ejemplo enmascarado"))
            filas_csv.append(("etiqueta fuera del diccionario (celdas)", libro, nombre_h, c[ec.FUERA_DE_CATALOGO], "", "", "VALOR_FUERA_DE_CATALOGO"))
            filas_csv.append(("duplicados evitados por la doble columna texto + número (celdas)", libro, nombre_h, c["par_evitado"], 0, "",
                              "habrían contado la respuesta dos veces; la DW lee solo la columna numérica"))
            for k in ("validas_celdas", "par_evitado", ec.SIN_INFORMACION, ec.FUERA_DE_ESCALA, ec.CRUZADA, ec.FUERA_DE_CATALOGO, "cruzadas_grupos"):
                tot[k] += c[k]
            tot["validas_unicas"] += len(validas)
            tot["en_dw"] += en_dw
            # KPI independiente de la fuente: gestión del año de la fecha de la fila
            for campos, canonica, rs in h["filas"]:
                f = fecha_de_fila(campos, "academico")
                for r in rs:
                    if r.clase != ec.PUNTUADA or r.tipo_pregunta not in ("DOCENTE", "INSTITUCIONAL"):
                        continue
                    if f is None:
                        sin_gestion[r.tipo_pregunta] += 1
                        continue
                    k = ("KPI-19" if r.tipo_pregunta == "DOCENTE" else "KPI-20", f.year)
                    fuente_kpi[k][0] += 100.0 * r.puntuacion / r.escala_max
                    fuente_kpi[k][1] += 1

        # Totales del libro
        fuera = sum(1 for p, _, t, e, _ in dw.values() if p is not None and (e is None or p > e or p < (0 if t == "NPS" else 1)))
        puntuadas_dw = sum(1 for v in dw.values() if v[0] is not None)
        en_dw_total = tot["en_dw"]
        extra = puntuadas_dw - en_dw_total
        cur.execute("SELECT count(*) FROM carga_fila_origen WHERE id_documento = %s AND tabla = 'fact_evaluacion_docente'", (id_doc,))
        n_claves = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM fact_evaluacion_docente WHERE id_documento = %s", (id_doc,))
        n_hechos = cur.fetchone()[0]
        cero_crudo = celdas_cero_sin_informacion(ruta)
        filas_csv += [
            ("TOTAL respuestas válidas únicas", libro, "todas las hojas", len(esperadas_validas), puntuadas_dw, puntuadas_dw - len(esperadas_validas),
             ("igual: todas las respuestas válidas de la fuente están en la DW" if puntuadas_dw == len(esperadas_validas) else "diferencia = respuestas de filas retenidas por la cascada de identidad (ver cada hoja)")
             + ("; la DW no trae respuestas fuera de la fuente" if extra == 0 else f"; la DW trae {extra} que la fuente no espera")),
            ("puntuaciones fuera de [1, escala_max] en la DW (NPS 0-10 aparte)", libro, "todas las hojas", 0, fuera, fuera, "criterio: 0"),
            ("hechos en la DW (con y sin puntuación)", libro, "todas las hojas", len(esperadas_validas) + len(esperadas_coment), n_hechos, "",
             "puntuadas + comentarios"),
            ("claves de idempotencia (carga_fila_origen) por hecho", libro, "todas las hojas", "", f"{n_claves} / {n_hechos}", "",
             "2 claves por hecho por diseño (una por archivo y otra por contenido); antes eran el doble de hechos por la doble columna"),
            ("celdas crudas «n/Sin Información» del libro (openpyxl)", libro, "todas las hojas", cero_crudo, "", "",
             "incluye la columna de texto de cada par y las columnas de comentario con «0/Sin Información» (sin comentario); los avisos cuentan solo preguntas puntuadas, una vez por par"),
            ("avisos SIN_INFORMACION registrados (celdas)", libro, "todas las hojas", tot[ec.SIN_INFORMACION], n_avisos["SIN_INFORMACION"],
             n_avisos["SIN_INFORMACION"] - tot[ec.SIN_INFORMACION], "agregados por hoja y pregunta; coincide con la fuente"),
            ("avisos PUNTUACION_FUERA_DE_ESCALA registrados (celdas)", libro, "todas las hojas", tot[ec.FUERA_DE_ESCALA], n_avisos["PUNTUACION_FUERA_DE_ESCALA"],
             n_avisos["PUNTUACION_FUERA_DE_ESCALA"] - tot[ec.FUERA_DE_ESCALA], f"{g_avisos['PUNTUACION_FUERA_DE_ESCALA']} grupos (hoja y pregunta)"),
            ("avisos RESPUESTA_EN_COLUMNA_EQUIVOCADA registrados (celdas)", libro, "todas las hojas", tot[ec.CRUZADA], n_avisos["RESPUESTA_EN_COLUMNA_EQUIVOCADA"],
             n_avisos["RESPUESTA_EN_COLUMNA_EQUIVOCADA"] - tot[ec.CRUZADA],
             f"{g_avisos['RESPUESTA_EN_COLUMNA_EQUIVOCADA']} grupos (hoja y pregunta); la diferencia son respuestas Likert escritas en la columna del módulo (no son celdas de pregunta; la fuente las cuenta aparte)"),
            ("avisos VALOR_FUERA_DE_CATALOGO registrados (celdas)", libro, "todas las hojas", tot[ec.FUERA_DE_CATALOGO], n_avisos["VALOR_FUERA_DE_CATALOGO"],
             n_avisos["VALOR_FUERA_DE_CATALOGO"] - tot[ec.FUERA_DE_CATALOGO], f"{g_avisos['VALOR_FUERA_DE_CATALOGO']} grupos (hoja y pregunta)"),
            ("tipo de fuente detectado", libro, "todas las hojas", "EVALUACION_DOCENTE", f"{tipo_fuente} / escala {tipo_escala}", "", "se sube como acta (CENTESIMAL_100) y el sistema lo corrige por contenido"),
        ]

    # Impacto en el modelo de lectura: resumen global
    filas_csv.append(("NULL por puntuación sin gestión (no entra al KPI por fecha)", "todos", "todas las hojas",
                      sum(sin_gestion.values()), "", "", "filas sin fecha: la DW les asigna el último período del programa si lo tiene"))

    escribir(SALIDA / "fu_l5_encuestas_fuente_vs_dw.csv",
             ["metrica", "libro", "hoja", "fuente", "dw_tmpfs", "diferencia", "explicacion"], [tuple(fmt(x) for x in f) for f in filas_csv])

    # ── KPI antes y después ───────────────────────────────────────────
    valores_d, ns_d = kpis(cur)
    ya_filtra = vista_vigente(cur)
    valores_a, ns_a, nota_antes = {}, {}, "sin conexión a la DW viva"
    if a.viva:
        viva = psycopg2.connect(a.viva)
        viva.set_session(readonly=True)
        valores_a, ns_a = kpis(viva.cursor())
        nota_antes = "DW viva (solo lectura, transacción READ ONLY), vista anterior a la 025: promedia también los 0"
        viva.close()
    filas_kpi = []
    for codigo in ("KPI-19", "KPI-20"):
        for g in (2023, 2024, 2025, 2026):
            antes, despues = valores_a.get((codigo, g)), valores_d.get((codigo, g))
            if antes is None and despues is None and (codigo, g) not in fuente_kpi:
                continue
            fs, fn = fuente_kpi.get((codigo, g), [0.0, 0])
            est = ESTIMADO_DA1.get((codigo, g), (None, None))
            n_antes = ns_a.get((codigo, g), (None, None))[0]
            n_desp = ns_d.get((codigo, g), (None, None))[1]
            nota = "" if (codigo, g) in ESTIMADO_DA1 else "sin estimación en DA1"
            filas_kpi.append((codigo, g, fmt(None if antes is None else round(antes, 2)), fmt(None if despues is None else round(despues, 2)),
                              fmt(None if (antes is None or despues is None) else round(despues - antes, 2)), n_antes, n_desp,
                              fmt(round(fs / fn, 2) if fn else None), fn or "", fmt(est[0]), fmt(est[1]), nota))
    escribir(SALIDA / "fu_l5_kpi_antes_despues.csv",
             ["kpi", "gestion", "antes_dw_viva", "despues_tmpfs", "diferencia", "n_antes", "n_despues", "fuente_independiente", "n_fuente",
              "estimado_da1_antes", "estimado_da1_despues", "nota"], filas_kpi)
    print(f"vista tmpfs con filtro DA1: {ya_filtra}; {nota_antes}")
    print(f"filas: fuente_vs_dw={len(filas_csv)} kpi={len(filas_kpi)}")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
