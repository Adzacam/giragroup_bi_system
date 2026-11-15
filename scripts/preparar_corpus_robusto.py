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
"""
import argparse
import hashlib
import json
import random
import re
import sys
import unicodedata
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


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--salida", required=True, help="Directorio de salida (obligatorio; no se escribe en data/ por defecto)")
    ap.add_argument("--uploads", default=str(BASE_DIR / "uploads"), help="Directorio uploads/ con los Excel fuente")
    ap.add_argument("--semilla", type=int, default=SEMILLA_POR_DEFECTO)
    ap.add_argument("--fraccion-dev", type=float, default=FRACCION_DEV_POR_DEFECTO,
                    help="Fracción de PERSONAS (no de líneas) reservada para dev")
    ap.add_argument("--n-total", type=int, default=N_TOTAL_POR_DEFECTO, help="Líneas train+dev (80/20)")
    args = ap.parse_args(argv)

    salida = Path(args.salida)
    if salida.resolve().is_relative_to((BASE_DIR / "pipeline").resolve()) or salida.resolve() == (BASE_DIR / "data").resolve():
        ap.error("--salida debe ser un directorio nuevo fuera de pipeline/ y data/")
    if any((salida / n).exists() for n in ARCHIVOS_CORPUS):
        ap.error("La salida ya contiene corpus; elija un directorio nuevo")
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
