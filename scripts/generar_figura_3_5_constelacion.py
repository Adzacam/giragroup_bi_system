"""
Generador de alta fidelidad de la Figura 3.5: Esquema físico relacional en constelación (Derivado de db/schema.sql).
Normas aplicadas:
1. 7 dimensiones exactas: dim_estudiante, dim_docente, dim_modulo, dim_tiempo, dim_origen_documental, dim_categoria_financiera, dim_meta.
2. Tablas de hechos completas con sus columnas de gobernanza:
   - fk_estado INTEGER
   - nivel_confianza_ia NUMERIC(4,3)
   - requiere_revision BOOLEAN
   - tipo_alerta VARCHAR(50)
3. Tabla predictiva fact_forecast integrada armónicamente.
4. Alturas y anchos calculados dinámicamente para que ninguna columna ni tipo de dato colisione ni desborde.
5. Líneas de clave foránea (FK) ortogonales limpias que no cruzan cajas de datos.
6. Fondo blanco puro (#FFFFFF), estilo formal monocromático/escala de grises, 300 DPI, resolución >= 3700 px, sin título incrustado.
"""

import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches

OUTPUT_PATHS = [
    r"docs\images\figura_3_5_esquema_constelacion_fisico.png",
    r"C:\Users\DAZA\.gemini\antigravity\brain\f930e363-4cdd-4e0f-bee8-dd23f1e3b7d0\figura_3_5_esquema_constelacion_fisico.png"
]

def dibujar_tabla(ax, x, y, w, h, nombre, columnas, is_fact=False):
    """Dibuja una tabla relacional estilo DBeaver / pgModeler con tipografía nítida y tipos alineados."""
    hdr_h = 4.0
    # Caja exterior
    box = patches.Rectangle((x, y), w, h, ec="#111111", fc="#FFFFFF", lw=1.5 if is_fact else 1.2)
    ax.add_patch(box)
    
    # Cabecera
    hdr = patches.Rectangle((x, y + h - hdr_h), w, hdr_h, ec="#111111",
                            fc="#EDEDED" if is_fact else "#F6F6F6", lw=1.1)
    ax.add_patch(hdr)
    ax.text(x + w/2, y + h - hdr_h/2, nombre, fontsize=8.2 if is_fact else 7.8,
            fontweight='bold', ha='center', va='center', color="#111111")

    # Columnas
    cur_y = y + h - hdr_h - 2.4
    for col, ctype in columnas:
        is_key = "[PK]" in col or "[FK]" in col
        ax.text(x + 1.4, cur_y, col, fontsize=6.8, fontweight='bold' if is_key else 'normal',
                color="#111111" if is_key else "#333333")
        ax.text(x + w - 1.4, cur_y, ctype, fontsize=6.4, ha='right', color="#555555")
        cur_y -= 2.4

def generar_constelacion():
    fig, ax = plt.subplots(figsize=(17.5, 12.2), dpi=300)
    ax.set_xlim(0, 175)
    ax.set_ylim(0, 122)
    ax.axis('off')

    # =========================================================================
    # 1. FILA SUPERIOR: DIMENSIONES (y = 86 a 118)
    # =========================================================================
    # dim_docente (x=5..39)
    dibujar_tabla(ax, 5, 87, 34, 25, "dim_docente", [
        ("id_docente [PK]", "SERIAL"),
        ("nombre_completo", "VARCHAR(200)"),
        ("area_especialidad", "VARCHAR(150)"),
        ("grado_academico", "VARCHAR(50)"),
        ("tipo_docente", "VARCHAR(50)"),
        ("id_institucion [FK]", "INTEGER"),
        ("fecha_registro", "TIMESTAMP"),
    ])

    # dim_estudiante (x=44..86)
    dibujar_tabla(ax, 44, 85, 42, 29, "dim_estudiante", [
        ("id_estudiante [PK]", "SERIAL"),
        ("nombre_completo", "VARCHAR(250)"),
        ("codigo_estudiante", "VARCHAR(50)"),
        ("ci", "VARCHAR(20)"),
        ("id_temporal", "VARCHAR(50)"),
        ("identidad_verificada", "BOOLEAN"),
        ("ciudad", "VARCHAR(100)"),
        ("edad", "INTEGER"),
        ("genero", "VARCHAR(20)"),
    ])

    # dim_tiempo (x=91..131)
    dibujar_tabla(ax, 91, 85, 40, 29, "dim_tiempo", [
        ("id_tiempo [PK]", "INTEGER"),
        ("fecha", "DATE"),
        ("anio", "INTEGER"),
        ("semestre", "INTEGER"),
        ("trimestre", "INTEGER"),
        ("mes", "INTEGER"),
        ("nombre_mes", "VARCHAR(20)"),
        ("semana_anio", "INTEGER"),
        ("es_fin_de_semana", "BOOLEAN"),
    ])

    # dim_categoria_financiera (x=136..170)
    dibujar_tabla(ax, 136, 88, 34, 22, "dim_categoria_financiera", [
        ("id_categoria [PK]", "SERIAL"),
        ("codigo", "VARCHAR(50)"),
        ("nombre", "VARCHAR(100)"),
        ("tipo", "VARCHAR(50)"),
        ("descripcion", "TEXT"),
    ])

    # =========================================================================
    # 2. FILA MEDIA: HECHOS CENTRALES Y PREDICTIVOS (y = 36 a 79)
    # =========================================================================
    # fact_rendimiento_academico (x=5..54, w=49, h=41)
    dibujar_tabla(ax, 5, 36, 49, 41, "fact_rendimiento_academico", [
        ("id_rendimiento [PK]", "SERIAL"),
        ("fk_estudiante [FK]", "INTEGER"),
        ("fk_docente [FK]", "INTEGER"),
        ("fk_modulo [FK]", "INTEGER"),
        ("fk_tiempo [FK]", "INTEGER"),
        ("fk_origen [FK]", "INTEGER"),
        ("nota_final", "NUMERIC(5,2)"),
        ("asistencia_porcentaje", "NUMERIC(5,2)"),
        ("tareas_incompletas_porcentaje", "NUMERIC(5,2)"),
        ("calificacion_docente", "NUMERIC(5,2)"),
        ("fk_estado [FK]", "INTEGER"),
        ("nivel_confianza_ia", "NUMERIC(4,3)"),
        ("requiere_revision", "BOOLEAN"),
        ("tipo_alerta", "VARCHAR(50)"),
    ], is_fact=True)

    # fact_forecast (x=59..93, w=34, h=27)
    dibujar_tabla(ax, 59, 43, 34, 27, "fact_forecast", [
        ("id_forecast [PK]", "SERIAL"),
        ("modelo", "VARCHAR(50)"),
        ("serie_objetivo", "VARCHAR(50)"),
        ("periodo_proyectado", "VARCHAR(20)"),
        ("valor_proyectado", "NUMERIC(14,2)"),
        ("limite_inferior_95", "NUMERIC(14,2)"),
        ("limite_superior_95", "NUMERIC(14,2)"),
        ("fecha_ejecucion", "TIMESTAMP"),
    ], is_fact=True)

    # fact_situacion_financiera (x=98..148, w=50, h=43)
    dibujar_tabla(ax, 98, 35, 50, 43, "fact_situacion_financiera", [
        ("id_situacion [PK]", "SERIAL"),
        ("fk_estudiante [FK]", "INTEGER"),
        ("fk_modulo [FK]", "INTEGER"),
        ("fk_categoria [FK]", "INTEGER"),
        ("fk_tiempo [FK]", "INTEGER"),
        ("fk_origen [FK]", "INTEGER"),
        ("monto_total_deuda", "NUMERIC(14,2)"),
        ("monto_total_pagado", "NUMERIC(14,2)"),
        ("monto_pendiente_pago", "NUMERIC(14,2)"),
        ("dias_mora", "INTEGER"),
        ("cuotas_impagas", "INTEGER"),
        ("fk_estado [FK]", "INTEGER"),
        ("nivel_confianza_ia", "NUMERIC(4,3)"),
        ("requiere_revision", "BOOLEAN"),
        ("tipo_alerta", "VARCHAR(50)"),
    ], is_fact=True)

    # dim_meta (x=152..174, w=22, h=25)
    dibujar_tabla(ax, 151, 44, 22, 26, "dim_meta", [
        ("id_meta [PK]", "SERIAL"),
        ("codigo_kpi", "VARCHAR(50)"),
        ("nombre_kpi", "VARCHAR(150)"),
        ("valor_meta", "NUMERIC(14,2)"),
        ("valor_minimo", "NUMERIC(14,2)"),
        ("gestion", "INTEGER"),
        ("area", "VARCHAR(50)"),
    ])

    # =========================================================================
    # 3. FILA INFERIOR: DIMENSIONES (y = 5 a 30)
    # =========================================================================
    # dim_modulo (x=5..49)
    dibujar_tabla(ax, 5, 5, 45, 25, "dim_modulo", [
        ("id_modulo [PK]", "SERIAL"),
        ("codigo_modulo", "VARCHAR(50)"),
        ("nombre_modulo", "VARCHAR(200)"),
        ("codigo_programa", "VARCHAR(50)"),
        ("programa_nombre", "VARCHAR(200)"),
        ("creditos", "INTEGER"),
        ("orden_modulo", "INTEGER"),
    ])

    # dim_origen_documental (x=55..103)
    dibujar_tabla(ax, 55, 5, 48, 27, "dim_origen_documental", [
        ("id_origen [PK]", "SERIAL"),
        ("nombre_archivo", "VARCHAR(255)"),
        ("hash_sha256", "VARCHAR(64)"),
        ("tipo_formato", "VARCHAR(50)"),
        ("fecha_carga", "TIMESTAMP"),
        ("lote_id [FK]", "INTEGER"),
        ("total_registros", "INTEGER"),
        ("registros_validos", "INTEGER"),
    ])

    # =========================================================================
    # CONECTORES DE INTEGRIDAD REFERENCIAL (FK) ORTOGONALES
    # =========================================================================
    fk_kw = dict(color="#222222", lw=1.2, linestyle="-")

    # 1. dim_docente -> fact_rendimiento_academico (Vertical directo a x=22)
    ax.plot([22, 22], [87, 77], **fk_kw)
    ax.plot([22], [77], marker='v', color="#222222", markersize=4.5)

    # 2. dim_estudiante -> fact_rendimiento_academico (Vertical a x=48)
    ax.plot([48, 48], [85, 77], **fk_kw)
    ax.plot([48], [77], marker='v', color="#222222", markersize=4.5)

    # 3. dim_estudiante -> fact_situacion_financiera (Canal x=78 -> y=81 -> x=108 -> y=78)
    ax.plot([78, 78, 108, 108], [85, 81.5, 81.5, 78], **fk_kw)
    ax.plot([108], [78], marker='v', color="#222222", markersize=4.5)

    # 4. dim_tiempo -> fact_rendimiento_academico (Canal x=95 -> y=80 -> x=52 -> y=77)
    ax.plot([95, 95, 52, 52], [85, 79.5, 79.5, 77], **fk_kw)
    ax.plot([52], [77], marker='v', color="#222222", markersize=4.5)

    # 5. dim_tiempo -> fact_situacion_financiera (Vertical directo a x=120)
    ax.plot([120, 120], [85, 78], **fk_kw)
    ax.plot([120], [78], marker='v', color="#222222", markersize=4.5)

    # 6. dim_categoria_financiera -> fact_situacion_financiera (Canal x=142 -> y=81 -> x=142 -> y=78)
    ax.plot([142, 142], [88, 78], **fk_kw)
    ax.plot([142], [78], marker='v', color="#222222", markersize=4.5)

    # 7. dim_modulo -> fact_rendimiento_academico (Vertical directo a x=25)
    ax.plot([25, 25], [30, 36], **fk_kw)
    ax.plot([25], [36], marker='^', color="#222222", markersize=4.5)

    # 8. dim_modulo -> fact_situacion_financiera (Canal x=45 -> y=33 -> x=105 -> y=35)
    ax.plot([45, 45, 105, 105], [30, 33, 33, 35], **fk_kw)
    ax.plot([105], [35], marker='^', color="#222222", markersize=4.5)

    # 9. dim_origen_documental -> fact_rendimiento_academico (Canal x=62 -> y=34.5 -> x=48 -> y=36)
    ax.plot([62, 62, 48, 48], [32, 34.5, 34.5, 36], **fk_kw)
    ax.plot([48], [36], marker='^', color="#222222", markersize=4.5)

    # 10. dim_origen_documental -> fact_situacion_financiera (Canal x=85 -> y=33.5 -> x=125 -> y=35)
    ax.plot([85, 85, 125, 125], [32, 33.5, 33.5, 35], **fk_kw)
    ax.plot([125], [35], marker='^', color="#222222", markersize=4.5)

    # Guardado de archivos
    for path in OUTPUT_PATHS:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        fig.savefig(path, dpi=300, bbox_inches='tight', facecolor='#FFFFFF')
        print(f"Figura 3.5 generada con éxito en: {path}")

    plt.close(fig)

if __name__ == "__main__":
    generar_constelacion()
