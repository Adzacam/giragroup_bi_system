#!/usr/bin/env python
"""D-B: Validez del reentrenamiento de beto-v2 frente a beto-v1 (solo lectura)."""
import hashlib
import json
import re
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.auditar_f0_corpus import normalize as normalize_f0
from scripts.f1_fuga_evaluacion import extraer_personas_iob2, norm_oracion, sha256_file
from scripts.preparar_corpus_robusto import clave_persona

TITULOS_RE = re.compile(r"\b(lic|ing|msc|dr|dra|prof|mg)\b\.?\s*", re.IGNORECASE)


def leer_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def leer_layouts(path: Path) -> List[Dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))["ejemplos"]


def texto_registro(rec: Dict[str, Any]) -> str:
    if "texto" in rec and rec["texto"]:
        return rec["texto"]
    return " ".join(rec.get("tokens") or [])


def norm_texto_sin_titulos(rec: Dict[str, Any]) -> str:
    txt = texto_registro(rec)
    sin_titulos = TITULOS_RE.sub(" ", txt)
    return normalize_f0(sin_titulos)


def plantilla_enmascarada(rec: Dict[str, Any]) -> str:
    tokens = rec.get("tokens") or []
    tags = rec.get("tags") or []
    salida: List[str] = []
    for tok, tag in zip(tokens, tags):
        if tag.startswith("B-"):
            salida.append(f"<{tag[2:]}>")
        elif tag.startswith("I-"):
            continue
        else:
            norm_tok = normalize_f0(tok)
            if norm_tok:
                salida.append(norm_tok)
    return " ".join(salida)


def tokens_normalizados_set(rec: Dict[str, Any]) -> Set[str]:
    return set(norm_texto_sin_titulos(rec).split())


def jaccard(a: Set[str], b: Set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def personas_registro(rec: Dict[str, Any]) -> Set[str]:
    return extraer_personas_iob2(rec.get("tokens") or [], rec.get("tags") or [])


def personas_corpus(records: List[Dict[str, Any]]) -> Set[str]:
    out: Set[str] = set()
    for r in records:
        out.update(personas_registro(r))
    return out


def personas_spans_corpus(records: List[Dict[str, Any]]) -> Set[str]:
    out: Set[str] = set()
    for r in records:
        for s in r.get("spans") or []:
            if s.get("tipo", "").startswith("PER_"):
                c = clave_persona(r["texto"][s["start"]:s["end"]])
                if c:
                    out.add(c)
    return out


def resumen_corpus(path: Path, records: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "ruta": str(path.relative_to(ROOT)).replace("\\", "/"),
        "sha256": sha256_file(path),
        "filas": len(records),
        "personas_unicas": len(personas_corpus(records)),
    }


def comparar_fuga(
    train_recs: List[Dict[str, Any]],
    eval_recs: List[Dict[str, Any]],
) -> Dict[str, Any]:
    # a) hash de la oración exacta
    tr_exact: Dict[str, List[int]] = defaultdict(list)
    for i, r in enumerate(train_recs, 1):
        h = hashlib.sha256(texto_registro(r).encode("utf-8")).hexdigest()
        tr_exact[h].append(i)
    pares_a = []
    for j, r in enumerate(eval_recs, 1):
        h = hashlib.sha256(texto_registro(r).encode("utf-8")).hexdigest()
        for i in tr_exact.get(h, []):
            pares_a.append({"train_idx": i, "eval_idx": j, "sha256": h})

    # b) hash del texto normalizado (NFKD, casefold, sin tildes ni títulos)
    tr_norm: Dict[str, List[int]] = defaultdict(list)
    for i, r in enumerate(train_recs, 1):
        h = hashlib.sha256(norm_texto_sin_titulos(r).encode("utf-8")).hexdigest()
        tr_norm[h].append(i)
    pares_b = []
    for j, r in enumerate(eval_recs, 1):
        h = hashlib.sha256(norm_texto_sin_titulos(r).encode("utf-8")).hexdigest()
        for i in tr_norm.get(h, []):
            pares_b.append({"train_idx": i, "eval_idx": j, "sha256": h})

    # c) variantes: plantilla con entidades enmascaradas por tipo y Jaccard >= 0.8
    tr_tpl: Dict[str, List[int]] = defaultdict(list)
    tr_toks: List[Set[str]] = []
    for i, r in enumerate(train_recs, 1):
        tr_tpl[plantilla_enmascarada(r)].append(i)
        tr_toks.append(tokens_normalizados_set(r))

    pares_c_plantilla = []
    pares_c_jaccard = []
    pares_c_unicos: Set[Tuple[int, int]] = set()
    for j, r in enumerate(eval_recs, 1):
        tpl = plantilla_enmascarada(r)
        for i in tr_tpl.get(tpl, []):
            pares_c_plantilla.append(
                {
                    "train_idx": i,
                    "eval_idx": j,
                    "plantilla_sha256": hashlib.sha256(tpl.encode("utf-8")).hexdigest(),
                }
            )
            pares_c_unicos.add((i, j))
        ev_toks = tokens_normalizados_set(r)
        for i, tr_t in enumerate(tr_toks, 1):
            sim = jaccard(tr_t, ev_toks)
            if sim >= 0.8:
                pares_c_jaccard.append(
                    {"train_idx": i, "eval_idx": j, "jaccard": round(sim, 4)}
                )
                pares_c_unicos.add((i, j))

    # d) personas normalizadas compartidas
    tr_pers: Dict[str, List[int]] = defaultdict(list)
    for i, r in enumerate(train_recs, 1):
        for p in personas_registro(r):
            tr_pers[p].append(i)
    pares_d = []
    personas_compartidas: Set[str] = set()
    for j, r in enumerate(eval_recs, 1):
        for p in sorted(personas_registro(r)):
            if p in tr_pers:
                personas_compartidas.add(p)
                for i in tr_pers[p]:
                    pares_d.append(
                        {
                            "train_idx": i,
                            "eval_idx": j,
                            "persona_sha256": hashlib.sha256(p.encode("utf-8")).hexdigest(),
                        }
                    )

    return {
        "a_oracion_exacta": {
            "coincidencias": len(pares_a),
            "pares": pares_a,
        },
        "b_texto_normalizado": {
            "coincidencias": len(pares_b),
            "pares": pares_b,
        },
        "c_variantes": {
            "coincidencias_total_unicas": len(pares_c_unicos),
            "plantilla_enmascarada_exacta": {
                "coincidencias": len(pares_c_plantilla),
                "pares": pares_c_plantilla,
            },
            "jaccard_tokens_norm_ge_0_8": {
                "coincidencias": len(pares_c_jaccard),
                "pares": pares_c_jaccard,
            },
        },
        "d_personas_normalizadas_compartidas": {
            "personas_unicas_compartidas": len(personas_compartidas),
            "coincidencias_pares": len(pares_d),
            "pares": pares_d,
        },
    }


def main() -> None:
    ti_v1 = json.loads(
        (ROOT / "output/f1/beto_local_respaldo/training_info.json").read_text(encoding="utf-8")
    )
    ti_v2 = json.loads(
        (ROOT / "docs/mediciones/f1_training_info.json").read_text(encoding="utf-8")
    )

    v1_train_p = ROOT / "data/train_robusto.jsonl"
    v1_dev_p = ROOT / "data/dev_robusto.jsonl"
    v2_train_p = ROOT / "output/f1/reproduccion_1/corpus/train_robusto.jsonl"
    v2_dev_p = ROOT / "output/f1/reproduccion_1/corpus/dev_robusto.jsonl"
    gold_p = ROOT / "data/test_gold_real.jsonl"
    layouts_p = ROOT / "uploads/test/layouts_adversarios/gold_layouts_adversarios.json"

    v1_train = leer_jsonl(v1_train_p)
    v1_dev = leer_jsonl(v1_dev_p)
    v2_train = leer_jsonl(v2_train_p)
    v2_dev = leer_jsonl(v2_dev_p)
    gold = leer_jsonl(gold_p)
    layouts = leer_layouts(layouts_p)

    v1_tr_pers = personas_corpus(v1_train)
    v1_dv_pers = personas_corpus(v1_dev)
    v2_tr_pers = personas_corpus(v2_train)
    v2_dv_pers = personas_corpus(v2_dev)
    v1_tr_sp = personas_spans_corpus(v1_train)
    v1_dv_sp = personas_spans_corpus(v1_dev)
    v2_tr_sp = personas_spans_corpus(v2_train)
    v2_dv_sp = personas_spans_corpus(v2_dev)

    resultado = {
        "tarea": "D-B",
        "timestamp": datetime.now(ZoneInfo("America/La_Paz")).isoformat(),
        "tabla_v1_vs_v2": {
            "beto-v1": {
                "training_info_ruta": "output/f1/beto_local_respaldo/training_info.json",
                "train_corpus": resumen_corpus(v1_train_p, v1_train),
                "dev_corpus": resumen_corpus(v1_dev_p, v1_dev),
                "epochs": ti_v1.get("epochs"),
                "best_epoch": ti_v1.get("best_epoch"),
                "learning_rate": ti_v1.get("learning_rate"),
                "weight_decay": ti_v1.get("weight_decay"),
                "batch_size": ti_v1.get("batch_size"),
                "max_length": ti_v1.get("max_length"),
                "seed": ti_v1.get("seed"),
                "train_duration_sec": ti_v1.get("train_duration_sec"),
                "best_dev_f1": ti_v1.get("best_dev_f1"),
            },
            "beto-v2": {
                "training_info_ruta": "docs/mediciones/f1_training_info.json",
                "train_corpus": resumen_corpus(v2_train_p, v2_train),
                "dev_corpus": resumen_corpus(v2_dev_p, v2_dev),
                "epochs": ti_v2.get("epochs"),
                "best_epoch": ti_v2.get("best_epoch"),
                "learning_rate": ti_v2.get("learning_rate"),
                "weight_decay": ti_v2.get("weight_decay"),
                "batch_size": ti_v2.get("batch_size"),
                "max_length": ti_v2.get("max_length"),
                "seed": ti_v2.get("seed"),
                "train_duration_sec": ti_v2.get("train_duration_sec"),
                "best_dev_f1": ti_v2.get("best_dev_f1"),
            },
        },
        "orden_aumento_separacion": {
            "separa_antes_de_aumentar": True,
            "script": "scripts/preparar_corpus_robusto.py",
            "evidencia_codigo": {
                "particion_por_claves_persona": "lineas 101-110 (particionar_por_persona con random.Random(semilla).shuffle(claves))",
                "llamada_particion": "linea 334 (train_p, dev_p = particionar_por_persona(ests + docs, args.fraccion_dev, args.semilla))",
                "aumento_por_pool_separado": "lineas 336-344 (est_tr/doc_tr y est_dv/doc_dv alimentan generar_muestras por separado)",
            },
            "prueba_empirica_train_vs_dev": {
                "beto-v1": {
                    "personas_train_iob2": len(v1_tr_pers),
                    "personas_dev_iob2": len(v1_dv_pers),
                    "personas_compartidas_train_dev_iob2": len(v1_tr_pers & v1_dv_pers),
                    "personas_compartidas_train_dev_spans": len(v1_tr_sp & v1_dv_sp),
                },
                "beto-v2": {
                    "personas_train_iob2": len(v2_tr_pers),
                    "personas_dev_iob2": len(v2_dv_pers),
                    "personas_compartidas_train_dev_iob2": len(v2_tr_pers & v2_dv_pers),
                    "personas_compartidas_train_dev_spans": len(v2_tr_sp & v2_dv_sp),
                    "nota_iob2_vs_spans": "Spans exactos comparten 0 personas; la diferencia de 1 en IOB2 proviene de tokenización de abreviaturas con punto (p.ej. 'M . Sc .').",
                },
            },
        },
        "conjuntos_evaluacion": {
            "gold_510": resumen_corpus(gold_p, gold),
            "layouts_5": resumen_corpus(layouts_p, layouts),
        },
        "fuga_4_niveles": {
            "v1_train_vs_gold_510": comparar_fuga(v1_train, gold),
            "v1_train_vs_layouts_5": comparar_fuga(v1_train, layouts),
            "v2_train_vs_gold_510": comparar_fuga(v2_train, gold),
            "v2_train_vs_layouts_5": comparar_fuga(v2_train, layouts),
        },
    }

    out = ROOT / "docs/mediciones/f1_d3b_validez.json"
    out.write_text(json.dumps(resultado, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Escrito {out.relative_to(ROOT)}")
    print("train/dev shared persons:", resultado["orden_aumento_separacion"]["prueba_empirica_train_vs_dev"])
    for k, v in resultado["fuga_4_niveles"].items():
        print(
            k,
            "a=", v["a_oracion_exacta"]["coincidencias"],
            "b=", v["b_texto_normalizado"]["coincidencias"],
            "c_total=", v["c_variantes"]["coincidencias_total_unicas"],
            "c_tpl=", v["c_variantes"]["plantilla_enmascarada_exacta"]["coincidencias"],
            "c_jac=", v["c_variantes"]["jaccard_tokens_norm_ge_0_8"]["coincidencias"],
            "d_pers=", v["d_personas_normalizadas_compartidas"]["personas_unicas_compartidas"],
        )


if __name__ == "__main__":
    main()
