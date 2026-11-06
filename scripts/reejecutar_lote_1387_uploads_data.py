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

from pipeline.normalization.person_resolver import resolver_persona, cargar_personas_dw
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


def _banda(c):
    return 0 if c >= 0.85 else (1 if c >= 0.60 else 2)


def main():
    lote = cargar_lote_1387_uploads_data()
    assert len(lote) == 1387, f"Se esperaban 1.387 registros, se obtuvieron {len(lote)}"
    evaluador = EvaluadorAblacion()
    est_dw = cargar_personas_dw("dim_estudiante")
    doc_dw = cargar_personas_dw("dim_docente")
    print(f"Dimensiones del DW: dim_estudiante={len(est_dw)}, dim_docente={len(doc_dw)}")

    bandas = {"pre": [0, 0, 0], "post": [0, 0, 0]}
    conf_registro, s_todas, s_beto, ent_beto = [], [], [], []
    fuentes = {"CI_EXACTA": 0, "ENCABEZADO": 0, "FUZZY": 0, "REGEX": 0, "BETO": 0}
    personas = {"total": 0, "resueltas_CI_EXACTA": 0, "resueltas_FUZZY": 0, "sin_coincidencia_HITL": 0}
    directo_a_hitl = 0

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
        sin_resolver = False
        for e in todas:
            if e["tipo"] not in ("PER_ESTUDIANTE", "PER_DOCENTE"):
                continue
            personas["total"] += 1
            est = e["tipo"] == "PER_ESTUDIANTE"
            r = resolver_persona(e["valor"], ci if est else None, est_dw if est else doc_dw, contexto=ctx)
            if r:
                personas["resueltas_" + r["fuente"]] += 1
            else:
                personas["sin_coincidencia_HITL"] += 1
                sin_resolver = True
        b_post = max(b_pre, 1) if sin_resolver else b_pre  # sin coincidencia -> HITL
        if sin_resolver and b_pre == 0:
            directo_a_hitl += 1
        bandas["post"][b_post] += 1

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
        "distribucion_bandas_sin_regla_personas": dist(bandas["pre"]),
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
    }
    out = ROOT_DIR / "docs" / "evidencias"
    out.mkdir(parents=True, exist_ok=True)
    (out / "lote_1387_uploads_data_arquitectura_b.json").write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "muestra_50_entidades_beto_semilla42.json").write_text(
        json.dumps({"semilla": 42, "total_entidades_beto": len(ent_beto), "muestra": muestra}, indent=2, ensure_ascii=False),
        encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("dimensiones_dw_usadas", "personas", "distribucion_bandas_sin_regla_personas",
                                          "distribucion_bandas_con_regla_personas", "kpis", "conteos_fuente_resolucion")},
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
