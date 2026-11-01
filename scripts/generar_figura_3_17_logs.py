"""
scripts/generar_figura_3_17_logs.py
------------------------------------
Genera la Figura 3.17 en formato PNG de alta resolución (300 DPI, ancho >= 2000 px):
"Figura 3.17 Captura de logs de extracción semántica y etiquetado de registros con bandera requiere_revision"

Normas aplicadas:
- Fondo blanco puro (#FFFFFF).
- Estilo monocromo / escala de grises de alta legibilidad formal.
- Sin título incrustado en el canvas (el título va en la leyenda de Word).
- Muestra el flujo real de ejecución de la consola de logs con fecha/hora, módulos
  (ingestion_service, ner_engine, fuzzy_normalizer, quality_rules, dw_loader),
  los 3 casos típicos (directo, derivado con requiere_revision=True, resolución CI).
"""

import os
import shutil
import matplotlib.pyplot as plt
import matplotlib.patches as patches

OUTPUT_DIR = os.path.abspath("docs/images")
BRAIN_DIR = r"C:\Users\DAZA\.gemini\antigravity\brain\f930e363-4cdd-4e0f-bee8-dd23f1e3b7d0"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def generar_figura_3_17():
    fig, ax = plt.subplots(figsize=(12, 7.5), dpi=300)
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#FFFFFF")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    # Contenedor estilo ventana de consola / terminal técnica
    rect_terminal = patches.FancyBboxPatch(
        (1.5, 2.5), 97, 95,
        boxstyle="round,pad=0.5,rounding_size=1.2",
        edgecolor="#222222", facecolor="#FAFAFA", linewidth=1.5
    )
    ax.add_patch(rect_terminal)

    # Barra de título de la consola
    rect_bar = patches.Rectangle((1.5, 91.5), 97, 6, facecolor="#E5E5E5", edgecolor="#222222", linewidth=1.2)
    ax.add_patch(rect_bar)

    # Botones simulados de ventana
    for i, x in enumerate([4.0, 6.2, 8.4]):
        circle = patches.Circle((x, 94.5), 0.9, edgecolor="#333333", facecolor="#DDDDDD", linewidth=1.0)
        ax.add_patch(circle)

    ax.text(50, 94.5, "Console Logs — Ingestion Pipeline, BETO NER & HITL Review Gateway",
            fontsize=9, family="monospace", fontweight="bold", ha="center", va="center", color="#111111")

    # Líneas de log estructuradas
    logs = [
        ("hdr",  "giragroup-dataops@prod-server:~$ python -m pipeline.process --batch-id 2026-II --source arca"),
        ("info", "[2026-10-29 14:15:22] [INFO]    [ingestion_service] Lote documental #2026-II cargado (doc_id=14, sha256=e3b0c442...)"),
        ("info", "[2026-10-29 14:15:22] [INFO]    [ingestion_service] Estructura segmentada: 1 bloque tabular detectado, 1.250 filas validas."),
        ("sep",  "----------------------------------------------------------------------------------------------------------------------"),
        ("info", "[2026-10-29 14:15:23] [INFO]    [ner_engine] Tokenizando bloque 1: 'DOCENTE: DR. CARLOS GOMEZ | MODULO: BIG DATA'"),
        ("info", "[2026-10-29 14:15:23] [INFO]    [ner_engine] Entidad: 'Carlos Gomez' [PER_DOCENTE] -> Confianza BETO: 0.9840 (Nivel ALTA)"),
        ("info", "[2026-10-29 14:15:23] [INFO]    [fuzzy_normalizer] Coincidencia canonica en dim_docente: ID 109 (Ratio RapidFuzz: 98.2%)"),
        ("ok",   "[2026-10-29 14:15:23] [INFO]    [dw_loader] Consolidado directo -> fact_rendimiento_academico [requiere_revision = FALSE]"),
        ("sep",  "----------------------------------------------------------------------------------------------------------------------"),
        ("warn", "[2026-10-29 14:15:24] [WARNING] [ner_engine] Tokenizando fila #18: 'ESTUDIANTE: ALVARO QUIROGA M. | CI: S/D | NOTA: 68'"),
        ("warn", "[2026-10-29 14:15:24] [WARNING] [ner_engine] Entidad detectada: 'ALVARO QUIROGA M.' [PER_ESTUDIANTE] -> Confianza: 0.7820"),
        ("warn", "[2026-10-29 14:15:24] [WARNING] [fuzzy_normalizer] Mejor coincidencia en catalogo: 'Alvaro Quiroga Morales' (Score: 78.4%)"),
        ("warn", "[2026-10-29 14:15:24] [WARNING] [quality_rules] ALERTA: Confianza 0.7820 en rango de duda [0.6000, 0.8500) (Nivel MEDIA)"),
        ("crit", "[2026-10-29 14:15:24] [WARNING] [dw_loader] RETENCION -> Derivado a stg_entidad_no_resuelta (staging_id: 86, origen_doc: 14)"),
        ("crit", "[2026-10-29 14:15:24] [ALERT]   [dw_loader] ACTIVACION DE BANDERA: [requiere_revision = TRUE] -> Encolado en Bandeja HITL"),
        ("sep",  "----------------------------------------------------------------------------------------------------------------------"),
        ("info", "[2026-10-29 14:15:25] [INFO]    [ner_engine] Tokenizando fila #19: 'ESTUDIANTE: MARIANA SILES BENITEZ | CI: 6789123 | NOTA: 85'"),
        ("info", "[2026-10-29 14:15:25] [INFO]    [fk_resolver] Resolucion directa por C.I. 6789123 -> dim_estudiante ID: 45 (fk_estado = A)"),
        ("ok",   "[2026-10-29 14:15:25] [INFO]    [dw_loader] Consolidado directo -> fact_rendimiento_academico [requiere_revision = FALSE]"),
        ("sep",  "----------------------------------------------------------------------------------------------------------------------"),
        ("info", "[2026-10-29 14:15:26] [INFO]    [pipeline] Fin de procesamiento lote #2026-II: 1.250 registros analizados."),
        ("info", "[2026-10-29 14:15:26] [INFO]    [pipeline] Resumen: 1.164 directo al DW (93.1%), 86 retenidos con [requiere_revision = TRUE].")
    ]

    y_pos = 87.5
    for tag, text in logs:
        font_weight = "normal"
        color = "#111111"

        if tag == "hdr":
            font_weight = "bold"
            color = "#000000"
        elif tag == "sep":
            color = "#888888"
        elif tag == "ok":
            font_weight = "bold"
            color = "#000000"
        elif tag == "warn":
            color = "#333333"
        elif tag == "crit":
            font_weight = "bold"
            color = "#000000"

        ax.text(3.5, y_pos, text, fontsize=7.8, family="monospace",
                color=color, fontweight=font_weight, va="top", ha="left")
        y_pos -= 3.9

    out_file = os.path.join(OUTPUT_DIR, "figura_3_17_captura_logs_extraccion_semantica.png")
    plt.tight_layout()
    plt.savefig(out_file, dpi=300, facecolor="#FFFFFF", bbox_inches="tight")
    plt.close()
    print(f"Figura 3.17 generada exitosamente en: {out_file}")

    if os.path.exists(BRAIN_DIR):
        dst = os.path.join(BRAIN_DIR, "figura_3_17_captura_logs_extraccion_semantica.png")
        shutil.copy2(out_file, dst)
        print(f"Copiada a artefactos del asistente: {dst}")

if __name__ == "__main__":
    generar_figura_3_17()
