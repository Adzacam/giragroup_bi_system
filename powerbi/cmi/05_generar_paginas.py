"""Genera las 5 páginas del CMI dentro de un .pbix en formato PBIR.

Uso:  python 05_generar_paginas.py <entrada.pbix> <salida.pbix> [gestion_por_defecto]

Requiere que el modelo ya tenga las tablas y medidas de 01_power_query.pq / 04_tabular_editor.cs.
Reemplaza todas las páginas del informe y aplica el tema 03_tema_giragroup_cmi.json.
"""
import json
import sys
import zipfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
SCH = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition"
W, H = 1280, 720
VERDE, AMBAR, ROJO, GRIS, TINTA, SUAVE = "#1B8754", "#C27C0E", "#D9383A", "#9A9CA3", "#17191C", "#777B86"
TEMA = "GiraGroupCMI.json"


# ---------- expresiones ----------
def lit(v):
    if isinstance(v, bool):
        s = "true" if v else "false"
    elif isinstance(v, int):
        s = f"{v}L"
    elif isinstance(v, float):
        s = f"{v}D"
    else:
        s = "'" + str(v).replace("'", "''") + "'"
    return {"expr": {"Literal": {"Value": s}}}


def num(v):
    return {"expr": {"Literal": {"Value": f"{v}D"}}}


def color(c):
    return {"solid": {"color": lit(c)}}


def ref_m(tabla, medida):
    return {"Measure": {"Expression": {"SourceRef": {"Entity": tabla}}, "Property": medida}}


def ref_c(tabla, col):
    return {"Column": {"Expression": {"SourceRef": {"Entity": tabla}}, "Property": col}}


def color_campo(tabla, medida):
    return {"solid": {"color": {"expr": ref_m(tabla, medida)}}}


def proy(campo, nombre=None):
    """campo: ('m'|'c'|'sum', tabla, propiedad)."""
    tipo, t, p = campo
    if tipo == "m":
        f, qr = ref_m(t, p), f"{t}.{p}"
    elif tipo == "c":
        f, qr = ref_c(t, p), f"{t}.{p}"
    else:
        f = {"Aggregation": {"Expression": ref_c(t, p), "Function": 0}}
        qr = f"Sum({t}.{p})"
    d = {"field": f, "queryRef": qr, "nativeQueryRef": nombre or p}
    if nombre:
        d["displayName"] = nombre
    return d


def qr(campo):
    tipo, t, p = campo
    return f"Sum({t}.{p})" if tipo == "sum" else f"{t}.{p}"


def filtro_in(tabla, col, valores):
    return {"Version": 2, "From": [{"Name": "x", "Entity": tabla, "Type": 0}],
            "Where": [{"Condition": {"In": {
                "Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "x"}}, "Property": col}}],
                "Values": [[{"Literal": {"Value": lit(v)["expr"]["Literal"]["Value"]}}] for v in valores]}}}]}


# ---------- contenedores ----------
class Pagina:
    def __init__(self, nombre, titulo):
        self.nombre, self.titulo, self.visuales, self.filtros = nombre, titulo, [], []

    def add(self, nombre, x, y, w, h, visual, titulo=None, titulo_medida=None, extra=None, marco=True):
        z = len(self.visuales)
        cont = {}
        if titulo or titulo_medida:
            texto = {"expr": ref_m(*titulo_medida)} if titulo_medida else lit(titulo)
            cont["title"] = [{"properties": {"show": lit(True), "text": texto, "fontSize": num(12),
                                             "fontColor": color(TINTA), "bold": lit(True)}}]
        else:
            cont["title"] = [{"properties": {"show": lit(False)}}]
        if not marco:
            cont["background"] = [{"properties": {"show": lit(False)}}]
            cont["border"] = [{"properties": {"show": lit(False)}}]
        visual.setdefault("drillFilterOtherVisuals", True)
        if cont:
            visual["visualContainerObjects"] = cont
        v = {"$schema": f"{SCH}/visualContainer/2.4.0/schema.json", "name": f"{self.nombre}_{nombre}",
             "position": {"x": x, "y": y, "z": z * 1000, "width": w, "height": h, "tabOrder": z * 1000},
             "visual": visual}
        if extra:
            v.update(extra)
        self.visuales.append(v)


def textbox(parrafos):
    """parrafos: lista de (texto, tamaño_pt, color, negrita)."""
    ps = [{"textRuns": [{"value": t, "textStyle": {"fontSize": f"{s}pt", "color": c,
                                                   **({"fontWeight": "bold"} if b else {})}}]}
          for t, s, c, b in parrafos]
    return {"visualType": "textbox", "objects": {"general": [{"properties": {"paragraphs": ps}}]}}


def tarjeta(campo, tam=36, color_medida=None, color_fijo=TINTA, etiqueta=False):
    lab = {"fontSize": num(tam), "color": color_campo(*color_medida) if color_medida else color(color_fijo)}
    return {"visualType": "card",
            "query": {"queryState": {"Values": {"projections": [proy(campo)]}}},
            "objects": {"labels": [{"properties": lab}],
                        "categoryLabels": [{"properties": {"show": lit(etiqueta)}}],
                        "wordWrap": [{"properties": {"show": lit(True)}}]}}


def multitarjeta(campos):
    return {"visualType": "multiRowCard",
            "query": {"queryState": {"Values": {"projections": [proy(c) for c in campos]}}},
            "objects": {"dataLabels": [{"properties": {"fontSize": num(20), "color": color(TINTA)}}],
                        "categoryLabels": [{"properties": {"fontSize": num(10), "color": color(SUAVE)}}],
                        "card": [{"properties": {"outline": lit("None"), "barShow": lit(False)}}]}}


def sel(campo):
    return {"data": [{"dataViewWildcard": {"matchingOption": 1}}], "metadata": qr(campo)}


def tabla(columnas, fuente_color=(), fondo_color=(), barras=(), fijos=()):
    """columnas: lista de (campo, nombre). fuente_color/fondo_color: [(campo, (tabla, medida))]."""
    vals = []
    for campo, med in fuente_color:
        vals.append({"properties": {"fontColor": color_campo(*med)}, "selector": sel(campo)})
    for campo, med in fondo_color:
        vals.append({"properties": {"backColor": color_campo(*med), "fontColor": color("#FFFFFF")},
                     "selector": sel(campo)})
    for campo, c in fijos:
        vals.append({"properties": {"fontColor": color(c)}, "selector": sel(campo)})
    for campo in barras:
        vals.append({"properties": {"dataBars": {"positiveColor": color("#D99B26"),
                                                 "negativeColor": color(ROJO),
                                                 "axisColor": color("#ECECEC"),
                                                 "reverseDirection": lit(False), "hideText": lit(True)}},
                     "selector": sel(campo)})
    obj = {"total": [{"properties": {"totals": lit(False)}}],
           "grid": [{"properties": {"gridHorizontal": lit(True), "gridHorizontalColor": color("#ECECEC"),
                                    "gridVertical": lit(False), "rowPadding": num(6), "textSize": num(10)}}],
           "columnHeaders": [{"properties": {"fontColor": color(SUAVE), "backColor": color("#FAF9F6"),
                                             "bold": lit(True), "wordWrap": lit(True)}}],
           "values": [{"properties": {"fontColorPrimary": color(TINTA), "backColorPrimary": color("#FFFFFF"),
                                      "backColorSecondary": color("#FFFFFF"), "wordWrap": lit(True)}}] + vals}
    return {"visualType": "tableEx",
            "query": {"queryState": {"Values": {"projections": [proy(c, n) for c, n in columnas]}}},
            "objects": obj}


def segmentador(gestion):
    return {"visualType": "slicer",
            "query": {"queryState": {"Values": {"projections": [proy(("c", "Gestiones", "gestion"))]}}},
            "objects": {
                "data": [{"properties": {"mode": lit("Basic")}}],
                "general": [{"properties": {"orientation": num(1),
                                            "filter": {"filter": filtro_in("Gestiones", "gestion", [gestion])}}}],
                "selection": [{"properties": {"singleSelect": lit(True), "strictSingleSelect": lit(True),
                                              "selectAllCheckboxEnabled": lit(False)}}],
                "header": [{"properties": {"show": lit(False)}}],
                "items": [{"properties": {"fontColor": color(TINTA), "background": color("#F2F2F3"),
                                          "textSize": num(11)}}]},
            "syncGroup": {"groupName": "gestion", "fieldChanges": True, "filterChanges": True}}


# ---------- campos ----------
IP = "IndicePerspectiva"
SC = "Scorecard"
INDICE_TXT = ("m", IP, "Indice Texto")
CONTEOS = [("m", IP, "En meta"), ("m", IP, "En alerta"), ("m", IP, "Críticos"), ("m", IP, "Sin evaluar")]
COLOR_CONTEO = dict(zip([qr(c) for c in CONTEOS], [VERDE, AMBAR, ROJO, GRIS]))
NOTA = ("Cada indicador puntúa 100 en meta, 60 en alerta y 20 si es crítico; "
        "los indicadores sin dato o sin umbral no puntúan. Índice ≥ 80 en meta · ≥ 50 en alerta · < 50 crítico.")


def encabezado(p, titulo, subtitulo, gestion):
    p.add("titulo", 24, 12, 860, 64,
          textbox([(titulo, 20, TINTA, True), (subtitulo, 10, SUAVE, False)]), marco=False)
    p.add("gestion", 900, 20, 356, 52, segmentador(gestion))


def barra_distribucion():
    return {"visualType": "hundredPercentStackedBarChart",
            "query": {"queryState": {"Y": {"projections": [proy(c) for c in CONTEOS]}}},
            "objects": {"dataPoint": [{"properties": {"fill": color(c)}, "selector": {"metadata": m}}
                                      for m, c in COLOR_CONTEO.items()],
                        "legend": [{"properties": {"show": lit(True), "position": lit("Bottom"),
                                                   "fontSize": num(9)}}],
                        "labels": [{"properties": {"show": lit(True), "color": color("#FFFFFF")}}],
                        "categoryAxis": [{"properties": {"show": lit(False)}}],
                        "valueAxis": [{"properties": {"show": lit(False), "gridlineShow": lit(False)}}]}}


def pagina_resumen(gestion):
    p = Pagina("resumen", "Resumen")
    encabezado(p, "Cuadro de Mando Integral", "GiraGroup · desempeño estratégico por perspectiva", gestion)
    p.add("indice", 24, 88, 300, 196, tarjeta(INDICE_TXT, 54, color_medida=(IP, "Indice Color")),
          titulo_medida=(IP, "Titulo Gestion"))
    p.add("conteos", 340, 88, 440, 196, multitarjeta(CONTEOS), titulo="Indicadores por estado")
    p.add("distribucion", 796, 88, 460, 196, barra_distribucion(), titulo="Distribución del semáforo")
    p.add("nota", 24, 292, 1232, 40, textbox([(NOTA, 9, SUAVE, False)]), marco=False)
    p.add("mapa", 24, 340, 1232, 356, tabla(
        [(("c", "Perspectivas", "nombre"), "Perspectiva"), (("m", IP, "Objetivo"), "Objetivo estratégico"),
         (INDICE_TXT, "Índice"), (("m", IP, "Evaluados Texto"), "Cobertura")],
        fondo_color=[(INDICE_TXT, (IP, "Indice Color"))],
        fijos=[(("m", IP, "Evaluados Texto"), SUAVE)]), titulo="Mapa estratégico")
    return p


def tabla_indicadores():
    return tabla(
        [(("c", SC, "codigo"), "Código"), (("c", SC, "nombre"), "Indicador"),
         (("m", SC, "Valor Texto"), "Valor"), (("m", SC, "Avance Meta"), "Avance"),
         (("m", SC, "Meta Texto"), "Meta"), (("m", SC, "Estado Icono"), "Estado"),
         (("m", SC, "Tendencia Texto"), "Variación"), (("m", SC, "Valor Anterior Texto"), "Gestión anterior")],
        fuente_color=[(("m", SC, "Estado Icono"), (SC, "Estado Color")),
                      (("m", SC, "Tendencia Texto"), (SC, "Tendencia Color"))],
        barras=[("m", SC, "Avance Meta")],
        fijos=[(("c", SC, "codigo"), SUAVE), (("m", SC, "Valor Anterior Texto"), SUAVE)])


def pagina_perspectiva(nombre, titulo, codigo, subtitulo, gestion, alto_tabla):
    p = Pagina(nombre, titulo)
    encabezado(p, titulo, subtitulo, gestion)
    p.add("indice", 24, 88, 220, 120, tarjeta(INDICE_TXT, 36, color_medida=(IP, "Indice Color")),
          titulo="Índice de la perspectiva")
    p.add("objetivo", 256, 88, 600, 120, tarjeta(("m", IP, "Objetivo"), 13), titulo="Objetivo estratégico")
    p.add("conteos", 868, 88, 388, 120, multitarjeta(CONTEOS), titulo="Indicadores por estado")
    p.add("indicadores", 24, 220, 1232, alto_tabla, tabla_indicadores(), titulo="Indicadores")
    p.filtros.append({"name": f"f_{nombre}", "field": ref_c("Perspectivas", "codigo"), "type": "Categorical",
                      "filter": filtro_in("Perspectivas", "codigo", [codigo]), "howCreated": "User",
                      "isHiddenInViewMode": True})
    return p


def combo_metas():
    return {"visualType": "lineClusteredColumnComboChart",
            "query": {"queryState": {
                "Category": {"projections": [proy(("c", "MetasMensual", "fecha_mes"), "Mes")]},
                "Y": {"projections": [proy(("m", "MetasMensual", "Ejecutado Bs")),
                                      proy(("m", "MetasMensual", "Meta Bs"))]},
                "Y2": {"projections": [proy(("m", "MetasMensual", "Ejecutado Año Anterior Bs"))]}}},
            "objects": {"dataPoint": [
                {"properties": {"fill": color("#0C1E33")}, "selector": {"metadata": "MetasMensual.Ejecutado Bs"}},
                {"properties": {"fill": color("#D99B26")}, "selector": {"metadata": "MetasMensual.Meta Bs"}},
                {"properties": {"fill": color(GRIS)},
                 "selector": {"metadata": "MetasMensual.Ejecutado Año Anterior Bs"}}],
                "legend": [{"properties": {"show": lit(True), "position": lit("Top")}}],
                "categoryAxis": [{"properties": {"axisType": lit("Categorical")}}],
                "valueAxis": [{"properties": {"secShow": lit(False)}}]}}


def anillo_cartera():
    return {"visualType": "donutChart",
            "query": {"queryState": {
                "Category": {"projections": [proy(("c", "CarteraEstado", "estado_cartera"), "Estado")]},
                "Y": {"projections": [proy(("sum", "CarteraEstado", "deuda_bs"), "Deuda Bs")]}}},
            "objects": {"legend": [{"properties": {"show": lit(True), "position": lit("Bottom")}}],
                        "labels": [{"properties": {"labelStyle": lit("Percent of total")}}]}}


def pagina_financiera(g):
    p = pagina_perspectiva("financiera", "Financiera", "FINANCIERA",
                           "¿Cómo crecemos en ingresos y protegemos la cartera?", g, 236)
    p.add("metas", 24, 468, 820, 228, combo_metas(), titulo="Ingresos ejecutados vs meta mensual")
    p.add("cartera", 856, 468, 400, 228, anillo_cartera(), titulo="Deuda por estado de cartera")
    return p


def pagina_procesos(g):
    p = pagina_perspectiva("procesos", "Procesos internos", "PROCESOS_INTERNOS",
                           "¿En qué procesos debemos ser excelentes?", g, 252)
    D = "DataOpsDocumento"
    p.add("dataops", 24, 484, 1232, 212, tabla(
        [(("c", D, "nombre_archivo"), "Archivo"), (("c", D, "tipo_fuente"), "Fuente"),
         (("c", D, "fecha"), "Fecha"), (("m", D, "Registros"), "Registros"),
         (("m", D, "Consolidado directo"), "Consolidado directo"), (("m", D, "Revisión humana"), "Revisión humana"),
         (("m", D, "Pendientes"), "Pendientes")]), titulo="Calidad de datos por documento cargado")
    return p


def pagina_aprendizaje(g):
    p = pagina_perspectiva("aprendizaje", "Aprendizaje y crecimiento", "APRENDIZAJE",
                           "¿Cómo sostenemos la capacidad de mejorar?", g, 236)
    R = "RiesgoEstudiante"
    p.add("riesgo", 24, 468, 600, 228, {
        "visualType": "clusteredColumnChart",
        "query": {"queryState": {
            "Category": {"projections": [proy(("c", R, "nivel_prioridad"), "Prioridad")]},
            "Y": {"projections": [proy(("m", R, "Estudiantes"))]}}},
        "objects": {"dataPoint": [{"properties": {"fill": color("#0C1E33")}}],
                    "labels": [{"properties": {"show": lit(True)}}],
                    "legend": [{"properties": {"show": lit(False)}}]}},
        titulo="Estudiantes por nivel de riesgo")
    p.add("programas", 636, 468, 620, 228, tabla(
        [(("c", R, "programa"), "Programa"), (("m", R, "Estudiantes"), "Estudiantes"),
         (("m", R, "Prioridad crítica"), "Prioridad crítica")],
        fijos=[(("m", R, "Prioridad crítica"), ROJO)]), titulo="Riesgo por programa")
    return p


# ---------- empaquetado ----------
def page_json(p):
    d = {"$schema": f"{SCH}/page/2.1.0/schema.json", "name": p.nombre, "displayName": p.titulo,
         "displayOption": "FitToPage", "height": H, "width": W}
    if p.filtros:
        d["filterConfig"] = {"filters": p.filtros}
    return d


def generar(entrada, salida, gestion):
    paginas = [pagina_resumen(gestion), pagina_financiera(gestion),
               pagina_perspectiva("clientes", "Estudiantes y mercado", "CLIENTES",
                                  "¿Cómo nos ven estudiantes e instituciones?", gestion, 476),
               pagina_procesos(gestion), pagina_aprendizaje(gestion)]
    zin = zipfile.ZipFile(entrada)
    nuevos = {}
    for p in paginas:
        base = f"Report/definition/pages/{p.nombre}"
        nuevos[f"{base}/page.json"] = page_json(p)
        for v in p.visuales:
            nuevos[f"{base}/visuals/{v['name']}/visual.json"] = v
    nuevos["Report/definition/pages/pages.json"] = {
        "$schema": f"{SCH}/pagesMetadata/1.1.0/schema.json",
        "pageOrder": [p.nombre for p in paginas], "activePageName": paginas[0].nombre}

    rep = json.loads(zin.read("Report/definition/report.json").decode("utf-8-sig"))
    rep["themeCollection"]["customTheme"]["name"] = TEMA
    for pkg in rep["resourcePackages"]:
        if pkg["type"] == "RegisteredResources":
            pkg["items"] = [i for i in pkg["items"] if i.get("type") != "CustomTheme"]
            pkg["items"].append({"name": TEMA, "path": TEMA, "type": "CustomTheme"})
    nuevos["Report/definition/report.json"] = rep
    tema = json.loads((AQUI / "03_tema_giragroup_cmi.json").read_text(encoding="utf-8"))
    nuevos[f"Report/StaticResources/RegisteredResources/{TEMA}"] = tema

    viejo_tema = [i["path"] for pkg in json.loads(zin.read("Report/definition/report.json").decode("utf-8-sig"))
                  ["resourcePackages"] for i in pkg["items"] if i.get("type") == "CustomTheme"]
    omitir = {"SecurityBindings"} | {f"Report/StaticResources/RegisteredResources/{x}" for x in viejo_tema}

    with zipfile.ZipFile(salida, "w") as zout:
        for info in zin.infolist():
            n = info.filename
            if n in omitir or n.startswith("Report/definition/pages/") or n in nuevos:
                continue
            data = zin.read(n)
            if n == "[Content_Types].xml":
                data = data.replace(b'<Override PartName="/SecurityBindings" ContentType="" />', b"")
            zout.writestr(info, data)
        for n, d in nuevos.items():
            zout.writestr(n, json.dumps(d, ensure_ascii=False, indent=2).encode("utf-8"),
                          compress_type=zipfile.ZIP_DEFLATED)
    print(f"{salida}: {len(paginas)} páginas, {sum(len(p.visuales) for p in paginas)} visuales")


if __name__ == "__main__":
    generar(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 2026)
