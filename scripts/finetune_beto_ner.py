#!/usr/bin/env python
"""
scripts/finetune_beto_ner.py
============================
Pipeline de Fine-Tuning y Extracción Relacional con BETO (dccuchile/bert-spanish-cased).

Objetivos:
1. Token Classification (NER) para 7 entidades de dominio institucional:
   - ESTUDIANTE, DOCENTE, PROGRAMA, MODULO, NOTA, MONTO, FECHA.
   - Esquema BIO (15 clases incluyendo 'O').
2. Extracción de Relaciones Semánticas (Joint Entity & Relation Extraction):
   - Tupla Académica: (Estudiante -> Modulo -> Nota)
   - Tupla Financiera: (Estudiante -> Monto [-> Fecha/Cuota])
   - Tupla Docente:    (Docente -> Modulo)
3. Persistencia de Pesos / Modelo en models/beto_ner_gira/.
"""

import argparse
import json
import logging
import os
import re
import sys
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("beto_ner_finetuner")

# ── Etiquetas BIO para Token Classification ─────────────────────────────────
LABEL_LIST = [
    "O",
    "B-PER_ESTUDIANTE", "I-PER_ESTUDIANTE",
    "B-PER_DOCENTE", "I-PER_DOCENTE",
    "B-MODULO", "I-MODULO",
    "B-PROGRAMA", "I-PROGRAMA"
]
LABEL2ID: Dict[str, int] = {label: i for i, label in enumerate(LABEL_LIST)}
ID2LABEL: Dict[int, str] = {i: label for i, label in enumerate(LABEL_LIST)}


# ── Extracción Relacional ───────────────────────────────────────────────────

@dataclass
class TuplaAcademica:
    estudiante: str
    modulo: str
    nota: float
    confianza: float
    texto_fuente: str

@dataclass
class TuplaFinanciera:
    estudiante: str
    monto: float
    fecha: Optional[str]
    concepto: Optional[str]
    confianza: float
    texto_fuente: str

@dataclass
class TuplaDocente:
    docente: str
    modulo: str
    confianza: float
    texto_fuente: str


def _parsear_numero_es(val: Any) -> float:
    """Extrae valores numéricos manejando formatos español (coma decimal, punto de miles) e internacional."""
    if val is None:
        return 0.0
    s = str(val).replace("Bs", "").replace("$", "").replace("USD", "").strip()
    if "." in s and "," in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    m = re.search(r"[-+]?\d+(?:\.\d+)?", s)
    if m:
        try:
            return float(m.group(0))
        except ValueError:
            return 0.0
    return 0.0


class RelationalExtractor:
    """
    Motor determinista y semántico de extracción de tuplas relacionales
    a partir de entidades reconocidas en el texto.
    """

    @staticmethod
    def extraer_tuplas(entidades: List[Dict[str, Any]], texto: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Dada una lista de entidades {'tipo': ..., 'valor': ..., 'score': ..., 'start': ..., 'end': ...}
        y el texto fuente, asocia parejas y ternas relacionales:
          - academicas: (Estudiante -> Modulo -> Nota)
          - financieras: (Estudiante -> Monto)
          - docentes:    (Docente -> Modulo)
        """
        estudiantes = [e for e in entidades if e.get("tipo") in ("ESTUDIANTE", "PER_ESTUDIANTE", "ALUMNO")]
        docentes = [e for e in entidades if e.get("tipo") in ("DOCENTE", "PER_DOCENTE")]
        modulos = [e for e in entidades if e.get("tipo") in ("MODULO", "PROGRAMA")]
        notas = [e for e in entidades if e.get("tipo") in ("NOTA", "CALIFICACION")]
        montos = [e for e in entidades if e.get("tipo") in ("MONTO", "MONTO_DEUDA", "MONTO_PAGADO", "SALDO")]
        fechas = [e for e in entidades if e.get("tipo") in ("FECHA",)]

        relaciones: Dict[str, List[Dict[str, Any]]] = {
            "academicas": [],
            "financieras": [],
            "docentes": []
        }

        # 1. Tuplas Académicas: (Estudiante -> Modulo -> Nota)
        modulos_disponibles = list(modulos)
        notas_disponibles = list(notas)

        for est in estudiantes:
            # Encontrar módulo más próximo (priorizando hacia adelante en el texto)
            mod_candidato = None
            if modulos_disponibles:
                cands_mod = [m for m in modulos_disponibles if m.get("start", 0) >= est.get("start", 0)]
                cands = cands_mod if cands_mod else modulos_disponibles
                mod_candidato = min(cands, key=lambda m: abs(m.get("start", 0) - est.get("start", 0)))
                modulos_disponibles.remove(mod_candidato)
            elif modulos:
                mod_candidato = min(modulos, key=lambda m: abs(m.get("start", 0) - est.get("start", 0)))

            # Encontrar nota más próxima (priorizando hacia adelante en el texto)
            nota_candidata = None
            if notas_disponibles:
                cands_nota = [n for n in notas_disponibles if n.get("start", 0) >= est.get("start", 0)]
                cands = cands_nota if cands_nota else notas_disponibles
                nota_candidata = min(cands, key=lambda n: abs(n.get("start", 0) - est.get("start", 0)))
                notas_disponibles.remove(nota_candidata)
            elif notas:
                nota_candidata = min(notas, key=lambda n: abs(n.get("start", 0) - est.get("start", 0)))

            if mod_candidato or nota_candidata:
                val_nota = _parsear_numero_es(nota_candidata.get("valor", "")) if nota_candidata else 0.0

                score_est = float(est.get("score", 0.90))
                score_mod = float(mod_candidato.get("score", 0.85)) if mod_candidato else 0.80
                score_nota = float(nota_candidata.get("score", 0.85)) if nota_candidata else 0.80
                conf = round((score_est + score_mod + score_nota) / 3.0, 3)

                tupla_aca = TuplaAcademica(
                    estudiante=str(est.get("valor", "")).strip(),
                    modulo=str(mod_candidato.get("valor", "Módulo General")).strip() if mod_candidato else "Módulo General",
                    nota=val_nota,
                    confianza=conf,
                    texto_fuente=texto
                )
                relaciones["academicas"].append(asdict(tupla_aca))

        # 2. Tuplas Financieras: (Estudiante -> Monto)
        montos_disponibles = list(montos)
        for est in estudiantes:
            m_candidato = None
            if montos_disponibles:
                cands_monto = [m for m in montos_disponibles if m.get("start", 0) >= est.get("start", 0)]
                cands = cands_monto if cands_monto else montos_disponibles
                m_candidato = min(cands, key=lambda m: abs(m.get("start", 0) - est.get("start", 0)))
                montos_disponibles.remove(m_candidato)
            elif montos:
                m_candidato = min(montos, key=lambda m: abs(m.get("start", 0) - est.get("start", 0)))

            if m_candidato:
                val_monto = _parsear_numero_es(m_candidato.get("valor", ""))

                fec_val = None
                if fechas:
                    cands_fec = [f for f in fechas if f.get("start", 0) >= est.get("start", 0)]
                    fec_candidata = min(cands_fec, key=lambda f: abs(f.get("start", 0) - est.get("start", 0))) if cands_fec else fechas[0]
                    fec_val = fec_candidata.get("valor")

                conf = round((float(est.get("score", 0.90)) + float(m_candidato.get("score", 0.85))) / 2.0, 3)

                tupla_fin = TuplaFinanciera(
                    estudiante=str(est.get("valor", "")).strip(),
                    monto=val_monto,
                    fecha=str(fec_val) if fec_val else None,
                    concepto=str(m_candidato.get("concepto") or "Cuota / Arancel"),
                    confianza=conf,
                    texto_fuente=texto
                )
                relaciones["financieras"].append(asdict(tupla_fin))

        # 3. Tuplas Docentes: (Docente -> Modulo)
        for doc in docentes:
            mod_candidato = modulos[0] if modulos else None
            if len(modulos) > 1 and "start" in doc:
                mod_candidato = min(modulos, key=lambda m: abs(m.get("start", 0) - doc.get("start", 0)))

            if mod_candidato:
                conf = round((float(doc.get("score", 0.90)) + float(mod_candidato.get("score", 0.85))) / 2.0, 3)
                tupla_doc = TuplaDocente(
                    docente=str(doc.get("valor", "")).strip(),
                    modulo=str(mod_candidato.get("valor", "")).strip(),
                    confianza=conf,
                    texto_fuente=texto
                )
                relaciones["docentes"].append(asdict(tupla_doc))

        return relaciones


def extraer_tuplas_relacionales(entidades: List[Dict[str, Any]], texto: str) -> Dict[str, List[Dict[str, Any]]]:
    """Función de interfaz directa para extracción relacional."""
    return RelationalExtractor.extraer_tuplas(entidades, texto)


# ── Generador Sintético de Dominio para Fine-Tuning ──────────────────────────

def generar_dataset_sintetico_dominio(num_muestras: int = 150) -> List[Dict[str, Any]]:
    """
    Genera oraciones de dominio educativo y financiero con anotaciones de spans (start, end, label)
    usando entidades canónicas del contexto de GiraGroup BI.
    """
    estudiantes = [
        "Carlos Mamani Quispe", "Ana Claudia Torrico", "Javier Mendoza Salazar",
        "Maria Elena Rios", "Rodrigo Fernandez Roca", "Patricia Daza Arteaga",
        "Guillermo Justiniano", "Valeria Gutierrez Paz", "Sergio Alarcon Flores"
    ]
    docentes = [
        "Lic. Roberto Carlos Duran", "Dra. Carmen Rosa Morales", "Ing. Marcelo Claure",
        "Mg. Sofia Alarcon", "Prof. Gonzalo Sanchez", "Dr. Alejandro Siles"
    ]
    programas = [
        "Maestría en Data Science", "Diplomado en Inteligencia de Negocios",
        "Especialidad en Gestión Tributaria", "Diplomado en Educación Superior",
        "Maestría en Finanzas Corporativas"
    ]
    modulos = [
        "Módulo 1 Fundamentos de Big Data", "Módulo 2 Modelado Dimensional",
        "Módulo 3 Arquitectura ETL", "Módulo 4 Visualización Analítica",
        "Taller de Grado", "Módulo 5 Econometría Aplicada"
    ]
    fechas = ["15/03/2025", "10/06/2024", "22/08/2025", "2024-11-30", "05/02/2026"]
    montos = ["1500 Bs", "2400.00", "3200 Bs", "1800", "500.50 Bs", "4500 Bs"]
    notas = ["95", "82", "70", "48", "65", "88", "100", "55"]

    dataset = []

    for i in range(num_muestras):
        est = estudiantes[i % len(estudiantes)]
        doc = docentes[i % len(docentes)]
        prog = programas[i % len(programas)]
        mod = modulos[i % len(modulos)]
        fec = fechas[i % len(fechas)]
        monto = montos[i % len(montos)]
        nota = notas[i % len(notas)]

        tipo_patron = i % 3

        if tipo_patron == 0:
            # Académico
            texto = f"El estudiante {est} cursó el {mod} del programa {prog} con el docente {doc} obteniendo una nota final de {nota}."
            spans = [
                {"label": "ESTUDIANTE", "valor": est},
                {"label": "MODULO", "valor": mod},
                {"label": "PROGRAMA", "valor": prog},
                {"label": "DOCENTE", "valor": doc},
                {"label": "NOTA", "valor": nota},
            ]
        elif tipo_patron == 1:
            # Financiero
            texto = f"El alumno {est} registra un saldo pendiente de {monto} en fecha {fec} correspondiente a la cuota del {prog}."
            spans = [
                {"label": "ESTUDIANTE", "valor": est},
                {"label": "MONTO", "valor": monto},
                {"label": "FECHA", "valor": fec},
                {"label": "PROGRAMA", "valor": prog},
            ]
        else:
            # Docente / Módulo
            texto = f"En fecha {fec}, el docente {doc} fue asignado al {mod} del programa {prog}."
            spans = [
                {"label": "FECHA", "valor": fec},
                {"label": "DOCENTE", "valor": doc},
                {"label": "MODULO", "valor": mod},
                {"label": "PROGRAMA", "valor": prog},
            ]

        # Calcular offsets exactos
        spans_offsets = []
        for s in spans:
            val = s["valor"]
            idx = texto.find(val)
            if idx != -1:
                spans_offsets.append({
                    "label": s["label"],
                    "start": idx,
                    "end": idx + len(val),
                    "valor": val
                })

        dataset.append({
            "texto": texto,
            "entidades": spans_offsets
        })

    return dataset


# ── Entrenamiento de BETO con PyTorch / Transformers ────────────────────────

def tokenizar_y_alinear_etiquetas(tokenizer, texto: str, entidades: List[Dict[str, Any]], max_len: int = 128):
    """
    Alinea los subwords generados por el WordPiece de BETO con las etiquetas BIO,
    asignando -100 a los subtokens subsiguientes para ignorar el cómputo de CrossEntropyLoss.
    """
    encoding = tokenizer(
        texto,
        max_length=max_len,
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

        for ent in entidades:
            e_start = ent["start"]
            e_end = ent["end"]
            e_label = ent["label"]

            if start_char >= e_start and end_char <= e_end:
                if start_char == e_start:
                    tag = f"B-{e_label}"
                else:
                    tag = f"I-{e_label}"
                labels[i] = LABEL2ID.get(tag, LABEL2ID["O"])
                break

    return encoding, labels


def entrenar_beto_ner(
    model_name: str = "dccuchile/bert-base-spanish-wwm-cased",
    output_dir: str = "models/beto_ner_gira",
    epochs: int = 3,
    batch_size: int = 8,
    lr: float = 3e-5,
    num_samples: int = 100,
    device_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Ejecuta el fine-tuning de BETO para token classification.
    Si faltan dependencias o el modelo base, lanza RuntimeError (sin métricas simuladas).
    """
    os.makedirs(output_dir, exist_ok=True)

    try:
        import torch
        from torch.utils.data import Dataset, DataLoader
        from transformers import BertTokenizerFast, BertForTokenClassification, AutoTokenizer
    except ImportError as e:
        # Sin dependencias no hay entrenamiento: no se escribe ningún training_info.json
        raise RuntimeError(f"Torch/Transformers no disponibles: {e}. No se entrenó el modelo.") from e

    device = torch.device(device_name if device_name else ("cuda" if torch.cuda.is_available() else "cpu"))
    logger.info("Iniciando fine-tuning de BETO en dispositivo: %s", device)

    try:
        try:
            tokenizer = BertTokenizerFast.from_pretrained(model_name)
        except Exception:
            tokenizer = AutoTokenizer.from_pretrained(model_name)

        model = BertForTokenClassification.from_pretrained(
            model_name,
            num_labels=len(LABEL_LIST),
            id2label=ID2LABEL,
            label2id=LABEL2ID
        )
        model.to(device)
    except Exception as e_hub:
        # Sin modelo base no hay entrenamiento: nunca se registran métricas simuladas
        raise RuntimeError(f"No fue posible cargar '{model_name}': {e_hub}. No se entrenó el modelo.") from e_hub

    raw_data = generar_dataset_sintetico_dominio(num_samples)

    class DomainNERDataset(Dataset):
        def __init__(self, data):
            self.data = data

        def __len__(self):
            return len(self.data)

        def __getitem__(self, idx):
            item = self.data[idx]
            enc, labs = tokenizar_y_alinear_etiquetas(tokenizer, item["texto"], item["entidades"])
            return {
                "input_ids": enc["input_ids"].squeeze(0),
                "attention_mask": enc["attention_mask"].squeeze(0),
                "labels": torch.tensor(labs, dtype=torch.long)
            }

    train_ds = DomainNERDataset(raw_data)
    loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)

    optimizer = torch.optim.AdamW(model.parameters(), lr=lr)
    model.train()

    total_loss = 0.0
    for epoch in range(epochs):
        epoch_loss = 0.0
        for batch in loader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)

            optimizer.zero_grad()
            outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
            loss = outputs.loss
            loss.backward()
            optimizer.step()

            epoch_loss += loss.item()

        avg_loss = epoch_loss / max(1, len(loader))
        total_loss = avg_loss
        logger.info("Epoch %d/%d completado. Loss promedio: %.4f", epoch + 1, epochs, avg_loss)

    # Guardar modelo y tokenizer
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)

    metrics = {
        "status": "trained_success",
        "model_base": model_name,
        "output_dir": output_dir,
        "epochs": epochs,
        "loss_final": round(total_loss, 4),
        # Este script no evalúa: F1/precisión/recall reales se obtienen con
        # scripts/entrenar_beto_robusto.py sobre dev y test_gold_real.
        "f1_score": None,
        "precision": None,
        "recall": None,
        "device": str(device)
    }

    with open(os.path.join(output_dir, "training_info.json"), "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    logger.info("Modelo BETO guardado exitosamente en: %s", output_dir)
    return metrics


# ── CLI Runner ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="BETO Fine-Tuning y Extractor Relacional — GiraGroup BI")
    parser.add_argument("--train", action="store_true", help="Ejecutar fine-tuning sobre BETO")
    parser.add_argument("--epochs", type=int, default=3, help="Número de épocas")
    parser.add_argument("--batch_size", type=int, default=8, help="Batch size")
    parser.add_argument("--lr", type=float, default=3e-5, help="Learning rate")
    parser.add_argument("--model", type=str, default="dccuchile/bert-base-spanish-wwm-cased", help="Modelo base")
    parser.add_argument("--output_dir", type=str, default="models/beto_ner_gira", help="Directorio de salida")
    parser.add_argument("--extract_relations", action="store_true", help="Demostrar extracción relacional")
    parser.add_argument("--text", type=str, default=None, help="Texto de prueba para extracción")

    args = parser.parse_args()

    if args.train:
        res = entrenar_beto_ner(
            model_name=args.model,
            output_dir=args.output_dir,
            epochs=args.epochs,
            batch_size=args.batch_size,
            lr=args.lr
        )
        print("Resultado de entrenamiento:", json.dumps(res, indent=2))

    if args.extract_relations or args.text:
        sample_text = args.text or "El estudiante Carlos Mamani Quispe cursó el Módulo 1 Fundamentos de Big Data con el docente Lic. Roberto Carlos Duran obteniendo la nota 95, adeudando un monto de 1500 Bs."
        # Extraer entidades usando gazetteer / regex de simulación
        ents = [
            {"tipo": "ESTUDIANTE", "valor": "Carlos Mamani Quispe", "score": 0.96, "start": 15, "end": 35},
            {"tipo": "MODULO", "valor": "Módulo 1 Fundamentos de Big Data", "score": 0.94, "start": 45, "end": 77},
            {"tipo": "DOCENTE", "valor": "Lic. Roberto Carlos Duran", "score": 0.95, "start": 93, "end": 118},
            {"tipo": "NOTA", "valor": "95", "score": 0.99, "start": 137, "end": 139},
            {"tipo": "MONTO", "valor": "1500 Bs", "score": 0.92, "start": 164, "end": 171}
        ]
        tuplas = extraer_tuplas_relacionales(ents, sample_text)
        print("\n--- Extracción de Tuplas Relacionales ---")
        print("Texto:", sample_text)
        print("Tuplas extraídas:")
        print(json.dumps(tuplas, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
