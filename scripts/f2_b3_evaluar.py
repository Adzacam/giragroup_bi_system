#!/usr/bin/env python
"""F2-3 (B-3 / P-3): Evaluación de gold_510 con beto-v2 usando el evaluador exacto de F0 (evaluar_f0_gold.py) + control v1."""
import csv
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ["BETO_INT8"] = "0"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["PYTHONHASHSEED"] = "0"

from scripts import ablacion_beto as legacy  # noqa: E402
from scripts import evaluar_f0_gold as f0_eval  # noqa: E402

MED = ROOT / "docs/mediciones"


def evaluar_modelo(modelo_dir: Path, gold_path: Path, records: list) -> dict:
    original = legacy.classification_report
    captured = []

    def capture(g, p, **kw):
        captured.append((g, p))
        return original(g, p, **kw)

    legacy.classification_report = capture
    try:
        evaluator = legacy.EvaluadorAblacion(model_dir=str(modelo_dir))
        rows = []
        por_modo = {}
        for mode in ("A", "B", "C"):
            legacy_res = evaluator.evaluar_dataset_gold(str(gold_path), mode)
            gs, ps = captured.pop()
            mode_records = []
            for i, (g, p) in enumerate(zip(gs, ps), 1):
                gsp = f0_eval.spans_iob2(g)
                psp = f0_eval.spans_iob2(p)
                matches = {
                    name: f0_eval.match(gsp, psp, rel)
                    for name, rel in (("strict", False), ("relaxed", True))
                }
                mode_records.append({"line_id": i, "gold": gsp, "prediction": psp, "matches": matches})

            por_modo[mode] = {}
            for name in ("strict", "relaxed"):
                tp = sum(len(r["matches"][name]) for r in mode_records)
                ng = sum(len(r["gold"]) for r in mode_records)
                np_ = sum(len(r["prediction"]) for r in mode_records)
                met = f0_eval.metrics(tp, np_ - tp, ng - tp)
                per_type = {}
                for typ in f0_eval.TYPES:
                    t = sum(sum(r["gold"][i][0] == typ for i, _j in r["matches"][name]) for r in mode_records)
                    g_cnt = sum(sum(s[0] == typ for s in r["gold"]) for r in mode_records)
                    p_cnt = sum(sum(s[0] == typ for s in r["prediction"]) for r in mode_records)
                    per_type[typ] = f0_eval.metrics(t, p_cnt - t, g_cnt - t)
                rows.append({"mode": mode, "criterion": name, **met})
                por_modo[mode][name] = {**met, "by_type": per_type}
            por_modo[mode]["legacy_seqeval"] = {
                k: v for k, v in legacy_res.items() if k in ("reporte_seqeval_estricto", "reporte_seqeval_relajado")
            }
        return {"rows": rows, "por_modo": por_modo}
    finally:
        legacy.classification_report = original


def main() -> None:
    gold_path = ROOT / "data/test_gold_real.jsonl"
    records = [json.loads(s) for s in gold_path.read_text(encoding="utf-8").splitlines() if s.strip()]

    res_v1 = evaluar_modelo(ROOT / "output/f1/beto_local_respaldo", gold_path, records)
    res_v2 = evaluar_modelo(ROOT / "pipeline/semantic/beto_local", gold_path, records)

    # Control: v1 debe reproducir f0_b3_ablacion.csv con delta = 0
    f0_ref = {(r["mode"], r["criterion"]): r for r in csv.DictReader((MED / "f0_b3_ablacion.csv").open(encoding="utf-8"))}
    control_v1 = []
    for row in res_v1["rows"]:
        ref = f0_ref[(row["mode"], row["criterion"])]
        d_tp = row["tp"] - int(ref["tp"])
        d_fp = row["fp"] - int(ref["fp"])
        d_fn = row["fn"] - int(ref["fn"])
        control_v1.append({
            "mode": row["mode"],
            "criterion": row["criterion"],
            "delta_tp": d_tp,
            "delta_fp": d_fp,
            "delta_fn": d_fn,
            "exacto_delta_0": (d_tp == 0 and d_fp == 0 and d_fn == 0),
        })

    # Datos del Gráfico 3.1: soporte 510 por tipo y explicación del 503
    f0_conteos = json.loads((MED / "f0_b3_conteos.json").read_text(encoding="utf-8"))
    d3b_cal = json.loads((MED / "f1_d3b_calidad.json").read_text(encoding="utf-8"))

    csv_out = MED / "f2_b3_ablacion_v2.csv"
    with csv_out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(res_v2["rows"][0]))
        w.writeheader()
        w.writerows(res_v2["rows"])

    out = {
        "tarea": "F2-3 (B-3 / P-3)",
        "estado": "F2, provisional",
        "timestamp": datetime.now(timezone.utc).astimezone().isoformat(),
        "semilla": 42,
        "evaluador_f0_sha256": f0_eval.sha(ROOT / "scripts/evaluar_f0_gold.py"),
        "ablacion_beto_sha256": f0_eval.sha(ROOT / "scripts/ablacion_beto.py"),
        "gold_sha256": f0_eval.sha(gold_path),
        "modelo_v2_sha256": f0_eval.sha(ROOT / "pipeline/semantic/beto_local/model.safetensors"),
        "control_v1_vs_f0_b3": {
            "reproduce_delta_0": all(x["exacto_delta_0"] for x in control_v1),
            "filas": control_v1,
        },
        "v2_rows": res_v2["rows"],
        "v2_por_modo": res_v2["por_modo"],
        "grafico_3_1_soporte": {
            "soporte_total": f0_conteos["full_gold_support"],
            "visible_128_support": f0_conteos["visible_128_support"],
            "por_tipo": f0_conteos["full_by_type"],
            "explicacion_503": f0_conteos["definition"],
        },
        "diferencia_con_seqeval_d3b": {
            "nota": (
                "En D3B (f1_d3b_calidad.json), scripts/ablacion_beto.py usa seqeval por defecto para estricto y any-overlap para relajado; "
                "el evaluador de F0 (evaluar_f0_gold.py) usa IOB2 estricto explícito y emparejamiento bipartito 1:1 para relajado. "
                "No se mezclan cifras entre ambos evaluadores."
            ),
            "d3b_v2_modo_c_seqeval": [
                r for r in d3b_cal["filas"]
                if r["version"] == "beto-v2" and r["dataset"] == "gold_510" and r["modo"] == "C"
            ],
        },
    }
    json_out = MED / "f2_b3_ablacion_v2.json"
    json_out.write_text(
        json.dumps(out, indent=2, ensure_ascii=False, default=lambda v: v.item()) + "\n",
        encoding="utf-8",
    )
    print(f"[OK] Control v1 delta=0: {out['control_v1_vs_f0_b3']['reproduce_delta_0']}")
    for r in res_v2["rows"]:
        print(f"v2 {r['mode']} {r['criterion']:7s}: TP={r['tp']} FP={r['fp']} FN={r['fn']} F1={r['f1']:.6f}")


if __name__ == "__main__":
    main()
