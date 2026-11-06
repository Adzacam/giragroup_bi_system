import json
from pathlib import Path

def main():
    p = Path("docs/evidencias/ablacion_beto.json")
    with open(p, "r", encoding="utf-8") as f:
        d = json.load(f)

    with open("docs/evidencias/lote_1387_uploads_data_arquitectura_b.json", "r", encoding="utf-8") as f_up:
        d_up = json.load(f_up)

    d["metricas_produccion_arquitectura_b_uploads_data"] = d_up

    d["definicion_f1_relajado"] = {
        "criterio_coincidencia": "Token-overlap matching con preservacion de tipo semantico",
        "condicion_acierto": "Se considera True Positive (TP) si tipo(e_pred) == tipo(e_gold) y len(set(tokens_gold) & set(tokens_pred)) >= 1 (interseccion de indices de tokens no vacia)",
        "diferencia_con_estricto": "La evaluacion estricta (seqeval / CoNLL-2003) exige coincidencia exacta de limites de frontera de inicio y fin de todos los tokens del span (B-... I-...). La evaluacion relajada tolera cuando el analizador captura el valor semantico de la entidad omitiendo prefijos sintacticos o palabras de control (e.g., extraer '1' o '1 - Derecho Notarial' cuando el gold etiqueto 'Modulo 1', o diferencias en articulos iniciales)",
        "formulas_matematicas": {
            "precision_relajada": "Precision_relajada = |{e_pred : existe e_gold con tipo(e_pred)=tipo(e_gold) y tokens(e_pred) ∩ tokens(e_gold) != vacio}| / |E_pred|",
            "recall_relajado": "Recall_relajado = |{e_gold : existe e_pred con tipo(e_pred)=tipo(e_gold) y tokens(e_pred) ∩ tokens(e_gold) != vacio}| / |E_gold|",
            "f1_relajado": "F1_relajado = 2 * (Precision_relajada * Recall_relajado) / max(1e-6, Precision_relajada + Recall_relajado)"
        }
    }

    with open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)

    print("docs/evidencias/ablacion_beto.json actualizado exitosamente.")

if __name__ == "__main__":
    main()
