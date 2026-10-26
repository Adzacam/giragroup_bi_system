"""
Script para generar las Figuras 3.9 y 3.12 en formato PNG de alta resolución (300 DPI)
con fondo blanco puro, estilo formal académico / tesis (sin colores estridentes, en escala de grises / formal).
"""

import os
import shutil
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# Configuración de estilo global para publicaciones académicas
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['font.size'] = 9.5
plt.rcParams['axes.edgecolor'] = '#1A1A1A'
plt.rcParams['figure.facecolor'] = 'white'

def generar_figura_3_9():
    fig, ax = plt.subplots(figsize=(10, 14), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 140)
    ax.axis('off')

    # Título superior formal
    ax.text(50, 136, "Diagrama de Actividad: Pipeline de Ingesta Documental y Transformación a Texto Plano", 
            ha='center', va='center', fontsize=12, fontweight='bold', color='#111111')
    ax.text(50, 133, "(Metodología de Ingesta Multifuente - Sprint 2)", 
            ha='center', va='center', fontsize=9.5, fontstyle='italic', color='#444444')

    # Círculo inicial
    circle_start = plt.Circle((50, 127), 2.2, color='#111111', ec='#111111')
    ax.add_patch(circle_start)

    steps = [
        (25, 115, 50, 7.5, "1. Carga de Archivo Fuente\n(.xlsx, .csv, Google Sheets / Forms, Moodle)", False),
        (25, 101, 50, 7.5, "2. Validación de Integridad y Hash SHA-256\n(Sanitización de nombres y control MIME)", False),
        (50, 89, 14, 8, "¿Formato y\nestructura\nválida?", True),
        (25, 71, 50, 7.5, "3. Detección de Islas de Datos y Celdas Combinadas\n(Algoritmo detectar_islas / detectar_bloques)", False),
        (25, 57, 50, 7.5, "4. Normalización de Cabecera Desplazada\n(Descarte de subtotales y filas informativas vacías)", False),
        (25, 43, 50, 7.5, "5. Transformación y Serialización a Texto Plano\n(Estructuración clave-valor: DOCENTE, ALUMNO, NOTAS)", False),
        (25, 29, 50, 7.5, "6. Registro en dim_origen_documental y Staging\n(Trazabilidad de metadatos, período y hash)", False),
        (25, 15, 50, 7.5, "7. Despacho al Pipeline Semántico PLN\n(Handoff a ner_engine.py para tokenización BETO)", False),
    ]

    ax.annotate('', xy=(50, 122.5), xytext=(50, 124.8), arrowprops=dict(arrowstyle="->", color='#111111', lw=1.5))

    for item in steps:
        if not item[5]:
            x, y, w, h, text, _ = item
            box = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=1.2,rounding_size=2", 
                                         ec="#1A1A1A", fc="#FBFBFB", lw=1.4)
            ax.add_patch(box)
            ax.text(x + w/2, y + h/2, text, ha='center', va='center', fontsize=9, color='#111111', multialignment='center')
        else:
            cx, cy, rw, rh, text, _ = item
            diamond = patches.Polygon([
                [cx, cy + rh], [cx + rw, cy], [cx, cy - rh], [cx - rw, cy]
            ], closed=True, ec="#1A1A1A", fc="#FFFFFF", lw=1.4)
            ax.add_patch(diamond)
            ax.text(cx, cy, text, ha='center', va='center', fontsize=8, color='#111111', multialignment='center')

    connections = [
        ((50, 115), (50, 108.5)),
        ((50, 101), (50, 97)),
        ((50, 81), (50, 78.5)),
        ((50, 71), (50, 64.5)),
        ((50, 57), (50, 50.5)),
        ((50, 43), (50, 36.5)),
        ((50, 29), (50, 22.5)),
        ((50, 15), (50, 9)),
    ]

    for start, end in connections:
        ax.annotate('', xy=end, xytext=start, arrowprops=dict(arrowstyle="->", color='#111111', lw=1.4))

    ax.text(52, 83.5, "Sí", fontsize=8.5, fontweight='bold', color='#111111')

    ax.annotate('', xy=(85, 89), xytext=(64, 89), arrowprops=dict(arrowstyle="->", color='#111111', lw=1.4))
    ax.text(71, 90.5, "No", fontsize=8.5, fontweight='bold', color='#111111')
    
    error_box = patches.FancyBboxPatch((75, 78), 20, 7, boxstyle="round,pad=0.8,rounding_size=1.5", 
                                       ec="#666666", fc="#F0F0F0", lw=1.2)
    ax.add_patch(error_box)
    ax.text(85, 81.5, "Rechazo de Archivo\n(Log de Error en Auditoría)", ha='center', va='center', fontsize=7.8, color='#333333')
    ax.annotate('', xy=(85, 85), xytext=(85, 89), arrowprops=dict(arrowstyle="->", color='#111111', lw=1.4))

    circle_outer = plt.Circle((50, 6.5), 2.5, ec='#111111', fc='white', lw=1.5)
    circle_inner = plt.Circle((50, 6.5), 1.6, color='#111111')
    ax.add_patch(circle_outer)
    ax.add_patch(circle_inner)
    ax.text(50, 2.5, "Fin de Ingesta / Inicio NER", ha='center', va='center', fontsize=8.5, fontstyle='italic', color='#444444')

    plt.tight_layout()
    output_path = os.path.abspath("docs/images/figura_3_9_diagrama_actividad_ingesta.png")
    plt.savefig(output_path, dpi=300, facecolor='white', bbox_inches='tight')
    plt.close()
    print(f"Figura 3.9 generada en: {output_path}")
    return output_path

def generar_figura_3_12():
    fig, ax = plt.subplots(figsize=(10, 14), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 140)
    ax.axis('off')

    ax.text(50, 136, "Diagrama de Flujo: Pipeline de Extracción NER (BETO) y Normalización (RapidFuzz)", 
            ha='center', va='center', fontsize=12, fontweight='bold', color='#111111')
    ax.text(50, 133, "(Modelo de Procesamiento de Lenguaje Natural - Sprint 3)", 
            ha='center', va='center', fontsize=9.5, fontstyle='italic', color='#444444')

    circle_start = plt.Circle((50, 127), 2.2, color='#111111', ec='#111111')
    ax.add_patch(circle_start)

    steps = [
        (25, 115, 50, 7.5, "1. Texto Plano Estructurado\n(Generado por módulo de ingesta en Sprint 2)", False),
        (25, 101, 50, 7.5, "2. Tokenización con BETO Transformer\n(dccuchile/bert-base-spanish-wwm-cased)", False),
        (25, 87, 50, 7.5, "3. Inferencia NER y Extracción de Entidades\n(Etiquetas: B-PER/I-PER, B-MISC/I-MISC, Fechas, Notas)", False),
        (50, 75, 14, 7.5, "¿Entidad posee\nCI válido directo\nen dim_estudiante?", True),
        (25, 55, 50, 7.5, "4. Emparejamiento Difuso con RapidFuzz\n(Algoritmo Token Sort Ratio sobre catálogos canónicos)", False),
        (50, 42, 14, 7.5, "¿Nivel confianza\nprobabilística\n≥ 0.85 (85%)?", True),
        (10, 24, 38, 8, "5A. Inserción Directa a Tablas de Hechos\n(fact_rendimiento_academico, fact_financiera)", False),
        (52, 24, 38, 8, "5B. Derivación a Staging HITL\n(staging_entidad_no_resuelta / requiere_revision)", False),
    ]

    ax.annotate('', xy=(50, 122.5), xytext=(50, 124.8), arrowprops=dict(arrowstyle="->", color='#111111', lw=1.5))

    for item in steps:
        if not item[5]:
            x, y, w, h, text, _ = item
            box = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=1.2,rounding_size=2", 
                                         ec="#1A1A1A", fc="#FBFBFB", lw=1.4)
            ax.add_patch(box)
            ax.text(x + w/2, y + h/2, text, ha='center', va='center', fontsize=9, color='#111111', multialignment='center')
        else:
            cx, cy, rw, rh, text, _ = item
            diamond = patches.Polygon([
                [cx, cy + rh], [cx + rw, cy], [cx, cy - rh], [cx - rw, cy]
            ], closed=True, ec="#1A1A1A", fc="#FFFFFF", lw=1.4)
            ax.add_patch(diamond)
            ax.text(cx, cy, text, ha='center', va='center', fontsize=7.8, color='#111111', multialignment='center')

    ax.annotate('', xy=(50, 108.5), xytext=(50, 115), arrowprops=dict(arrowstyle="->", color='#111111', lw=1.4))
    ax.annotate('', xy=(50, 94.5), xytext=(50, 101), arrowprops=dict(arrowstyle="->", color='#111111', lw=1.4))
    ax.annotate('', xy=(50, 82.5), xytext=(50, 87), arrowprops=dict(arrowstyle="->", color='#111111', lw=1.4))

    ax.annotate('', xy=(15, 75), xytext=(36, 75), arrowprops=dict(arrowstyle="-", color='#111111', lw=1.4))
    ax.annotate('', xy=(15, 32), xytext=(15, 75), arrowprops=dict(arrowstyle="->", color='#111111', lw=1.4))
    ax.text(24, 76.5, "Sí (Match Exacto CI)", fontsize=8, fontweight='bold', color='#111111')

    ax.annotate('', xy=(50, 62.5), xytext=(50, 67.5), arrowprops=dict(arrowstyle="->", color='#111111', lw=1.4))
    ax.text(52, 65, "No", fontsize=8.5, fontweight='bold', color='#111111')

    ax.annotate('', xy=(50, 49.5), xytext=(50, 55), arrowprops=dict(arrowstyle="->", color='#111111', lw=1.4))

    ax.annotate('', xy=(29, 32), xytext=(36, 42), arrowprops=dict(arrowstyle="->", color='#111111', lw=1.4))
    ax.text(25, 41, "Sí (≥ 0.85)", fontsize=8, fontweight='bold', color='#111111')

    ax.annotate('', xy=(71, 32), xytext=(64, 42), arrowprops=dict(arrowstyle="->", color='#111111', lw=1.4))
    ax.text(67, 41, "No (< 0.85)", fontsize=8, fontweight='bold', color='#111111')

    c_out1 = plt.Circle((29, 13), 2.2, ec='#111111', fc='white', lw=1.4)
    c_in1 = plt.Circle((29, 13), 1.4, color='#111111')
    ax.add_patch(c_out1)
    ax.add_patch(c_in1)
    ax.annotate('', xy=(29, 15.2), xytext=(29, 24), arrowprops=dict(arrowstyle="->", color='#111111', lw=1.4))
    ax.text(29, 9, "Consolidado en DW", ha='center', va='center', fontsize=8, fontstyle='italic', color='#333333')

    c_out2 = plt.Circle((71, 13), 2.2, ec='#111111', fc='white', lw=1.4)
    c_in2 = plt.Circle((71, 13), 1.4, color='#111111')
    ax.add_patch(c_out2)
    ax.add_patch(c_in2)
    ax.annotate('', xy=(71, 15.2), xytext=(71, 24), arrowprops=dict(arrowstyle="->", color='#111111', lw=1.4))
    ax.text(71, 9, "Pendiente Resolución HITL", ha='center', va='center', fontsize=8, fontstyle='italic', color='#333333')

    plt.tight_layout()
    output_path = os.path.abspath("docs/images/figura_3_12_diagrama_flujo_beto_rapidfuzz.png")
    plt.savefig(output_path, dpi=300, facecolor='white', bbox_inches='tight')
    plt.close()
    print(f"Figura 3.12 generada en: {output_path}")
    return output_path

if __name__ == "__main__":
    p1 = generar_figura_3_9()
    p2 = generar_figura_3_12()
    art_dir = r"C:\Users\DAZA\.gemini\antigravity\brain\f930e363-4cdd-4e0f-bee8-dd23f1e3b7d0"
    if os.path.exists(art_dir):
        shutil.copy(p1, os.path.join(art_dir, os.path.basename(p1)))
        shutil.copy(p2, os.path.join(art_dir, os.path.basename(p2)))
        print("Copiadas al directorio de artefactos con éxito.")
