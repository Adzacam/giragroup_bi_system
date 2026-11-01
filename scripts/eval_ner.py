import json
import re
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from seqeval.metrics import classification_report
from seqeval.scheme import IOB2
from sklearn.metrics import confusion_matrix

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from pipeline.semantic.ner_engine import BetoNEREngine
from pipeline.semantic.formatter import obtener_gazetteer

plt.rcParams.update({
    "font.family": "serif",
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
})

TOKEN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)


def tokenize_with_offsets(text: str):
    tokens = []
    for m in TOKEN_RE.finditer(text):
        tokens.append((m.group(0), m.start(), m.end()))
    return tokens


def spans_to_iob2(tokens_with_offsets, spans):
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


def strip_academic_title(name: str) -> str:
    return re.sub(
        r"^(?:Dr\.|Dra\.|Lic\.|Ing\.|Mg\.|MSc\.|PhD\.|Prof\.)\s+",
        "",
        str(name).strip(),
        flags=re.IGNORECASE,
    ).strip()


def build_test_conll(conll_path: Path):
    """
    Construye test.conll a partir del conjunto de prueba reservado en uploads/test/
    (muestra estratificada de las fuentes académicas, docentes, formularios, Moodle e inscripciones).
    """
    gaz = obtener_gazetteer()
    arca_notas = pd.read_excel("uploads/test/Base_Academica_ARCA_TEST.xlsx", sheet_name="ACTAS DE NOTAS")
    arca_mod = pd.read_excel("uploads/test/Base_Academica_ARCA_TEST.xlsx", sheet_name="MODULOS")
    eval_doc = pd.read_excel("uploads/test/BBDD_Evaluacion_Docente_GiraGroup_TEST.xlsx", sheet_name="TBL EVALUACION DOCENTE")
    exp_dip = pd.read_excel("uploads/test/Experiencia_Docente_TEST.xlsx", sheet_name="DIPLOMADOS DOCENTE")
    forms = pd.read_csv("uploads/test/Inscripciones_Google_Forms_TEST.csv")
    moodle = pd.read_csv("uploads/test/Reporte_Aula_Virtual_Moodle_TEST.csv")
    insc = pd.read_excel("uploads/test/TBL_INSCRITOS_TEST.xlsx", sheet_name="TBL_INSCRITOS")

    sentences_and_spans = []

    # 1. ACTAS DE NOTAS (50 registros)
    prog_list = list(arca_mod["NOMBRE DEL PROGRAMA"].dropna().unique())
    doc_list = list(arca_mod["DOCENTE"].dropna().unique())
    for idx, row in arca_notas.head(50).iterrows():
        nom = f"{row['NOMBRES']} {row['APELLIDO PATERNO']} {row['APELLIDO MATERNO']}".strip()
        prog = prog_list[idx % len(prog_list)]
        mod_num = (idx % 6) + 1
        mod_str = f"{mod_num}" if idx % 5 != 0 else f"Módulo {mod_num} Gestión"
        nota = int(row["MÓDULO 1"]) if pd.notna(row["MÓDULO 1"]) else 80
        doc_raw = str(doc_list[idx % len(doc_list)]).strip()
        # En 85% usamos nombre limpio, en 15% dejamos prefijo académico o estructura invertida
        doc = strip_academic_title(doc_raw) if idx % 7 != 0 else doc_raw

        if idx % 8 == 0:
            # Oración pasiva donde docente y estudiante están próximos sin marcador fuerte
            text = f"En el programa {prog}, {doc} registró al participante {nom} en el módulo {mod_str} con la nota {nota}."
        else:
            text = f"En el programa {prog}, el docente {doc} evaluó al estudiante {nom} en el módulo {mod_str} con la nota {nota}."

        spans = []
        for etype, val in [
            ("PROGRAMA", prog),
            ("PER_DOCENTE", doc),
            ("PER_ESTUDIANTE", nom),
            ("MODULO", mod_str),
        ]:
            pos_i = text.find(val)
            if pos_i != -1:
                spans.append({"tipo": etype, "start": pos_i, "end": pos_i + len(val)})
        sentences_and_spans.append((text, spans))

    # 2. MODULOS (50 registros)
    for idx, row in arca_mod.head(50).iterrows():
        prog = str(row["NOMBRE DEL PROGRAMA"]).strip()
        doc_raw = str(row["DOCENTE"]).strip()
        doc = strip_academic_title(doc_raw) if idx % 6 != 0 else doc_raw
        mod_val = str(row["MODULO N°"]).strip()
        mod_str = mod_val if idx % 6 != 0 else f"Taller {mod_val}"
        fec = str(row["FECHA INICIO"])[:10]

        if idx % 9 == 0:
            text = f"Asignación académica de {prog}: {doc} impartió el módulo {mod_str} en fecha {fec}."
        else:
            text = f"En el programa {prog}, el docente {doc} dictó el módulo {mod_str} en fecha {fec}."

        spans = []
        for etype, val in [
            ("PROGRAMA", prog),
            ("PER_DOCENTE", doc),
            ("MODULO", mod_str),
        ]:
            pos_i = text.find(val)
            if pos_i != -1:
                spans.append({"tipo": etype, "start": pos_i, "end": pos_i + len(val)})
        sentences_and_spans.append((text, spans))

    # 3. TBL EVALUACION DOCENTE (45 registros)
    for idx, row in eval_doc.head(45).iterrows():
        est = str(row["NOMBRE COMPLETO"]).strip()
        prog = str(row["PROGRAMA"]).strip()
        mod_val = str(row["MÓDULO"]).strip()
        doc_raw = str(doc_list[idx % len(doc_list)]).strip()
        doc = strip_academic_title(doc_raw) if idx % 7 != 0 else doc_raw
        fec = str(row["FECHA"]).strip()

        text = f"En la evaluación del programa {prog}, el estudiante {est} calificó al docente {doc} en el módulo {mod_val} en fecha {fec}."
        spans = []
        for etype, val in [
            ("PROGRAMA", prog),
            ("PER_ESTUDIANTE", est),
            ("PER_DOCENTE", doc),
            ("MODULO", mod_val),
        ]:
            pos_i = text.find(val)
            if pos_i != -1:
                spans.append({"tipo": etype, "start": pos_i, "end": pos_i + len(val)})
        sentences_and_spans.append((text, spans))

    # 4. EXPERIENCIA DOCENTE - DIPLOMADOS (35 registros)
    for idx, row in exp_dip.head(35).iterrows():
        est = str(row["NOMBRE COMPLETO DEL USUARIO"]).strip()
        prog_raw = str(row["PROGRAMA POS"]).split("/")[0].strip()
        mod_val = str(row["MÓDULO"]).strip()
        fec = str(row["FECHA"]).strip()

        text = f"En el programa {prog_raw}, el estudiante {est} completó el módulo {mod_val} en fecha {fec}."
        spans = []
        for etype, val in [
            ("PROGRAMA", prog_raw),
            ("PER_ESTUDIANTE", est),
            ("MODULO", mod_val),
        ]:
            pos_i = text.find(val)
            if pos_i != -1:
                spans.append({"tipo": etype, "start": pos_i, "end": pos_i + len(val)})
        sentences_and_spans.append((text, spans))

    # 5. GOOGLE FORMS INSCRIPCIONES & MOODLE & TBL_INSCRITOS (50 registros)
    for idx, row in forms.head(20).iterrows():
        est = str(row["Nombre Completo"]).strip()
        prog = str(row["Programa de Interés"]).strip()
        ci = str(row["Cédula de Identidad"]).replace("CI-", "").strip()
        text = f"El estudiante {est} con carnet CI {ci} se inscribió en el programa {prog}."
        spans = []
        for etype, val in [("PER_ESTUDIANTE", est), ("PROGRAMA", prog)]:
            pos_i = text.find(val)
            if pos_i != -1:
                spans.append({"tipo": etype, "start": pos_i, "end": pos_i + len(val)})
        sentences_and_spans.append((text, spans))

    for idx, row in moodle.head(15).iterrows():
        est = f"{row['First name']} {row['Surname']}".strip()
        course_parts = str(row["Course"]).split(" - ")
        prog = course_parts[-1].strip()
        nota = int(float(row["Tarea 1: Análisis de Caso (Real)"]))
        text = f"En el programa {prog}, el estudiante {est} aprobó el módulo 1 con la nota {nota}."
        spans = []
        for etype, val in [("PROGRAMA", prog), ("PER_ESTUDIANTE", est), ("MODULO", "1")]:
            pos_i = text.find(val) if etype != "MODULO" else text.find("módulo 1") + len("módulo ")
            if pos_i != -1:
                spans.append({"tipo": etype, "start": pos_i, "end": pos_i + len(val)})
        sentences_and_spans.append((text, spans))

    for idx, row in insc.head(15).iterrows():
        est = f"{row['NOMBRES']} {row['PATERNO']} {row['MATERNO']}".strip()
        prog = str(row["NOMBRE DEL PROGRAMA"]).strip()
        ci = str(row["CI"]).strip()
        text = f"En el programa {prog}, se registró al estudiante {est} con carnet CI {ci}."
        spans = []
        for etype, val in [("PROGRAMA", prog), ("PER_ESTUDIANTE", est)]:
            pos_i = text.find(val)
            if pos_i != -1:
                spans.append({"tipo": etype, "start": pos_i, "end": pos_i + len(val)})
        sentences_and_spans.append((text, spans))

    lines_out = []
    for text, spans in sentences_and_spans:
        toks = tokenize_with_offsets(text)
        tags = spans_to_iob2(toks, spans)
        for (tok, _, _), tag in zip(toks, tags):
            lines_out.append(f"{tok}\t{tag}")
        lines_out.append("")

    conll_path.write_text("\n".join(lines_out), encoding="utf-8")
    return sentences_and_spans


def load_conll(path: Path):
    sents, tags = [], []
    cur_t, cur_y = [], []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            if cur_t:
                sents.append(cur_t)
                tags.append(cur_y)
                cur_t, cur_y = [], []
        else:
            t, y = line.rsplit("\t", 1)
            cur_t.append(t)
            cur_y.append(y)
    if cur_t:
        sents.append(cur_t)
        tags.append(cur_y)
    return sents, tags


def reconstruct_text_and_offsets(tokens):
    parts = []
    offsets = []
    cur = 0
    for i, tok in enumerate(tokens):
        if i > 0 and not re.match(r"^[.,;:!?)]$", tok) and parts[-1] != "(":
            parts.append(" ")
            cur += 1
        start = cur
        parts.append(tok)
        cur += len(tok)
        offsets.append((tok, start, cur))
    return "".join(parts), offsets


def main():
    conll_path = Path("test.conll")
    build_test_conll(conll_path)
    X, Y_true = load_conll(conll_path)

    engine = BetoNEREngine()
    map_type = {
        "ESTUDIANTE": "PER_ESTUDIANTE",
        "DOCENTE": "PER_DOCENTE",
        "MODULO": "MODULO",
        "PROGRAMA": "PROGRAMA",
    }

    Y_pred = []
    for tokens in X:
        text, tok_offsets = reconstruct_text_and_offsets(tokens)
        res = engine.extraer_entidades(text)
        pred_spans = []
        for ent in res.entidades:
            t_mapped = map_type.get(ent.tipo)
            if t_mapped:
                pred_spans.append({
                    "tipo": t_mapped,
                    "start": ent.start_char,
                    "end": ent.end_char,
                })
        pred_tags = spans_to_iob2(tok_offsets, pred_spans)
        Y_pred.append(pred_tags)

    rep = classification_report(
        Y_true, Y_pred, mode="strict", scheme=IOB2, output_dict=True, digits=4
    )

    def make_serializable(obj):
        if isinstance(obj, dict):
            return {k: make_serializable(v) for k, v in obj.items()}
        if isinstance(obj, (np.integer, int)):
            return int(obj)
        if isinstance(obj, (np.floating, float)):
            return round(float(obj), 4)
        return obj

    rep_clean = make_serializable(rep)
    Path("metricas_ner.json").write_text(
        json.dumps(rep_clean, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("Reporte seqeval (strict, IOB2):")
    print(json.dumps(rep_clean, indent=2, ensure_ascii=False))

    # Gráfico 3.3: Desempeño de métricas por entidad (mismo JSON que Tabla 3.21)
    ents = ["PER_ESTUDIANTE", "PER_DOCENTE", "MODULO", "PROGRAMA"]
    y = np.arange(len(ents))
    fig, ax = plt.subplots(figsize=(7.5, 4.2), facecolor="white")
    for i, (m, lbl, h, c) in enumerate([
        ("precision", "Precisión", "", "#333333"),
        ("recall", "Recall", "//", "#888888"),
        ("f1-score", "F1-Score", "..", "#cccccc"),
    ]):
        vals = [rep[e][m] * 100 for e in ents]
        bars = ax.barh(
            y + (i - 1) * 0.25,
            vals,
            0.24,
            label=lbl,
            color=c,
            edgecolor="#111111",
            hatch=h,
        )
        for b, v in zip(bars, vals):
            ax.text(
                v + 0.6,
                b.get_y() + b.get_height() / 2.0,
                f"{v:.1f}%",
                va="center",
                ha="left",
                fontsize=8,
                color="#111111",
            )

    ax.set_yticks(y)
    ax.set_yticklabels(ents, fontsize=9.5)
    ax.set_xlim(0, 112)
    ax.set_xlabel("Porcentaje (%)", fontsize=10)
    ax.grid(axis="x", linestyle=":", color="#bbbbbb", alpha=0.8)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.13), ncol=3)
    fig.tight_layout()
    fig.savefig("grafico_3_3.png", dpi=300, facecolor="white")
    fig.savefig("docs/images/grafico_3_3_desempeno_metricas_por_entidad.png", dpi=300, facecolor="white")
    plt.close(fig)

    # Gráfico 3.1: Matriz de confusión por token (normalizada por fila)
    labels = ents + ["O"]
    yt = [t.split("-", 1)[-1] for s in Y_true for t in s]
    yp = [t.split("-", 1)[-1] for s in Y_pred for t in s]
    cm = confusion_matrix(yt, yp, labels=labels, normalize="true")

    fig, ax = plt.subplots(figsize=(6.4, 5.2), facecolor="white")
    im = ax.imshow(cm, cmap="Greys", vmin=0, vmax=1)
    for (i, j), v in np.ndenumerate(cm):
        ax.text(
            j,
            i,
            f"{v:.2f}",
            ha="center",
            va="center",
            color="white" if v > 0.5 else "black",
            fontsize=9.5,
            fontweight="bold" if i == j else "normal",
        )
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=25, ha="right", fontsize=9)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("Predicción del modelo", fontsize=10)
    ax.set_ylabel("Etiqueta real ( Conjunto de prueba )", fontsize=10)
    fig.tight_layout()
    fig.savefig("grafico_3_1.png", dpi=300, facecolor="white")
    fig.savefig("docs/images/grafico_3_1_matriz_confusion_beto.png", dpi=300, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    main()
