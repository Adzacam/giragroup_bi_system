import matplotlib.pyplot as plt
import matplotlib.patches as patches

# Configurar fuente legible >= 11 pt
plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "figure.autolayout": False,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.dpi": 300
})

fig, ax = plt.subplots(figsize=(14, 8.5))
ax.set_xlim(0, 14)
ax.set_ylim(0, 8.5)
ax.axis("off")

# Header
title_box = patches.FancyBboxPatch((0.5, 7.5), 13.0, 0.8, boxstyle="round,pad=0.1", fc="#1e3a8a", ec="#1e3a8a")
ax.add_patch(title_box)
ax.text(7.0, 7.9, "Arquitectura Híbrida NER (BETO) + Normalización Léxica (RapidFuzz)", color="white", weight="bold", fontsize=15, ha="center", va="center")

# Columnas
cols = [
    {"title": "1. Fuentes y Preproceso", "x": 0.5, "w": 2.9, "fc": "#f8fafc", "ec": "#64748b", "tc": "#0f172a"},
    {"title": "2. BETO NER (Puerto 8006)", "x": 3.7, "w": 3.1, "fc": "#eff6ff", "ec": "#3b82f6", "tc": "#1e40af"},
    {"title": "3. Catálogos y RapidFuzz", "x": 7.1, "w": 3.1, "fc": "#faf5ff", "ec": "#a855f7", "tc": "#6b21a8"},
    {"title": "4. Calidad y Carga DW", "x": 10.5, "w": 3.0, "fc": "#f0fdf4", "ec": "#22c55e", "tc": "#15803d"}
]

for col in cols:
    box = patches.FancyBboxPatch((col["x"], 0.8), col["w"], 6.4, boxstyle="round,pad=0.1", fc=col["fc"], ec=col["ec"], lw=1.5)
    ax.add_patch(box)
    header = patches.FancyBboxPatch((col["x"], 6.7), col["w"], 0.5, boxstyle="round,pad=0.05", fc=col["ec"], ec=col["ec"])
    ax.add_patch(header)
    ax.text(col["x"] + col["w"]/2, 6.95, col["title"], color="white", weight="bold", fontsize=11.5, ha="center", va="center")

# Contenido Columna 1
c1_text = (
    "Fuentes Académicas:\n"
    "• Actas de Notas (ARCA)\n"
    "• Evaluaciones Docentes\n"
    "• Inscripciones Google Forms\n"
    "• Reportes Moodle\n\n"
    "Fuentes Financieras:\n"
    "• BD Cobranzas y Egresos\n"
    "• BD Techos Presupuestarios\n\n"
    "Preprocesamiento:\n"
    "• Canonización 'Apellidos, Nom'\n"
    "• Remoción prefijos académicos\n"
    "• Limpieza diacrítica NFKD\n"
    "• Tokenizer Fast WordPiece"
)
ax.text(0.7, 3.8, c1_text, fontsize=11, va="center", color="#1e293b", linespacing=1.35)

# Contenido Columna 2
c2_text = (
    "Checkpoint Fine-Tuned:\n"
    "• Base: bert-base-spanish-wwm\n"
    "• Ruta: pipeline/semantic/beto_local\n"
    "• model.safetensors (437 MB)\n"
    "• 9 Etiquetas BIO institucionales:\n"
    "  PER_EST, PER_DOC, MOD, PROG\n"
    "• Vector Contextual: 768d\n\n"
    "Fallback HuggingFace Hub:\n"
    "• mrm8488/...ner (CoNLL)\n\n"
    "Reglas Léxico-Sintácticas:\n"
    "• POS-#### (4000 a 7000)\n"
    "• Calificación 0-100 (unif. x10)\n"
    "• C.I. y Montos en Bs."
)
ax.text(3.9, 3.8, c2_text, fontsize=11, va="center", color="#1e293b", linespacing=1.35)

# Contenido Columna 3
c3_text = (
    "Catálogo Maestro (3NF):\n"
    "• catalog_db (PostgreSQL p. 5433)\n"
    "• Programas Posgrado, Docentes,\n"
    "  Módulos y Alumnos\n\n"
    "Umbrales RapidFuzz:\n"
    "• Scorer: token_sort_ratio\n"
    "• Similitud ≥ 95%: Bono +12 (+0.12)\n"
    "• Similitud [90, 95)%: Bono +6..+12\n"
    "• Similitud [85, 90)%: Bono +4 (+0.04)\n"
    "• Similitud < 80%: Flag Revisión\n\n"
    "Compuerta Inferencia:\n"
    "• Lectura Base Mínima: 70%"
)
ax.text(7.3, 3.8, c3_text, fontsize=11, va="center", color="#1e293b", linespacing=1.35)

# Contenido Columna 4
c4_text = (
    "Compuerta de Calidad:\n"
    "• Índice Final = Lectura + Bonos\n"
    "• Tope Máximo: 99% (0.99)\n\n"
    "Decisión de Ingesta:\n"
    "• Índice ≥ 85% (0.85):\n"
    "  -> Inserción directa en DW\n"
    "• Índice < 85%:\n"
    "  -> requiere_revision = True\n"
    "  -> Cuarentena / Inconsistencias\n\n"
    "Data Warehouse Constelación:\n"
    "• fact_rendimiento_academico\n"
    "• fact_transaccion_financiera\n"
    "• fact_evaluacion_docente"
)
ax.text(10.7, 3.8, c4_text, fontsize=11, va="center", color="#1e293b", linespacing=1.35)

# Flechas de conexión
arrow_style = dict(arrowstyle="-|>", lw=2, color="#334155", mutation_scale=15)
ax.annotate("", xy=(3.6, 4.2), xytext=(3.45, 4.2), arrowprops=arrow_style)
ax.annotate("", xy=(7.0, 4.2), xytext=(6.85, 4.2), arrowprops=arrow_style)
ax.annotate("", xy=(10.4, 4.2), xytext=(10.25, 4.2), arrowprops=arrow_style)

# Pie de figura
ax.text(0.5, 0.4, "Fuente: Elaboración propia a partir del código verificado en giragroup_bi_system (PyTorch, BETO, RapidFuzz, PostgreSQL)", fontsize=10, style="italic", color="#64748b")

plt.tight_layout()
plt.savefig("output/figura_arquitectura_ner_rapidfuzz.png", dpi=300, bbox_inches="tight")
print("PNG generado en output/figura_arquitectura_ner_rapidfuzz.png")
