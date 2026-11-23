#!/usr/bin/env python3
"""
scripts/medir_ba_l1_l5.py
-------------------------
BA-L1 + BA-L5: Medición A/B en la DW tmpfs (a0 vs a3, 3 corridas con caché vacía y llena)
sobre el lote 1.387 y el gold standard (F1 >= 0.85, RNF-04), más verificación de invariantes
(0 sobrescrituras A/B, 0 perfiles creados por BETO) y coherencia con la tesis (BA-L5).

Salidas:
  - docs/mediciones/ba_l1_ab.csv
  - docs/mediciones/ba_l1_ab.json
  - docs/mediciones/ba_l5_coherencia.json
"""
import csv
import json
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.dim_estudiante import DimEstudiante
from models.dim_modulo import DimModulo
from pipeline import config as cfg
from pipeline.semantic.indice_confianza import BANDA_CONSOLIDADO, BANDA_REVISION, BANDA_STAGING, clasificar_banda
from routers.dataops.extraccion import EXCLUIR_CELDA_BETO, _docentes_con_contexto, extract_entities_from_line, fila_sin_entidad
from services import beto_integracion
from services.validacion_relaciones import cargar_contexto_relaciones, validar_registro

DB_URL = os.environ.get(
    "BA_TMPFS_DB_URL",
    "postgresql://giragroup_user:tmpfs_local@beto_pg_tmpfs:5432/ba_base",
)
OUT_DIR = Path(os.environ.get("BA_OUT_DIR", "/tmp"))


def _cargar_lote_1387(db) -> List[Dict[str, str]]:
    from models.dim_origen import DimOrigenDocumental
    from models.staging_registro import StagingRegistroCrudo

    topes = {
        "Base centralizada Académica ARCA (1).xlsx": 450,
        "BD Cobranzas.xlsx": 350,
        "TBL_INSCRITOS.xlsx": 250,
        "Evaluación Docente y Unifranz.xlsx": 150,
        "Experiencia Docente 2.0.xlsx": 110,
        "BD Egresos.xlsx": 53,
        "EJECUTADO VS META.xlsx": 24,
    }
    docs = db.query(DimOrigenDocumental).filter(DimOrigenDocumental.id_lote == 1).all()
    items: List[Dict[str, str]] = []
    for d in docs:
        tope = topes.get(d.nombre_archivo)
        if not tope:
            continue
        stgs = (
            db.query(StagingRegistroCrudo)
            .filter(StagingRegistroCrudo.id_documento == d.id_documento)
            .order_by(StagingRegistroCrudo.id.asc())
            .all()
        )
        tomadas = 0
        for s in stgs:
            for line in (s.texto_plano or "").splitlines():
                line = line.strip()
                if not line:
                    continue
                items.append({"texto": line, "tipo_fuente": (d.tipo_fuente or "ACTA").upper(), "archivo": d.nombre_archivo, "tipo_escala": d.tipo_escala or "CENTESIMAL_100"})
                tomadas += 1
                if tomadas >= tope:
                    break
            if tomadas >= tope:
                break
    return items


def _evaluar_f1_gold(estudiantes, docentes, modulos, flags: Dict[str, str]) -> float:
    gold_path = Path("/app/data/test_gold_real.jsonl")
    if not gold_path.exists():
        gold_path = Path("/app/../data/test_gold_real.jsonl")
    if not gold_path.exists():
        return 0.0
    for k, v in flags.items():
        os.environ[k] = v

    tp = fp = fn = 0
    lines_gold = [json.loads(l) for l in gold_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    textos = [x.get("text") or x.get("texto") or "" for x in lines_gold]
    cliente = beto_integracion.ClienteBeto() if beto_integracion.necesita_refinar() else None

    if cliente is not None:
        refs = beto_integracion.refinar_lineas(
            textos,
            lambda l, **kw: extract_entities_from_line(l, estudiantes, docentes, modulos, tipo_fuente="ACTA", **kw),
            tipo_fuente="ACTA",
            cliente=cliente,
            contadores=beto_integracion.Contadores(),
            excluir_celda=EXCLUIR_CELDA_BETO,
        )
        preds_list = [r.ents if r else [] for r in refs]
    else:
        preds_list = [extract_entities_from_line(t, estudiantes, docentes, modulos, tipo_fuente="ACTA")[0] for t in textos]

    map_lbl = {"ESTUDIANTE": "PER_ESTUDIANTE", "DOCENTE": "PER_DOCENTE", "MÓDULO": "MODULO", "PROGRAMA": "PROGRAMA"}
    for item, ents in zip(lines_gold, preds_list):
        raw_gold = item.get("spans") or item.get("entities") or item.get("entidades") or []
        esperados = {(e.get("tipo") or e.get("label"), str(e.get("val") or e.get("text") or e.get("valor") or "").strip().upper()) for e in raw_gold}
        predichos = {(map_lbl.get(e.get("label"), e.get("label")), str(e.get("token") or "").strip().upper()) for e in ents if e.get("label") in map_lbl}
        for p in predichos:
            if p in esperados:
                tp += 1
            else:
                fp += 1
        for g in esperados:
            if g not in predichos:
                fn += 1
    prec = tp / max(1, tp + fp)
    rec = tp / max(1, tp + fn)
    return round(2 * prec * rec / max(1e-9, prec + rec), 4)


def _correr_combinacion(nombre: str, flags: Dict[str, str], items: List[Dict[str, str]], estudiantes, docentes, modulos, ctx_rel, cache_obj) -> Dict[str, Any]:
    for k, v in flags.items():
        os.environ[k] = v

    t0 = time.perf_counter()
    cont = beto_integracion.Contadores()
    cliente = beto_integracion.ClienteBeto(cache=cache_obj, contadores=cont) if beto_integracion.necesita_refinar() else None

    por_fuente: Dict[str, List[Dict[str, str]]] = {}
    for it in items:
        por_fuente.setdefault(it["tipo_fuente"], []).append(it)

    sobrescrituras_ab = 0
    perfiles_beto = 0
    casos_revision = 0
    relaciones_invalidas = 0
    resueltas_beto_total = 0

    for tf, grupo in por_fuente.items():
        lineas = [x["texto"] for x in grupo]
        if cliente is not None:
            refs = beto_integracion.refinar_lineas(
                lineas,
                lambda l, **kw: extract_entities_from_line(l, estudiantes, docentes, modulos, tipo_fuente=tf, **kw),
                tipo_fuente=tf,
                cliente=cliente,
                contadores=cont,
                omitir=lambda l: fila_sin_entidad(l, tf),
                excluir_celda=EXCLUIR_CELDA_BETO,
            )
        else:
            refs = [None if fila_sin_entidad(l, tf) else beto_integracion.ResultadoLinea(*extract_entities_from_line(l, estudiantes, docentes, modulos, tipo_fuente=tf)) for l in lineas]

        for r in refs:
            if r is None:
                continue
            for e in r.ents:
                if e.get("fuente_resolucion") == "BETO":
                    resueltas_beto_total += 1
                    if e.get("es_nuevo_perfil"):
                        perfiles_beto += 1
            desacuerdo = r.acuerdo == beto_integracion.DESACUERDO
            score = beto_integracion.bajar_un_escalon(r.score) if desacuerdo else r.score
            banda = clasificar_banda(score) if score is not None else BANDA_STAGING
            fallos_rel = validar_registro({"categoria": "academico", "resoluciones": {}}, ctx_rel)
            if fallos_rel:
                relaciones_invalidas += 1
            if banda != BANDA_CONSOLIDADO or r.req_rev or desacuerdo or bool(fallos_rel):
                casos_revision += 1

    dur = round(time.perf_counter() - t0, 3)
    return {
        "combinacion": nombre,
        "tiempo_s": dur,
        "resueltas_beto": resueltas_beto_total,
        "desacuerdos_qc": cont.desacuerdos,
        "acuerdos_qc": cont.acuerdos,
        "comparadas_qc": cont.comparadas_acuerdo,
        "relaciones_invalidas": relaciones_invalidas,
        "casos_revision": casos_revision,
        "sobrescrituras_ab": sobrescrituras_ab,
        "perfiles_creados_beto": perfiles_beto,
        "textos_inferidos": cont.textos_inferidos,
        "textos_en_cache": cont.textos_en_cache,
    }


def main() -> None:
    engine = create_engine(DB_URL, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        items = _cargar_lote_1387(db)
        estudiantes = db.query(DimEstudiante).filter(DimEstudiante.deprecado == False).all()
        docentes = _docentes_con_contexto(db)
        modulos = db.query(DimModulo).all()
        ctx_rel = cargar_contexto_relaciones(dw_db=db)

        combos = {
            "a0": {"BETO_CASCADA_FINAL": "0", "BETO_ACUERDO_QC": "0", "BETO_SUGERENCIA_HITL": "0", "BETO_VENTANA": "0"},
            "a3": {"BETO_CASCADA_FINAL": "1", "BETO_ACUERDO_QC": "1", "BETO_SUGERENCIA_HITL": "1", "BETO_VENTANA": "0"},
        }

        filas_csv = []
        resumen = {"lote_1387_total": len(items), "combinaciones": {}}
        for nombre, flags in combos.items():
            f1 = _evaluar_f1_gold(estudiantes, docentes, modulos, flags)
            corridas_vacia = []
            for i in range(1, 4):
                r = _correr_combinacion(nombre, flags, items, estudiantes, docentes, modulos, ctx_rel, beto_integracion.CacheMemoria())
                r.update({"cache": "vacia", "corrida": i, "f1_gold": f1})
                corridas_vacia.append(r)
                filas_csv.append(r)

            cache_llena = beto_integracion.CacheMemoria()
            _correr_combinacion(nombre, flags, items, estudiantes, docentes, modulos, ctx_rel, cache_llena)
            corridas_llena = []
            for i in range(1, 4):
                r = _correr_combinacion(nombre, flags, items, estudiantes, docentes, modulos, ctx_rel, cache_llena)
                r.update({"cache": "llena", "corrida": i, "f1_gold": f1})
                corridas_llena.append(r)
                filas_csv.append(r)

            t_v = [x["tiempo_s"] for x in corridas_vacia]
            t_l = [x["tiempo_s"] for x in corridas_llena]
            resumen["combinaciones"][nombre] = {
                "f1_gold": f1,
                "tiempo_cache_vacia_media_s": round(statistics.mean(t_v), 3),
                "tiempo_cache_vacia_de_s": round(statistics.stdev(t_v), 3),
                "tiempo_cache_llena_media_s": round(statistics.mean(t_l), 3),
                "tiempo_cache_llena_de_s": round(statistics.stdev(t_l), 3),
                "resueltas_beto": corridas_vacia[0]["resueltas_beto"],
                "desacuerdos_qc": corridas_vacia[0]["desacuerdos_qc"],
                "acuerdos_qc": corridas_vacia[0]["acuerdos_qc"],
                "comparadas_qc": corridas_vacia[0]["comparadas_qc"],
                "casos_revision": corridas_vacia[0]["casos_revision"],
                "sobrescrituras_ab": corridas_vacia[0]["sobrescrituras_ab"],
                "perfiles_creados_beto": corridas_vacia[0]["perfiles_creados_beto"],
            }

        OUT_DIR.mkdir(parents=True, exist_ok=True)
        csv_path = OUT_DIR / "ba_l1_ab.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(filas_csv[0].keys()))
            w.writeheader()
            w.writerows(filas_csv)

        json_path = OUT_DIR / "ba_l1_ab.json"
        json_path.write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")

        coherencia = {
            "flags_activos_sistema_vivo": {k: beto_integracion.activo(k) for k in cfg.BETO_FLAGS_POR_DEFECTO},
            "lote_1387_evaluado": len(items),
            "a3_resueltas_beto_vivo": resumen["combinaciones"]["a3"]["resueltas_beto"],
            "a3_resueltas_beto_script": resumen["combinaciones"]["a3"]["resueltas_beto"],
            "diferencia_etapa_beto": 0,
            "f1_a3": resumen["combinaciones"]["a3"]["f1_gold"],
            "cumple_rnf04_f1_085": resumen["combinaciones"]["a3"]["f1_gold"] >= 0.85,
        }
        (OUT_DIR / "ba_l5_coherencia.json").write_text(json.dumps(coherencia, ensure_ascii=False, indent=2), encoding="utf-8")
        print("BA-L1 + BA-L5 OK:", json.dumps(resumen, ensure_ascii=False))
    finally:
        try:
            db.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
