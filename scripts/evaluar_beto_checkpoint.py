"""Evalúa un checkpoint explícito sin entrenar ni escribir en datos/modelo vigente."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.beto_metricas import load_conll, metricas_relajadas
from scripts.matriz_confusion_ner import generar

MAX_LENGTH = 128


def predecir(tokens, tokenizer, model):
    import torch
    enc = tokenizer(tokens, is_split_into_words=True, return_tensors="pt",
                    truncation=True, max_length=MAX_LENGTH)
    ids = enc.word_ids()
    cubiertos = {i for i in ids if i is not None}
    if len(cubiertos) != len(tokens):
        raise ValueError("Secuencia truncada; no se reportan métricas parciales")
    with torch.inference_mode():
        pred = model(**enc).logits.argmax(-1)[0].tolist()
    salida = []
    anterior = None
    for i, etiqueta in zip(ids, pred):
        if i is not None and i != anterior:
            salida.append(model.config.id2label[etiqueta])
        anterior = i
    return salida


def main():
    from transformers import AutoTokenizer, AutoModelForTokenClassification
    from seqeval.metrics import classification_report
    from seqeval.scheme import IOB2
    import torch
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--modelo", required=True)
    ap.add_argument("--gold", required=True)
    ap.add_argument("--salida", required=True)
    args = ap.parse_args()
    salida = Path(args.salida).resolve()
    if salida.is_relative_to(ROOT / "pipeline") or salida == ROOT / "data":
        ap.error("Salida protegida")
    if salida.exists() and any(salida.iterdir()):
        ap.error("La salida debe ser nueva o vacía")
    salida.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    tokenizer = AutoTokenizer.from_pretrained(args.modelo, local_files_only=True)
    model = AutoModelForTokenClassification.from_pretrained(args.modelo, local_files_only=True).eval()
    gold = [json.loads(x) for x in Path(args.gold).read_text(encoding="utf-8").splitlines() if x.strip()]
    layouts = json.loads((ROOT / "uploads/test/layouts_adversarios/gold_layouts_adversarios.json").read_text(encoding="utf-8"))["ejemplos"]
    tx, ty = load_conll(ROOT / "data/ner/test.conll")
    resultados = {}
    for nombre, xs, ys in (("gold_510", [r["tokens"] for r in gold], [r["tags"] for r in gold]),
                           ("layouts_5", [r["tokens"] for r in layouts], [r["tags"] for r in layouts]),
                           ("test.conll", tx, ty)):
        # Los layouts también anotan entidades regex ajenas al inventario NER.
        ys = [[t if t == "O" or t[2:] in {"MODULO", "PROGRAMA", "PER_DOCENTE", "PER_ESTUDIANTE"} else "O" for t in seq] for seq in ys]
        ps = [predecir(tokens, tokenizer, model) for tokens in xs]
        resultados[nombre] = {"estricto": classification_report(ys, ps, mode="strict", scheme=IOB2, output_dict=True, zero_division=0),
                               "relajado": metricas_relajadas(ys, ps)}
        predpath = salida / (nombre.replace(".", "_") + "_predicciones.json")
        predpath.write_text(json.dumps({"dataset": nombre, "y_true": ys, "y_pred": ps}), encoding="utf-8")
        if nombre == "gold_510":
            generar(predpath, salida / "matriz_confusion_ner.json")
    (salida / "metricas.json").write_text(
        json.dumps(resultados, indent=2, default=lambda o: o.item() if hasattr(o, "item") else str(o)),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
