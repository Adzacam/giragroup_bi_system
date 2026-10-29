#!/usr/bin/env python
"""
scripts/evaluar_robustez_layouts.py
===================================
Evalúa los 5 layouts adversarios con estructuras inéditas (Punto 5):
Mide:
- Filas totales del archivo
- Filas leídas / procesadas por el pipeline
- Entidades extraídas por BetoNEREngine
- Filas derivadas a staging (stg_entidad_no_resuelta)
- Excepciones no controladas (exigencia: 0)

Persiste el reporte de robustez en output/reporte_robustez_layouts.json.
"""

import os
import sys
import glob
import json
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from pipeline.normalization.asymmetric_flattener import AsymmetricFlattener
from pipeline.ingesta import leer_archivo, detectar_bloques, a_texto_plano
from pipeline.semantic.ner_engine import BetoNEREngine

def evaluar_layouts():
    carpeta = os.path.join("uploads", "test", "layouts_adversarios")
    archivos = sorted(glob.glob(os.path.join(carpeta, "*.xlsx")))
    
    engine = BetoNEREngine()
    resultados = []
    
    print(f"Iniciando evaluación de robustez sobre {len(archivos)} layouts adversarios...\n")

    total_excepciones = 0

    for ruta in archivos:
        nombre = os.path.basename(ruta)
        stats = {
            "archivo": nombre,
            "filas_totales": 0,
            "filas_procesadas": 0,
            "entidades_extraidas": 0,
            "derivadas_staging": 0,
            "excepciones": 0,
            "detalle_entidades": {},
            "status": "PASS"
        }

        try:
            with open(ruta, "rb") as f:
                file_bytes = f.read()

            # Diagnóstico de estructura asimétrica
            asym_res = AsymmetricFlattener.procesar_archivo_asimetrico(file_bytes, nombre)
            diag = asym_res.get("diagnostico_estructural", {})

            # Lectura de hojas
            hojas_dict = leer_archivo(ruta)
            filas_totales_libro = sum(len(df) for df in hojas_dict.values())
            stats["filas_totales"] = filas_totales_libro

            for nombre_hoja, df_hoja in hojas_dict.items():
                if df_hoja is None or df_hoja.empty:
                    continue

                bloques = detectar_bloques(df_hoja)
                if not bloques:
                    bloques = [df_hoja]

                for b in bloques:
                    if b.empty:
                        continue
                    
                    texto_plano = a_texto_plano(b)
                    lineas = [l.strip() for l in texto_plano.split("\n") if l.strip()]
                    stats["filas_procesadas"] += len(lineas)

                    for linea in lineas:
                        try:
                            ner_res = engine.extraer_entidades(linea)
                            ents = ner_res.entidades
                            stats["entidades_extraidas"] += len(ents)

                            for e in ents:
                                tipo = str(e.tipo).replace("TipoEntidad.", "")
                                stats["detalle_entidades"][tipo] = stats["detalle_entidades"].get(tipo, 0) + 1

                            # Si no se reconoció estudiante o programa, derivar a staging sin perder registro
                            tiene_est = any(str(e.tipo).endswith("ESTUDIANTE") for e in ents)
                            tiene_prog = any(str(e.tipo).endswith("PROGRAMA") for e in ents)

                            if not (tiene_est and tiene_prog):
                                stats["derivadas_staging"] += 1

                        except Exception as e_line:
                            stats["excepciones"] += 1
                            total_excepciones += 1
                            print(f"  [ERROR] Excepción en línea: {e_line}")

        except Exception as e_file:
            stats["excepciones"] += 1
            stats["status"] = "FAIL"
            total_excepciones += 1
            print(f"[FAIL] Excepción al procesar archivo {nombre}: {e_file}")

        resultados.append(stats)
        print(f"| {nombre:<42} | Tot: {stats['filas_totales']:<2} | Proc: {stats['filas_procesadas']:<2} | Ent: {stats['entidades_extraidas']:<2} | Stg: {stats['derivadas_staging']:<2} | Exc: {stats['excepciones']} |")

    os.makedirs("output", exist_ok=True)
    out_json = os.path.join("output", "reporte_robustez_layouts.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({
            "total_archivos_evaluados": len(archivos),
            "total_excepciones_globales": total_excepciones,
            "criterio_cero_excepciones_cumplido": (total_excepciones == 0),
            "detalle_layouts": resultados
        }, f, indent=2, ensure_ascii=False)

    print(f"\nEvaluación de robustez completada. Excepciones totales: {total_excepciones}")
    print(f"Reporte guardado en: {out_json}")

if __name__ == "__main__":
    evaluar_layouts()
