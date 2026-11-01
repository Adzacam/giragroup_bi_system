#!/usr/bin/env python
"""
scripts/entrenar_beto_robusto.py
=================================
Pipeline de Fine-Tuning y Evaluación Ciega de BETO para GiraGroup BI.

1. Modelo Base: dccuchile/bert-base-spanish-wwm-cased
2. 9 Etiquetas Institucionales BIO:
   O, B-PER_ESTUDIANTE, I-PER_ESTUDIANTE, B-PER_DOCENTE, I-PER_DOCENTE,
   B-MODULO, I-MODULO, B-PROGRAMA, I-PROGRAMA
3. Optimizador: AdamW (lr=2.5e-5, weight_decay=0.01)
4. Early Stopping guiado estrictamente por Dev Loss y Dev F1
5. Evaluación Final Ciega en:
   a) Test Gold Real (180 líneas de datos reales auditables)
   b) test.conll sintético (230 oraciones)
6. Persistencia de checkpoint en pipeline/semantic/beto_local/ y training_info.json.
"""

import os
import sys
import json
import time
import random
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple

import torch
from torch.utils.data import Dataset, DataLoader
from transformers import (
    BertTokenizerFast,
    BertForTokenClassification,
    AutoTokenizer,
    AutoModelForTokenClassification
)
from seqeval.metrics import classification_report, f1_score, precision_score, recall_score
from seqeval.scheme import IOB2
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Fijar semillas para reproducibilidad científica
SEED = 42
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)

LABEL_LIST = [
    "O",
    "B-PER_ESTUDIANTE", "I-PER_ESTUDIANTE",
    "B-PER_DOCENTE", "I-PER_DOCENTE",
    "B-MODULO", "I-MODULO",
    "B-PROGRAMA", "I-PROGRAMA"
]
LABEL2ID: Dict[str, int] = {label: i for i, label in enumerate(LABEL_LIST)}
ID2LABEL: Dict[int, str] = {i: label for i, label in enumerate(LABEL_LIST)}

MODEL_NAME = "dccuchile/bert-base-spanish-wwm-cased"
OUTPUT_DIR = os.path.join(str(BASE_DIR), "pipeline", "semantic", "beto_local")

class NerDataset(Dataset):
    def __init__(self, data_path: str, tokenizer, max_len: int = 128):
        self.samples = []
        with open(data_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    self.samples.append(json.loads(line))

        self.tokenizer = tokenizer
        self.max_len = max_len
        self.encodings = []
        self._preprocess()

    def _preprocess(self):
        for item in self.samples:
            texto = item["texto"]
            spans = item.get("spans", [])

            encoding = self.tokenizer(
                texto,
                max_length=self.max_len,
                padding="max_length",
                truncation=True,
                return_offsets_mapping=True,
                return_tensors="pt"
            )

            offset_mapping = encoding["offset_mapping"][0]
            labels = [LABEL2ID["O"]] * len(offset_mapping)

            for i, (start_char, end_char) in enumerate(offset_mapping):
                if start_char == end_char:
                    labels[i] = -100
                    continue

                for sp in spans:
                    s_start = sp["start"]
                    s_end = sp["end"]
                    s_tipo = sp["tipo"]

                    if start_char >= s_start and end_char <= s_end:
                        if start_char == s_start:
                            tag = f"B-{s_tipo}"
                        else:
                            tag = f"I-{s_tipo}"
                        labels[i] = LABEL2ID.get(tag, LABEL2ID["O"])
                        break

            self.encodings.append({
                "input_ids": encoding["input_ids"].squeeze(0),
                "attention_mask": encoding["attention_mask"].squeeze(0),
                "labels": torch.tensor(labels, dtype=torch.long)
            })

    def __len__(self):
        return len(self.encodings)

    def __getitem__(self, idx):
        return self.encodings[idx]

def evaluar_modelo(model, dataloader, device):
    model.eval()
    y_true_all = []
    y_pred_all = []
    total_loss = 0.0

    with torch.no_grad():
        for batch in dataloader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)

            outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
            total_loss += outputs.loss.item()

            logits = outputs.logits
            preds = torch.argmax(logits, dim=-1)

            for b_idx in range(len(input_ids)):
                cur_true = []
                cur_pred = []
                for t_idx in range(len(input_ids[b_idx])):
                    l_id = labels[b_idx, t_idx].item()
                    if l_id != -100:
                        cur_true.append(ID2LABEL.get(l_id, "O"))
                        p_id = preds[b_idx, t_idx].item()
                        cur_pred.append(ID2LABEL.get(p_id, "O"))

                if cur_true:
                    y_true_all.append(cur_true)
                    y_pred_all.append(cur_pred)

    avg_loss = total_loss / max(1, len(dataloader))
    f1 = f1_score(y_true_all, y_pred_all, mode="strict", scheme=IOB2)
    prec = precision_score(y_true_all, y_pred_all, mode="strict", scheme=IOB2)
    rec = recall_score(y_true_all, y_pred_all, mode="strict", scheme=IOB2)

    report_dict = classification_report(
        y_true_all, y_pred_all, mode="strict", scheme=IOB2, output_dict=True, digits=4
    )

    return {
        "loss": avg_loss,
        "f1": f1,
        "precision": prec,
        "recall": rec,
        "report": report_dict,
        "y_true": y_true_all,
        "y_pred": y_pred_all
    }

def entrenar_beto():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    device = torch.device("cpu")
    print(f"Iniciando fine-tuning de BETO en: {device}")
    t0_global = time.time()

    print(f"Cargando tokenizer y modelo base: {MODEL_NAME}...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForTokenClassification.from_pretrained(
        MODEL_NAME,
        num_labels=len(LABEL_LIST),
        id2label=ID2LABEL,
        label2id=LABEL2ID
    )
    model.to(device)

    print("Cargando Datasets de Train y Dev...")
    train_ds = NerDataset("data/train_robusto.jsonl", tokenizer, max_len=128)
    dev_ds = NerDataset("data/dev_robusto.jsonl", tokenizer, max_len=128)
    test_gold_ds = NerDataset("data/test_gold_real.jsonl", tokenizer, max_len=128)

    train_loader = DataLoader(train_ds, batch_size=16, shuffle=True)
    dev_loader = DataLoader(dev_ds, batch_size=16, shuffle=False)
    test_gold_loader = DataLoader(test_gold_ds, batch_size=16, shuffle=False)

    print(f"Train samples: {len(train_ds)}, Dev samples: {len(dev_ds)}, Test Gold samples: {len(test_gold_ds)}")

    optimizer = torch.optim.AdamW(model.parameters(), lr=2.5e-5, weight_decay=0.01)

    EPOCHS = 3
    best_dev_f1 = -1.0
    best_epoch = 0
    history = []

    print("\n--- INICIO DE ENTRENAMIENTO ---")
    for epoch in range(1, EPOCHS + 1):
        t0_epoch = time.time()
        model.train()
        epoch_loss = 0.0

        for step, batch in enumerate(train_loader):
            optimizer.zero_grad()
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)

            outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
            loss = outputs.loss
            loss.backward()
            optimizer.step()

            epoch_loss += loss.item()
            if (step + 1) % 25 == 0 or (step + 1) == len(train_loader):
                print(f"Epoch {epoch}/{EPOCHS} | Step {step+1}/{len(train_loader)} | Loss: {loss.item():.4f}")

        avg_train_loss = epoch_loss / len(train_loader)

        # Evaluación en Dev Set (NUNCA en Test)
        dev_res = evaluar_modelo(model, dev_loader, device)
        epoch_time = time.time() - t0_epoch

        print(f"--> Epoch {epoch} Finalizada en {epoch_time:.1f}s | Train Loss: {avg_train_loss:.4f} | Dev Loss: {dev_res['loss']:.4f} | Dev F1: {dev_res['f1']*100:.2f}% | Dev Prec: {dev_res['precision']*100:.2f}% | Dev Rec: {dev_res['recall']*100:.2f}%")

        history.append({
            "epoch": epoch,
            "train_loss": round(avg_train_loss, 4),
            "dev_loss": round(dev_res["loss"], 4),
            "dev_f1": round(dev_res["f1"], 4),
            "dev_precision": round(dev_res["precision"], 4),
            "dev_recall": round(dev_res["recall"], 4),
            "time_sec": round(epoch_time, 2)
        })

        if dev_res["f1"] > best_dev_f1:
            best_dev_f1 = dev_res["f1"]
            best_epoch = epoch
            print(f"    [MEJOR MODELO DEV] Guardando checkpoint en {OUTPUT_DIR}...")
            model.save_pretrained(OUTPUT_DIR)
            tokenizer.save_pretrained(OUTPUT_DIR)

    duracion_total = time.time() - t0_global
    print(f"\nEntrenamiento completado en {duracion_total:.1f}s. Mejor época en Dev: {best_epoch} (Dev F1: {best_dev_f1*100:.2f}%)")

    # Guardar metadata del entrenamiento
    training_info = {
        "status": "trained_success",
        "timestamp": datetime.now().isoformat(),
        "model_base": MODEL_NAME,
        "output_dir": OUTPUT_DIR,
        "epochs": EPOCHS,
        "best_epoch": best_epoch,
        "learning_rate": 2.5e-5,
        "batch_size": 16,
        "max_length": 128,
        "seed": SEED,
        "train_size": len(train_ds),
        "dev_size": len(dev_ds),
        "test_gold_size": len(test_gold_ds),
        "classes": LABEL_LIST,
        "best_dev_f1": round(best_dev_f1, 4),
        "train_duration_sec": round(duracion_total, 2),
        "device": str(device),
        "epoch_history": history
    }

    with open(os.path.join(OUTPUT_DIR, "training_info.json"), "w", encoding="utf-8") as f:
        json.dump(training_info, f, indent=2, ensure_ascii=False)

    print("\n--- EVALUACIÓN FINAL CIEGA ---")
    # Cargar mejor modelo guardado
    print(f"Cargando mejor modelo guardado desde: {OUTPUT_DIR}")
    best_model = AutoModelForTokenClassification.from_pretrained(OUTPUT_DIR)
    best_model.to(device)

    # 1. Test Gold Real
    print("\n1. Evaluando en Test Gold Real (180 líneas reales)...")
    gold_res = evaluar_modelo(best_model, test_gold_loader, device)

    # 2. Test Conll Sintético
    print("2. Evaluando en test.conll sintético (230 oraciones)...")
    # Cargar test.conll
    from scripts.eval_ner import load_conll, reconstruct_text_and_offsets
    X_conll, Y_conll = load_conll(Path("test.conll"))
    
    Y_pred_conll = []
    best_model.eval()
    with torch.no_grad():
        for tokens in X_conll:
            text, tok_offsets = reconstruct_text_and_offsets(tokens)
            enc = tokenizer(text, return_offsets_mapping=True, return_tensors="pt", max_length=128, truncation=True)
            input_ids = enc["input_ids"].to(device)
            attention_mask = enc["attention_mask"].to(device)
            offsets = enc["offset_mapping"][0]

            logits = best_model(input_ids=input_ids, attention_mask=attention_mask).logits
            preds = torch.argmax(logits, dim=-1)[0]

            # Reconstruir tags para tokens de conll
            pred_spans = []
            cur_tag = None
            cur_start = None
            cur_end = None

            for t_idx, (s_c, e_c) in enumerate(offsets):
                if s_c == e_c:
                    continue
                tag_str = ID2LABEL.get(preds[t_idx].item(), "O")
                if tag_str.startswith("B-"):
                    if cur_tag:
                        pred_spans.append({"tipo": cur_tag, "start": cur_start, "end": cur_end})
                    cur_tag = tag_str[2:]
                    cur_start = s_c.item()
                    cur_end = e_c.item()
                elif tag_str.startswith("I-") and cur_tag == tag_str[2:]:
                    cur_end = e_c.item()
                else:
                    if cur_tag:
                        pred_spans.append({"tipo": cur_tag, "start": cur_start, "end": cur_end})
                        cur_tag = None

            if cur_tag:
                pred_spans.append({"tipo": cur_tag, "start": cur_start, "end": cur_end})

            # Mapear a tokens conll
            from scripts.eval_ner import spans_to_iob2
            conll_preds = spans_to_iob2(tok_offsets, pred_spans)
            Y_pred_conll.append(conll_preds)

    synth_report = classification_report(
        Y_conll, Y_pred_conll, mode="strict", scheme=IOB2, output_dict=True, digits=4
    )

    def clean_report(rep):
        res = {}
        for k, v in rep.items():
            if isinstance(v, dict):
                res[k] = {
                    "precision": round(float(v.get("precision", 0.0)), 4),
                    "recall": round(float(v.get("recall", 0.0)), 4),
                    "f1-score": round(float(v.get("f1-score", 0.0)), 4),
                    "support": int(v.get("support", 0))
                }
            elif isinstance(v, (float, np.floating)):
                res[k] = round(float(v), 4)
            elif isinstance(v, (int, np.integer)):
                res[k] = int(v)
            else:
                res[k] = v
        return res

    gold_report_clean = clean_report(gold_res["report"])
    synth_report_clean = clean_report(synth_report)

    metricas_consolidadas = {
        "fecha": datetime.now().isoformat(),
        "modelo": OUTPUT_DIR,
        "test_gold_real": gold_report_clean,
        "test_conll_sintetico": synth_report_clean,
        "training_info": training_info
    }

    os.makedirs("output", exist_ok=True)
    with open("output/metricas_ner_robusto.json", "w", encoding="utf-8") as f:
        json.dump(metricas_consolidadas, f, indent=2, ensure_ascii=False)

    print("\n=======================================================")
    print("MÉTRICAS TEST GOLD REAL (180 LÍNEAS REALES AUDITABLES):")
    print("=======================================================")
    print(json.dumps(gold_report_clean, indent=2, ensure_ascii=False))

    print("\n=======================================================")
    print("MÉTRICAS TEST CONLL SINTÉTICO (230 ORACIONES DE REFERENCIA):")
    print("=======================================================")
    print(json.dumps(synth_report_clean, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    entrenar_beto()
