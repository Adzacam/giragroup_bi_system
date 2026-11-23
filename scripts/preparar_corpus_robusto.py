#!/usr/bin/env python
"""
scripts/preparar_corpus_robusto.py
===================================
Generador del corpus NER de BETO (train / dev / test gold) en formato de
producción 'a_texto_plano' (col: val | col: val). Corpus SINTÉTICO y programático:
los valores salen de los Excel reales de uploads/, los spans se derivan de la
construcción del texto (no hay anotación manual).

Garantías:
  * Determinismo: mismas entradas + misma semilla => mismos bytes (SHA-256 idéntico),
    independiente de PYTHONHASHSEED (no se itera ningún set sin ordenar). Aun así se
    recomienda ejecutarlo con PYTHONHASHSEED=0.
  * Partición por persona: ninguna persona normalizada (sin títulos, tildes ni
    mayúsculas) aparece a la vez en train y dev, ni en el test gold.
  * No pisa datos vigentes: --salida es obligatorio.

Uso:
    PYTHONHASHSEED=0 python scripts/preparar_corpus_robusto.py --salida <directorio>
    python scripts/preparar_corpus_robusto.py --salida output/cf/corpus_v2 --inventario-cf docs/mediciones/cf_l0_familias_residuales.csv
"""
import argparse
import csv
import hashlib
import json
import random
import re
import shutil
import sys
import unicodedata
from collections import Counter, defaultdict
from importlib.metadata import version
from itertools import combinations
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Set, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

SEMILLA_POR_DEFECTO = 42
N_TOTAL_POR_DEFECTO = 1750          # 80 % train (1400) + 20 % dev (350)
FRACCION_DEV_POR_DEFECTO = 0.2
ARCHIVOS_CORPUS = ("train_robusto.jsonl", "dev_robusto.jsonl", "test_gold_real.jsonl")

TOKEN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)
_TITULO_RE = re.compile(r"^(?:Dr\.|Dra\.|Lic\.|Ing\.|Mg\.|MSc\.|Prof\.)\s+", re.IGNORECASE)

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


# ── Utilidades de texto ─────────────────────────────────────────────────────────
def tokenize_with_offsets(text: str) -> List[Tuple[str, int, int]]:
    return [(m.group(0), m.start(), m.end()) for m in TOKEN_RE.finditer(text)]


def spans_to_iob2(tokens_with_offsets, spans) -> List[str]:
    tags = ["O"] * len(tokens_with_offsets)
    for sp in spans:
        etype, s_char, e_char = sp["tipo"], sp["start"], sp["end"]
        first = True
        for i, (_, tok_s, tok_e) in enumerate(tokens_with_offsets):
            if max(tok_s, s_char) < min(tok_e, e_char):
                tags[i] = f"{'B' if first else 'I'}-{etype}"
                first = False
    return tags


def strip_accents(text: str) -> str:
    if not text:
        return ""
    return "".join(c for c in unicodedata.normalize("NFD", str(text)) if unicodedata.category(c) != "Mn")


def normalizar_nombre(nom) -> str:
    if nom is None or (isinstance(nom, float) and nom != nom):
        return ""
    limpio = _TITULO_RE.sub("", str(nom).strip())
    return " ".join(limpio.split()).title()


def clave_persona(nombre: str) -> str:
    """Clave de identidad de una persona: sin título, sin tildes, minúsculas, espacios colapsados."""
    return " ".join(strip_accents(_TITULO_RE.sub("", str(nombre).strip())).lower().split())


# ── Partición por persona ───────────────────────────────────────────────────────
def particionar_por_persona(
    personas: Iterable[str], fraccion_dev: float = FRACCION_DEV_POR_DEFECTO, semilla: int = SEMILLA_POR_DEFECTO
) -> Tuple[List[str], List[str]]:
    """Reparte personas (estudiantes y docentes juntos) en dos grupos disjuntos por clave normalizada.

    Devuelve (train, dev) como listas ordenadas de nombres. Determinista: ordena antes de barajar
    con un generador propio sembrado, sin depender de PYTHONHASHSEED ni del estado global de random.
    """
    if not 0 < fraccion_dev < 1:
        raise ValueError("fraccion_dev debe estar entre 0 y 1")
    por_clave: Dict[str, str] = {}
    for p in sorted(set(personas)):
        por_clave.setdefault(clave_persona(p), p)
    claves = sorted(por_clave)
    random.Random(semilla).shuffle(claves)
    n_dev = int(round(len(claves) * fraccion_dev))
    claves_dev = set(claves[:n_dev])
    train = sorted(por_clave[k] for k in claves if k not in claves_dev)
    dev = sorted(por_clave[k] for k in claves if k in claves_dev)
    return train, dev


def calcular_solapamiento(train: Sequence[dict], dev: Sequence[dict], test: Sequence[dict]) -> Dict[str, Any]:
    """Cuenta solapamiento de textos, personas (clave normalizada) y programas entre los tres conjuntos."""
    def personas(D):
        return {clave_persona(r["texto"][s["start"]:s["end"]])
                for r in D for s in r["spans"] if s["tipo"].startswith("PER_")}

    def programas(D):
        return {clave_persona(r["texto"][s["start"]:s["end"]]) for r in D for s in r["spans"] if s["tipo"] == "PROGRAMA"}

    textos = {n: {r["texto"] for r in D} for n, D in (("train", train), ("dev", dev), ("test", test))}
    per = {"train": personas(train), "dev": personas(dev), "test": personas(test)}
    prog = {"train": programas(train), "dev": programas(dev), "test": programas(test)}
    pares = (("train", "dev"), ("train", "test"), ("dev", "test"))
    return {
        "personas_unicas": {k: len(v) for k, v in per.items()},
        "personas_solapadas": {f"{a}_{b}": len(per[a] & per[b]) for a, b in pares},
        "textos_solapados": {f"{a}_{b}": len(textos[a] & textos[b]) for a, b in pares},
        "programas_solapados": {f"{a}_{b}": len(prog[a] & prog[b]) for a, b in pares},
        "lineas_dev_con_persona_en_train": sum(
            1 for r in dev if any(clave_persona(r["texto"][s["start"]:s["end"]]) in per["train"]
                                  for s in r["spans"] if s["tipo"].startswith("PER_"))),
    }


# ── Generación de muestras ──────────────────────────────────────────────────────
def generar_muestras(n: int, est_pool: Sequence[str], doc_pool: Sequence[str], prog_list: Sequence[str]) -> List[dict]:
    """Genera n muestras con aumentación a partir de los pools dados (usa el random global ya sembrado)."""
    raw = []
    for i in range(n):
        est = est_pool[i % len(est_pool)]
        doc = doc_pool[i % len(doc_pool)]
        prog = prog_list[i % len(prog_list)]
        mod_num = (i % 8) + 1
        mod_str = f"Módulo {mod_num}" if (i % 3 != 0) else f"Módulo {mod_num} Metodología"
        nota = str(random.randint(55, 100))
        random.randint(500, 3500)  # monto: consume aleatorio para conservar la secuencia histórica

        doc_display = f"{random.choice(TITULOS_DOCENTE)} {doc}" if random.random() < 0.4 else doc
        est_display = strip_accents(est) if random.random() < 0.2 else est
        if random.random() < 0.15:
            doc_display = strip_accents(doc_display)

        if i % 6 != 0:
            parts = [
                (random.choice(SYNONYMS["ESTUDIANTE"]), est_display, "PER_ESTUDIANTE"),
                (random.choice(SYNONYMS["DOCENTE"]), doc_display, "PER_DOCENTE"),
                (random.choice(SYNONYMS["PROGRAMA"]), prog, "PROGRAMA"),
                (random.choice(SYNONYMS["MODULO"]), mod_str, "MODULO"),
            ]
            if random.random() < 0.5:
                parts.append((random.choice(SYNONYMS["NOTA"]), nota, None))
            if random.random() < 0.3:
                parts.append(("Cédula", f"CI-{random.randint(4000000, 9999999)}", None))
            if random.random() < 0.2:
                parts.append(("Estado", random.choice(["Aprobado", "Regular", "Pendiente", "Inscrito"]), None))
            if random.random() < 0.15:
                parts.append(("Obs", "N/A", None))
            random.shuffle(parts)

            line_parts, spans, cur_idx = [], [], 0
            for hdr, val, etype in parts:
                if random.random() < 0.15:
                    hdr_txt = hdr.upper()
                elif random.random() < 0.15:
                    hdr_txt = hdr.lower()
                else:
                    hdr_txt = hdr
                seg = f"{hdr_txt}: {val}"
                if line_parts:
                    cur_idx += 3
                val_start = cur_idx + len(hdr_txt) + 2
                if etype:
                    spans.append({"tipo": etype, "start": val_start, "end": val_start + len(val), "val": val})
                line_parts.append(seg)
                cur_idx += len(seg)
            line_text = " | ".join(line_parts)
        else:
            t = i % 4
            if t == 0:
                line_text = f"En el programa {prog}, el docente {doc_display} evaluó al estudiante {est_display} en el {mod_str} con la nota {nota}."
            elif t == 1:
                line_text = f"Acta oficial de {prog}: se certifica que {est_display} aprobó el {mod_str} dictado por {doc_display}."
            elif t == 2:
                line_text = f"Asignación docente en {prog}: {doc_display} imparte el {mod_str} para el participante {est_display}."
            else:
                line_text = f"El estudiante {est_display} registra inscripción en el {mod_str} del programa {prog} con {doc_display}."
            spans = []
            for etype, val in [("PER_DOCENTE", doc_display), ("PER_ESTUDIANTE", est_display), ("PROGRAMA", prog), ("MODULO", mod_str)]:
                p_idx = line_text.find(val)
                if p_idx != -1:
                    spans.append({"tipo": etype, "start": p_idx, "end": p_idx + len(val), "val": val})

        toks = tokenize_with_offsets(line_text)
        raw.append({"texto": line_text, "tokens": [t[0] for t in toks],
                    "tags": spans_to_iob2(toks, spans), "spans": spans})
    return raw


# ── Entrada/Salida ──────────────────────────────────────────────────────────────
def sha256_archivo(ruta: Path) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def escribir_jsonl(ruta: Path, items: Iterable[dict]) -> None:
    with open(ruta, "w", encoding="utf-8", newline="\n") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")


def leer_jsonl(ruta: Path) -> List[dict]:
    with open(ruta, "r", encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def construir_gold(uploads: Path, prog_meta: dict) -> Tuple[List[dict], Set[str]]:
    """Test gold real (180 líneas) desde los archivos reservados. Devuelve (registros, claves de persona)."""
    import pandas as pd
    df_exp = pd.read_excel(uploads / "data" / "Experiencia Docente 2.0.xlsx", sheet_name="DIPLOMADOS DOCENTE")
    df_exp = df_exp[df_exp["Nombre completo del usuario"].notna()].copy()
    df_arca = pd.read_excel(uploads / "test" / "Base_Academica_ARCA_TEST.xlsx", sheet_name="MODULOS")
    df_arca = df_arca[df_arca["DOCENTE"].notna()].copy()
    df_insc = pd.read_excel(uploads / "test" / "TBL_INSCRITOS_TEST.xlsx", sheet_name="TBL_INSCRITOS")
    df_insc = df_insc[df_insc["NOMBRES"].notna()].copy()

    registros: List[Tuple[str, List[dict]]] = []
    claves: Set[str] = set()

    for _, row in df_exp.head(100).iterrows():
        est = normalizar_nombre(row["Nombre completo del usuario"])
        pos_cod = str(row.get("Programa POS", "POS-5377")).strip()
        prog = prog_meta.get(pos_cod, {}).get("nombre", f"Programa {pos_cod}")
        mod_str = f"Módulo {str(row.get('Módulo', '1')).strip()}"
        claves.add(clave_persona(est))
        registros.append((f"ESTUDIANTE: {est} | PROGRAMA: {prog} | MODULO: {mod_str}",
                          [{"tipo": "PER_ESTUDIANTE", "val": est}, {"tipo": "PROGRAMA", "val": prog}, {"tipo": "MODULO", "val": mod_str}]))
    for _, row in df_arca.head(50).iterrows():
        doc = normalizar_nombre(row["DOCENTE"])
        prog = str(row["NOMBRE DEL PROGRAMA"]).strip()
        mod_num = str(row["MODULO N°"]).strip()
        mod_str = f"Módulo {mod_num}" if not mod_num.lower().startswith("m") else mod_num
        claves.add(clave_persona(doc))
        registros.append((f"DOCENTE: {doc} | PROGRAMA: {prog} | MODULO: {mod_str}",
                          [{"tipo": "PER_DOCENTE", "val": doc}, {"tipo": "PROGRAMA", "val": prog}, {"tipo": "MODULO", "val": mod_str}]))
    for _, row in df_insc.head(30).iterrows():
        est = normalizar_nombre(f"{row['NOMBRES']} {row['PATERNO']} {row['MATERNO']}")
        prog = str(row["NOMBRE DEL PROGRAMA"]).strip()
        claves.add(clave_persona(est))
        registros.append((f"ESTUDIANTE: {est} | CI: {str(row['CI']).strip()} | PROGRAMA: {prog}",
                          [{"tipo": "PER_ESTUDIANTE", "val": est}, {"tipo": "PROGRAMA", "val": prog}]))

    out = []
    for line, spec in registros:
        spans = []
        for s in spec:
            pos = line.find(s["val"])
            if pos != -1:
                spans.append({"tipo": s["tipo"], "start": pos, "end": pos + len(s["val"]), "val": s["val"]})
        toks = tokenize_with_offsets(line)
        out.append({"texto": line, "tokens": [t[0] for t in toks], "tags": spans_to_iob2(toks, spans), "spans": spans})
    return out, claves


def construir_personas_entrenamiento(uploads: Path, claves_test: Set[str]) -> Tuple[List[str], List[str], List[str]]:
    """Listas ORDENADAS de estudiantes, docentes y programas disponibles (sin los del test)."""
    import pandas as pd
    arca = pd.ExcelFile(uploads / "data" / "Base centralizada Académica ARCA (1).xlsx")
    df_mod = arca.parse("MODULOS")
    df_mod.columns = [c.strip() for c in df_mod.columns]
    df_notas = arca.parse("ACTAS DE NOTAS")
    df_notas.columns = [c.strip() for c in df_notas.columns]
    df_insc = pd.read_excel(uploads / "data" / "TBL_INSCRITOS.xlsx", sheet_name="TBL_INSCRITOS")
    df_insc.columns = [c.strip() for c in df_insc.columns]

    docs = {normalizar_nombre(d) for d in df_mod["DOCENTE"].dropna().unique()}
    docs = {n for n in docs if len(n) > 4 and clave_persona(n) not in claves_test}

    progs: List[str] = []
    for p in df_mod["NOMBRE DEL PROGRAMA"].dropna().unique():
        p_str = str(p).strip()
        if len(p_str) > 5 and not p_str.lower().startswith("unnamed") and p_str not in progs:
            progs.append(p_str)

    ests: Set[str] = set()
    for _, r in df_notas.iterrows():
        ests.add(normalizar_nombre(f"{r.get('NOMBRES', '')} {r.get('APELLIDO PATERNO', '')} {r.get('APELLIDO MATERNO', '')}"))
    for _, r in df_insc.iterrows():
        ests.add(normalizar_nombre(f"{r.get('NOMBRES', '')} {r.get('PATERNO', '')} {r.get('MATERNO', '')}"))
    ests = {n for n in ests if len(n) > 5 and clave_persona(n) not in claves_test}
    return sorted(ests), sorted(docs), progs


TIPOS_CF = ("PER_ESTUDIANTE", "PER_DOCENTE", "MODULO", "PROGRAMA")
ETIQUETAS_CF = ["O", *(f"{p}-{t}" for t in TIPOS_CF for p in ("B", "I"))]
MODELO_CF = "dccuchile/bert-base-spanish-wwm-cased"
MAX_TOKENS_CF = 128
SEMILLA_RECHAZO = BASE_DIR / "db/seeds/seed_catalogos_config.sql"
TEMA_EMPRESARIAL = re.compile(
    r"\b(?:empres\w*|negocios?|finanzas?|financier\w*|contab\w*|tribut\w*|"
    r"auditor\w*|marketing|mercad\w*|comercial\w*|proyectos?|emprend\w*|"
    r"logistic\w*|credit\w*|gerencia\w*|administracion)\b"
)
TITULOS_CF = re.compile(r"^(?:(?:dr|dra|lic|ing|m\s*sc|prof|mg|abog|arq|phd)\s*\.\s*)+", re.I)


def normalizar_cf(texto: str) -> str:
    return " ".join(re.findall(r"\w+", strip_accents(texto).casefold()))


def clave_persona_cf(nombre: str) -> str:
    """Agrupa variantes de títulos, tildes, puntuación y orden de nombres/apellidos."""
    return " ".join(sorted(normalizar_cf(TITULOS_CF.sub("", nombre)).split()))


def identidades_cf(registros) -> Set[str]:
    return {
        clave_persona_cf(r["texto"][s["start"]:s["end"]])
        for r in registros for s in r["spans"] if s["tipo"] in TIPOS_CF[:2]
    } - {""}


def registro_cf(*partes) -> dict:
    texto, spans = "", []
    for valor, tipo in partes:
        if tipo:
            spans.append({"tipo": tipo, "start": len(texto), "end": len(texto) + len(valor), "val": valor})
        texto += valor
    tokens = tokenize_with_offsets(texto)
    return {"texto": texto, "tokens": [t[0] for t in tokens], "tags": spans_to_iob2(tokens, spans), "spans": spans}


def reglas_rechazo_cf():
    patron = r"\('MODULO_RECHAZO',\s*'([^']+)',\s*'((?:[^']|'')*)',\s*'MODULO',"
    reglas = defaultdict(list)
    for subtipo, valor in re.findall(patron, SEMILLA_RECHAZO.read_text(encoding="utf-8")):
        reglas[subtipo].append(valor.replace("''", "'"))
    if set(reglas) != {"CENTINELA", "PREFIJO_TITULO", "PROFESION_OCUPACION"}:
        raise ValueError("La seed MODULO_RECHAZO no contiene los tres subtipos")
    return reglas


def muestras_institucionales_cf(inventario: Path, reglas, semilla: int):
    from backend.services.modulo_validador import validar_nombre_modulo

    with inventario.open(encoding="utf-8-sig", newline="") as archivo:
        filas = list(csv.DictReader(archivo))
    ofertas = {f["codigo"]: f for f in filas if f["tipo"] == "cat_programa"}
    datos = defaultdict(list)
    rng = random.Random(semilla)

    for f in filas:
        codigo = f["codigo"]
        oferta = ofertas.get(codigo)
        if not oferta or not re.fullmatch(r"POS-\d+", codigo):
            continue
        familia = normalizar_cf(oferta["detalle"].split(";", 1)[0].removeprefix("familia_heuristica="))
        programa = " ".join(oferta["texto"].split())
        valor = " ".join(f["texto"].split())
        if not (familia and programa and valor):
            continue
        if f["tipo"] == "cat_modulo_maestro":
            nro = f["detalle"].removeprefix("nro_modulo=")
            if not nro.isdecimal() or normalizar_cf(valor) == normalizar_cf(programa):
                continue
            if not validar_nombre_modulo(valor, reglas_override=reglas)[0]:
                continue
            formatos = (
                (("ASIGNATURA › ", None), (valor, "MODULO"), (f"  ||  {codigo} / ", None), (programa, "PROGRAMA")),
                ((programa, "PROGRAMA"), (f"  •  {codigo}\nMódulo n.º {nro}: ", None), (valor, "MODULO")),
                ((valor, "MODULO"), (f"\t{codigo}-M{nro}\t", None), (programa, "PROGRAMA")),
                (("Oferta académica = ", None), (programa, "PROGRAMA"), (" | Unnamed: 7 | Materia = ", None), (valor, "MODULO")),
            )
            clase = "modulo_empresarial" if TEMA_EMPRESARIAL.search(f"{familia} {normalizar_cf(valor)}") else "modulo_otro"
        elif f["tipo"] == "dim_modulo" and f["categoria"] == "titulo_oferta_marcado":
            formatos = (
                (("NOMBRE DEL PROGRAMA\n", None), (valor, "PROGRAMA"), ("\nAsignatura pendiente", None)),
                ((f"{codigo} :: ", None), (valor, "PROGRAMA"), (" | Tipo de registro = oferta", None)),
            )
            clase = "oferta_con_marcador"
        else:
            continue
        datos[familia].append((clase, registro_cf(*rng.choice(formatos))))

    familias = sorted(datos)
    rng.shuffle(familias)
    corte = round(len(familias) * 0.8)
    grupos = (familias[:corte], familias[corte:])
    limites = [
        {"modulo_empresarial": 160, "modulo_otro": 80, "oferta_con_marcador": 80},
        {"modulo_empresarial": 40, "modulo_otro": 20, "oferta_con_marcador": 20},
    ]
    negativos = [
        (subtipo, f"{valor.rstrip()} por confirmar" if subtipo == "PREFIJO_TITULO" else valor)
        for subtipo, valores in sorted(reglas.items()) for valor in valores
    ]
    rng.shuffle(negativos)
    corte_negativos = round(len(negativos) * 0.8)
    muestras = []
    for grupo, topes, rechazos in zip(grupos, limites, (negativos[:corte_negativos], negativos[corte_negativos:])):
        por_clase = defaultdict(dict)
        for familia in grupo:
            for clase, fila in datos[familia]:
                por_clase[clase].setdefault(normalizar_cf(fila["texto"]), fila)
        subconjunto = []
        for clase, tope in topes.items():
            candidatos = list(por_clase[clase].values())
            rng.shuffle(candidatos)
            subconjunto.extend((clase, fila) for fila in candidatos[:tope])
        for subtipo, valor in rechazos:
            if validar_nombre_modulo(valor, reglas_override=reglas)[0]:
                raise ValueError(f"Ejemplo MODULO_RECHAZO aceptado por el validador ({subtipo})")
            texto = rng.choice(("MATERIA: {} | Registro incompleto", "Estado: Inscrito \t Módulo = {}",
                                "Asignatura registrada › {}\nActa en revisión")).format(valor)
            subconjunto.append((f"negativo_{subtipo}", registro_cf((texto, None))))
        muestras.append(subconjunto)
    return muestras


def verificar_cf(registros, tokenizer, nombre):
    """Mide la entrada real del entrenador sin padding ni truncamiento."""
    longitudes = []
    for inicio in range(0, len(registros), 128):
        lote = registros[inicio:inicio + 128]
        codificados = tokenizer([r["texto"] for r in lote], truncation=False, return_offsets_mapping=True)
        for r, ids, offsets in zip(lote, codificados["input_ids"], codificados["offset_mapping"], strict=True):
            anterior = "O"
            for tag in r["tags"]:
                if tag not in ETIQUETAS_CF or (tag.startswith("I-") and anterior[2:] != tag[2:]):
                    raise ValueError(f"Etiqueta IOB2 inválida en {nombre}")
                anterior = tag
            tokens = tokenize_with_offsets(r["texto"])
            if r["tokens"] != [t[0] for t in tokens] or r["tags"] != spans_to_iob2(tokens, r["spans"]):
                raise ValueError(f"Tokens, etiquetas y spans incoherentes en {nombre}")
            fin_anterior = 0
            for s in sorted(r["spans"], key=lambda s: s["start"]):
                inicio_span, fin_span = s["start"], s["end"]
                if not fin_anterior <= inicio_span < fin_span <= len(r["texto"]):
                    raise ValueError(f"Offsets inválidos o solapados en {nombre}")
                if not any(a == inicio_span and a < b <= fin_span for a, b in offsets):
                    raise ValueError(f"Span sin etiqueta B alineada al tokenizer BETO en {nombre}")
                fin_anterior = fin_span
            longitudes.append(len(ids))
    return longitudes


def preparar_cf(args, salida: Path) -> dict:
    from transformers import AutoTokenizer

    from scripts.beto_metricas import load_conll
    from scripts.f1_fuga_evaluacion import extraer_personas_iob2

    inventario = Path(args.inventario_cf)
    uploads = Path(args.uploads)
    gold_path = BASE_DIR / "data/test_gold_real.jsonl"
    layouts_path = uploads / "test/layouts_adversarios/gold_layouts_adversarios.json"
    conll_path = BASE_DIR / "data/ner/test.conll"
    gold = leer_jsonl(gold_path)
    layouts = json.loads(layouts_path.read_text(encoding="utf-8"))["ejemplos"]
    xs, ys = load_conll(conll_path)
    personas = {
        "test_gold_real": identidades_cf(gold),
        "layouts_5": {clave_persona_cf(s["valor"]) for r in layouts
                      for s in r["spans"] if s["tipo"] in TIPOS_CF[:2]} - {""},
        "test_conll": {clave_persona_cf(p) for x, y in zip(xs, ys, strict=True)
                       for p in extraer_personas_iob2(x, y)} - {""},
    }
    textos_exactos = {
        "test_gold_real": {r["texto"] for r in gold},
        "layouts_5": {r["texto"] for r in layouts},
        "test_conll": {" ".join(x) for x in xs},
    }
    textos = {k: {normalizar_cf(t) for t in ts} for k, ts in textos_exactos.items()}
    reservadas = set().union(*personas.values())
    ests, docs, progs = construir_personas_entrenamiento(uploads, set())
    estudiantes = {clave_persona_cf(p): p for p in ests}
    docentes = {clave_persona_cf(p): p for p in docs}
    ids = sorted((estudiantes.keys() | docentes.keys()) - reservadas - {""})
    rng = random.Random(args.semilla)
    rng.shuffle(ids)
    corte = round(len(ids) * args.fraccion_dev)
    n_train = int(args.n_total * (1 - args.fraccion_dev))
    reglas = reglas_rechazo_cf()
    aumentos = muestras_institucionales_cf(inventario, reglas, args.semilla)
    tokenizer = AutoTokenizer.from_pretrained(MODELO_CF, local_files_only=True)
    registros = {}
    descartes = {}
    clases = {}
    longitudes = {}
    random.seed(args.semilla)
    for nombre, grupo, n, aumento in zip(("train", "dev"), (ids[corte:], ids[:corte]),
                                        (n_train, args.n_total - n_train), aumentos):
        est_pool = [estudiantes[p] for p in grupo if p in estudiantes]
        doc_pool = [docentes[p] for p in grupo if p in docentes]
        if not (est_pool and doc_pool and n):
            raise ValueError(f"Partición o pool de personas vacío en {nombre}")
        base = generar_muestras(n, est_pool, doc_pool, progs)
        candidatos = [("base", r) for r in base] + aumento
        longitudes_candidatas = verificar_cf([r for _, r in candidatos], tokenizer, nombre)
        vistos = set().union(*textos.values())
        aceptados, descartados = [], Counter()
        for (clase, r), longitud in zip(candidatos, longitudes_candidatas, strict=True):
            normalizado = normalizar_cf(r["texto"])
            if longitud > MAX_TOKENS_CF:
                descartados["exceso_tokens"] += 1
            elif normalizado in vistos:
                descartados["texto_normalizado_repetido"] += 1
            else:
                vistos.add(normalizado)
                aceptados.append((clase, r, longitud))
        rng.shuffle(aceptados)
        registros[nombre] = [r for _, r, _ in aceptados]
        personas[nombre] = identidades_cf(registros[nombre])
        textos_exactos[nombre] = {r["texto"] for r in registros[nombre]}
        textos[nombre] = {normalizar_cf(t) for t in textos_exactos[nombre]}
        descartes[nombre] = dict(descartados)
        clases[nombre] = dict(Counter(clase for clase, _, _ in aceptados))
        longitudes[nombre] = max(l for _, _, l in aceptados)
    longitudes["test_gold_real"] = max(verificar_cf(gold, tokenizer, "test_gold_real"))
    longitudes["layouts_5"] = max(map(len, tokenizer([r["texto"] for r in layouts], truncation=False)["input_ids"]))
    longitudes["test_conll"] = max(map(len, tokenizer(xs, is_split_into_words=True, truncation=False)["input_ids"]))
    cruces = list(combinations(personas, 2))
    personas_solapadas = {f"{a}/{b}": len(personas[a] & personas[b]) for a, b in cruces}
    textos_solapados = {f"{a}/{b}": len(textos[a] & textos[b]) for a, b in cruces}
    exactos_solapados = {f"{a}/{b}": len(textos_exactos[a] & textos_exactos[b]) for a, b in cruces}
    for a, b in cruces:
        if {"train", "dev"} & {a, b} and (personas_solapadas[f"{a}/{b}"] or textos_solapados[f"{a}/{b}"]):
            raise ValueError(f"Solapamiento en {a}/{b}")
    if max(longitudes.values()) > MAX_TOKENS_CF:
        raise ValueError("Un conjunto reservado excede 128 tokens y requiere evaluación por ventanas")
    etiquetas_observadas = {tag for r in registros["train"] for tag in r["tags"]}
    if etiquetas_observadas != set(ETIQUETAS_CF):
        raise ValueError("El entrenamiento no contiene las nueve etiquetas IOB2")

    salida.mkdir(parents=True, exist_ok=True)
    escribir_jsonl(salida / ARCHIVOS_CORPUS[0], registros["train"])
    escribir_jsonl(salida / ARCHIVOS_CORPUS[1], registros["dev"])
    shutil.copyfile(gold_path, salida / ARCHIVOS_CORPUS[2])
    fuentes = (Path(__file__), inventario, SEMILLA_RECHAZO, gold_path, layouts_path, conll_path,
               uploads / "data/Base centralizada Académica ARCA (1).xlsx",
               uploads / "data/TBL_INSCRITOS.xlsx")
    return {
        "version": "CF-L2 corpus v2", "semilla": args.semilla, "fraccion_dev_personas": args.fraccion_dev,
        "tamanos": {**{k: len(v) for k, v in registros.items()}, "test": len(gold)},
        "sha256": {n: sha256_archivo(salida / n) for n in ARCHIVOS_CORPUS},
        "fuentes_sha256": {r.resolve().relative_to(BASE_DIR).as_posix() if r.resolve().is_relative_to(BASE_DIR)
                           else r.name: sha256_archivo(r) for r in fuentes},
        "metodo": "Base programática de Excel fuente particionada por identidad antes de generar muestras. "
                  "Las claves de identidad agrupan tildes, títulos, puntuación y permutaciones de nombres. "
                  "Aumento por familia heurística CF-L0, con prioridad temática empresarial y negativos de la "
                  "seed MODULO_RECHAZO etiquetados O.",
        "reglas_modulo_rechazo_seed": {k: len(v) for k, v in reglas.items()},
        "clases_de_muestras": clases, "descartes": descartes,
        "etiquetas_iob2": ETIQUETAS_CF,
        "tokenizador": {"modelo": MODELO_CF, "transformers": version("transformers"), "tokenizers": version("tokenizers"),
                         "sha256_json": hashlib.sha256(tokenizer.backend_tokenizer.to_str().encode()).hexdigest(),
                         "limite": MAX_TOKENS_CF, "maximos_sin_truncar_con_especiales": longitudes},
        "reservados": {"test_gold_real": len(gold), "layouts_5": len(layouts), "test_conll": len(xs)},
        "solapamiento": {"personas_unicas": {k: len(v) for k, v in personas.items()},
                         "personas_normalizadas_compartidas": personas_solapadas,
                         "textos_exactos_compartidos": exactos_solapados,
                         "textos_normalizados_compartidos": textos_solapados},
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--salida", required=True, help="Directorio de salida (obligatorio; no se escribe en data/ por defecto)")
    ap.add_argument("--uploads", default=str(BASE_DIR / "uploads"), help="Directorio uploads/ con los Excel fuente")
    ap.add_argument("--semilla", type=int, default=SEMILLA_POR_DEFECTO)
    ap.add_argument("--fraccion-dev", type=float, default=FRACCION_DEV_POR_DEFECTO,
                    help="Fracción de PERSONAS (no de líneas) reservada para dev")
    ap.add_argument("--n-total", type=int, default=N_TOTAL_POR_DEFECTO, help="Líneas train+dev (80/20)")
    ap.add_argument("--inventario-cf", help="CSV de CF-L0 para generar el corpus v2 institucional")
    args = ap.parse_args(argv)

    salida = Path(args.salida)
    if salida.resolve().is_relative_to((BASE_DIR / "pipeline").resolve()) or salida.resolve() == (BASE_DIR / "data").resolve():
        ap.error("--salida debe ser un directorio nuevo fuera de pipeline/ y data/")
    if any((salida / n).exists() for n in (*ARCHIVOS_CORPUS, "corpus_meta.json")):
        ap.error("La salida ya contiene corpus; elija un directorio nuevo")
    if args.inventario_cf:
        if not 0 < args.fraccion_dev < 1:
            ap.error("--fraccion-dev debe estar entre 0 y 1")
        meta = preparar_cf(args, salida)
        contenido = json.dumps(meta, indent=2, ensure_ascii=False) + "\n"
        (salida / "corpus_meta.json").write_text(contenido, encoding="utf-8")
        print(contenido, end="")
        return 0
    salida.mkdir(parents=True, exist_ok=True)
    uploads = Path(args.uploads)
    random.seed(args.semilla)

    from pipeline.normalization.catalog_repository import obtener_catalogo_repositorio
    prog_meta = obtener_catalogo_repositorio().programas_meta

    gold, claves_test = construir_gold(uploads, prog_meta)
    ests, docs, progs = construir_personas_entrenamiento(uploads, claves_test)

    # Partición por persona sobre estudiantes + docentes juntos (una persona = un solo conjunto).
    train_p, dev_p = particionar_por_persona(ests + docs, args.fraccion_dev, args.semilla)
    set_ests, set_docs = set(ests), set(docs)
    est_tr = [p for p in train_p if p in set_ests]; doc_tr = [p for p in train_p if p in set_docs]
    est_dv = [p for p in dev_p if p in set_ests];   doc_dv = [p for p in dev_p if p in set_docs]
    random.shuffle(est_tr); random.shuffle(doc_tr); random.shuffle(est_dv); random.shuffle(doc_dv)
    assert est_tr and doc_tr and est_dv and doc_dv, "Pools vacíos tras partición por persona"

    n_dev = args.n_total - int(args.n_total * 0.8)
    n_train = args.n_total - n_dev
    train = generar_muestras(n_train, est_tr, doc_tr, progs)
    dev = generar_muestras(n_dev, est_dv, doc_dv, progs)
    random.shuffle(train)
    random.shuffle(dev)

    sol = calcular_solapamiento(train, dev, gold)
    for par in ("train_dev", "train_test", "dev_test"):
        assert sol["personas_solapadas"][par] == 0, f"Personas solapadas en {par}: {sol['personas_solapadas'][par]}"

    escribir_jsonl(salida / "train_robusto.jsonl", train)
    escribir_jsonl(salida / "dev_robusto.jsonl", dev)
    escribir_jsonl(salida / "test_gold_real.jsonl", gold)

    meta = {
        "semilla": args.semilla, "fraccion_dev_personas": args.fraccion_dev,
        "tamanos": {"train": len(train), "dev": len(dev), "test": len(gold)},
        "sha256": {n: sha256_archivo(salida / n) for n in ARCHIVOS_CORPUS},
        "solapamiento": sol,
    }
    with open(salida / "corpus_meta.json", "w", encoding="utf-8", newline="\n") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    print(json.dumps(meta, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
