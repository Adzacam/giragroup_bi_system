"""
Generador de alta fidelidad de la Figura 3.4: Modelo conceptual del almacén de datos (Metodología Hefesto - Paso 1).
Perfeccionamiento geométrico y de enrutamiento:
- Se expanden los canales intermedios a 8 unidades para que las cardinalidades no se toquen.
- El conector de Estudiante hacia Situación Financiera sale limpiamente desde el borde inferior de Estudiante (sin cruzar su texto).
- Los conectores inferiores hacia Módulo y Origen Documental transitan por niveles de Y separados (y=34 y y=31).
- 2 núcleos de hechos: Rendimiento Académico y Situación Financiera.
- Montos estrictamente en Bolivianos (Bs, no $).
- 6 dimensiones exactas (4 conformadas: Estudiante, Tiempo, Módulo/Programa, Origen Documental; 2 específicas: Docente y Categoría Financiera).
- 300 DPI, formato PNG, fondo blanco puro (#FFFFFF), sin título incrustado.
"""

import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches

OUTPUT_PATHS = [
    r"docs\images\figura_3_4_modelo_conceptual_hefesto.png",
    r"C:\Users\DAZA\.gemini\antigravity\brain\f930e363-4cdd-4e0f-bee8-dd23f1e3b7d0\figura_3_4_modelo_conceptual_hefesto.png"
]

def dibujar_hefesto():
    fig, ax = plt.subplots(figsize=(16.8, 10.5), dpi=300)
    ax.set_xlim(0, 168)
    ax.set_ylim(0, 102)
    ax.axis('off')

    c_border_fact = "#111111"
    c_border_dim = "#222222"
    c_hdr_fact = "#EDEDED"
    c_hdr_dim = "#F5F5F5"
    c_text_dark = "#111111"
    c_text_muted = "#333333"

    def draw_entity(x, y, w, h, stereotype, title, attrs, is_fact=False):
        hdr_h = 6.2
        box = patches.Rectangle((x, y), w, h, ec=c_border_fact if is_fact else c_border_dim,
                                fc="#FFFFFF", lw=1.6 if is_fact else 1.2)
        ax.add_patch(box)
        hdr = patches.Rectangle((x, y + h - hdr_h), w, hdr_h,
                                ec=c_border_fact if is_fact else c_border_dim,
                                fc=c_hdr_fact if is_fact else c_hdr_dim, lw=1.1)
        ax.add_patch(hdr)
        ax.text(x + w/2, y + h - 2.2, f"«{stereotype}»", fontsize=7.2, fontstyle='italic', ha='center', color=c_text_muted)
        ax.text(x + w/2, y + h - 4.6, title, fontsize=8.6 if is_fact else 8.2, fontweight='bold', ha='center', color=c_text_dark)

        cur_y = y + h - hdr_h - 2.8
        for attr in attrs:
            is_pk = "Identificador" in attr or "Nota Final" in attr or "Monto Deuda" in attr
            fweight = 'bold' if is_pk else 'normal'
            ax.text(x + 1.8, cur_y, attr, fontsize=7.4, fontweight=fweight, color=c_text_dark if is_pk else c_text_muted)
            cur_y -= 2.6

    # =========================================================================
    # 1. DIMENSIÓN CONFORMADA: ESTUDIANTE (Arriba Centro, x=54..114, y=76..98)
    # =========================================================================
    draw_entity(54, 76, 60, 22, "Dimensión Conformada", "Estudiante", [
        "Identificador: id_estudiante (PK)",
        "Código Estudiante & Cédula de Identidad (CI)",
        "Nombre Completo del Estudiante",
        "Sede / Institución Titular (cat_institucion)",
        "Género y Rango de Edad",
        "Ciudad de Residencia"
    ])

    # =========================================================================
    # 2. CAPA MEDIA CON CANALES AMPLIOS (x=4..27 | 34..66 | 74..98 | 106..138 | 145..168)
    # =========================================================================
    # Dimensión Específica: Docente (Extremo Izquierdo)
    draw_entity(4, 38, 23, 29, "Dimensión Específica", "Docente", [
        "Identificador: id_docente",
        "Nombre Completo",
        "Área de Especialidad",
        "Grado Académico Máximo",
        "Tipo (Titular / Invitado)",
        "Institución de Origen"
    ])

    # Núcleo de Hechos: Rendimiento Académico (Centro-Izquierda)
    draw_entity(34, 36, 32, 33, "Núcleo de Hechos", "Rendimiento Académico", [
        "Nota Final (Escala 0 - 100)",
        "Asistencia Porcentual (%)",
        "Incumplimiento de Tareas (%)",
        "Calificación Evaluación Docente",
        "Nivel de Confianza IA (0.00 - 1.00)",
        "Alerta de Retención Estudiantil",
        "Flag Requiere Revisión (HITL)"
    ], is_fact=True)

    # Dimensión Conformada: Tiempo (Centro Exacto)
    draw_entity(74, 38, 24, 29, "Dimensión Conformada", "Tiempo", [
        "Identificador: id_tiempo",
        "Gestión (Año Calendario)",
        "Semestre / Trimestre",
        "Mes (Número y Nombre)",
        "Semana del Año",
        "Fecha Calendario (Día)"
    ])

    # Núcleo de Hechos: Situación Financiera (Centro-Derecha)
    draw_entity(106, 36, 32, 33, "Núcleo de Hechos", "Situación Financiera", [
        "Monto Deuda Devengada (Bs)",
        "Monto Pagado Amortizado (Bs)",
        "Monto Saldo Pendiente (Bs)",
        "Cuotas Impagas Vencidas",
        "Días de Mora Acumulados",
        "Estado de Cartera (Mora / Al Día)",
        "Alerta Financiera Crediticia"
    ], is_fact=True)

    # Dimensión Específica: Categoría Financiera (Extremo Derecho)
    draw_entity(145, 38, 23, 29, "Dimensión Específica", "Categoría Financiera", [
        "Identificador: id_categoria",
        "Código Estándar Contable",
        "Nombre de la Partida",
        "Tipo Flujo (Ingreso/Egreso)",
        "Rubro Presupuestario"
    ])

    # =========================================================================
    # 3. CAPA INFERIOR: MÓDULO / PROGRAMA | ORIGEN DOCUMENTAL
    # =========================================================================
    # Dimensión Conformada: Módulo / Programa (Abajo Izquierda)
    draw_entity(14, 7, 52, 22, "Dimensión Conformada", "Módulo / Programa", [
        "Identificador: id_modulo (PK)",
        "Nombre del Módulo Curricular",
        "Código Programa (POS Code)",
        "Programa Académico Contenedor",
        "Sede / Escuela Titular",
        "Créditos Académicos"
    ])

    # Dimensión Conformada: Origen Documental (Abajo Derecha)
    draw_entity(90, 7, 54, 22, "Dimensión Conformada", "Origen Documental", [
        "Identificador: id_origen (PK)",
        "Nombre del Archivo Fuente",
        "Tipo Formato (Excel, CSV, Formulario)",
        "Hash Criptográfico SHA-256",
        "Lote de Ingesta Asociado",
        "Fecha y Hora de Procesamiento"
    ])

    # =========================================================================
    # CONECTORES ORTOGONALES Y CARDINALIDADES (SIN CRUCE DE LÍNEAS SOBRE TEXTO)
    # =========================================================================
    def card_badge(x, y, text):
        ax.text(x, y, text, fontsize=7.2, fontweight='bold', ha='center', va='center',
                bbox=dict(boxstyle="square,pad=0.2", fc="#FFFFFF", ec="#777777", lw=0.7))

    line_kw = dict(color="#222222", lw=1.3)

    # 1. Docente <-> Rendimiento Académico (Canal x=27..34, 7 unidades)
    ax.plot([27, 34], [52, 52], **line_kw)
    card_badge(28.8, 52, "1")
    card_badge(32.2, 52, "1..*")

    # 2. Rendimiento Académico <-> Tiempo (Canal x=66..74, 8 unidades)
    ax.plot([66, 74], [52, 52], **line_kw)
    card_badge(68.2, 52, "1..*")
    card_badge(71.8, 52, "1")

    # 3. Tiempo <-> Situación Financiera (Canal x=98..106, 8 unidades)
    ax.plot([98, 106], [52, 52], **line_kw)
    card_badge(100.2, 52, "1")
    card_badge(103.8, 52, "1..*")

    # 4. Situación Financiera <-> Categoría Financiera (Canal x=138..145, 7 unidades)
    ax.plot([138, 145], [52, 52], **line_kw)
    card_badge(139.8, 52, "1..*")
    card_badge(143.2, 52, "1")

    # 5. Estudiante <-> Rendimiento Académico (Vertical directo desde base de Estudiante)
    ax.plot([60, 60], [76, 69], **line_kw)
    card_badge(60, 74, "1")
    card_badge(60, 70.8, "1..*")

    # 6. Estudiante <-> Situación Financiera (Sale de base inferior de Estudiante a x=108, baja a Situación a x=118)
    ax.plot([108, 108, 118, 118], [76, 72.5, 72.5, 69], **line_kw)
    card_badge(108, 74.2, "1")
    card_badge(118, 70.8, "1..*")

    # 7. Módulo / Programa <-> Rendimiento Académico (Vertical directo a x=42)
    ax.plot([42, 42], [36, 29], **line_kw)
    card_badge(42, 34.2, "1..*")
    card_badge(42, 30.5, "1")

    # 8. Módulo / Programa <-> Situación Financiera (Nivel inferior de canal Y=31.5)
    ax.plot([56, 56, 110, 110], [29, 31.5, 31.5, 36], **line_kw)
    card_badge(56, 30.2, "1")
    card_badge(110, 34.5, "1..*")

    # 9. Origen Documental <-> Situación Financiera (Vertical directo a x=122)
    ax.plot([122, 122], [36, 29], **line_kw)
    card_badge(122, 34.2, "1..*")
    card_badge(122, 30.5, "1")

    # 10. Origen Documental <-> Rendimiento Académico (Nivel superior de canal Y=34.0)
    ax.plot([62, 62, 98, 98], [36, 34.0, 34.0, 29], **line_kw)
    card_badge(62, 34.8, "1..*")
    card_badge(98, 30.5, "1")

    # Guardado de archivos
    for path in OUTPUT_PATHS:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        fig.savefig(path, dpi=300, bbox_inches='tight', facecolor='#FFFFFF')
        print(f"Figura 3.4 generada con éxito en: {path}")

    plt.close(fig)

if __name__ == "__main__":
    dibujar_hefesto()
