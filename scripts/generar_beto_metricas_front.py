#!/usr/bin/env python3
"""Genera frontend/src/constants/betoMetricas.json desde las mediciones reales.

Lee directamente:
- docs/mediciones/f3r_matriz_confusion.json
- docs/mediciones/f3r_ablacion.json
- docs/mediciones/f1_training_info.json
- docs/mediciones/f1_evaluacion_despues/matriz_confusion_ner.json

Nunca escribe cifras a mano.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SRC_MATRIZ_ENTIDADES = ROOT / "docs" / "mediciones" / "f3r_matriz_confusion.json"
SRC_ABLACION = ROOT / "docs" / "mediciones" / "f3r_ablacion.json"
SRC_TRAINING = ROOT / "docs" / "mediciones" / "f1_training_info.json"
SRC_MATRIZ_5X5 = ROOT / "docs" / "mediciones" / "f1_evaluacion_despues" / "matriz_confusion_ner.json"
OUT_JSON = ROOT / "frontend" / "src" / "constants" / "betoMetricas.json"


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _find_ablacion_row(filas: list[dict], dataset: str, modo: str, criterio: str) -> dict:
    for row in filas:
        if row.get("dataset") == dataset and row.get("modo") == modo and row.get("criterio") == criterio:
            return {
                "tp": int(row["tp"]),
                "fp": int(row["fp"]),
                "fn": int(row["fn"]),
                "support": int(row["support"]),
                "predicted": int(row["predicted"]),
                "precision": float(row["precision"]),
                "recall": float(row["recall"]),
                "f1": float(row["f1"]),
            }
    raise KeyError(f"No se encontró fila de ablación para {dataset}/{modo}/{criterio}")


def build_beto_metricas() -> dict:
    matriz_ent = _load_json(SRC_MATRIZ_ENTIDADES)
    ablacion = _load_json(SRC_ABLACION)
    training = _load_json(SRC_TRAINING)
    matriz_5x5 = _load_json(SRC_MATRIZ_5X5)

    classes = training["classes"]
    filas_ablacion = ablacion["filas"]

    desglose_por_clase = []
    por_tipo_estricto = matriz_ent["por_tipo_estricto"]
    f1_relajado = matriz_ent["f1_relajado_por_tipo"]
    for clase, stats in por_tipo_estricto.items():
        desglose_por_clase.append({
            "clase": clase,
            "support": int(stats["support"]),
            "tp": int(stats["tp"]),
            "fn": int(stats["fn"]),
            "fp": int(stats["fp"]),
            "precision": float(stats["precision"]),
            "recall": float(stats["recall"]),
            "f1_estricto": float(stats["f1"]),
            "f1_relajado": float(f1_relajado[clase]),
        })

    return {
        "fuentes": [
            "docs/mediciones/f1_training_info.json",
            "docs/mediciones/f3r_ablacion.json",
            "docs/mediciones/f3r_matriz_confusion.json",
            "docs/mediciones/f1_evaluacion_despues/matriz_confusion_ner.json",
        ],
        "ficha_modelo": {
            "model_base": training["model_base"],
            "etiquetas_iob2": classes,
            "num_etiquetas": len(classes),
            "epochs": int(training["epochs"]),
            "best_epoch": int(training["best_epoch"]),
            "best_dev_f1": float(training["best_dev_f1"]),
            "learning_rate": float(training["learning_rate"]),
            "weight_decay": float(training["weight_decay"]),
            "batch_size": int(training["batch_size"]),
            "max_length": int(training["max_length"]),
            "seed": int(training["seed"]),
            "train_size": int(training["train_size"]),
            "dev_size": int(training["dev_size"]),
            "test_gold_size": int(training["test_gold_size"]),
            "train_duration_sec": float(training["train_duration_sec"]),
            "device": training["device"],
            "selection": training["selection"],
            "model_sha256": training["sha256"]["model.safetensors"],
        },
        "epocas": [
            {
                "epoch": int(ep["epoch"]),
                "train_loss": float(ep["train_loss"]),
                "dev_loss": float(ep["dev_loss"]),
                "dev_f1": float(ep["dev_f1"]),
                "dev_precision": float(ep["dev_precision"]),
                "dev_recall": float(ep["dev_recall"]),
                "time_sec": float(ep["time_sec"]),
            }
            for ep in training["epoch_history"]
        ],
        "gold_510_modo_c": {
            "estricto": _find_ablacion_row(filas_ablacion, "gold_510", "C", "strict"),
            "relajado": _find_ablacion_row(filas_ablacion, "gold_510", "C", "relaxed"),
            "explicacion_503_vs_510": matriz_ent["explicacion_503_vs_510"],
        },
        "desglose_por_clase": desglose_por_clase,
        "matriz_confusion_5x5": {
            "clases": matriz_5x5["clases"],
            "matriz": matriz_5x5["matriz"],
            "por_clase": matriz_5x5["por_clase"],
            "n_tokens": int(matriz_5x5["n_tokens"]),
            "n_secuencias": int(matriz_5x5["n_secuencias"]),
            "nivel": matriz_5x5["nivel"],
            "conjunto": matriz_5x5["conjunto"],
        },
    }


def main() -> None:
    payload = build_beto_metricas()
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with OUT_JSON.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(f"Generado {OUT_JSON.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
