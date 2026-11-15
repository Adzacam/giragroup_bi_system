#!/usr/bin/env python
"""F1-L: Puerta de fuga para D3 (gold_510 y layouts_5 frente a train/dev de reproduccion_1).

Solo publica conteos y hashes SHA-256 (sin texto ni nombres de personas).
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Set, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.preparar_corpus_robusto import clave_persona, strip_accents


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def norm_oracion(tokens: Sequence[str]) -> str:
    return " ".join(strip_accents(" ".join(tokens)).lower().split())


def extraer_personas_iob2(tokens: Sequence[str], tags: Sequence[str]) -> Set[str]:
    personas: Set[str] = set()
    actual: List[str] = []
    tipo_actual: str = ""
    for tok, tag in zip(tokens, tags):
        if tag.startswith("B-") and tag[2:] in ("PER_ESTUDIANTE", "PER_DOCENTE"):
            if actual:
                clave = clave_persona(" ".join(actual))
                if clave:
                    personas.add(clave)
            actual = [tok]
            tipo_actual = tag[2:]
        elif tag.startswith("I-") and actual and tag[2:] == tipo_actual:
            actual.append(tok)
        else:
            if actual:
                clave = clave_persona(" ".join(actual))
                if clave:
                    personas.add(clave)
                actual = []
                tipo_actual = ""
    if actual:
        clave = clave_persona(" ".join(actual))
        if clave:
            personas.add(clave)
    return personas


def cargar_jsonl(path: Path) -> Tuple[Set[str], Set[str], int]:
    oraciones: Set[str] = set()
    personas: Set[str] = set()
    filas = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        filas += 1
        rec = json.loads(line)
        tokens = rec.get("tokens") or []
        tags = rec.get("tags") or []
        oraciones.add(norm_oracion(tokens))
        personas.update(extraer_personas_iob2(tokens, tags))
    return oraciones, personas, filas


def cargar_layouts(path: Path) -> Tuple[Set[str], Set[str], int]:
    data = json.loads(path.read_text(encoding="utf-8"))["ejemplos"]
    oraciones: Set[str] = set()
    personas: Set[str] = set()
    for rec in data:
        tokens = rec.get("tokens") or []
        tags = rec.get("tags") or []
        oraciones.add(norm_oracion(tokens))
        personas.update(extraer_personas_iob2(tokens, tags))
    return oraciones, personas, len(data)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus-dir", default="output/f1/reproduccion_1/corpus")
    ap.add_argument("--gold", default="data/test_gold_real.jsonl")
    ap.add_argument("--layouts", default="uploads/test/layouts_adversarios/gold_layouts_adversarios.json")
    ap.add_argument("--salida", default="docs/mediciones/f1_fuga_evaluacion.json")
    args = ap.parse_args()

    corpus_dir = ROOT / args.corpus_dir
    train_path = corpus_dir / "train_robusto.jsonl"
    dev_path = corpus_dir / "dev_robusto.jsonl"
    gold_path = ROOT / args.gold
    layouts_path = ROOT / args.layouts

    train_s, train_p, train_n = cargar_jsonl(train_path)
    dev_s, dev_p, dev_n = cargar_jsonl(dev_path)
    gold_s, gold_p, gold_n = cargar_jsonl(gold_path)
    lay_s, lay_p, lay_n = cargar_layouts(layouts_path)

    cruces = {}
    max_oraciones = 0
    for nombre_a, sa, pa in (("train", train_s, train_p), ("dev", dev_s, dev_p)):
        for nombre_b, sb, pb in (("gold_510", gold_s, gold_p), ("layouts_5", lay_s, lay_p)):
            sol_orac = len(sa & sb)
            sol_pers = len(pa & pb)
            max_oraciones = max(max_oraciones, sol_orac)
            cruces[f"{nombre_a}_vs_{nombre_b}"] = {
                "oraciones_normalizadas_solapadas": sol_orac,
                "personas_normalizadas_compartidas": sol_pers,
            }

    resultado = {
        "puerta": "F1-L",
        "criterio": "solapamiento_oraciones_normalizadas == 0 en todos los cruces",
        "fuentes": {
            "train_robusto": {"ruta": train_path.relative_to(ROOT).as_posix(), "sha256": sha256_file(train_path), "filas": train_n, "oraciones_unicas": len(train_s), "personas_unicas": len(train_p)},
            "dev_robusto": {"ruta": dev_path.relative_to(ROOT).as_posix(), "sha256": sha256_file(dev_path), "filas": dev_n, "oraciones_unicas": len(dev_s), "personas_unicas": len(dev_p)},
            "gold_510": {"ruta": gold_path.relative_to(ROOT).as_posix(), "sha256": sha256_file(gold_path), "filas": gold_n, "oraciones_unicas": len(gold_s), "personas_unicas": len(gold_p)},
            "layouts_5": {"ruta": layouts_path.relative_to(ROOT).as_posix(), "sha256": sha256_file(layouts_path), "filas": lay_n, "oraciones_unicas": len(lay_s), "personas_unicas": len(lay_p)},
        },
        "cruces": cruces,
        "veredicto": "pasa" if max_oraciones == 0 else "no pasa",
    }

    out_path = ROOT / args.salida
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(resultado, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(resultado, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
