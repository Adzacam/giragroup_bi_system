"""Métricas puras: coincidencia estricta IOB2 y relajada por solapamiento 1:1."""
import re
from pathlib import Path

def load_conll(path: Path):
    sents, tags = [], []
    cur_t, cur_y = [], []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            if cur_t:
                sents.append(cur_t)
                tags.append(cur_y)
                cur_t, cur_y = [], []
        else:
            t, y = line.rsplit("\t", 1)
            cur_t.append(t)
            cur_y.append(y)
    if cur_t:
        sents.append(cur_t)
        tags.append(cur_y)
    return sents, tags


def reconstruct_text_and_offsets(tokens):
    parts = []
    offsets = []
    cur = 0
    for i, tok in enumerate(tokens):
        if i > 0 and not re.match(r"^[.,;:!?)]$", tok) and parts[-1] != "(":
            parts.append(" ")
            cur += 1
        start = cur
        parts.append(tok)
        cur += len(tok)
        offsets.append((tok, start, cur))
    return "".join(parts), offsets


def entidades(tags):
    from seqeval.metrics.sequence_labeling import get_entities
    return get_entities(tags)


def metricas_relajadas(y_true, y_pred):
    if len(y_true) != len(y_pred) or any(len(t) != len(p) for t,p in zip(y_true,y_pred)):
        raise ValueError("Predicciones desalineadas")
    hits = ng = np = 0
    for ts, ps in zip(y_true, y_pred):
        gold, pred = entidades(ts), entidades(ps)
        ng += len(gold); np += len(pred)
        matches = {}
        def asignar(i, vistos):
            gt, gs, ge = gold[i]
            for j, (pt, start, end) in enumerate(pred):
                if j in vistos or gt != pt or max(gs, start) > min(ge, end):
                    continue
                vistos.add(j)
                if j not in matches or asignar(matches[j], vistos):
                    matches[j] = i
                    return True
            return False
        hits += sum(asignar(i, set()) for i in range(len(gold)))
    precision = hits / np if np else 0.0
    recall = hits / ng if ng else 0.0
    return {"precision": precision, "recall": recall,
            "f1": 2*precision*recall/(precision+recall) if precision+recall else 0.0,
            "tp": hits, "gold": ng, "pred": np,
            "criterio": "mismo tipo y solapamiento de tokens; matching máximo uno a uno"}
