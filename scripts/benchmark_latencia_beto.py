import time
import json
import torch
from transformers import BertTokenizerFast, BertForTokenClassification

model_path = "pipeline/semantic/beto_local"
device = torch.device("cpu")
print("Cargando tokenizer y modelo...")
tokenizer = BertTokenizerFast.from_pretrained(model_path)
model = BertForTokenClassification.from_pretrained(model_path)
model.to(device)
model.eval()

# Cargar 50 lineas de texto real
textos = []
with open("data/test_gold_real.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        textos.append(json.loads(line)["texto"])
        if len(textos) == 50:
            break

print(f"Total muestras para benchmark: {len(textos)} lineas")

# Warm-up (3 inferencias)
for t in textos[:3]:
    inputs = tokenizer(t, return_tensors="pt", truncation=True, max_length=128).to(device)
    with torch.no_grad():
        _ = model(**inputs)

# Medicion 1: Inferencia linea por linea (secuencial)
tiempos_individuales = []
for t in textos:
    inputs = tokenizer(t, return_tensors="pt", truncation=True, max_length=128).to(device)
    t0 = time.perf_counter()
    with torch.no_grad():
        _ = model(**inputs)
    t1 = time.perf_counter()
    tiempos_individuales.append((t1 - t0) * 1000.0)

avg_indiv = sum(tiempos_individuales) / len(tiempos_individuales)
min_indiv = min(tiempos_individuales)
max_indiv = max(tiempos_individuales)

# Medicion 2: Inferencia en lote unico (batch de 50)
t0_batch = time.perf_counter()
batch_inputs = tokenizer(textos, return_tensors="pt", padding=True, truncation=True, max_length=128).to(device)
with torch.no_grad():
    _ = model(**batch_inputs)
t1_batch = time.perf_counter()
tiempo_total_batch_ms = (t1_batch - t0_batch) * 1000.0
ms_por_linea_batch = tiempo_total_batch_ms / len(textos)

print(f"\n=======================================================")
print(f"BENCHMARK DE LATENCIA INFERENCIA BETO_LOCAL (N=50)")
print(f"=======================================================")
print(f"Modo Secuencial (linea por linea):")
print(f"  Minimo: {min_indiv:.2f} ms/linea")
print(f"  Promedio: {avg_indiv:.2f} ms/linea")
print(f"  Maximo: {max_indiv:.2f} ms/linea")
print(f"\nModo Lote (Batch de 50 agrupado con padding):")
print(f"  Tiempo total batch: {tiempo_total_batch_ms:.2f} ms")
print(f"  Latencia amortizada: {ms_por_linea_batch:.2f} ms/linea")
print(f"=======================================================")
