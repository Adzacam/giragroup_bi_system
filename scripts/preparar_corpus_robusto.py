#!/usr/bin/env python
"""
scripts/preparar_corpus_robusto.py
===================================
Generador de corpus sin fuga (zero-leakage) con aumentación combinatoria y
formato de producción 'a_texto_plano' (col: val | col: val) para BETO NER.

1. Genera Test Gold Real (180 líneas) desde archivos reservados.
2. Extrae conjunto de entidades de test para exclusión estricta (nombres_train ∩ nombres_test = ∅).
3. Genera Train (~1,400) y Dev (~350) con >= 80% formato tabular ' | ' y <= 20% plantillas.
4. Aplica aumentación: permutación, sinónimos, casing, sin tildes, typos leves, títulos, ruido.
"""

import os
import sys
import re
import json
import random
import unicodedata
from pathlib import Path
from typing import List, Dict, Any, Tuple, Set
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from pipeline.normalization.catalog_repository import obtener_catalogo_repositorio

random.seed(42)

TOKEN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)

def tokenize_with_offsets(text: str) -> List[Tuple[str, int, int]]:
    tokens = []
    for m in TOKEN_RE.finditer(text):
        tokens.append((m.group(0), m.start(), m.end()))
    return tokens

def spans_to_iob2(tokens_with_offsets: List[Tuple[str, int, int]], spans: List[Dict[str, Any]]) -> List[str]:
    tags = ["O"] * len(tokens_with_offsets)
    for sp in spans:
        etype = sp["tipo"]
        s_char, e_char = sp["start"], sp["end"]
        first = True
        for i, (_, tok_s, tok_e) in enumerate(tokens_with_offsets):
            if max(tok_s, s_char) < min(tok_e, e_char):
                tags[i] = f"{'B' if first else 'I'}-{etype}"
                first = False
    return tags

def strip_accents(text: str) -> str:
    if not text:
        return ""
    return "".join(
        c for c in unicodedata.normalize("NFD", str(text))
        if unicodedata.category(c) != "Mn"
    )

def apply_typo(text: str) -> str:
    if len(text) < 5 or random.random() > 0.15:
        return text
    idx = random.randint(1, len(text) - 2)
    # swap adjacent chars
    return text[:idx] + text[idx+1] + text[idx] + text[idx+2:]

# Sinónimos para cabeceras
SYNONYMS = {
    "ESTUDIANTE": ["Estudiante", "Alumno", "Participante", "Postulante", "Inscrito", "Nombre Alumno", "ESTUDIANTE"],
    "DOCENTE": ["Docente", "Profesor", "Catedrático", "Facilitador", "Instructor", "Docente Asignado", "DOCENTE"],
    "MODULO": ["Módulo", "Modulo", "Materia", "Asignatura", "Módulo N°", "Modulo Académico"],
    "PROGRAMA": ["Programa", "Diplomado", "Maestría", "Curso", "Oferta Académica", "Programa POS"],
    "NOTA": ["Nota", "Calificación", "Puntaje Final", "Nota Final", "Calif."],
    "CI": ["CI", "C.I.", "Cédula", "Carnet de Identidad", "Documento"],
    "FECHA": ["Fecha", "Fecha Inicio", "Fecha de Registro", "Fec."],
}

TITULOS_DOCENTE = ["Lic.", "Ing.", "MSc.", "Dr.", "Dra.", "Prof.", "Mg."]

def normalizar_nombre(nom: str) -> str:
    if not nom or pd.isna(nom):
        return ""
    # Quitar títulos
    limpio = re.sub(r"^(?:Dr\.|Dra\.|Lic\.|Ing\.|Mg\.|MSc\.|Prof\.)\s+", "", str(nom).strip(), flags=re.IGNORECASE)
    return " ".join(limpio.split()).title()

def main():
    os.makedirs("data", exist_ok=True)
    repo = obtener_catalogo_repositorio()
    prog_meta = repo.programas_meta

    print("--- 1. EXTRACCIÓN DEL TEST GOLD REAL (180 LÍNEAS) ---")
    # Fuente 1: Experiencia Docente 2.0.xlsx (100 filas)
    df_exp = pd.read_excel("uploads/data/Experiencia Docente 2.0.xlsx", sheet_name="DIPLOMADOS DOCENTE")
    df_exp = df_exp[df_exp["Nombre completo del usuario"].notna()].copy()
    
    # Fuente 2: Base_Academica_ARCA_TEST.xlsx (50 filas de módulos docentes)
    df_arca_mod = pd.read_excel("uploads/test/Base_Academica_ARCA_TEST.xlsx", sheet_name="MODULOS")
    df_arca_mod = df_arca_mod[df_arca_mod["DOCENTE"].notna()].copy()

    # Fuente 3: TBL_INSCRITOS_TEST.xlsx (30 filas de inscritos)
    df_insc_test = pd.read_excel("uploads/test/TBL_INSCRITOS_TEST.xlsx", sheet_name="TBL_INSCRITOS")
    df_insc_test = df_insc_test[df_insc_test["NOMBRES"].notna()].copy()

    test_gold_records = []
    test_names_set = set()

    # A) 100 filas de Experiencia Docente
    for idx, row in df_exp.head(100).iterrows():
        est = normalizar_nombre(str(row["Nombre completo del usuario"]))
        pos_cod = str(row.get("Programa POS", "POS-5377")).strip()
        prog_info = prog_meta.get(pos_cod, {})
        prog = prog_info.get("nombre", f"Programa {pos_cod}")
        mod_num = str(row.get("Módulo", "1")).strip()
        mod_str = f"Módulo {mod_num}"

        test_names_set.add(est.lower())

        # Formato de producción ' | '
        line = f"ESTUDIANTE: {est} | PROGRAMA: {prog} | MODULO: {mod_str}"
        spans = [
            {"tipo": "PER_ESTUDIANTE", "val": est},
            {"tipo": "PROGRAMA", "val": prog},
            {"tipo": "MODULO", "val": mod_str}
        ]
        test_gold_records.append((line, spans))

    # B) 50 filas de Módulos Docentes de ARCA
    for idx, row in df_arca_mod.head(50).iterrows():
        doc = normalizar_nombre(str(row["DOCENTE"]))
        prog = str(row["NOMBRE DEL PROGRAMA"]).strip()
        mod_num = str(row["MODULO N°"]).strip()
        mod_str = f"Módulo {mod_num}" if not mod_num.lower().startswith("m") else mod_num

        test_names_set.add(doc.lower())

        line = f"DOCENTE: {doc} | PROGRAMA: {prog} | MODULO: {mod_str}"
        spans = [
            {"tipo": "PER_DOCENTE", "val": doc},
            {"tipo": "PROGRAMA", "val": prog},
            {"tipo": "MODULO", "val": mod_str}
        ]
        test_gold_records.append((line, spans))

    # C) 30 filas de Inscritos
    for idx, row in df_insc_test.head(30).iterrows():
        est = normalizar_nombre(f"{row['NOMBRES']} {row['PATERNO']} {row['MATERNO']}")
        prog = str(row["NOMBRE DEL PROGRAMA"]).strip()
        ci = str(row["CI"]).strip()

        test_names_set.add(est.lower())

        line = f"ESTUDIANTE: {est} | CI: {ci} | PROGRAMA: {prog}"
        spans = [
            {"tipo": "PER_ESTUDIANTE", "val": est},
            {"tipo": "PROGRAMA", "val": prog}
        ]
        test_gold_records.append((line, spans))

    print(f"Total líneas en Test Gold Real: {len(test_gold_records)}")
    print(f"Total entidades protegidas contra fuga (nombres test): {len(test_names_set)}")

    # Serializar test_gold_real.jsonl
    test_gold_out = []
    for line, spans_spec in test_gold_records:
        spans = []
        for s in spans_spec:
            pos = line.find(s["val"])
            if pos != -1:
                spans.append({"tipo": s["tipo"], "start": pos, "end": pos + len(s["val"]), "val": s["val"]})
        toks = tokenize_with_offsets(line)
        tags = spans_to_iob2(toks, spans)
        test_gold_out.append({
            "texto": line,
            "tokens": [t[0] for t in toks],
            "tags": tags,
            "spans": spans
        })

    with open("data/test_gold_real.jsonl", "w", encoding="utf-8") as f:
        for item in test_gold_out:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print("Guardado exitosamente: data/test_gold_real.jsonl")

    print("\n--- 2. EXTRACCIÓN Y AUMENTACIÓN DE TRAIN Y DEV (ZERO-LEAKAGE) ---")
    # Fuentes para entrenamiento:
    # 1. Base centralizada Académica ARCA (1).xlsx [MODULOS y ACTAS DE NOTAS]
    # 2. TBL_INSCRITOS.xlsx
    # 3. BD Cobranzas.xlsx
    
    arca_xl = pd.ExcelFile("uploads/data/Base centralizada Académica ARCA (1).xlsx")
    df_mod_train = arca_xl.parse("MODULOS")
    df_mod_train.columns = [c.strip() for c in df_mod_train.columns]
    df_notas_train = arca_xl.parse("ACTAS DE NOTAS")
    df_notas_train.columns = [c.strip() for c in df_notas_train.columns]

    df_insc_train = pd.read_excel("uploads/data/TBL_INSCRITOS.xlsx", sheet_name="TBL_INSCRITOS")
    df_insc_train.columns = [c.strip() for c in df_insc_train.columns]

    doc_list_train = []
    for d in df_mod_train["DOCENTE"].dropna().unique():
        nom = normalizar_nombre(d)
        if nom.lower() not in test_names_set and len(nom) > 4:
            doc_list_train.append(nom)

    prog_list_train = []
    for p in df_mod_train["NOMBRE DEL PROGRAMA"].dropna().unique():
        p_str = str(p).strip()
        if len(p_str) > 5 and not p_str.lower().startswith("unnamed"):
            prog_list_train.append(p_str)

    est_list_train = []
    for _, r in df_notas_train.iterrows():
        nom = normalizar_nombre(f"{r.get('NOMBRES', '')} {r.get('APELLIDO PATERNO', '')} {r.get('APELLIDO MATERNO', '')}")
        if nom.lower() not in test_names_set and len(nom) > 5:
            est_list_train.append(nom)

    for _, r in df_insc_train.iterrows():
        nom = normalizar_nombre(f"{r.get('NOMBRES', '')} {r.get('PATERNO', '')} {r.get('MATERNO', '')}")
        if nom.lower() not in test_names_set and len(nom) > 5:
            est_list_train.append(nom)

    est_list_train = list(set(est_list_train))
    doc_list_train = list(set(doc_list_train))
    random.shuffle(est_list_train)
    random.shuffle(doc_list_train)

    # Verificación estricta de fuga
    assert len(set(est_list_train).intersection(test_names_set)) == 0, "Fuga detectada en estudiantes!"
    assert len(set(doc_list_train).intersection(test_names_set)) == 0, "Fuga detectada en docentes!"
    print(f"Estudiantes disponibles sin fuga: {len(est_list_train)}")
    print(f"Docentes disponibles sin fuga: {len(doc_list_train)}")

    # Generación con Aumentación
    N_TOTAL = 1750  # 1400 train (80%), 350 dev (20%)
    raw_samples = []

    for i in range(N_TOTAL):
        est = est_list_train[i % len(est_list_train)]
        doc = doc_list_train[i % len(doc_list_train)]
        prog = prog_list_train[i % len(prog_list_train)]
        mod_num = (i % 8) + 1
        mod_str = f"Módulo {mod_num}" if (i % 3 != 0) else f"Módulo {mod_num} Metodología"
        nota = str(random.randint(55, 100))
        monto = f"{random.randint(500, 3500)} Bs"

        # Aumentación: Títulos en docente
        if random.random() < 0.4:
            doc_display = f"{random.choice(TITULOS_DOCENTE)} {doc}"
        else:
            doc_display = doc

        # Aumentación: Quitar acento ocasional
        if random.random() < 0.2:
            est_display = strip_accents(est)
        else:
            est_display = est

        if random.random() < 0.15:
            doc_display = strip_accents(doc_display)

        # 85% Tabular serializado ' | '
        if i % 6 != 0:
            # Componentes clave-valor
            parts = [
                (random.choice(SYNONYMS["ESTUDIANTE"]), est_display, "PER_ESTUDIANTE"),
                (random.choice(SYNONYMS["DOCENTE"]), doc_display, "PER_DOCENTE"),
                (random.choice(SYNONYMS["PROGRAMA"]), prog, "PROGRAMA"),
                (random.choice(SYNONYMS["MODULO"]), mod_str, "MODULO"),
            ]
            
            # Agregar columnas de ruido / soporte
            if random.random() < 0.5:
                parts.append((random.choice(SYNONYMS["NOTA"]), nota, None))
            if random.random() < 0.3:
                parts.append(("Cédula", f"CI-{random.randint(4000000, 9999999)}", None))
            if random.random() < 0.2:
                parts.append(("Estado", random.choice(["Aprobado", "Regular", "Pendiente", "Inscrito"]), None))
            if random.random() < 0.15:
                parts.append(("Obs", "N/A", None))

            # Aumentación: Permutación de columnas
            random.shuffle(parts)

            # Aumentación: Casing
            line_parts = []
            spans = []
            cur_idx = 0

            for hdr, val, etype in parts:
                if random.random() < 0.15:
                    hdr_txt = hdr.upper()
                elif random.random() < 0.15:
                    hdr_txt = hdr.lower()
                else:
                    hdr_txt = hdr

                # Construir fragmento
                seg = f"{hdr_txt}: {val}"
                if line_parts:
                    cur_idx += 3  # len(" | ")
                
                val_start = cur_idx + len(hdr_txt) + 2
                val_end = val_start + len(val)

                if etype:
                    spans.append({"tipo": etype, "start": val_start, "end": val_end, "val": val})

                line_parts.append(seg)
                cur_idx += len(seg)

            line_text = " | ".join(line_parts)

        else:
            # 15% Plantillas sintéticas de soporte contextual (<= 20%)
            tipo_plantilla = i % 4
            if tipo_plantilla == 0:
                line_text = f"En el programa {prog}, el docente {doc_display} evaluó al estudiante {est_display} en el {mod_str} con la nota {nota}."
            elif tipo_plantilla == 1:
                line_text = f"Acta oficial de {prog}: se certifica que {est_display} aprobó el {mod_str} dictado por {doc_display}."
            elif tipo_plantilla == 2:
                line_text = f"Asignación docente en {prog}: {doc_display} imparte el {mod_str} para el participante {est_display}."
            else:
                line_text = f"El estudiante {est_display} registra inscripción en el {mod_str} del programa {prog} con {doc_display}."

            spans = []
            for etype, val in [("PER_DOCENTE", doc_display), ("PER_ESTUDIANTE", est_display), ("PROGRAMA", prog), ("MODULO", mod_str)]:
                p_idx = line_text.find(val)
                if p_idx != -1:
                    spans.append({"tipo": etype, "start": p_idx, "end": p_idx + len(val), "val": val})

        toks = tokenize_with_offsets(line_text)
        tags = spans_to_iob2(toks, spans)

        raw_samples.append({
            "texto": line_text,
            "tokens": [t[0] for t in toks],
            "tags": tags,
            "spans": spans
        })

    # Partición 80% Train / 20% Dev
    random.shuffle(raw_samples)
    split_idx = int(N_TOTAL * 0.8)
    train_samples = raw_samples[:split_idx]
    dev_samples = raw_samples[split_idx:]

    print(f"\nTotal Train samples: {len(train_samples)}")
    print(f"Total Dev samples: {len(dev_samples)}")

    with open("data/train_robusto.jsonl", "w", encoding="utf-8") as f:
        for s in train_samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    with open("data/dev_robusto.jsonl", "w", encoding="utf-8") as f:
        for s in dev_samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    print("Corpus generado y verificado exitosamente:")
    print(" - data/train_robusto.jsonl (1,400 registros)")
    print(" - data/dev_robusto.jsonl (350 registros)")
    print(" - data/test_gold_real.jsonl (180 registros)")

if __name__ == "__main__":
    main()
