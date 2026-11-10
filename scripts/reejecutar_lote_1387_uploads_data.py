"""
scripts/reejecutar_lote_1387_uploads_data.py
============================================
Reejecuta la evaluación del lote de 1.387 registros usando EXCLUSIVAMENTE
los archivos reales de uploads/data/ (sin tocar uploads/test/).

Arquitectura B: CI_EXACTA -> ENCABEZADO -> FUZZY -> REGEX -> BETO
(BETO solo actúa sobre posiciones que el parser dejó sin resolver, sin sobrescritura).

Tarea 1 aplicada: las personas (PER_ESTUDIANTE / PER_DOCENTE) se resuelven SIN cat_docente:
CI exacta -> dim_estudiante; sin CI -> RapidFuzz contra dim_* filtrando por programa/módulo y apellido;
sin coincidencia -> HITL.

Salida:
- docs/evidencias/lote_1387_uploads_data_arquitectura_b.json  (bandas, KPI-10 a/b, KPI-11, fuentes, muestreo)
- docs/evidencias/muestra_50_entidades_beto_semilla42.json     (50 entidades BETO al azar, semilla 42)

Requiere DATABASE_URL apuntando al DW (docker-compose, p. ej. localhost:5434).
"""

import json
from collections import Counter
import os
import random
import re
import sys
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pipeline.normalization.person_resolver import (
    resolver_persona_detalle, cargar_personas_dw, es_correo, parece_nombre_propio, es_etiqueta_likert, componer_nombre_partido, quitar_titulos, _candidatos, _tokens, _coincide_contexto)


def _regla_previa(valor, ci, pool, ctx):
    """Regla anterior (solo para el 'antes'): umbral 0,85, contexto como filtro duro, sin escalar."""
    det = resolver_persona_detalle(valor, ci, pool, contexto=None, umbral=0.85)
    if det["nivel"] == "CI":
        return det["resultado"], None
    cand = quitar_titulos(valor or "")
    toks = _tokens(cand)
    if len(toks) < 2:
        return None, "sin_candidatos"
    p2 = [p for p in pool if _coincide_contexto(p.get("contextos") or [], ctx)] if ctx else pool
    c85 = _candidatos(p2, cand, toks, 0.85)
    if c85:
        c85.sort(key=lambda x: (x[0], x[1]), reverse=True)
        return {"id": c85[0][2]["id"], "fuente": "FUZZY"}, None
    return None, ("umbral" if _candidatos(p2, cand, toks, 0.0) else "sin_candidatos")
from scripts.ablacion_beto import EvaluadorAblacion

MUESTRAS = [
    ("Base centralizada Académica ARCA (1).xlsx", "ACTAS DE NOTAS", 450, "academico"),
    ("BD Cobranzas.xlsx", "COBRANZAS 2024 2025", 350, "financiero"),
    ("TBL_INSCRITOS.xlsx", "TBL_INSCRITOS", 250, "inscritos"),
    ("Evaluación Docente y Unifranz.xlsx", "DIP. EXP DOC. X MODULO", 150, "evaluacion_docente"),
    ("Experiencia Docente 2.0.xlsx", "CURSOS DOC 1", 110, "evaluacion_docente"),
    ("BD Egresos.xlsx", "egresos", 53, "financiero"),
    ("EJECUTADO VS META.xlsx", "EJECUTADO", 24, "financiero"),
]
MUESTREO = []  # criterio efectivo por archivo (se vuelca al JSON)


def cargar_lote_1387_uploads_data():
    data_dir = ROOT_DIR / "uploads" / "data"
    filas, reg_id = [], 1
    for nombre, sheet, max_r, cat in MUESTRAS:
        path_arch = data_dir / nombre
        if not path_arch.exists():
            print(f"ERROR: No se encuentra {path_arch}")
            continue
        df = pd.read_excel(path_arch, sheet_name=sheet).dropna(how="all")
        tomadas = disponibles = 0
        for idx, row in df.iterrows():
            items = [f"{str(c).strip()}: {str(v).strip()}" for c, v in row.items() if pd.notna(v) and str(v).strip()]
            if not items:
                continue
            disponibles += 1
            if tomadas >= max_r or len(filas) >= 1387:
                continue
            filas.append({
                "registro": reg_id, "archivo": path_arch.name, "hoja": sheet,
                "fila_origen": int(idx) + 2,  # índice del DataFrame + 2 (encabezado en la fila 1 de la hoja)
                "texto": " | ".join(items[:8]), "categoria": cat,
            })
            reg_id += 1
            tomadas += 1
        MUESTREO.append({
            "archivo": nombre, "hoja": sheet, "tope_en_codigo": max_r, "filas_no_vacias_en_hoja": disponibles,
            "filas_tomadas": tomadas, "el_tope_agota_la_hoja": disponibles <= max_r,
            "seleccion": "primeras N filas no vacías en el orden del archivo (sin aleatorización)",
        })
    print(f"Total registros cargados desde uploads/data/: {len(filas)}")
    return filas


def _norm(s):
    s = unicodedata.normalize("NFD", str(s)).lower()
    return re.sub(r"\s+", " ", "".join(c for c in s if unicodedata.category(c) != "Mn")).strip()


_RE_COL_COMENTARIO = re.compile(r"comentari|sugerenc|observaci|opini|mejorar|aspectos|otro contenido|explorar|libre", re.I)
_VACIOS = {"", "nan", "none", "n/a", "na", "ninguno", "ninguna", "-", "sin comentarios", "no"}


def _comentarios_del_registro(texto):
    """Textos de las celdas 'encabezado: valor' cuyo encabezado es de comentario/sugerencia/observación/opinión (no vacíos)."""
    out = []
    for celda in texto.split(" | "):
        hdr, sep, val = celda.partition(": ")
        if sep and _RE_COL_COMENTARIO.search(hdr) and val.strip().lower() not in _VACIOS:
            out.append(val.strip())
    return out


def _en_comentario(valor, comentarios):
    v = (valor or "").strip().lower()
    return bool(v) and any(v in c.lower() for c in comentarios)


def _spans_beto(tokens, pred_a, pred_beto, probs_beto):
    """Spans B-/I- cuyo primer token dejó sin resolver el parser (A) y etiquetó BETO."""
    spans, i = [], 0
    while i < len(tokens):
        if pred_a[i] == "O" and pred_beto[i].startswith("B-"):
            tipo, j = pred_beto[i][2:], i + 1
            while j < len(tokens) and pred_a[j] == "O" and pred_beto[j] == f"I-{tipo}":
                j += 1
            spans.append({"tipo": tipo, "valor": " ".join(tokens[i:j]),
                          "score": float(np.mean(probs_beto[i:j])), "fuente": "BETO"})
            i = j
        else:
            i += 1
    return spans


def _presencia_en_dw(valores):
    """Columnas dim_* donde aparece el valor (igualdad normalizada). Este script no escribe en el DW."""
    from sqlalchemy import create_engine, text
    out = {v: [] for v in valores}
    url = os.getenv("DATABASE_URL")
    if not url:
        return out
    cols = [("dim_estudiante", "nombre_completo"), ("dim_docente", "nombre_completo"),
            ("dim_modulo", "nombre_modulo"), ("dim_modulo", "programa"), ("dim_modulo", "pos_code")]
    with create_engine(url).connect() as c:
        for tabla, col in cols:
            idx = {_norm(r[0]) for r in c.execute(text(f"SELECT {col} FROM {tabla} WHERE {col} IS NOT NULL"))}
            for v in valores:
                if _norm(v) in idx:
                    out[v].append(f"{tabla}.{col}")
    return out


def _registrar_descartes(descartadas):
    """Registra cada entidad PER descartada por forma en log_inconsistencias (tipo_regla PER_SIN_FORMA_NOMBRE); idempotente:
    reemplaza las filas previas de esa regla. Devuelve cuántas quedaron. Sin DATABASE_URL no escribe."""
    from sqlalchemy import create_engine, text
    url = os.getenv("DATABASE_URL")
    if not url:
        return None
    with create_engine(url).begin() as c:
        ids = {r[0]: r[1] for r in c.execute(text("SELECT nombre_archivo, max(id_documento) FROM dim_origen_documental GROUP BY 1"))}
        c.execute(text("DELETE FROM log_inconsistencias WHERE tipo_regla = 'PER_SIN_FORMA_NOMBRE'"))
        filas = [{"d": ids.get(x["archivo"]), "f": x["fila_origen"], "c": x["tipo"], "v": x["valor"][:2000], "h": x["hecho_sin_persona"],
                  "ds": f"{x['archivo']} / {x['hoja']}: entidad {x['tipo']} sin CI ni coincidencia y sin forma de nombre propio; "
                        + ("el registro quedó sin persona: va a HITL" if x["hecho_sin_persona"] else "el registro conserva otra persona")}
                 for x in descartadas]
        if filas:
            c.execute(text("INSERT INTO log_inconsistencias (id_documento, fila_origen, campo_afectado, valor_recibido, tipo_regla, severidad, estado_resolucion, descripcion) "
                           "VALUES (:d, :f, :c, :v, 'PER_SIN_FORMA_NOMBRE', 'MEDIA', 'DESCARTADO', :ds)"), filas)
        return c.execute(text("SELECT count(*) FROM log_inconsistencias WHERE tipo_regla = 'PER_SIN_FORMA_NOMBRE'")).scalar()


def _banda(c):
    return 0 if c >= 0.85 else (1 if c >= 0.60 else 2)


def _resumen_excepciones(exc, total_registros):
    """Ronda 10: excepciones del lote por regla y destino. 'sin_control' = excepcion que exigia HITL (persona sin coincidencia o hecho sin persona)
    y cuyo registro quedo en la banda directo."""
    por_regla = {}
    for e in exc:
        r = por_regla.setdefault(e["regla"], {"entidades": 0, "destino": e["destino"], "registros": set(), "registros_en_hitl": set()})
        r["entidades"] += 1
        r["registros"].add(e["registro"])
        if e["banda_final"] >= 1:
            r["registros_en_hitl"].add(e["registro"])
    sin_control = [e for e in exc if (e["destino"] == "hitl" or e["hecho_sin_persona"]) and e["banda_final"] == 0]
    return {"total_entidades": len(exc), "registros_afectados": len({e["registro"] for e in exc}), "de_registros": total_registros,
            "por_regla": {k: {"entidades": v["entidades"], "registros": len(v["registros"]), "destino": v["destino"], "registros_con_banda_hitl": len(v["registros_en_hitl"])}
                          for k, v in sorted(por_regla.items())},
            "por_destino": {d: sum(1 for e in exc if e["destino"] == d) for d in sorted({e["destino"] for e in exc})},
            "habrian_ingresado_al_dw_sin_control": len(sin_control)}


def main():
    lote = cargar_lote_1387_uploads_data()
    assert len(lote) == 1387, f"Se esperaban 1.387 registros, se obtuvieron {len(lote)}"
    evaluador = EvaluadorAblacion()
    est_dw = cargar_personas_dw("dim_estudiante")
    doc_dw = cargar_personas_dw("dim_docente")
    print(f"Dimensiones del DW: dim_estudiante={len(est_dw)}, dim_docente={len(doc_dw)}")

    bandas = {"pre": [0, 0, 0], "post": [0, 0, 0], "prev": [0, 0, 0]}
    conf_registro, s_todas, s_beto, ent_beto = [], [], [], []
    fuentes = {"CI_EXACTA": 0, "ENCABEZADO": 0, "FUZZY": 0, "REGEX": 0, "BETO": 0}
    personas = {"total": 0, "resueltas_CI_EXACTA": 0, "resueltas_FUZZY": 0, "nuevos_estado_C": 0, "sin_coincidencia_HITL": 0}
    correos = {"entidades": 0, "registros": 0}
    texto_libre = Counter()
    fk_estado = {"estudiante": Counter(), "docente": Counter()}
    directo_a_hitl = 0
    descartadas, hechos_sin_persona = [], []  # PER_SIN_FORMA_NOMBRE y registros que quedaron sin ninguna persona
    desglose_antes = {"estudiante": Counter(), "docente": Counter()}
    desglose_despues = {"estudiante": Counter(), "docente": Counter()}
    niveles = Counter()
    por_archivo = {}  # archivo -> [directo, hitl, staging] (arquitectura final)
    excepciones = []  # ronda 10: cada entidad/registro con excepcion, su regla y su destino

    for item in lote:
        txt = item["texto"]
        tokens = [t for t in txt.split() if t]
        res_a = evaluador.parser.procesar_fila(txt)
        ents = [{"tipo": e.tipo, "valor": e.valor, "score": float(e.score), "fuente": e.fuente_resolucion or "ENCABEZADO"}
                for e in res_a["entidades"]]
        pred_a = evaluador.extraer_spans_bio(tokens, [{"tipo": e["tipo"], "valor": e["valor"]} for e in ents])
        pred_beto, probs_beto = evaluador.inferir_beto_tokens(tokens)
        eb = _spans_beto(tokens, pred_a, pred_beto, probs_beto)
        for e in ents:
            fuentes[e["fuente"]] = fuentes.get(e["fuente"], 0) + 1
        fuentes["BETO"] += len(eb)
        todas = ents + eb
        s_todas += [e["score"] for e in todas]
        s_beto += [e["score"] for e in eb]
        ent_beto += [{**e, "archivo": item["archivo"], "hoja": item["hoja"],
                      "fila_origen": item["fila_origen"], "registro": item["registro"]} for e in eb]

        conf = round(float(np.mean([e["score"] for e in todas])), 4) if todas else (0.55 if len(txt) < 20 else 0.72)
        conf_registro.append(conf)
        b_pre = _banda(conf)
        bandas["pre"][b_pre] += 1

        # Tarea 1: CI exacta -> dim_estudiante; sin CI: RapidFuzz en la dim (programa/módulo + apellido); si no -> HITL
        ci = next((e["valor"] for e in todas if e["tipo"] == "CI"), None)
        ctx = [e["valor"] for e in todas if e["tipo"] in ("PROGRAMA", "MODULO", "POS")]
        comentarios_reg = _comentarios_del_registro(txt)
        # Nombre partido en columnas (APELLIDO PATERNO / MATERNO / NOMBRES): una sola persona con el nombre completo
        comp = componer_nombre_partido(txt.split(" | "))
        if comp:
            partes = {_norm(x) for x in comp["partes"]}
            quitadas = [e for e in todas if e["tipo"] in ("PER_ESTUDIANTE", "PER_DOCENTE") and _norm(e["valor"]) in partes]
            if quitadas:
                todas = [e for e in todas if e not in quitadas] + [
                    {"tipo": quitadas[0]["tipo"], "valor": comp["nombre"], "score": float(np.mean([e["score"] for e in quitadas])), "fuente": "ENCABEZADO"}]
                texto_libre["nombres_compuestos_desde_columnas_partidas"] += 1
                texto_libre["entidades_PER_partidas_reemplazadas"] += len(quitadas)
        texto_libre["comentarios_en_columnas_de_texto_libre"] += len(comentarios_reg)
        texto_libre["registros_con_comentarios"] += int(bool(comentarios_reg))
        sin_resolver = False
        correo_en_registro = False
        sin_resolver_prev = False
        descartadas_reg, personas_reg = [], 0
        exc_reg = []
        for e in todas:
            if e["tipo"] not in ("PER_ESTUDIANTE", "PER_DOCENTE"):
                continue
            if es_etiqueta_likert(e["valor"]):
                texto_libre["entidades_excluidas_etiqueta_likert"] += 1
                exc_reg.append(("ETIQUETA_LIKERT", "descarte"))
                continue  # '5/Totalmente de acuerdo': escala de respuesta, no una persona
            if _en_comentario(e["valor"], comentarios_reg):
                texto_libre["entidades_excluidas_por_columna_de_comentario"] += 1
                exc_reg.append(("COLUMNA_DE_COMENTARIO", "descarte"))
                continue  # tomada de una columna de comentario/sugerencia/observación/opinión: no es una persona
            if es_correo(e["valor"]):
                correos["entidades"] += 1
                exc_reg.append(("CORREO_NO_ES_NOMBRE", "descarte"))
                correo_en_registro = True
                continue  # los correos no son nombres: fuera de la resolución de personas
            personas["total"] += 1
            est = e["tipo"] == "PER_ESTUDIANTE"
            pool = est_dw if est else doc_dw
            ctx_mod = [e2["valor"] for e2 in todas if e2["tipo"] == "MODULO"]
            det = resolver_persona_detalle(e["valor"], ci if est else None, pool, contexto=ctx, ctx_modulo=ctx_mod)
            r = det["resultado"]
            tipo = "estudiante" if est else "docente"
            rp, mot_prev = _regla_previa(e["valor"], ci if est else None, pool, ctx)
            if rp is None:
                sin_resolver_prev = True
                desglose_antes[tipo][mot_prev] += 1
            if not r and not parece_nombre_propio(e["valor"]):
                # sin CI ni fuzzy y con forma de texto, no de nombre: se descarta (no va a HITL). Si hay CI exacta se resuelve igual
                personas["total"] -= 1
                texto_libre["entidades_PER_descartadas_no_parece_nombre"] += 1
                exc_reg.append(("PER_SIN_FORMA_NOMBRE", "log+descarte"))
                descartadas_reg.append({"tipo": e["tipo"], "valor": e["valor"], "archivo": item["archivo"], "hoja": item["hoja"], "fila_origen": item["fila_origen"]})
                continue
            personas_reg += 1
            if r:
                personas["resueltas_" + r["fuente"]] += 1
                niveles[det["nivel"]] += 1
                fk_estado[tipo]["A" if r["fuente"] == "CI_EXACTA" else "B"] += 1
            elif det["motivo"] == "sin_candidatos" and len(_tokens(quitar_titulos(e["valor"]))) >= 2 and parece_nombre_propio(e["valor"]):
                # Tarea 1 (ronda 2): sin candidatos => miembro nuevo con clave sustituta y fk_estado='C'; la fila sigue su banda
                personas["nuevos_estado_C"] += 1
                fk_estado[tipo]["C"] += 1
            else:
                personas["sin_coincidencia_HITL"] += 1
                motivo_h = (det["motivo"] if det["motivo"] == "empate" else "sin_identidad_un_token"
                            if len(_tokens(quitar_titulos(e["valor"]))) < 2 else "no_parece_nombre_de_persona")
                desglose_despues[tipo][motivo_h] += 1
                sin_resolver = True
                exc_reg.append(("PERSONA_SIN_COINCIDENCIA", "hitl"))
        correos["registros"] += int(correo_en_registro)
        if descartadas_reg:
            # Un hecho que pierde su única persona por el descarte no puede cargarse directo: va a HITL
            pierde = personas_reg == 0
            for d in descartadas_reg:
                d["hecho_sin_persona"] = pierde
            descartadas += descartadas_reg
            if pierde:
                hechos_sin_persona.append(descartadas_reg[0])
                sin_resolver = True
        bandas["prev"][max(b_pre, 1) if sin_resolver_prev else b_pre] += 1
        b_post = max(b_pre, 1) if sin_resolver else b_pre  # sin coincidencia -> HITL
        if sin_resolver and b_pre == 0:
            directo_a_hitl += 1
        bandas["post"][b_post] += 1
        por_archivo.setdefault(item["archivo"], [0, 0, 0])[b_post] += 1
        for regla, destino in exc_reg:
            excepciones.append({"regla": regla, "destino": destino, "archivo": item["archivo"], "registro": item["registro"],
                                "banda_final": b_post, "hecho_sin_persona": bool(descartadas_reg and personas_reg == 0)})

    total = len(lote)

    def dist(v):
        return {k: {"conteo": n, "porcentaje": round(n / total * 100.0, 2)} for k, n in zip(("directo", "hitl", "staging"), v)}

    muestra = random.Random(42).sample(ent_beto, min(50, len(ent_beto)))
    pres = _presencia_en_dw([m["valor"] for m in muestra])
    for m in muestra:
        m["score"] = round(m["score"], 4)
        m["persistida_en_dw"] = pres.get(m["valor"], [])

    res = {
        "lote_evaluado": {"total_registros": total, "origen": "EXCLUSIVAMENTE uploads/data/ (archivos de producción)",
                          "archivos": [{"archivo": n, "hoja": h, "filas": c} for n, h, c, _ in MUESTRAS]},
        "muestreo_por_archivo": {
            "criterio_documentado": False,
            "nota": ("No existe criterio de muestreo documentado: los topes 450/350/250/150/110/53/24 son constantes escritas "
                     "en este script (suman 1.387, el tamaño objetivo del lote). La selección es 'primeras N filas no vacías en "
                     "orden de archivo', sin aleatorización ni estratificación. 'el_tope_agota_la_hoja' indica en qué hojas el "
                     "tope coincide con (o supera) la hoja completa."),
            "detalle": MUESTREO,
        },
        "arquitectura": "B (CI_EXACTA -> ENCABEZADO -> FUZZY -> REGEX -> BETO) + personas sin cat_docente (tarea 1)",
        "dimensiones_dw_usadas": {"dim_estudiante": len(est_dw), "dim_docente": len(doc_dw)},
        "personas": personas,
        "personas_hitl_desglose_regla_previa_umbral_085": {k: dict(v) for k, v in desglose_antes.items()},
        "personas_hitl_desglose_bloqueo_escalonado_umbral_092": {k: dict(v) for k, v in desglose_despues.items()},
        "personas_resueltas_por_nivel": dict(niveles),
        "correos_filtrados_como_no_nombre": correos,
        "descartadas_PER_SIN_FORMA_NOMBRE": {
            "entidades": len(descartadas), "registros_afectados": len({(d['archivo'], d['hoja'], d['fila_origen']) for d in descartadas}),
            "hechos_sin_persona_van_a_hitl": len(hechos_sin_persona),
            "ejemplos_20": [{k: d[k] for k in ("valor", "archivo", "hoja", "fila_origen", "hecho_sin_persona")} for d in descartadas[:20]],
            "ejemplos_20_hecho_sin_persona": [{k: d[k] for k in ("valor", "archivo", "hoja", "fila_origen")} for d in hechos_sin_persona[:20]]},
        "log_inconsistencias_PER_SIN_FORMA_NOMBRE_registradas": _registrar_descartes(descartadas),
        "texto_libre": dict(texto_libre),
        "personas_por_fk_estado": {k: dict(v) for k, v in fk_estado.items()},
        "distribucion_bandas_sin_regla_personas": dist(bandas["pre"]),
        "distribucion_bandas_con_regla_personas_previa_umbral_085": dist(bandas["prev"]),
        "distribucion_bandas_con_regla_personas": dist(bandas["post"]),
        "registros_directo_movidos_a_hitl_por_persona_sin_resolver": directo_a_hitl,
        "kpis": {
            "KPI_10a_media_todas_las_entidades": round(float(np.mean(s_todas)), 4),
            "KPI_10a_n_entidades": len(s_todas),
            "KPI_10b_media_solo_entidades_BETO": round(float(np.mean(s_beto)), 4) if s_beto else None,
            "KPI_10b_n_entidades": len(s_beto),
            "KPI_10_previo_media_por_registro": round(float(np.mean(conf_registro)), 4),
            "KPI_11_directo_sin_regla_personas_pct": dist(bandas["pre"])["directo"]["porcentaje"],
            "KPI_11_directo_con_regla_personas_pct": dist(bandas["post"])["directo"]["porcentaje"],
        },
        "conteos_fuente_resolucion": fuentes,
        "distribucion_por_archivo": {a: {**{k: {"conteo": n, "porcentaje": round(n / sum(v) * 100.0, 2)} for k, n in zip(("directo", "hitl", "staging"), v)}, "total": sum(v)}
                                     for a, v in por_archivo.items()},
        "excepciones": _resumen_excepciones(excepciones, total),
    }
    out = ROOT_DIR / "docs" / "evidencias"
    out.mkdir(parents=True, exist_ok=True)
    (out / "lote_1387_uploads_data_arquitectura_b.json").write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "muestra_50_entidades_beto_semilla42.json").write_text(
        json.dumps({"semilla": 42, "total_entidades_beto": len(ent_beto), "muestra": muestra}, indent=2, ensure_ascii=False),
        encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("dimensiones_dw_usadas", "personas", "personas_hitl_desglose_regla_previa_umbral_085", "personas_hitl_desglose_bloqueo_escalonado_umbral_092", "personas_resueltas_por_nivel", "distribucion_bandas_sin_regla_personas",
                                          "distribucion_bandas_con_regla_personas", "kpis", "conteos_fuente_resolucion")},
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
