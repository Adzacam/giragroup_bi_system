"""L6-0: inventario de hojas y columnas del lote Excel y busqueda de embudo previo a inscripcion.

Solo lectura. Imprime encabezados (nombres de columna) y conteos; no imprime valores de celda.
Uso: python -I adw_l6_0_inventario_excel.py <carpeta_xlsx> <csv_salida>
"""
import csv
import os
import re
import sys

import openpyxl

KW = re.compile(r"interes|lead|prospect|reserv|postulan|preinscri|pre-inscri|pre inscri|captaci|"
                "contacto|solicitud|admisi|embudo|inscrit|matricul|consulta", re.IGNORECASE)
HEADER_KW = re.compile(r"interes|lead|prospect|reserv|postulan|preinscri|pre-inscri|pre inscri|"
                       "captaci|contacto|solicitud|admisi|embudo", re.IGNORECASE)

ARCHIVOS = {
    "TBL_INSCRITOS.xlsx": "doc 44",
    "BD Cobranzas.xlsx": "doc 36",
    "BD Techos.xlsx": "doc 37",
    "EJECUTADO VS META.xlsx": "doc 38",
    "BD Egresos.xlsx": "doc 39",
    "[BBDD] ANTIGUO RESPUESTAS EVALUACIÓN DOCENTE - EXP. UNIFRANZ POSTGRADO.xlsx": "doc 40",
    "Evaluación Docente y Unifranz.xlsx": "doc 41",
    "Experiencia Docente 2.0.xlsx": "doc 42",
    "Base centralizada Académica ARCA (1).xlsx": "doc 43",
    "PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx": "doc 1",
}


def encabezado(filas):
    """Primera fila de las 15 primeras con >= 2 celdas de texto no vacias."""
    for i, fila in enumerate(filas[:15]):
        textos = [c for c in fila if isinstance(c, str) and c.strip()]
        if len(textos) >= 2:
            return i, fila
    return None, []


def main(carpeta, salida):
    filas_csv = []
    resumen = []
    for nombre, doc in ARCHIVOS.items():
        ruta = os.path.join(carpeta, nombre)
        if not os.path.exists(ruta):
            resumen.append((doc, nombre, "NO EXISTE", ""))
            continue
        wb = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
        for hoja in wb.sheetnames:
            ws = wb[hoja]
            filas = [list(r) for r in ws.iter_rows(values_only=True)]
            idx, cab = encabezado(filas)
            if idx is None:
                resumen.append((doc, nombre, hoja, "sin encabezado de texto (filas=%d)" % len(filas)))
                continue
            datos = filas[idx + 1:]
            ncol = len(cab)
            nombres = [str(c).strip() if c is not None else "(vacia_%d)" % (j + 1) for j, c in enumerate(cab)]
            resumen.append((doc, nombre, hoja, "filas_datos=%d cols=%d" % (len(datos), ncol)))
            for j in range(ncol):
                col_vals = [r[j] if j < len(r) else None for r in datos]
                n_no_vacias = sum(1 for v in col_vals if v is not None and str(v).strip() != "")
                cab_hit = bool(HEADER_KW.search(nombres[j]))
                hits = {}
                for v in col_vals:
                    if isinstance(v, str):
                        m = KW.search(v)
                        if m:
                            k = m.group(0).lower()
                            hits[k] = hits.get(k, 0) + 1
                hits_txt = ";".join("%s=%d" % kv for kv in sorted(hits.items()))
                filas_csv.append({
                    # hojas sin cabecera real: la «cabecera» detectada es una fila de datos (PII); se enmascara
                    "doc": doc, "archivo": nombre, "hoja": hoja,
                    "columna": ("[celda de datos sin cabecera: enmascarada]"
                                if hoja == "BAJAS POR DUPLICADOS" or re.search(r"@|\d{6,}", nombres[j])
                                else nombres[j]),
                    "n_filas_datos": len(datos), "n_no_vacias": n_no_vacias,
                    "kw_en_encabezado": "SI" if cab_hit else "", "kw_en_valores_celda": hits_txt,
                })
        wb.close()

    with open(salida, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["doc", "archivo", "hoja", "columna", "n_filas_datos",
                                          "n_no_vacias", "kw_en_encabezado", "kw_en_valores_celda"])
        w.writeheader()
        w.writerows(filas_csv)

    for r in resumen:
        print(" | ".join(str(x) for x in r))
    print("columnas_total=%d" % len(filas_csv))
    for r in filas_csv:
        if r["kw_en_encabezado"] or r["kw_en_valores_celda"]:
            print("HIT", r["doc"], "|", r["hoja"], "|", r["columna"], "| no_vacias=", r["n_no_vacias"],
                  "| valores:", r["kw_en_valores_celda"])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
