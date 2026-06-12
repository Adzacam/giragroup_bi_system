"""
prototype_nlp.py — GIRA-9
Script SQA independiente para validar el motor NER (BETO).
Calcula Precision, Recall y F1 sobre un corpus etiquetado.

Uso:
    python tests/prototype_nlp.py --corpus uploads/corpus_prueba/
"""

import argparse
import json
import os
import sys

# Agregar raíz del proyecto al path para importar módulos del pipeline
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.normalization.ner_engine import BetoNerEngine


def cargar_corpus(directorio: str) -> list[dict]:
    """
    Carga archivos JSON etiquetados desde un directorio.
    Formato esperado por archivo:
    {
        "texto": "El Ing. Carlos Mendez de la Universidad Univalle...",
        "entidades_esperadas": {
            "PER": ["Carlos Mendez"],
            "ORG": ["Universidad Univalle"]
        }
    }
    """
    corpus = []
    if not os.path.isdir(directorio):
        print(f"[ERROR] Directorio no encontrado: {directorio}")
        return corpus

    for nombre_archivo in sorted(os.listdir(directorio)):
        if not nombre_archivo.endswith(".json"):
            continue
        ruta = os.path.join(directorio, nombre_archivo)
        with open(ruta, "r", encoding="utf-8") as f:
            corpus.append(json.load(f))

    return corpus


def calcular_metricas(esperados: list[str], predichos: list[str]) -> dict:
    """Calcula Precision, Recall y F1 entre dos listas de strings."""
    set_esperados = set(e.lower().strip() for e in esperados)
    set_predichos = set(p.lower().strip() for p in predichos)

    if not set_esperados and not set_predichos:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0}

    verdaderos_positivos = len(set_esperados & set_predichos)

    precision = verdaderos_positivos / len(set_predichos) if set_predichos else 0.0
    recall = verdaderos_positivos / len(set_esperados) if set_esperados else 0.0

    if precision + recall == 0:
        f1 = 0.0
    else:
        f1 = 2 * (precision * recall) / (precision + recall)

    return {"precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4)}


def main():
    parser = argparse.ArgumentParser(description="Prototipo SQA para motor NER BETO")
    parser.add_argument("--corpus", required=True, help="Ruta al directorio del corpus etiquetado")
    args = parser.parse_args()

    print("=" * 60)
    print("  PROTOTIPO SQA — Motor NER BETO (GIRA-9)")
    print("=" * 60)

    corpus = cargar_corpus(args.corpus)
    if not corpus:
        print("[ERROR] No se encontraron archivos .json en el corpus.")
        sys.exit(1)

    print(f"\n  Muestras cargadas: {len(corpus)}")

    engine = BetoNerEngine()

    metricas_per_total = {"precision": [], "recall": [], "f1": []}
    metricas_org_total = {"precision": [], "recall": [], "f1": []}

    for i, muestra in enumerate(corpus):
        texto = muestra.get("texto", "")
        esperadas = muestra.get("entidades_esperadas", {})

        resultado = engine.extraer_entidades(texto)

        m_per = calcular_metricas(
            esperadas.get("PER", []),
            resultado["entidades_per"]
        )
        m_org = calcular_metricas(
            esperadas.get("ORG", []),
            resultado["entidades_org"]
        )

        for k in metricas_per_total:
            metricas_per_total[k].append(m_per[k])
        for k in metricas_org_total:
            metricas_org_total[k].append(m_org[k])

        print(f"\n  [{i+1}/{len(corpus)}] Confianza NER: {resultado['confianza_ner']}")
        print(f"    PER → P={m_per['precision']}  R={m_per['recall']}  F1={m_per['f1']}")
        print(f"    ORG → P={m_org['precision']}  R={m_org['recall']}  F1={m_org['f1']}")

    # Promedios globales
    print("\n" + "=" * 60)
    print("  RESULTADOS GLOBALES")
    print("=" * 60)

    def promedio(lst):
        return round(sum(lst) / len(lst), 4) if lst else 0.0

    print(f"\n  PER (Personas):")
    print(f"    Precision:  {promedio(metricas_per_total['precision'])}")
    print(f"    Recall:     {promedio(metricas_per_total['recall'])}")
    print(f"    F1:         {promedio(metricas_per_total['f1'])}")

    print(f"\n  ORG (Organizaciones):")
    print(f"    Precision:  {promedio(metricas_org_total['precision'])}")
    print(f"    Recall:     {promedio(metricas_org_total['recall'])}")
    print(f"    F1:         {promedio(metricas_org_total['f1'])}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
