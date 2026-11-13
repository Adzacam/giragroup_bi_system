"""¿Cuánto cuesta sacar las entidades NER de los mismos logits que calcula /indice, en vez de un segundo forward?

Corre dentro de giragroup_pipeline (mismo modelo beto_local, mismos hilos que el servicio). Sobre N textos de 8 celdas:
  (1) índice actual: calcular_indices (forward en lotes de 32, truncado a 128 tokens)
  (2) entidades actuales: pipeline NER de transformers (segundo forward, aggregation_strategy="simple")
  (3) una pasada: un forward en lotes de 32 con offsets -> índice (misma fórmula) + entidades con el postprocess del propio pipeline
Comprueba que (3) da los mismos índices que (1) y las mismas entidades que (2) (etiqueta, offsets; score con tolerancia 1e-4).

Uso: docker exec giragroup_pipeline python /app/output/benchmark_una_pasada.py <textos.json> <salida.json> [N=1024]
"""
import json
import sys
import time

import numpy as np
import torch

from pipeline.semantic.indice_confianza import BATCH_SIZE, MAX_LENGTH_TOKENS, calcular_indices
from pipeline.semantic.inference_server import get_engine_and_tokenizer


def una_pasada(pipe, textos, max_len=MAX_LENGTH_TOKENS):
    tok, modelo = pipe.tokenizer, pipe.model
    id2label = modelo.config.id2label
    especiales = (tok.cls_token_id, tok.sep_token_id, tok.pad_token_id)
    indices, entidades = [], []
    for i in range(0, len(textos), BATCH_SIZE):
        lote = textos[i:i + BATCH_SIZE]
        enc = tok(lote, return_tensors="pt", padding=True, truncation=True, max_length=max_len,
                  return_offsets_mapping=True, return_special_tokens_mask=True)
        offsets, stm = enc.pop("offset_mapping"), enc.pop("special_tokens_mask")
        with torch.inference_mode():
            logits = modelo(**enc).logits
        probs = torch.softmax(logits, dim=-1)
        for b, texto in enumerate(lote):
            n = int(enc["attention_mask"][b].sum())
            p, ids = probs[b], enc["input_ids"][b]
            pred = torch.argmax(p, dim=-1)
            conf = [float(p[t, pid]) for t, (tid, pid) in enumerate(zip(ids, pred)) if tid not in especiales and id2label.get(int(pid), "O") != "O"]
            indices.append(round(float(np.mean(conf)), 4) if conf else (0.55 if len(texto) < 20 else 0.72))
            salida = {"logits": logits[b:b + 1, :n], "input_ids": ids[None, :n], "offset_mapping": offsets[b:b + 1, :n],
                      "special_tokens_mask": stm[b:b + 1, :n], "sentence": texto, "is_last": True}
            entidades.append(pipe.postprocess([salida], aggregation_strategy=pipe._postprocess_params.get("aggregation_strategy")))
    return indices, entidades


def norm(ents):
    return [(e["entity_group"], int(e["start"]), int(e["end"]), float(e["score"])) for e in ents]


def main(ruta, salida, n):
    textos = json.load(open(ruta, encoding="utf-8"))[:n]
    engine, _ = get_engine_and_tokenizer()
    pipe = engine._nlp_pipeline
    calcular_indices(textos[:32]); pipe(textos[:32], batch_size=32); una_pasada(pipe, textos[:32])  # calentamiento
    r = {"n": len(textos), "hilos_torch": torch.get_num_threads()}
    t0 = time.perf_counter(); idx1 = calcular_indices(textos); r["indice_actual_s"] = round(time.perf_counter() - t0, 2)
    t0 = time.perf_counter(); ent2 = pipe(textos, batch_size=BATCH_SIZE); r["ner_pipeline_s"] = round(time.perf_counter() - t0, 2)
    t0 = time.perf_counter(); idx3, ent3 = una_pasada(pipe, textos); r["una_pasada_s"] = round(time.perf_counter() - t0, 2)
    r["indices_iguales"] = sum(a == b for a, b in zip(idx1, idx3))
    r["indices_max_dif"] = max(abs(a - b) for a, b in zip(idx1, idx3))
    iguales = mismas_etiquetas = 0
    for a, b in zip(ent2, ent3):
        na, nb = norm(a), norm(b)
        mismas_etiquetas += [x[:3] for x in na] == [x[:3] for x in nb]
        iguales += len(na) == len(nb) and all(x[:3] == y[:3] and abs(x[3] - y[3]) < 1e-4 for x, y in zip(na, nb))
    r["entidades_identicas"] = iguales
    r["entidades_mismas_etiquetas_y_offsets"] = mismas_etiquetas
    largos = [len(pipe.tokenizer(t)["input_ids"]) > MAX_LENGTH_TOKENS for t in textos]
    r["textos_truncados_128"] = sum(largos)
    distintos = [k for k, (a, b) in enumerate(zip(ent2, ent3)) if [x[:3] for x in norm(a)] != [x[:3] for x in norm(b)]]
    r["entidades_distintas_que_son_textos_truncados"] = f"{sum(largos[k] for k in distintos)} de {len(distintos)}"
    # Variante sin recorte (512 tokens): entidades como el pipeline NER, pero el índice de los textos largos cambia
    t0 = time.perf_counter(); idx4, ent4 = una_pasada(pipe, textos, 512); r["una_pasada_512_s"] = round(time.perf_counter() - t0, 2)
    r["una_pasada_512_entidades_mismas_etiquetas_y_offsets"] = sum([x[:3] for x in norm(a)] == [x[:3] for x in norm(b)] for a, b in zip(ent2, ent4))
    r["una_pasada_512_indices_distintos_al_actual"] = sum(a != b for a, b in zip(idx1, idx4))
    r["una_pasada_512_indice_medio_vs_actual"] = [round(float(np.mean(idx1)), 4), round(float(np.mean(idx4)), 4)]
    r["lineas_por_s"] = {k: round(len(textos) / r[k], 1) for k in ("indice_actual_s", "ner_pipeline_s", "una_pasada_s", "una_pasada_512_s")}
    r["costo_decodificar_s"] = round(r["una_pasada_s"] - r["indice_actual_s"], 2)
    json.dump(r, open(salida, "w"), indent=1)
    print(json.dumps(r))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 1024)
