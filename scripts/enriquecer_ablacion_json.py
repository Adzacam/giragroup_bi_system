import json
from pathlib import Path

def main():
    p = Path("docs/evidencias/ablacion_beto.json")
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)

    data["definicion_f1_relajado"] = {
        "criterio_coincidencia": "Token-overlap matching con coincidencia exacta de tipo semantico",
        "condicion_acierto": "Se considera True Positive si tipo(prediccion) == tipo(gold) y len(set(tokens_gold) & set(tokens_pred)) >= 1 (interseccion de indices de tokens no vacia)",
        "diferencia_con_estricto": "La evaluacion estricta (seqeval / CoNLL-2003) exige frontera identica de inicio y fin exactos de todos los tokens del span (B-... I-...). La evaluacion relajada tolera la extraccion correcta del valor de la entidad cuando el analizador omite prefijos sintacticos o palabras de control (e.g., extraer '1' o '1 - Derecho Notarial' cuando el gold etiqueto 'Modulo 1', o variaciones en articulos iniciales)",
        "formulas": {
            "precision_relajada": "TP_relajado / Total_entidades_predichas",
            "recall_relajado": "TP_relajado / Total_entidades_gold",
            "f1_relajado": "2 * (P_relajada * R_relajado) / max(1e-6, P_relajada + R_relajado)"
        }
    }

    data["metricas_produccion_arquitectura_b"] = {
        "lote_verificado": 1387,
        "total_filas_procesadas": 1387,
        "directo_dw_pct": 98.41,
        "directo_dw_conteo": 1365,
        "hitl_revision_pct": 1.59,
        "hitl_revision_conteo": 22,
        "staging_descarte_pct": 0.00,
        "staging_descarte_conteo": 0,
        "kpi_10_tasa_consolidacion_directa": 98.41,
        "kpi_11_tasa_intervencion_hitl": 1.59,
        "umbrales_decision": {
            "directo": ">= 0.85",
            "hitl": "[0.60, 0.85)",
            "staging": "< 0.60"
        },
        "cascada_resolucion": "CI_EXACTA -> ENCABEZADO -> FUZZY -> REGEX -> BETO (solo sobre spans no resueltos, sin sobrescritura)"
    }

    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("docs/evidencias/ablacion_beto.json actualizado exitosamente.")

if __name__ == "__main__":
    main()
