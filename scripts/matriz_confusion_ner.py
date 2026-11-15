#!/usr/bin/env python
"""
scripts/matriz_confusion_ner.py
===============================
Matriz de confusión REAL (token a token, con la clase O) calculada desde y_true / y_pred de la
evaluación sobre data/test_gold_real.jsonl. Reemplaza la matriz escrita a mano del gráfico 3.1.

Entrada : JSON {"y_true": [[tag,...],...], "y_pred": [[tag,...],...]} (lo escribe
          scripts/entrenar_beto_robusto.py como predicciones_test_gold.json).
Salida  : docs/evidencias/matriz_confusion_ner.json (filas = real, columnas = predicho).
Las etiquetas IOB2 se colapsan al tipo de entidad (B-X e I-X => X); O queda como clase propia.

Uso:
    python scripts/matriz_confusion_ner.py --predicciones <predicciones_test_gold.json> \
        [--salida docs/evidencias/matriz_confusion_ner.json]
"""
import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Sequence

CLASES = ["O", "MODULO", "PER_DOCENTE", "PER_ESTUDIANTE", "PROGRAMA"]


def _tipo(tag: str) -> str:
    return "O" if tag == "O" else tag.split("-", 1)[1]


def matriz_confusion(y_true: Sequence[Sequence[str]], y_pred: Sequence[Sequence[str]],
                     clases: Sequence[str] = CLASES) -> Dict[str, Any]:
    """Matriz absoluta (filas = real, columnas = predicho) a nivel de token; incluye la clase O."""
    if len(y_true) != len(y_pred):
        raise ValueError("y_true y y_pred difieren en número de secuencias")
    idx = {c: i for i, c in enumerate(clases)}
    m = [[0] * len(clases) for _ in clases]
    for t_seq, p_seq in zip(y_true, y_pred):
        if len(t_seq) != len(p_seq):
            raise ValueError("secuencia con longitudes distintas entre y_true y y_pred")
        for t, p in zip(t_seq, p_seq):
            m[idx[_tipo(t)]][idx[_tipo(p)]] += 1
    por_clase = {}
    for c, i in idx.items():
        tp = m[i][i]
        fn = sum(m[i]) - tp
        fp = sum(m[r][i] for r in range(len(clases))) - tp
        por_clase[c] = {"tp": tp, "fp": fp, "fn": fn, "soporte": sum(m[i])}
    return {"clases": list(clases), "matriz": m, "por_clase": por_clase,
            "n_tokens": sum(sum(f) for f in m), "n_secuencias": len(y_true)}


def generar(predicciones: Path, salida: Path) -> Dict[str, Any]:
    datos = json.loads(Path(predicciones).read_text(encoding="utf-8"))
    res = matriz_confusion(datos["y_true"], datos["y_pred"])
    res.update({
        "nivel": "token (B-/I- colapsados al tipo; incluye O)",
        "conjunto": datos.get("dataset", "test_gold_real.jsonl"),
        "origen": str(predicciones),
    })
    Path(salida).parent.mkdir(parents=True, exist_ok=True)
    Path(salida).write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--predicciones", required=True)
    ap.add_argument("--salida", default="docs/evidencias/matriz_confusion_ner.json")
    a = ap.parse_args()
    r = generar(Path(a.predicciones), Path(a.salida))
    print(json.dumps({"clases": r["clases"], "matriz": r["matriz"]}, ensure_ascii=False))
