#!/usr/bin/env python
"""Consolida las 24 filas de D-A (v1 y v2 x gold_510 y layouts_5 x A/B/C x strict/relaxed)."""
import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import torch
import transformers

ROOT = Path(__file__).resolve().parents[1]
MED = ROOT / "docs/mediciones"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    filas = []
    fuentes = [
        ("beto-v1", "gold_510", MED / "f1_d3b_calidad_v1_gold.json"),
        ("beto-v1", "layouts_5", MED / "f1_d3b_calidad_v1_layouts.json"),
        ("beto-v2", "gold_510", MED / "f1_d3b_calidad_v2_gold.json"),
        ("beto-v2", "layouts_5", MED / "f1_d3b_calidad_v2_layouts.json"),
    ]

    for version, dataset, path in fuentes:
        data = json.loads(path.read_text(encoding="utf-8"))
        for modo in ("A", "B", "C"):
            bloque = data["por_modo"][modo][dataset]
            support = int(bloque["reporte_seqeval_estricto"]["micro avg"]["support"])
            for crit_key, criterio in (
                ("reporte_seqeval_estricto", "strict"),
                ("reporte_seqeval_relajado", "relaxed"),
            ):
                if crit_key == "reporte_seqeval_estricto":
                    mic = bloque[crit_key]["micro avg"]
                    p = float(mic["precision"])
                    r = float(mic["recall"])
                    f1 = float(mic["f1-score"])
                else:
                    rel = bloque[crit_key]
                    p = float(rel["p_micro_relajado"])
                    r = float(rel["r_micro_relajado"])
                    f1 = float(rel["f1_micro_relajado"])
                tp = int(round(r * support))
                fn = support - tp
                predicted = int(round(tp / p)) if p > 0 and tp > 0 else 0
                fp = predicted - tp
                filas.append(
                    {
                        "version": version,
                        "dataset": dataset,
                        "modo": modo,
                        "criterio": criterio,
                        "tp": tp,
                        "fp": fp,
                        "fn": fn,
                        "support": support,
                        "predicted": predicted,
                        "precision": round(p, 6),
                        "recall": round(r, 6),
                        "f1": round(f1, 6),
                        "fuente_json": str(path.relative_to(ROOT)).replace("\\", "/"),
                    }
                )

    # Control contra docs/mediciones/f0_b3_ablacion.csv (beto-v1 en gold_510)
    f0_rows = {}
    with (MED / "f0_b3_ablacion.csv").open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            f0_rows[(row["mode"], row["criterion"])] = row

    control_diffs = []
    for fila in filas:
        if fila["version"] == "beto-v1" and fila["dataset"] == "gold_510":
            ref = f0_rows[(fila["modo"], fila["criterio"])]
            d_tp = fila["tp"] - int(ref["tp"])
            d_fp = fila["fp"] - int(ref["fp"])
            d_fn = fila["fn"] - int(ref["fn"])
            d_f1 = round(fila["f1"] - float(ref["f1"]), 6)
            control_diffs.append(
                {
                    "modo": fila["modo"],
                    "criterio": fila["criterio"],
                    "d3b_v1": {"tp": fila["tp"], "fp": fila["fp"], "fn": fila["fn"], "f1": fila["f1"]},
                    "f0_b3": {
                        "tp": int(ref["tp"]),
                        "fp": int(ref["fp"]),
                        "fn": int(ref["fn"]),
                        "f1": round(float(ref["f1"]), 6),
                    },
                    "delta": {"tp": d_tp, "fp": d_fp, "fn": d_fn, "f1": d_f1},
                    "exacto_delta_0": (d_tp == 0 and d_fp == 0 and d_fn == 0),
                }
            )

    csv_out = MED / "f1_d3b_calidad.csv"
    campos = [
        "version",
        "dataset",
        "modo",
        "criterio",
        "tp",
        "fp",
        "fn",
        "support",
        "predicted",
        "precision",
        "recall",
        "f1",
        "fuente_json",
    ]
    with csv_out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(filas)

    resumen = {
        "tarea": "D-A",
        "timestamp": datetime.now(ZoneInfo("America/La_Paz")).isoformat(),
        "total_filas": len(filas),
        "entorno": {
            "ablacion_beto_ruta": "scripts/ablacion_beto.py",
            "ablacion_beto_sha256": sha256_file(ROOT / "scripts/ablacion_beto.py"),
            "semilla": 42,
            "BETO_INT8": "0",
            "max_tokens": 128,
            "torch": torch.__version__,
            "transformers": transformers.__version__,
        },
        "conjuntos": {
            "gold_510": {
                "ruta": "data/test_gold_real.jsonl",
                "sha256": sha256_file(ROOT / "data/test_gold_real.jsonl"),
                "soporte_declarado": 510,
                "motivo_soporte_510_vs_503": (
                    "Según docs/mediciones/f0_b3_conteos.json, data/test_gold_real.jsonl contiene 510 entidades "
                    "(130 PER_ESTUDIANTE, 180 PROGRAMA, 150 MODULO, 50 PER_DOCENTE), todas visibles dentro de max_tokens=128. "
                    "El valor histórico 503 provenía de una matriz 4x4 hardcodeada donde PROGRAMA sumaba 173 en lugar de 180."
                ),
            },
            "layouts_5": {
                "ruta": "uploads/test/layouts_adversarios/gold_layouts_adversarios.json",
                "sha256": sha256_file(ROOT / "uploads/test/layouts_adversarios/gold_layouts_adversarios.json"),
                "soporte_declarado": 72,
            },
        },
        "control_f0_b3_ablacion": {
            "reproduce_exactamente_delta_0": all(x["exacto_delta_0"] for x in control_diffs),
            "causa_diferencia": (
                "En modos A y B sobre gold_510, delta = 0 (F1 = 1.0). En modo C sobre gold_510: en relajado TP=508, FP=7, FN=2 "
                "(delta_f1 = -0.000020 por redondeo a 4 decimales); en estricto hay delta_FP = +2 (FP=16 vs 14, F1=0.975657 vs 0.977561) "
                "porque f0_b3_ablacion.csv fue calculado con el evaluador auxiliar de F0 (evaluator_sha256 555c085d..., IOB2 estricto explícito), "
                "mientras que scripts/ablacion_beto.py usa seqeval en modo por defecto. Ambas versiones v1 y v2 se midieron con el mismo "
                "scripts/ablacion_beto.py y las mismas versiones de torch y transformers, por lo que la comparación v1 vs v2 es homogénea."
            ),
            "filas": control_diffs,
        },
        "filas": filas,
    }
    json_out = MED / "f1_d3b_calidad.json"
    json_out.write_text(json.dumps(resumen, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Escrito {csv_out.relative_to(ROOT)} y {json_out.relative_to(ROOT)} ({len(filas)} filas)")
    for d in control_diffs:
        print("control", d["modo"], d["criterio"], "delta=", d["delta"])


if __name__ == "__main__":
    main()
