#!/usr/bin/env python
"""
scripts/contar_filas_uploads.py
================================
Recorre exhaustivamente uploads/data/ e inspecciona cada libro y hoja de cálculo.
Calcula:
- Filas totales
- Filas procesables (datos reales)
- Filas descartadas (subtotales, firmas, encabezados vacíos, ruido)
- Columnas detectadas
- Tipo de contenido inferido

Genera la Tabla 3.19 en formato Markdown y persiste el resultado en output/tabla_3_19_recuento_uploads.csv.
"""

import os
import glob
import re
import unicodedata
import pandas as pd
import openpyxl

SUBTOTAL_KEYWORDS = [
    "promedio", "promedio general", "media del curso", "overall average", "total",
    "subtotal", "suma", "firma", "docente:", "director", "coordinador", "rector",
    "observaciones generales:", "v°b°", "aprobado por:"
]

def strip_accents(text: str) -> str:
    if not text:
        return ""
    return "".join(
        c for c in unicodedata.normalize("NFD", str(text))
        if unicodedata.category(c) != "Mn"
    ).lower().strip()

def es_fila_ruido(fila_valores) -> bool:
    texto_fila = " ".join([str(v) for v in fila_valores if pd.notna(v)]).lower()
    if not texto_fila.strip():
        return True
    for kw in SUBTOTAL_KEYWORDS:
        if kw in texto_fila:
            return True
    return False

def inferir_categoria(nombre_archivo: str, nombre_hoja: str, columnas: list) -> str:
    cadena = f"{nombre_archivo} {nombre_hoja} {' '.join([str(c) for c in columnas])}".lower()
    if any(k in cadena for k in ["nota", "acta", "modulo", "arca", "calificacion"]):
        return "Académico / Actas"
    if any(k in cadena for k in ["cobranza", "egreso", "techo", "meta", "ingreso", "factura"]):
        return "Financiero / Cartera"
    if any(k in cadena for k in ["evaluacion docente", "experiencia docente", "encuesta"]):
        return "Desempeño Docente"
    if any(k in cadena for k in ["inscrito", "admision", "moodle", "forms"]):
        return "Admisiones / Inscritos"
    return "Planificación / OKRs"

def analizar_archivo_excel(ruta: str):
    resultados = []
    nombre_arch = os.path.basename(ruta)
    try:
        wb = openpyxl.load_workbook(ruta, data_only=True, read_only=True)
        hojas = wb.sheetnames
    except Exception as e:
        print(f"Error abriendo {nombre_arch} con openpyxl: {e}")
        try:
            xl = pd.ExcelFile(ruta)
            hojas = xl.sheet_names
        except Exception as e2:
            print(f"Error definitivo con pandas: {e2}")
            return resultados

    for hoja in hojas:
        try:
            df = pd.read_excel(ruta, sheet_name=hoja)
            filas_totales = len(df)
            if filas_totales == 0:
                resultados.append({
                    "archivo": nombre_arch,
                    "hoja": hoja,
                    "filas_totales": 0,
                    "filas_procesables": 0,
                    "filas_descartadas": 0,
                    "columnas": len(df.columns),
                    "categoria": inferir_categoria(nombre_arch, hoja, list(df.columns))
                })
                continue

            filas_ruido = 0
            filas_procesables = 0
            for _, row in df.iterrows():
                if es_fila_ruido(row.values):
                    filas_ruido += 1
                else:
                    filas_procesables += 1

            resultados.append({
                "archivo": nombre_arch,
                "hoja": hoja,
                "filas_totales": filas_totales,
                "filas_procesables": filas_procesables,
                "filas_descartadas": filas_ruido,
                "columnas": len(df.columns),
                "categoria": inferir_categoria(nombre_arch, hoja, list(df.columns))
            })
        except Exception as err:
            print(f"Error procesando {nombre_arch} [{hoja}]: {err}")
            resultados.append({
                "archivo": nombre_arch,
                "hoja": hoja,
                "filas_totales": 0,
                "filas_procesables": 0,
                "filas_descartadas": 0,
                "columnas": 0,
                "categoria": "No legible"
            })
    return resultados

def main():
    patron_xlsx = os.path.join("uploads", "data", "*.xlsx")
    patron_csv = os.path.join("uploads", "data", "*.csv")
    archivos = sorted(glob.glob(patron_xlsx) + glob.glob(patron_csv))

    os.makedirs("output", exist_ok=True)
    todos_resultados = []

    print(f"Iniciando análisis de {len(archivos)} archivos en uploads/data/...")
    for ruta in archivos:
        if ruta.endswith(".xlsx"):
            res = analizar_archivo_excel(ruta)
            todos_resultados.extend(res)
        elif ruta.endswith(".csv"):
            nombre_arch = os.path.basename(ruta)
            try:
                df = pd.read_csv(ruta)
                filas_totales = len(df)
                filas_ruido = sum(1 for _, row in df.iterrows() if es_fila_ruido(row.values))
                todos_resultados.append({
                    "archivo": nombre_arch,
                    "hoja": "N/A (CSV)",
                    "filas_totales": filas_totales,
                    "filas_procesables": filas_totales - filas_ruido,
                    "filas_descartadas": filas_ruido,
                    "columnas": len(df.columns),
                    "categoria": inferir_categoria(nombre_arch, "CSV", list(df.columns))
                })
            except Exception as e:
                print(f"Error procesando CSV {nombre_arch}: {e}")

    df_out = pd.DataFrame(todos_resultados)
    csv_path = os.path.join("output", "tabla_3_19_recuento_uploads.csv")
    df_out.to_csv(csv_path, index=False, encoding="utf-8")
    print(f"\nDatos guardados exitosamente en: {csv_path}")

    # Imprimir Tabla Markdown Resumida
    print("\n### Tabla 3.19: Inventario Exhaustivo de Archivos y Hojas en uploads/data/\n")
    print("| Archivo Fuente | Hoja de Cálculo | Categoría Temática | Columnas | Filas Totales | Filas Procesables | Filas Descartadas |")
    print("| :--- | :--- | :--- | :---: | :---: | :---: | :---: |")

    tot_filas = 0
    tot_proc = 0
    tot_desc = 0

    for _, r in df_out.iterrows():
        print(f"| `{r['archivo']}` | `{r['hoja']}` | {r['categoria']} | {r['columnas']} | {r['filas_totales']:,} | {r['filas_procesables']:,} | {r['filas_descartadas']:,} |")
        tot_filas += r['filas_totales']
        tot_proc += r['filas_procesables']
        tot_desc += r['filas_descartadas']

    print(f"| **TOTAL CONSOLIDADO** | **{len(df_out)} hojas** | — | — | **{tot_filas:,}** | **{tot_proc:,}** | **{tot_desc:,}** |")

if __name__ == "__main__":
    main()
