#!/usr/bin/env python
"""F2-4 (B-4 / P-4): Consolida auditoría del corpus de beto-v2 desde archivos existentes."""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MED = ROOT / "docs/mediciones"


def main() -> None:
    d3b_val = json.loads((MED / "f1_d3b_validez.json").read_text(encoding="utf-8"))
    f1_corp = json.loads((MED / "f1_corpus_auditoria.json").read_text(encoding="utf-8"))
    f0_aud = json.loads((MED / "f0_b4_auditoria.json").read_text(encoding="utf-8"))

    v2_meta = d3b_val["tabla_v1_vs_v2"]["beto-v2"]
    v2_td = d3b_val["orden_aumento_separacion"]["prueba_empirica_train_vs_dev"]["beto-v2"]

    fuga_v2 = {}
    for cruce in ("v2_train_vs_gold_510", "v2_train_vs_layouts_5"):
        d = d3b_val["fuga_4_niveles"][cruce]
        fuga_v2[cruce] = {
            "a_oracion_exacta": d["a_oracion_exacta"]["coincidencias"],
            "b_texto_normalizado": d["b_texto_normalizado"]["coincidencias"],
            "c_variantes_total_unicas": d["c_variantes"]["coincidencias_total_unicas"],
            "d_personas_normalizadas_compartidas": d["d_personas_normalizadas_compartidas"]["personas_unicas_compartidas"],
        }

    out = {
        "tarea": "F2-4 (B-4 / P-4)",
        "estado": "F2, provisional",
        "timestamp": datetime.now(timezone.utc).astimezone().isoformat(),
        "fuentes": [
            "docs/mediciones/f1_d3b_validez.json",
            "docs/mediciones/f1_corpus_auditoria.json",
            "docs/mediciones/f0_b4_auditoria.json",
        ],
        "orden_separacion_aumento": {
            "separa_antes_de_aumentar": d3b_val["orden_aumento_separacion"]["separa_antes_de_aumentar"],
            "script": d3b_val["orden_aumento_separacion"]["script"],
            "evidencia_codigo": d3b_val["orden_aumento_separacion"]["evidencia_codigo"],
        },
        "corpus_v2": {
            "train": v2_meta["train_corpus"],
            "dev": v2_meta["dev_corpus"],
            "determinismo_sha256_identico": f1_corp["determinismo_sha256_identico"],
            "sha256_auditoria_f1": f1_corp["archivos"],
            "solapamiento_f1": f1_corp["solapamiento"],
        },
        "personas_train_dev_v2": {
            "personas_compartidas_spans": v2_td["personas_compartidas_train_dev_spans"],
            "personas_compartidas_iob2": v2_td["personas_compartidas_train_dev_iob2"],
            "nota": v2_td["nota_iob2_vs_spans"],
        },
        "fuga_4_niveles_v2": fuga_v2,
        "anotacion_gold_510": {
            "fuente": "docs/mediciones/f0_b4_auditoria.json",
            "gold_dataset": f0_aud["datasets"]["gold"],
            "annotation": f0_aud["annotation"],
        },
    }
    dest = MED / "f2_b4_corpus_v2.json"
    dest.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[OK] Escrito {dest.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
