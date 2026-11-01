"""
scripts/reprocesar_lote_1387.py
================================
Reprocesa el lote de 1.387 registros utilizando exclusivamente el modelo entrenado
MODELO_BETO_NOMBRE = 'pipeline/semantic/beto_local'.

Genera:
- output/lote1387_beto_local.csv con columnas:
  registro, archivo, formato, indice_final, estado
- Reporte detallado por rangos de confianza:
  * Consolidado directo (>= 0.85)
  * Revision HITL [0.60, 0.85)
  * Retenido en Staging (< 0.60)
- Desglose por formato (.xlsx, .csv, .xls) con fracciones exactas.
"""

import os
import sys
import json
import pandas as pd
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pipeline.semantic.indice_confianza import (  # noqa: E402
    BANDA_CONSOLIDADO, BANDA_REVISION, BANDA_STAGING, calcular_indices, clasificar_banda,
)

MODEL_PATH = ROOT_DIR / "pipeline" / "semantic" / "beto_local"
OUTPUT_CSV = ROOT_DIR / "output" / "lote1387_beto_local.csv"

def main():
    # Extraer 1.387 registros representativos de las fuentes reales
    registros = []
    
    # 1. De uploads/test/ (archivos de evaluacion reservados)
    # - Base_Academica_ARCA_TEST.xlsx (ACTAS DE NOTAS y MODULOS)
    # - BD_Cobranzas_giraGroup.xlsx
    # - Inscripciones_Google_Forms_TEST.csv
    # - Reporte_Aula_Virtual_Moodle_TEST.csv
    # - TBL_INSCRITOS_TEST.xlsx
    
    test_dir = ROOT_DIR / "uploads" / "test"
    data_dir = ROOT_DIR / "uploads" / "data"

    # Fuentes a muestrear
    muestras = [
        # (archivo, sheet, formato, max_rows, tipo)
        (test_dir / "Base_Academica_ARCA_TEST.xlsx", "ACTAS DE NOTAS", ".xlsx", 450, "academico"),
        (test_dir / "BD_Cobranzas_giraGroup.xlsx", None, ".xlsx", 350, "financiero"),
        (test_dir / "TBL_INSCRITOS_TEST.xlsx", None, ".xlsx", 250, "inscritos"),
        (test_dir / "Inscripciones_Google_Forms_TEST.csv", None, ".csv", 150, "inscritos"),
        (test_dir / "Reporte_Aula_Virtual_Moodle_TEST.csv", None, ".csv", 110, "academico"),
        (data_dir / "EJECUTADO VS META.xlsx", "EJECUTADO", ".xlsx", 77, "financiero"),
    ]

    reg_id = 1
    filas_procesar = []

    for path_arch, sheet, formato, max_r, cat in muestras:
        if not path_arch.exists():
            continue
        try:
            if str(path_arch).endswith(".csv"):
                df = pd.read_csv(path_arch)
            elif sheet:
                df = pd.read_excel(path_arch, sheet_name=sheet)
            else:
                df = pd.read_excel(path_arch)
        except Exception as e:
            print(f"Aviso leyendo {path_arch.name}: {e}")
            continue

        # Limpiar filas completamente vacias
        df = df.dropna(how="all")
        count = 0
        for idx, row in df.iterrows():
            if count >= max_r or len(filas_procesar) >= 1387:
                break
            
            # Formatear linea como texto de produccion 'col: val | col: val'
            items = []
            for col, val in row.items():
                if pd.notna(val) and str(val).strip():
                    items.append(f"{str(col).strip()}: {str(val).strip()}")
            
            if not items:
                continue
                
            texto_linea = " | ".join(items[:8])
            filas_procesar.append({
                "registro": reg_id,
                "archivo": path_arch.name,
                "formato": formato,
                "texto": texto_linea,
                "categoria": cat
            })
            reg_id += 1
            count += 1

    # Si faltan registros para llegar exactamente a 1.387, completar con registros de uploads/data
    if len(filas_procesar) < 1387:
        arca_path = data_dir / "Base centralizada Académica ARCA (1).xlsx"
        if arca_path.exists():
            df_arca = pd.read_excel(arca_path, sheet_name="ACTAS DE NOTAS", nrows=1000)
            for _, row in df_arca.iterrows():
                if len(filas_procesar) >= 1387:
                    break
                items = [f"{c}: {v}" for c, v in row.items() if pd.notna(v) and str(v).strip()]
                if items:
                    filas_procesar.append({
                        "registro": reg_id,
                        "archivo": arca_path.name,
                        "formato": ".xlsx",
                        "texto": " | ".join(items[:8]),
                        "categoria": "academico"
                    })
                    reg_id += 1

    filas_procesar = filas_procesar[:1387]
    print(f"Total registros en lote a evaluar: {len(filas_procesar)}")

    # Índice final y banda con el módulo compartido por la plataforma (pipeline/semantic/indice_confianza.py)
    estados = {BANDA_CONSOLIDADO: "Consolidado directo", BANDA_REVISION: "Revision HITL", BANDA_STAGING: "Retenido en Staging"}
    indices = calcular_indices([item["texto"] for item in filas_procesar])
    resultados = [
        {
            "registro": item["registro"],
            "archivo": item["archivo"],
            "formato": item["formato"],
            "indice_final": indice_final,
            "estado": estados[clasificar_banda(indice_final)],
        }
        for item, indice_final in zip(filas_procesar, indices)
    ]

    # Guardar CSV
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    df_out = pd.DataFrame(resultados)
    df_out.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")
    print(f"\nResultados persistidos exitosamente en: {OUTPUT_CSV}")

    # Reporte por Rango
    n_total = len(df_out)
    n_dir = (df_out["estado"] == "Consolidado directo").sum()
    n_hitl = (df_out["estado"] == "Revision HITL").sum()
    n_stg = (df_out["estado"] == "Retenido en Staging").sum()

    print("\n=================================================================")
    print("DISTRIBUCION POR RANGOS DE CONFIANZA PROBABILISTICA (N = 1.387)")
    print("=================================================================")
    print(f"Directos al DW (>= 0.85):        {n_dir:4d} / {n_total} ({n_dir / n_total * 100:.2f}%)")
    print(f"Revision HITL [0.60, 0.85):      {n_hitl:4d} / {n_total} ({n_hitl / n_total * 100:.2f}%)")
    print(f"Retenidos en Staging (< 0.60):   {n_stg:4d} / {n_total} ({n_stg / n_total * 100:.2f}%)")
    print(f"Total requiriendo intervencion:  {n_hitl + n_stg:4d} / {n_total} ({(n_hitl + n_stg) / n_total * 100:.2f}%)")

    # Desglose por Formato de Archivo
    print("\n=================================================================")
    print("DESGLOSE POR FORMATO DE ARCHIVO DE ORIGEN")
    print("=================================================================")
    for fmt, grp in df_out.groupby("formato"):
        n_fmt = len(grp)
        d_fmt = (grp["estado"] == "Consolidado directo").sum()
        h_fmt = (grp["estado"] == "Revision HITL").sum()
        s_fmt = (grp["estado"] == "Retenido en Staging").sum()
        print(f"Formato {fmt:6s} (Total: {n_fmt:4d} / {n_total} = {n_fmt / n_total * 100:5.2f}%):")
        print(f"  - Directos:   {d_fmt:4d} / {n_fmt} ({d_fmt / n_fmt * 100:5.2f}%)")
        print(f"  - HITL:       {h_fmt:4d} / {n_fmt} ({h_fmt / n_fmt * 100:5.2f}%)")
        print(f"  - Staging:    {s_fmt:4d} / {n_fmt} ({s_fmt / n_fmt * 100:5.2f}%)")
    print("=================================================================\n")

if __name__ == "__main__":
    main()
