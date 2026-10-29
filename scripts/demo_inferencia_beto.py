"""
scripts/demo_inferencia_beto.py
Demostracion ejecutable de inferencia en tiempo real con BETO Local (NER).
Carga el checkpoint propio fine-tuneado 'pipeline/semantic/beto_local' y
extrae entidades sobre 4 lineas reales representativas del corpus universitario.
"""

import sys
import torch
from pathlib import Path
from transformers import BertTokenizerFast, BertForTokenClassification

ROOT_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = ROOT_DIR / "pipeline" / "semantic" / "beto_local"

def main():
    print("=" * 70)
    print("GIRAGROUP BI — INFERENCIA NER EN PRODUCCIÓN CON BETO LOCAL")
    print(f"Modelo cargado: {MODEL_PATH}")
    print("=" * 70)

    tokenizer = BertTokenizerFast.from_pretrained(str(MODEL_PATH))
    model = BertForTokenClassification.from_pretrained(str(MODEL_PATH))
    model.eval()

    id2label = model.config.id2label

    oraciones_reales = [
        "En el programa Diplomado en Finanzas Corporativas, el docente Lic. Carlos Mendoza evaluó al estudiante Marco Antonio Rojas en el módulo Módulo 1 con la nota 85.",
        "Asignación académica de Maestría en Educación Superior: Ing. Roberto Fernandez dictó el módulo Metodología de la Investigación en fecha 2025-03-15.",
        "En la evaluación del programa Experto en Ciberseguridad, la estudiante Patricia Morales Siles calificó al docente MSc. Javier Morales en el taller Seguridad Ofensiva.",
        "PROGRAMA: Diplomado en Big Data | MODULO: Arquitecturas Cloud | DOCENTE: Carlos Mendoza | ESTUDIANTE: Alejandro Vargas | NOTA: 78"
    ]

    for idx, oracion in enumerate(oraciones_reales, start=1):
        print(f"\n[LÍNEA REAL #{idx}]:")
        print(f"Texto: \"{oracion}\"")
        
        inputs = tokenizer(oracion, return_tensors="pt", truncation=True, max_length=128)
        with torch.no_grad():
            outputs = model(**inputs)
            logits = outputs.logits
            probs = torch.softmax(logits, dim=-1)

        token_ids = inputs["input_ids"][0]
        tokens = tokenizer.convert_ids_to_tokens(token_ids)
        pred_ids = torch.argmax(probs[0], dim=-1)

        entidades_detectadas = []
        current_entity = []
        current_type = None
        current_scores = []

        for tid, token, pid, prob_vector in zip(token_ids, tokens, pred_ids, probs[0]):
            if tid in (tokenizer.cls_token_id, tokenizer.sep_token_id, tokenizer.pad_token_id):
                continue
            label = id2label[int(pid)]
            score = float(prob_vector[pid].item())

            if label.startswith("B-"):
                if current_entity:
                    entidades_detectadas.append((
                        "".join(current_entity).replace("##", " "),
                        current_type,
                        sum(current_scores) / len(current_scores)
                    ))
                current_type = label[2:]
                current_entity = [token]
                current_scores = [score]
            elif label.startswith("I-") and current_type == label[2:]:
                current_entity.append(token if not token.startswith("##") else token[2:])
                current_scores.append(score)
            else:
                if current_entity:
                    entidades_detectadas.append((
                        "".join(current_entity).replace("##", " "),
                        current_type,
                        sum(current_scores) / len(current_scores)
                    ))
                    current_entity = []
                    current_type = None
                    current_scores = []

        if current_entity:
            entidades_detectadas.append((
                "".join(current_entity).replace("##", " "),
                current_type,
                sum(current_scores) / len(current_scores)
            ))

        print("Entidades Extraídas por BETO:")
        if entidades_detectadas:
            for ent_text, ent_type, conf in entidades_detectadas:
                print(f"  • {ent_type:<16} : \"{ent_text.strip()}\" (Confianza: {conf * 100:.2f}%)")
        else:
            print("  (Sin entidades detectadas)")

    print("\n" + "=" * 70)
    print("Inferencia completada con éxito. Checkpoint local operativo.")
    print("=" * 70)

if __name__ == "__main__":
    main()
