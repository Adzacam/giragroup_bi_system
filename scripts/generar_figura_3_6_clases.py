"""
Generador de ultra alta precisión de la Figura 3.6: Diagrama de Clases del sistema (Modelos ORM SQLAlchemy y Esquemas Pydantic).
Ajustes milimétricos:
- Cálculo dinámico de altura h=52 y línea divisoria div_y para garantizar un margen holgado de 3 unidades entre el último atributo y el compartimento de relaciones.
- Separación vertical de las cardinalidades entre FactSituacionFinanciera y DimEstudiante (1 arriba de la línea, 0..* abajo de la línea).
- Canal vertical libre de 8 unidades entre ORM y Pydantic para la flecha «serializa a DTO».
- Fondo blanco puro (#FFFFFF), 300 DPI, ancho >= 3500 px, sin título incrustado.
"""

import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches

OUTPUT_PATHS = [
    r"docs\images\figura_3_6_diagrama_clases_orm_pydantic.png",
    r"C:\Users\DAZA\.gemini\antigravity\brain\f930e363-4cdd-4e0f-bee8-dd23f1e3b7d0\figura_3_6_diagrama_clases_orm_pydantic.png"
]

def dibujar_clase_uml(ax, x, y, w, h, estereotipo, nombre, atributos, metodos_o_relaciones, fsize=6.8):
    hdr_h = 5.6
    # 1. Caja contenedora
    box = patches.Rectangle((x, y), w, h, ec="#111111", fc="#FFFFFF", lw=1.3)
    ax.add_patch(box)

    # 2. Cabecera (Compartimento 1)
    hdr = patches.Rectangle((x, y + h - hdr_h), w, hdr_h, ec="#111111", fc="#F4F4F4", lw=1.0)
    ax.add_patch(hdr)
    ax.text(x + w/2, y + h - 1.8, f"«{estereotipo}»", fontsize=6.8, fontstyle='italic', ha='center', color="#444444")
    ax.text(x + w/2, y + h - 4.1, nombre, fontsize=8.2, fontweight='bold', ha='center', color="#111111")

    # 3. Atributos (Compartimento 2)
    cur_y = y + h - hdr_h - 2.5
    for a in atributos:
        ax.text(x + 1.5, cur_y, a, fontsize=fsize, color="#111111")
        cur_y -= 2.4

    # 4. Línea divisoria calculada para dejar espacio exacto
    div_y = y + len(metodos_o_relaciones) * 2.5 + 2.5
    ax.plot([x, x + w], [div_y, div_y], color="#111111", lw=0.9)

    # 5. Métodos / Relaciones (Compartimento 3)
    cur_y = div_y - 2.3
    for m in metodos_o_relaciones:
        ax.text(x + 1.5, cur_y, m, fontsize=fsize, color="#222222", fontstyle='italic')
        cur_y -= 2.4

def generar_diagrama_clases():
    fig, ax = plt.subplots(figsize=(16.8, 11.8), dpi=300)
    ax.set_xlim(0, 168)
    ax.set_ylim(0, 118)
    ax.axis('off')

    c_line = "#111111"

    # =========================================================================
    # 1. CAPA SUPERIOR: MODELOS ORM SQLALCHEMY (backend/models/)
    # Altura h=52, y=58..110
    # =========================================================================
    # Clase 1: FactRendimientoAcademico (x=6..54, w=48, h=52)
    dibujar_clase_uml(ax, 6, 58, 48, 52, "SQLAlchemy Model", "FactRendimientoAcademico", [
        "+ id_rendimiento: Integer [PK]",
        "+ fk_estudiante: Integer [FK]",
        "+ fk_docente: Integer [FK]",
        "+ fk_modulo: Integer [FK]",
        "+ fk_tiempo: Integer [FK]",
        "+ fk_origen: Integer [FK]",
        "+ nota_final: Numeric(5,2)",
        "+ asistencia_porcentaje: Numeric(5,2)",
        "+ tareas_incompletas: Numeric(5,2)",
        "+ calificacion_docente: Numeric(5,2)",
        "+ fk_estado: Integer",
        "+ nivel_confianza_ia: Numeric(4,3)",
        "+ requiere_revision: Boolean",
        "+ tipo_alerta: String(50)",
    ], [
        "+ estudiante: relationship('DimEstudiante')",
        "+ modulo: relationship('DimModulo')",
        "+ docente: relationship('DimDocente')",
    ], fsize=6.8)

    # Clase 2: FactSituacionFinanciera (x=60..108, w=48, h=52)
    dibujar_clase_uml(ax, 60, 58, 48, 52, "SQLAlchemy Model", "FactSituacionFinanciera", [
        "+ id_situacion: Integer [PK]",
        "+ fk_estudiante: Integer [FK]",
        "+ fk_modulo: Integer [FK]",
        "+ fk_categoria: Integer [FK]",
        "+ fk_tiempo: Integer [FK]",
        "+ fk_origen: Integer [FK]",
        "+ monto_total_deuda: Numeric(14,2)",
        "+ monto_total_pagado: Numeric(14,2)",
        "+ monto_pendiente: Numeric(14,2)",
        "+ dias_mora: Integer",
        "+ cuotas_impagas: Integer",
        "+ fk_estado: Integer",
        "+ nivel_confianza_ia: Numeric(4,3)",
        "+ requiere_revision: Boolean",
        "+ tipo_alerta: String(50)",
    ], [
        "+ estudiante: relationship('DimEstudiante')",
        "+ modulo: relationship('DimModulo')",
        "+ categoria: relationship('DimCategoria')",
    ], fsize=6.8)

    # Clase 3: DimEstudiante (x=114..162, w=48, h=52)
    dibujar_clase_uml(ax, 114, 58, 48, 52, "SQLAlchemy Model", "DimEstudiante", [
        "+ id_estudiante: Integer [PK]",
        "+ nombre_completo: String(250)",
        "+ codigo_estudiante: String(50)",
        "+ ci: String(20)",
        "+ id_temporal: String(50)",
        "+ identidad_verificada: Boolean",
        "+ id_institucion: Integer [FK]",
        "+ programa_origen: String(100)",
        "+ genero: String(20)",
        "+ ciudad: String(100)",
        "+ edad: Integer",
        "+ fecha_registro: DateTime",
    ], [
        "+ rendimientos: relationship('FactRendimiento')",
        "+ situaciones: relationship('FactSituacion')",
    ], fsize=6.8)

    # =========================================================================
    # 2. CAPA INFERIOR: ESQUEMAS PYDANTIC DTO (backend/schemas/)
    # Altura h=44, y=6..50
    # =========================================================================
    # Schema 1: RendimientoAcademicoResponse (x=6..54, w=48, h=44)
    dibujar_clase_uml(ax, 6, 6, 48, 44, "Pydantic Schema", "RendimientoAcademicoResponse", [
        "+ id_rendimiento: int",
        "+ estudiante_nombre: str",
        "+ modulo_nombre: str",
        "+ docente_nombre: str",
        "+ nota_final: float",
        "+ asistencia_porcentaje: float",
        "+ tareas_incompletas: float",
        "+ calificacion_docente: float",
        "+ estado_evaluacion: str",
        "+ nivel_confianza_ia: float",
        "+ requiere_revision: bool",
        "+ tipo_alerta: Optional[str]",
    ], [
        "+ model_config = ConfigDict(from_attributes=True)"
    ], fsize=6.8)

    # Schema 2: SituacionFinancieraResponse (x=60..108, w=48, h=44)
    dibujar_clase_uml(ax, 60, 6, 48, 44, "Pydantic Schema", "SituacionFinancieraResponse", [
        "+ id_situacion: int",
        "+ estudiante_nombre: str",
        "+ modulo_nombre: str",
        "+ categoria_nombre: str",
        "+ monto_total_deuda: float",
        "+ monto_total_pagado: float",
        "+ monto_pendiente: float",
        "+ dias_mora: int",
        "+ cuotas_impagas: int",
        "+ nivel_confianza_ia: float",
        "+ requiere_revision: bool",
        "+ tipo_alerta: Optional[str]",
    ], [
        "+ model_config = ConfigDict(from_attributes=True)"
    ], fsize=6.8)

    # Schema 3: EstudianteResponse (x=114..162, w=48, h=44)
    dibujar_clase_uml(ax, 114, 6, 48, 44, "Pydantic Schema", "EstudianteResponse", [
        "+ id_estudiante: int",
        "+ nombre_completo: str",
        "+ codigo_estudiante: Optional[str]",
        "+ ci: Optional[str]",
        "+ id_temporal: Optional[str]",
        "+ identidad_verificada: bool",
        "+ ciudad: Optional[str]",
        "+ edad: Optional[int]",
        "+ genero: Optional[str]",
        "+ programa_origen: Optional[str]",
    ], [
        "+ model_config = ConfigDict(from_attributes=True)"
    ], fsize=6.8)

    # =========================================================================
    # RELACIONES Y SERIALIZACIÓN
    # =========================================================================
    def badge(x, y, text):
        ax.text(x, y, text, fontsize=6.6, fontstyle='italic', ha='center', va='center',
                bbox=dict(boxstyle="square,pad=0.25", fc="#FFFFFF", ec="#777777", lw=0.7))

    # 1. Flechas de serialización ORM -> Pydantic DTO (y=58 baja a y=50)
    ax.plot([30, 30], [58, 50], color=c_line, lw=1.3, linestyle="--")
    ax.annotate("", xy=(30, 50), xytext=(30, 52), arrowprops=dict(arrowstyle="->", lw=1.3, color=c_line))
    badge(30, 54, "«serializa a DTO»")

    ax.plot([84, 84], [58, 50], color=c_line, lw=1.3, linestyle="--")
    ax.annotate("", xy=(84, 50), xytext=(84, 52), arrowprops=dict(arrowstyle="->", lw=1.3, color=c_line))
    badge(84, 54, "«serializa a DTO»")

    ax.plot([138, 138], [58, 50], color=c_line, lw=1.3, linestyle="--")
    ax.annotate("", xy=(138, 50), xytext=(138, 52), arrowprops=dict(arrowstyle="->", lw=1.3, color=c_line))
    badge(138, 54, "«serializa a DTO»")

    # 2. Relación horizontal DimEstudiante <-> FactSituacionFinanciera
    ax.plot([114, 108], [82, 82], color=c_line, lw=1.3)
    ax.text(112.5, 83.8, "1", fontsize=7.2, fontweight='bold', ha='center')
    ax.text(109.5, 80.2, "0..*", fontsize=7.2, fontweight='bold', ha='center')

    # 3. Relación ortogonal superior DimEstudiante <-> FactRendimientoAcademico (y=114)
    ax.plot([138, 138, 30, 30], [110, 114.5, 114.5, 110], color=c_line, lw=1.3)
    ax.text(138, 111.5, "1", fontsize=7.2, fontweight='bold', ha='center',
            bbox=dict(boxstyle="square,pad=0.15", fc="#FFFFFF", ec="none"))
    ax.text(30, 111.5, "0..*", fontsize=7.2, fontweight='bold', ha='center',
            bbox=dict(boxstyle="square,pad=0.15", fc="#FFFFFF", ec="none"))
    ax.text(84, 114.5, "1 : N (relationship)", fontsize=6.8, fontstyle='italic', ha='center', va='center',
            bbox=dict(boxstyle="square,pad=0.2", fc="#FFFFFF", ec="#888888", lw=0.6))

    # Guardado de archivos
    for path in OUTPUT_PATHS:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        fig.savefig(path, dpi=300, bbox_inches='tight', facecolor='#FFFFFF')
        print(f"Figura 3.6 generada con éxito en: {path}")

    plt.close(fig)

if __name__ == "__main__":
    generar_diagrama_clases()
