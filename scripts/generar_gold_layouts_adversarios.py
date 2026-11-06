# scripts/generar_gold_layouts_adversarios.py
"""
Genera el Gold Standard formal para los 5 layouts adversarios en
uploads/test/layouts_adversarios/gold_layouts_adversarios.json.
Etiquetado manual con anotación BIO a nivel token para evaluación con seqeval.
"""

import json
import os
import re

OUT_FILE = os.path.join("uploads", "test", "layouts_adversarios", "gold_layouts_adversarios.json")

def tokenizar(texto: str):
    # Tokenizador por palabras y puntuación idéntico al corpus de entrenamiento
    return [t for t in re.findall(r"[\w]+|[^\w\s]", texto, re.UNICODE) if t.strip()]

def alinear_bio(texto: str, spans: list):
    tokens = tokenizar(texto)
    tags = ["O"] * len(tokens)
    
    # Mapear spans sobre tokens
    for sp in spans:
        tipo = sp["tipo"]
        val = sp["valor"]
        val_tokens = tokenizar(val)
        n = len(val_tokens)
        
        # Buscar coincidencia exacta de subsecuencia
        matched = False
        for i in range(len(tokens) - n + 1):
            if [t.lower() for t in tokens[i:i+n]] == [vt.lower() for vt in val_tokens]:
                tags[i] = f"B-{tipo}"
                for j in range(1, n):
                    tags[i+j] = f"I-{tipo}"
                matched = True
                break
    return tokens, tags

# Definición de líneas y entidades gold reales
datos_gold = [
    # --- Layout 1: Cabeceras desconocidas ---
    {
        "archivo": "layout1_cabeceras_desconocidas.xlsx",
        "hoja": "PLANILLA_INEDITA",
        "fila_idx": 1,
        "texto": "Dr. Alejandro Siles | Mariana Choquehuanca | Módulo 1 Finanzas | 88 | Maestría en Finanzas",
        "spans": [
            {"tipo": "PER_DOCENTE", "valor": "Dr. Alejandro Siles"},
            {"tipo": "PER_ESTUDIANTE", "valor": "Mariana Choquehuanca"},
            {"tipo": "MODULO", "valor": "Módulo 1 Finanzas"},
            {"tipo": "NOTA", "valor": "88"},
            {"tipo": "PROGRAMA", "valor": "Maestría en Finanzas"}
        ]
    },
    {
        "archivo": "layout1_cabeceras_desconocidas.xlsx",
        "hoja": "PLANILLA_INEDITA",
        "fila_idx": 2,
        "texto": "Lic. Roberto Carlos Duran | Gabriel Alarcón Flores | Módulo 2 Gestión | 92 | Diplomado en BI",
        "spans": [
            {"tipo": "PER_DOCENTE", "valor": "Lic. Roberto Carlos Duran"},
            {"tipo": "PER_ESTUDIANTE", "valor": "Gabriel Alarcón Flores"},
            {"tipo": "MODULO", "valor": "Módulo 2 Gestión"},
            {"tipo": "NOTA", "valor": "92"},
            {"tipo": "PROGRAMA", "valor": "Diplomado en BI"}
        ]
    },
    {
        "archivo": "layout1_cabeceras_desconocidas.xlsx",
        "hoja": "PLANILLA_INEDITA",
        "fila_idx": 3,
        "texto": "Ing. Marcelo Claure | Valeria Gutiérrez Paz | Módulo 3 Big Data | 74 | Maestría en Data Science",
        "spans": [
            {"tipo": "PER_DOCENTE", "valor": "Ing. Marcelo Claure"},
            {"tipo": "PER_ESTUDIANTE", "valor": "Valeria Gutiérrez Paz"},
            {"tipo": "MODULO", "valor": "Módulo 3 Big Data"},
            {"tipo": "NOTA", "valor": "74"},
            {"tipo": "PROGRAMA", "valor": "Maestría en Data Science"}
        ]
    },
    {
        "archivo": "layout1_cabeceras_desconocidas.xlsx",
        "hoja": "PLANILLA_INEDITA",
        "fila_idx": 4,
        "texto": "Dra. Carmen Rosa Morales | Fernando Torrico Roca | Módulo 4 Auditoría | 81 | Especialidad Tributaria",
        "spans": [
            {"tipo": "PER_DOCENTE", "valor": "Dra. Carmen Rosa Morales"},
            {"tipo": "PER_ESTUDIANTE", "valor": "Fernando Torrico Roca"},
            {"tipo": "MODULO", "valor": "Módulo 4 Auditoría"},
            {"tipo": "NOTA", "valor": "81"},
            {"tipo": "PROGRAMA", "valor": "Especialidad Tributaria"}
        ]
    },
    {
        "archivo": "layout1_cabeceras_desconocidas.xlsx",
        "hoja": "PLANILLA_INEDITA",
        "fila_idx": 5,
        "texto": "Prof. Gonzalo Sanchez | Claudia Méndez Vaca | Módulo 1 Fundamentos | 65 | Diplomado Educación",
        "spans": [
            {"tipo": "PER_DOCENTE", "valor": "Prof. Gonzalo Sanchez"},
            {"tipo": "PER_ESTUDIANTE", "valor": "Claudia Méndez Vaca"},
            {"tipo": "MODULO", "valor": "Módulo 1 Fundamentos"},
            {"tipo": "NOTA", "valor": "65"},
            {"tipo": "PROGRAMA", "valor": "Diplomado Educación"}
        ]
    },

    # --- Layout 2: Columnas invertidas + ruido ---
    {
        "archivo": "layout2_columnas_invertidas_ruido.xlsx",
        "hoja": "REGISTRO_COLUMNAS_INVERTIDAS",
        "fila_idx": 1,
        "texto": "95 | 70123456 | 2025-03-15 | Módulo 1 Big Data | Lic. Roberto Carlos Duran | Sin mora | Patricia Daza Arteaga",
        "spans": [
            {"tipo": "NOTA", "valor": "95"},
            {"tipo": "FECHA", "valor": "2025-03-15"},
            {"tipo": "MODULO", "valor": "Módulo 1 Big Data"},
            {"tipo": "PER_DOCENTE", "valor": "Lic. Roberto Carlos Duran"},
            {"tipo": "PER_ESTUDIANTE", "valor": "Patricia Daza Arteaga"}
        ]
    },
    {
        "archivo": "layout2_columnas_invertidas_ruido.xlsx",
        "hoja": "REGISTRO_COLUMNAS_INVERTIDAS",
        "fila_idx": 2,
        "texto": "60 | 71234567 | 2025-03-16 | Módulo 2 Modelado | Ing. Marcelo Claure | Pendiente pago | Rodrigo Fernández Roca",
        "spans": [
            {"tipo": "NOTA", "valor": "60"},
            {"tipo": "FECHA", "valor": "2025-03-16"},
            {"tipo": "MODULO", "valor": "Módulo 2 Modelado"},
            {"tipo": "PER_DOCENTE", "valor": "Ing. Marcelo Claure"},
            {"tipo": "PER_ESTUDIANTE", "valor": "Rodrigo Fernández Roca"}
        ]
    },
    {
        "archivo": "layout2_columnas_invertidas_ruido.xlsx",
        "hoja": "REGISTRO_COLUMNAS_INVERTIDAS",
        "fila_idx": 3,
        "texto": "82 | 72345678 | 2025-03-17 | Módulo 3 ETL | Dra. Carmen Rosa Morales | Regular | Guillermo Justiniano",
        "spans": [
            {"tipo": "NOTA", "valor": "82"},
            {"tipo": "FECHA", "valor": "2025-03-17"},
            {"tipo": "MODULO", "valor": "Módulo 3 ETL"},
            {"tipo": "PER_DOCENTE", "valor": "Dra. Carmen Rosa Morales"},
            {"tipo": "PER_ESTUDIANTE", "valor": "Guillermo Justiniano"}
        ]
    },
    {
        "archivo": "layout2_columnas_invertidas_ruido.xlsx",
        "hoja": "REGISTRO_COLUMNAS_INVERTIDAS",
        "fila_idx": 4,
        "texto": "45 | 73456789 | 2025-03-18 | Módulo 4 Visualización | Dr. Alejandro Siles | Riesgo académico | Ana Claudia Torrico",
        "spans": [
            {"tipo": "NOTA", "valor": "45"},
            {"tipo": "FECHA", "valor": "2025-03-18"},
            {"tipo": "MODULO", "valor": "Módulo 4 Visualización"},
            {"tipo": "PER_DOCENTE", "valor": "Dr. Alejandro Siles"},
            {"tipo": "PER_ESTUDIANTE", "valor": "Ana Claudia Torrico"}
        ]
    },

    # --- Layout 3: Celdas combinadas ---
    {
        "archivo": "layout3_celdas_combinadas_merged.xlsx",
        "hoja": "ACTA_CON_MERGED_CELLS",
        "fila_idx": 0,
        "texto": "PROGRAMA DE POSGRADO: MAESTRÍA EN DATA SCIENCE - GESTIÓN 2026",
        "spans": [
            {"tipo": "PROGRAMA", "valor": "MAESTRÍA EN DATA SCIENCE"}
        ]
    },
    {
        "archivo": "layout3_celdas_combinadas_merged.xlsx",
        "hoja": "ACTA_CON_MERGED_CELLS",
        "fila_idx": 1,
        "texto": "DOCENTE ASIGNADO: ING. MARCELO CLAURE | MÓDULO 2 ARQUITECTURA ETL",
        "spans": [
            {"tipo": "PER_DOCENTE", "valor": "ING. MARCELO CLAURE"},
            {"tipo": "MODULO", "valor": "MÓDULO 2 ARQUITECTURA ETL"}
        ]
    },
    {
        "archivo": "layout3_celdas_combinadas_merged.xlsx",
        "hoja": "ACTA_CON_MERGED_CELLS",
        "fila_idx": 3,
        "texto": "1 | Javier Mendoza Salazar | 90 | Aprobado",
        "spans": [
            {"tipo": "PER_ESTUDIANTE", "valor": "Javier Mendoza Salazar"},
            {"tipo": "NOTA", "valor": "90"}
        ]
    },
    {
        "archivo": "layout3_celdas_combinadas_merged.xlsx",
        "hoja": "ACTA_CON_MERGED_CELLS",
        "fila_idx": 4,
        "texto": "2 | Maria Elena Ríos | 85 | Aprobado",
        "spans": [
            {"tipo": "PER_ESTUDIANTE", "valor": "Maria Elena Ríos"},
            {"tipo": "NOTA", "valor": "85"}
        ]
    },
    {
        "archivo": "layout3_celdas_combinadas_merged.xlsx",
        "hoja": "ACTA_CON_MERGED_CELLS",
        "fila_idx": 5,
        "texto": "3 | Sergio Alarcón Flores | 78 | Aprobado",
        "spans": [
            {"tipo": "PER_ESTUDIANTE", "valor": "Sergio Alarcón Flores"},
            {"tipo": "NOTA", "valor": "78"}
        ]
    },
    {
        "archivo": "layout3_celdas_combinadas_merged.xlsx",
        "hoja": "ACTA_CON_MERGED_CELLS",
        "fila_idx": 6,
        "texto": "4 | Valeria Gutiérrez Paz | 50 | Reprobado",
        "spans": [
            {"tipo": "PER_ESTUDIANTE", "valor": "Valeria Gutiérrez Paz"},
            {"tipo": "NOTA", "valor": "50"}
        ]
    },

    # --- Layout 4: Filas de totales y subtotales ---
    {
        "archivo": "layout4_filas_totales_subtotales.xlsx",
        "hoja": "PLANILLA_CON_TOTALES",
        "fila_idx": 1,
        "texto": "Carlos Mamani Quispe | Lic. Roberto Carlos Duran | Diplomado en BI | Módulo 1 | 85",
        "spans": [
            {"tipo": "PER_ESTUDIANTE", "valor": "Carlos Mamani Quispe"},
            {"tipo": "PER_DOCENTE", "valor": "Lic. Roberto Carlos Duran"},
            {"tipo": "PROGRAMA", "valor": "Diplomado en BI"},
            {"tipo": "MODULO", "valor": "Módulo 1"},
            {"tipo": "NOTA", "valor": "85"}
        ]
    },
    {
        "archivo": "layout4_filas_totales_subtotales.xlsx",
        "hoja": "PLANILLA_CON_TOTALES",
        "fila_idx": 2,
        "texto": "Ana Claudia Torrico | Lic. Roberto Carlos Duran | Diplomado en BI | Módulo 1 | 90",
        "spans": [
            {"tipo": "PER_ESTUDIANTE", "valor": "Ana Claudia Torrico"},
            {"tipo": "PER_DOCENTE", "valor": "Lic. Roberto Carlos Duran"},
            {"tipo": "PROGRAMA", "valor": "Diplomado en BI"},
            {"tipo": "MODULO", "valor": "Módulo 1"},
            {"tipo": "NOTA", "valor": "90"}
        ]
    },
    {
        "archivo": "layout4_filas_totales_subtotales.xlsx",
        "hoja": "PLANILLA_CON_TOTALES",
        "fila_idx": 4,
        "texto": "Guillermo Justiniano | Lic. Roberto Carlos Duran | Diplomado en BI | Módulo 1 | 72",
        "spans": [
            {"tipo": "PER_ESTUDIANTE", "valor": "Guillermo Justiniano"},
            {"tipo": "PER_DOCENTE", "valor": "Lic. Roberto Carlos Duran"},
            {"tipo": "PROGRAMA", "valor": "Diplomado en BI"},
            {"tipo": "MODULO", "valor": "Módulo 1"},
            {"tipo": "NOTA", "valor": "72"}
        ]
    },
    {
        "archivo": "layout4_filas_totales_subtotales.xlsx",
        "hoja": "PLANILLA_CON_TOTALES",
        "fila_idx": 5,
        "texto": "Patricia Daza Arteaga | Lic. Roberto Carlos Duran | Diplomado en BI | Módulo 1 | 98",
        "spans": [
            {"tipo": "PER_ESTUDIANTE", "valor": "Patricia Daza Arteaga"},
            {"tipo": "PER_DOCENTE", "valor": "Lic. Roberto Carlos Duran"},
            {"tipo": "PROGRAMA", "valor": "Diplomado en BI"},
            {"tipo": "MODULO", "valor": "Módulo 1"},
            {"tipo": "NOTA", "valor": "98"}
        ]
    },
    {
        "archivo": "layout4_filas_totales_subtotales.xlsx",
        "hoja": "PLANILLA_CON_TOTALES",
        "fila_idx": 8,
        "texto": "Firma y Sello del Director Académico: Lic. René Salinas",
        "spans": [
            {"tipo": "PER_DOCENTE", "valor": "Lic. René Salinas"}
        ]
    },

    # --- Layout 5: Multihoja anidada ---
    {
        "archivo": "layout5_multihoja_anidada.xlsx",
        "hoja": "ACTA_NOTAS_REAL",
        "fila_idx": 1,
        "texto": "Rodrigo Fernández Roca | Dra. Carmen Rosa Morales | Módulo 3 Gestión | Especialidad Tributaria | 89",
        "spans": [
            {"tipo": "PER_ESTUDIANTE", "valor": "Rodrigo Fernández Roca"},
            {"tipo": "PER_DOCENTE", "valor": "Dra. Carmen Rosa Morales"},
            {"tipo": "MODULO", "valor": "Módulo 3 Gestión"},
            {"tipo": "PROGRAMA", "valor": "Especialidad Tributaria"},
            {"tipo": "NOTA", "valor": "89"}
        ]
    },
    {
        "archivo": "layout5_multihoja_anidada.xlsx",
        "hoja": "ACTA_NOTAS_REAL",
        "fila_idx": 2,
        "texto": "Valeria Gutiérrez Paz | Dra. Carmen Rosa Morales | Módulo 3 Gestión | Especialidad Tributaria | 94",
        "spans": [
            {"tipo": "PER_ESTUDIANTE", "valor": "Valeria Gutiérrez Paz"},
            {"tipo": "PER_DOCENTE", "valor": "Dra. Carmen Rosa Morales"},
            {"tipo": "MODULO", "valor": "Módulo 3 Gestión"},
            {"tipo": "PROGRAMA", "valor": "Especialidad Tributaria"},
            {"tipo": "NOTA", "valor": "94"}
        ]
    },
    {
        "archivo": "layout5_multihoja_anidada.xlsx",
        "hoja": "ACTA_NOTAS_REAL",
        "fila_idx": 3,
        "texto": "Sergio Alarcón Flores | Dra. Carmen Rosa Morales | Módulo 3 Gestión | Especialidad Tributaria | 70",
        "spans": [
            {"tipo": "PER_ESTUDIANTE", "valor": "Sergio Alarcón Flores"},
            {"tipo": "PER_DOCENTE", "valor": "Dra. Carmen Rosa Morales"},
            {"tipo": "MODULO", "valor": "Módulo 3 Gestión"},
            {"tipo": "PROGRAMA", "valor": "Especialidad Tributaria"},
            {"tipo": "NOTA", "valor": "70"}
        ]
    },
    {
        "archivo": "layout5_multihoja_anidada.xlsx",
        "hoja": "INSCRIPCIONES_NUEVAS",
        "fila_idx": 1,
        "texto": "Javier Mendoza Salazar | Maestría en Data Science | CI-6192831",
        "spans": [
            {"tipo": "PER_ESTUDIANTE", "valor": "Javier Mendoza Salazar"},
            {"tipo": "PROGRAMA", "valor": "Maestría en Data Science"},
            {"tipo": "CI", "valor": "6192831"}
        ]
    },
    {
        "archivo": "layout5_multihoja_anidada.xlsx",
        "hoja": "INSCRIPCIONES_NUEVAS",
        "fila_idx": 2,
        "texto": "Maria Elena Ríos | Diplomado en BI | CI-4920192",
        "spans": [
            {"tipo": "PER_ESTUDIANTE", "valor": "Maria Elena Ríos"},
            {"tipo": "PROGRAMA", "valor": "Diplomado en BI"},
            {"tipo": "CI", "valor": "4920192"}
        ]
    }
]

total_ner_core = 0
total_regex = 0
lineas_procesadas = []

for item in datos_gold:
    tokens, tags = alinear_bio(item["texto"], item["spans"])
    for sp in item["spans"]:
        if sp["tipo"] in ("PER_ESTUDIANTE", "PER_DOCENTE", "MODULO", "PROGRAMA"):
            total_ner_core += 1
        else:
            total_regex += 1
    lineas_procesadas.append({
        "archivo": item["archivo"],
        "hoja": item["hoja"],
        "fila_idx": item["fila_idx"],
        "texto": item["texto"],
        "tokens": tokens,
        "tags": tags,
        "spans": item["spans"]
    })

gold_doc = {
    "metadata": {
        "etiquetador": "Auditor de Calidad / Tesista (Adzacam - Adriano Daza Arteaga)",
        "rol": "Ingeniero de Datos y Evaluador de Calidad GiraGroup BI",
        "fecha_etiquetado": "2026-11-06",
        "descripcion": "Gold standard etiquetado manualmente para los 5 layouts adversarios con estructuras anomalas.",
        "total_lineas_anotadas": len(lineas_procesadas),
        "total_entidades_ner_core": total_ner_core,
        "total_entidades_regex": total_regex,
        "total_entidades": total_ner_core + total_regex,
        "desglose_por_tipo": {
            "PER_ESTUDIANTE": sum(1 for d in datos_gold for s in d["spans"] if s["tipo"] == "PER_ESTUDIANTE"),
            "PER_DOCENTE": sum(1 for d in datos_gold for s in d["spans"] if s["tipo"] == "PER_DOCENTE"),
            "MODULO": sum(1 for d in datos_gold for s in d["spans"] if s["tipo"] == "MODULO"),
            "PROGRAMA": sum(1 for d in datos_gold for s in d["spans"] if s["tipo"] == "PROGRAMA"),
            "NOTA": sum(1 for d in datos_gold for s in d["spans"] if s["tipo"] == "NOTA"),
            "FECHA": sum(1 for d in datos_gold for s in d["spans"] if s["tipo"] == "FECHA"),
            "CI": sum(1 for d in datos_gold for s in d["spans"] if s["tipo"] == "CI")
        }
    },
    "ejemplos": lineas_procesadas
}

os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
with open(OUT_FILE, "w", encoding="utf-8") as f:
    json.dump(gold_doc, f, indent=2, ensure_ascii=False)

print(f"Gold JSON generado exitosamente en: {OUT_FILE}")
print(f"Total lineas anotadas: {len(lineas_procesadas)}")
print(f"Entidades NER Core: {total_ner_core} (PER_ESTUDIANTE: {gold_doc['metadata']['desglose_por_tipo']['PER_ESTUDIANTE']}, PER_DOCENTE: {gold_doc['metadata']['desglose_por_tipo']['PER_DOCENTE']}, MODULO: {gold_doc['metadata']['desglose_por_tipo']['MODULO']}, PROGRAMA: {gold_doc['metadata']['desglose_por_tipo']['PROGRAMA']})")
print(f"Entidades Regex (NOTA/FECHA/CI): {total_regex}")
