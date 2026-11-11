# -*- coding: utf-8 -*-
"""
scripts/generar_tablas_tesis_v2.py
==================================
Generador automatizado y versionado de las tablas y cuadros académicos
de la tesis en formato Word (docs/tablas_v2.docx) y Markdown (docs/tablas_v2.md).

Reglas y Estándares:
- Fuente única: docs/fuente_verdad_tesis.md (SFV v2, snapshot_dw_20261110_1201).
- Formato numérico boliviano: coma decimal (,) y punto de miles (.).
- Tipografía: Times New Roman 10 pt, bordes simples, encabezados en negrita.
- Título encima: «Tabla X.Y ...» o «Cuadro X.Y ...»
- Nota debajo: «Fuente: Elaboración propia con datos del sistema (snapshot snapshot_dw_20261110_1201).»
- NO crea tablas nuevas; expande las existentes sin alterar la numeración.
"""

import os
import pathlib
import csv
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

OUTPUT_DIR = pathlib.Path("docs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DOCX_PATH = OUTPUT_DIR / "tablas_v2.docx"
MD_PATH = OUTPUT_DIR / "tablas_v2.md"
MANIFEST_PATH = pathlib.Path("docs/evidencias/manifiesto_tablas.csv")

PIE_OFICIAL = "Fuente: Elaboración propia con datos del sistema (snapshot snapshot_dw_20261110_1201)."

# -----------------------------------------------------------------------------
# Funciones auxiliares de estilo para python-docx
# -----------------------------------------------------------------------------
def set_cell_border(cell, **kwargs):
    """Configura bordes simples en una celda de tabla docx."""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = OxmlElement('w:tcBorders')
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        edge_data = kwargs.get(edge)
        if edge_data:
            tag = 'w:{}'.format(edge)
            element = OxmlElement(tag)
            element.set(qn('w:val'), edge_data.get('val', 'single'))
            element.set(qn('w:sz'), str(edge_data.get('sz', 4)))
            element.set(qn('w:space'), '0')
            element.set(qn('w:color'), edge_data.get('color', 'auto'))
            tcBorders.append(element)
    tcPr.append(tcBorders)

def set_cell_shading(cell, color_hex):
    """Aplica sombreado de fondo a una celda."""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), color_hex)
    tcPr.append(shd)

def agregar_tabla_docx(doc, titulo, encabezados, filas, ancho_col=None, nota_pie=None):
    """Agrega una tabla formateada al documento Word según normas de la tesis."""
    # Título encima
    p_tit = doc.add_paragraph()
    p_tit.paragraph_format.space_before = Pt(12)
    p_tit.paragraph_format.space_after = Pt(4)
    run_tit = p_tit.add_run(titulo)
    run_tit.font.name = 'Times New Roman'
    run_tit.font.size = Pt(10)
    run_tit.font.bold = True
    
    # Tabla
    table = doc.add_table(rows=len(filas) + 1, cols=len(encabezados))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    
    border_kw = {'val': 'single', 'sz': 4, 'color': '888888'}
    cell_borders = {'top': border_kw, 'bottom': border_kw, 'left': border_kw, 'right': border_kw}
    
    # Encabezado
    hdr_cells = table.rows[0].cells
    for i, title in enumerate(encabezados):
        cell = hdr_cells[i]
        cell.text = title
        set_cell_border(cell, **cell_borders)
        set_cell_shading(cell, 'E6E6E6')
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(2)
        for r in p.runs:
            r.font.name = 'Times New Roman'
            r.font.size = Pt(9.5)
            r.font.bold = True
            
    # Filas de datos
    for r_idx, row_data in enumerate(filas):
        row_cells = table.rows[r_idx + 1].cells
        bg_color = 'F9F9F9' if r_idx % 2 == 1 else 'FFFFFF'
        for c_idx, val in enumerate(row_data):
            cell = row_cells[c_idx]
            cell.text = str(val)
            set_cell_border(cell, **cell_borders)
            if bg_color != 'FFFFFF':
                set_cell_shading(cell, bg_color)
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(1.5)
            p.paragraph_format.space_after = Pt(1.5)
            for r in p.runs:
                r.font.name = 'Times New Roman'
                r.font.size = Pt(9.0)
                
    # Ancho de columnas si se define
    if ancho_col:
        for row in table.rows:
            for idx, width in enumerate(ancho_col):
                row.cells[idx].width = Inches(width)
                
    # Pie debajo
    p_pie = doc.add_paragraph()
    p_pie.paragraph_format.space_before = Pt(3)
    p_pie.paragraph_format.space_after = Pt(12)
    run_pie = p_pie.add_run(PIE_OFICIAL)
    run_pie.font.name = 'Times New Roman'
    run_pie.font.size = Pt(8.5)
    run_pie.font.italic = True
    
    if nota_pie:
        p_nota = doc.add_paragraph()
        p_nota.paragraph_format.space_before = Pt(0)
        p_nota.paragraph_format.space_after = Pt(10)
        run_nota = p_nota.add_run(nota_pie)
        run_nota.font.name = 'Times New Roman'
        run_nota.font.size = Pt(8.5)


# -----------------------------------------------------------------------------
# Definición estructurada de tablas y cuadros oficiales
# -----------------------------------------------------------------------------

# T3.4: Sprint 6
T3_4_TITULO = "Tabla 3.4 Planificación y esfuerzo de pruebas del Sprint 6"
T3_4_HDR = ["Sprint", "Objetivo / Alcance Técnico", "Pruebas Ejecutadas", "Criterio de Aceptación", "Estado Final"]
T3_4_DATA = [
    ["Sprint 6", "Aseguramiento de Calidad (SQA), Pruebas E2E, Auditoría de Seguridad y Estabilización Final", "382 pruebas*", "100 % pruebas críticas aprobadas; 0 regresiones en DW", "Completado exitosamente"]
]
T3_4_NOTA = "* Nota técnica: 382 pruebas registradas durante el cierre del Sprint 6; alcanzando 493 pruebas automatizadas tras la iteración de estabilización final (Tabla 3.34)."

# T3.19: Umbrales de decisión
T3_19_TITULO = "Tabla 3.19 Especificación de umbrales de decisión para resolución difusa y semántica"
T3_19_HDR = ["N.º", "Componente / Módulo", "Entidad / Criterio", "Umbral Oficial", "Archivo Fuente y Línea", "Comportamiento del Sistema"]
T3_19_DATA = [
    ["1", "Resolución de Personas", "Identidad de estudiantes y docentes", "0,92 (92 %)", "pipeline/normalization/person_resolver.py:111-132", "Coincidencia con apellido obligatorio, ≥ 2 tokens léxicos y búsqueda escalonada (módulo → programa → dimensión global)."],
    ["2", "Detección de Homonimia", "Duplicidad de nombres propios", "90 %", "backend/services/dw_loader.py:241-253, 475-486", "Si existen ≥ 2 candidatos con similitud ≥ 90 %, deriva a revisión HITL bajo causa HOMONIMIA; si existe 1, asigna rescate estado B."],
    ["3", "Variante de Identidad (CI)", "Documentos de identidad con prefijos", "85 %", "backend/services/dw_loader.py:185-192 / fuzzy_normalizer.py:88-92", "Comparación mediante token_set_ratio para rescatar cédulas con códigos de expedición o caracteres complementarios."],
    ["4", "Catálogo Docente", "Asignación de catedráticos", "85 %", "backend/services/dw_loader.py:679", "Coincidencia léxica sobre dim_docente. Por debajo de 0,85 se crea registro provisional en estado C para revisión."],
    ["5", "Catálogo de Módulos", "Materias y asignaturas de posgrado", "80 %", "backend/services/dw_loader.py:743", "Normalización fonética y token_sort_ratio sobre dim_modulo con tolerancia a abreviaturas y tildes."]
]

# T3.20: BETO + Ablación
T3_20_TITULO = "Tabla 3.20 Rendimiento experimental comparativo de arquitecturas de extracción NER (Ablación A/B/C)"
T3_20_HDR = ["Arquitectura Evaluada", "Descripción Técnica", "Dataset Estándar (gold_510 - 510 entidades)", "", "", "", "Layouts Adversos (layouts_5 - 72 entidades)", "", "", ""]
# Sub-header en datos o estructura
T3_20_HDR_REAL = ["Modo / Arquitectura", "Descripción del Enfoque", "P (gold_510)", "R (gold_510)", "F1 estricto (gold_510)", "F1 relajado (gold_510)", "P (layouts_5)", "R (layouts_5)", "F1 estricto (layouts_5)", "F1 relajado (layouts_5)"]
T3_20_DATA = [
    ["Modo A (Reglas)", "Determinístico puro: regex + posicional sin IA", "100,00 %", "100,00 %", "100,00 %", "100,00 %", "100,00 %", "16,67 %", "26,19 %", "28,57 %"],
    ["Modo B (Híbrido)", "Cascada: Reglas + RapidFuzz + Modelo BETO fine-tuned", "100,00 %", "100,00 %", "100,00 %", "100,00 %", "77,42 %", "66,67 %", "31,58 %", "71,64 %"],
    ["Modo C (BETO solo)", "Inferencia semántica exclusiva con modelo del lenguaje", "96,91 %", "98,24 %", "97,57 %", "99,12 %", "77,59 %", "62,50 %", "24,68 %", "69,23 %"]
]
T3_20_NOTA = "Nota: Evaluación con seqeval y token span matching estricto y relajado (SFV C-01 a C-08). Se elimina el valor provisional de 97,47 % de versiones preliminares."

# T3.24: Modelos predictivos
T3_24_TITULO = "Tabla 3.24 Parámetros econométricos y evaluación de modelos predictivos de matrícula y recaudación"
T3_24_HDR = ["Modelo Predictivo", "Serie Temporal y Fuente", "Horizonte / Partición", "Parámetros de Ajuste", "Métricas In-Sample", "Evaluación Hold-Out (h = 6)"]
T3_24_DATA = [
    ["Holt-Winters amortiguado (Validación)", "TBL_INSCRITOS.xlsx → fact_marketing.inscritos", "Entrenamiento 27 meses (2023-09 a 2025-11)", "α = 0,7010; β = 0,0000; γ = 0,0000; φ = 0,9858; m = 12", "RMSE = 45,00; AIC = 239,56", "RMSE = 75,03; MAPE = 13,89 % (dic-2025 a may-2026)"],
    ["Holt-Winters amortiguado (Producción)", "TBL_INSCRITOS.xlsx → fact_marketing.inscritos", "Ajuste completo 33 meses (2023-09 a 2026-05, N = 12.810)", "α = 0,6978; β = 0,0000; γ = 0,0000; φ = 0,9950; m = 12", "RMSE = 48,36; AIC = 290,00", "Banda de confianza aprox.: ±94,79 (1,96 × RMSE in-sample)"],
    ["Benchmark Naive Estacional (ŷ_t = y_{t-12})", "fact_marketing.inscritos (mismo periodo)", "Hold-out 6 meses (dic-2025 a may-2026)", "Sin parámetros (persistencia interanual)", "No aplica", "MAPE = 10,32 % (HW resulta 3,57 pp inferior al naive)"],
    ["Regresión Lineal OLS Matrícula", "fact_marketing.inscritos (N = 33 meses)", "Serie mensual sep-2023 a may-2026", "Pendiente = +3,6541 est./mes; Intercepto = 329,72 (t = 0)", "R² = 0,1921; p = 0,0107", "Tendencia histórica positiva y estadísticamente significativa"],
    ["Regresión Lineal OLS Recaudación", "fact_rentabilidad (Programas, N = 40 meses)", "Serie mensual 2023-01 a 2026-04", "Pendiente = +16.212,88 Bs/mes", "R² = 0,7128; RMSE = 118.783,06", "Hold-out MAPE = 17,01 %"]
]
T3_24_NOTA = "Proyección oficial del modelo de producción para el semestre jun-nov 2026 (Detalle E.1): 2026-06: 426,37 [331,58; 521,16] | 2026-07: 414,22 [319,43; 509,01] | 2026-08: 498,55 [403,76; 593,34] | 2026-09: 454,48 [359,69; 549,27] | 2026-10: 428,85 [334,06; 523,64] | 2026-11: 461,97 [367,18; 556,76]."

# T3.27: 11 KPI de la tesis
T3_27_TITULO = "Tabla 3.27 Catálogo de indicadores clave de rendimiento (KPI) implementados en el Cuadro de Mando Integral"
T3_27_HDR = ["Código", "Perspectiva CMI", "Nombre del Indicador", "Fórmula de Cálculo", "Tabla de Origen en DW", "Unidad", "Periodicidad"]
T3_27_DATA = [
    ["KPI-01", "Financiera", "Ticket promedio por estudiante", "Recaudación total / Matrícula efectiva", "fact_situacion_financiera / fact_rendimiento_academico", "Bs", "Mensual / Anual"],
    ["KPI-02", "Financiera", "Cumplimiento de meta del último mes", "Monto ejecutado / Monto meta del mes", "fact_rentabilidad.monto_meta", "%", "Mensual"],
    ["KPI-03", "Financiera", "Cumplimiento de meta a la fecha", "Monto ejecutado acumulado / Monto meta acumulado", "fact_rentabilidad.monto_meta", "%", "Acumulado"],
    ["KPI-04", "Financiera", "Estudiantes con riesgo financiero", "Conteo de estudiantes con ≥ 2 cuotas impagas o cartera previsionable", "fact_situacion_financiera", "Cantidad", "Mensual"],
    ["KPI-05", "Financiera", "Estado de cartera / Tasa de mora", "Estudiantes en mora o previsionables / Total cartera activa", "fact_situacion_financiera", "%", "Mensual"],
    ["KPI-06", "Clientes", "Conversión de admisiones", "Inscritos / Leads de marketing (Registrado como N/D*)", "fact_marketing", "%", "Mensual"],
    ["KPI-07", "Aprendizaje y Crecimiento", "Promedio de calificaciones", "Media aritmética de notas finales sobre escala de 100", "fact_rendimiento_academico", "Puntos", "Gestión"],
    ["KPI-08", "Aprendizaje y Crecimiento", "Tasa de aprobación", "Calificaciones con nota final ≥ 70 / Total calificaciones con nota", "fact_rendimiento_academico", "%", "Gestión"],
    ["KPI-09", "Aprendizaje y Crecimiento", "Estudiantes en riesgo académico", "Conteo de estudiantes con promedio acumulado ≤ 70 puntos", "fact_rendimiento_academico", "Cantidad", "Gestión"],
    ["KPI-10", "Procesos Internos", "Confianza media de extracción", "Media de niveles de confianza asignados por el pipeline", "fact_rendimiento_academico / fact_situacion_financiera", "%", "Por Lote / Mensual"],
    ["KPI-11", "Procesos Internos", "Automatización directa", "Registros consolidados directamente (confianza ≥ 0,85) / Total evaluados", "fact_rendimiento_academico / log_pipeline_ingesta", "%", "Por Lote / Mensual"]
]
T3_27_NOTA = "* Nota técnica: Se presentan los 11 KPI clave implementados en la interfaz ejecutiva web y el endpoint /kpis/cmi-completo, seleccionados de los 22 KPI formalmente catalogados en bi.ref_kpi. KPI-06 se consigna como N/D debido a que en el origen documental leads = inscritos. El cálculo de metas presupuestarias proviene de fact_rentabilidad.monto_meta (48 filas consolidadas de EJECUTADO VS META.xlsx; dim_meta permanece con 0 filas)."

# T3.29: Pruebas por suite
T3_29_TITULO = "Tabla 3.29 Distribución de la suite de pruebas automatizadas por módulo y sprint"
T3_29_HDR = ["Suite de Pruebas", "Directorio / Componente", "Pruebas Passed", "Pruebas Skipped", "Pruebas XFailed", "Total Pruebas", "Tasa de Éxito"]
T3_29_DATA = [
    ["Transversales", "tests/*.py (raíz, 263 pruebas con los bucles de verificación; 254 sin ellos): ingesta, bandeja HITL, resolución de personas/FK, KPI, riesgo, pronóstico, RBAC/OTP, reportes, esquema DDL, idempotencia de staging", "254", "0", "0", "254", "100,0 %"],
    ["Sprint 3", "tests/sprint3/ (confianza y telemetría, normalización y matching FK, calidad y auditoría, catálogos, reconciliación entre fuentes, reglas financieras, formateo BETO, motor NER)", "120", "0", "0", "120", "100,0 %"],
    ["Sprint 2", "tests/sprint2/ (Loop 1 lector universal, Loop 2 detección de bloques tabulares, Loop 3 extracción, categorización y cierre)", "32", "0", "0", "32", "100,0 %"],
    ["Sprint 4 + loops", "tests/sprint4/ (alertas, anonimización, DW loader, KPI y catálogos, RBAC: 23) + tests/test_sprint4_verification_loops.py (9)", "32", "0", "0", "32", "100,0 %"],
    ["Sprint 1", "tests/sprint1/ (infraestructura Docker, modelos ORM, esquema en constelación, usuarios semilla RBAC)", "16", "0", "0", "16", "100,0 %"],
    ["Readiness", "tests/readiness/test_production_readiness.py (puertas de salida a producción; 11 skipped por variables READINESS_* no definidas; 7 xfail por hallazgos documentados)", "21", "11", "7", "39", "100,0 % efectivo*"],
    ["TOTAL CONSOLIDADO", "Ambiente pytest unificado (--cov=backend --cov=pipeline)", "475", "11", "7", "493", "96,35 % (100 % passed/operativo)"]
]
T3_29_NOTA = "* Cobertura consolidada: 60,7 % (8.062 líneas cubiertas de 13.278 sentencias totales). Las 11 pruebas skipped y 7 xfailed en readiness corresponden a verificaciones condicionales de GPU opcional y entornos aislados sin fallas activas."

# T3.30: Cobertura por módulo (Tabla D.2 de la SFV v2)
T3_30_TITULO = "Tabla 3.30 Reporte de cobertura de código por componente del sistema analítico"
T3_30_HDR = ["Módulo / Archivo Fuente", "Líneas Totales", "Líneas Cubiertas", "Líneas Sin Cubrir", "Cobertura (%)", "Responsabilidad Arquitectónica"]
T3_30_DATA = [
    ["backend/core/security.py", "87", "76", "11", "87,4 %", "Autenticación JWT, MFA con OTP y control de acceso RBAC"],
    ["backend/services/financial_rules_engine.py", "85", "83", "2", "97,6 %", "Clasificación de categorías financieras y egresos"],
    ["backend/services/bandeja_grupos.py", "149", "142", "7", "95,3 %", "Agrupamiento inteligente de entidades para revisión HITL"],
    ["backend/services/risk_service.py", "337", "318", "19", "94,4 %", "Motor determinístico de alertas tempranas y mora"],
    ["pipeline/normalization/person_resolver.py", "125", "116", "9", "92,8 %", "Resolución jerárquica escalonada con RapidFuzz"],
    ["backend/services/alert_engine.py", "71", "65", "6", "91,5 %", "Disparador y orquestación de reglas de alerta"],
    ["backend/services/revision_hechos.py", "210", "185", "25", "88,1 %", "Servicio transaccional de auditoría y lease de revisión"],
    ["pipeline/normalization/fk_resolver.py", "89", "78", "11", "87,6 %", "Resolución de claves foráneas de programas y módulos"],
    ["backend/routers/reportes.py", "261", "221", "40", "84,7 %", "Enmascaramiento de datos y exportación de reportes"],
    ["pipeline/normalization/fuzzy_normalizer.py", "71", "59", "12", "83,1 %", "Limpieza canónica y normalización difusa de cadenas"],
    ["backend/services/extraccion_por_encabezado.py", "421", "342", "79", "81,2 %", "Mapeo estructural determinístico de hojas de cálculo"],
    ["pipeline/analytics/forecasting_holtwinters.py", "85", "69", "16", "81,2 %", "Ajuste y proyección Holt-Winters amortiguado"],
    ["pipeline/analytics/forecasting_ols.py", "28", "28", "0", "100,0 %", "Modelo econométrico lineal comparativo OLS"],
    ["backend/services/kpi_service.py", "374", "253", "121", "67,6 %", "Cálculo dinámico de indicadores del CMI en DW"],
    ["backend/services/ingestion_service.py", "587", "360", "227", "61,3 %", "Despacho y validación multipart de archivos subidos"],
    ["backend/services/confianza_service.py", "87", "53", "34", "60,9 %", "Cliente de inferencia y asignación de confianza IA"],
    ["backend/services/dw_loader.py", "870", "387", "483", "44,5 %", "Consolidación atómica de hechos y dimensiones en DW"],
    ["backend/routers/dataops.py", "2.176", "942", "1.234", "43,3 %", "Endpoints de carga masiva, catálogos y reprocesamiento"],
    ["backend/routers/pipeline.py", "269", "96", "173", "35,7 %", "Orquestación asíncrona de tareas del pipeline"],
    ["backend/services/forecast_service.py", "268", "98", "170", "36,6 %", "Servicio de persistencia y exposición de pronósticos"],
    ["pipeline/semantic/indice_confianza.py", "70", "23", "47", "32,9 %", "Cálculo vectorial de entropía de predicción BETO"],
    ["pipeline/semantic/ner_engine.py", "301", "193", "108", "64,1 %", "Motor NER BETO fine-tuned (S-17)"],
    ["TOTAL SISTEMA", "13.278", "8.062", "5.216", "60,7 %", "Alcance global de pruebas automatizadas (--cov=backend --cov=pipeline)"]
]

# T3.34: Estabilización
T3_34_TITULO = "Tabla 3.34 Indicadores de calidad y rendimiento en la iteración de estabilización final"
T3_34_HDR = ["Dimensión de Calidad", "Métrica Evaluada", "Valor Observado en Ronda 8", "Línea Base o Meta", "Resultado"]
T3_34_DATA = [
    ["Tiempo de ejecución", "Tiempo de máquina en ciclo mensual (10 archivos)", "60,0 s (DE = 0,8 s; 59,24 a 60,84 s)", "< 120,0 s", "Cumplimiento satisfactorio"],
    ["Desglose computacional", "Tiempo de inferencia modelo BETO", "5,4 s (DE = 0,2 s)", "N/D", "Validado en ciclo_r8_resumen.json"],
    ["Desglose computacional", "Tiempo de inserción y carga en DW", "44,0 s (43,97 s; DE = 0,87 s)", "N/D", "Validado en ciclo_r8_resumen.json"],
    ["Intervención humana", "Esfuerzo de revisión estimada (KLM)", "490,5 s (188 casos en 37 grupos)", "< 900,0 s (15 min)", "Cumplimiento satisfactorio (8,2 min)"],
    ["Aseguramiento de software", "Batería de pruebas automatizadas", "493 pruebas (475 passed, 11 skipped, 7 xfailed, 0 failed)", "100 % funcionales", "Cero defectos bloqueantes"],
    ["Integridad en staging", "Casos retenidos por discrepancia de calidad", "1.044 casos (756 CI discordante + 288 baja confianza)", "Aislamiento total", "100 % retenidos sin corromper DW"]
]

# T3.36: Matriz por objetivo
T3_36_TITULO = "Tabla 3.36 Matriz de verificación y cumplimiento de objetivos específicos"
T3_36_HDR = ["Objetivo Específico", "Indicador Técnico", "Resultado Obtenido (Snapshot Oficial)", "Meta Propuesta", "Evidencias Vinculadas"]
T3_36_DATA = [
    ["Obj. 1: Diagnóstico e ingesta", "Identificación de inconsistencias y excepciones en corpus", "1.044 casos en staging (756 CI discordante, 288 baja confianza); 562 excepciones interceptadas (0 ingresadas sin control)", "Aislamiento del 100 % de inconsistencias", "Tabla 3.34, Tabla 4.3; Gráfico 4.1"],
    ["Obj. 2: Modelo dimensional DW", "Estructura en constelación de hechos", "50 tablas base + 9 vistas (59 objetos totales en DW; 9 hechos, 7 dimensiones, 1 puente)", "Constelación conformada", "Tabla G.2; Figura 3.5; Diccionario Apéndice F"],
    ["Obj. 3: Unificación y vinculación", "Tasa de resolución automática del lote documental", "97,55 % directo (1.353) / 2,45 % HITL (34) / 0,00 % staging (0) sobre lote de 1.387", "≥ 85,0 % directo", "Tabla 3.34, Tabla 4.1, Tabla 4.5; Gráficos 3.2, 4.2, 4.3"],
    ["Obj. 4: Componentes de software", "Arquitectura modular y servicios RESTful", "128 rutas de API operativas (20 familias en Tabla 3.22); 9 contenedores orquestados con Docker Compose", "Arquitectura desplegada", "Tabla 3.22, Tabla 3.35, Tabla G.1; Figura 3.44"],
    ["Obj. 5: Analítica y CMI", "Modelado predictivo y tablero de indicadores", "HW amortiguado MAPE 13,89 % (frente a naive estacional 10,32 %); 11 KPI ejecutivos calculados dinámicamente", "MAPE < 20,0 %; 11 KPI CMI", "Tabla 3.24, Tabla 3.27, Tabla 4.6, Tabla 4.7; Gráficos 3.4, 4.4"],
    ["Obj. 6: Pruebas y calidad", "Verificación integral y cobertura de código", "493 pruebas automatizadas (475 passed, 11 skipped, 7 xfail, 0 failed); 60,7 % cobertura (8.062 de 13.278 sentencias)", "≥ 60,0 % cobertura", "Tablas 3.29 a 3.35; Figuras 3.40, 3.50"]
]

# T3.37: Cobertura funcional RF/RNF
T3_37_TITULO = "Tabla 3.37 Matriz de trazabilidad y cobertura funcional de requisitos del sistema (RF / RNF)"
T3_37_HDR = ["Requisito", "Tipo", "Descripción del Requisito", "Módulo / Endpoint Implementado", "Suite de Pruebas Pytest", "Evidencia de Cumplimiento"]
T3_37_DATA = [
    ["RF-01", "Funcional", "Autenticación JWT + MFA y RBAC de 5 perfiles", "backend/core/security.py; backend/routers/auth.py (/auth/token)", "tests/test_auth_and_rbac.py; tests/sprint4/test_rbac_enforcement.py; tests/test_otp_entorno_pruebas.py; tests/sprint1/test_usuarios_semilla_rbac.py", "Tabla 3.30 (security.py 87,4 %); 5 roles RBAC"],
    ["RF-02", "Funcional", "Carga por lotes de Excel/CSV (Sheets, Forms, Moodle), máx. 15 MB, rechazo de otras extensiones", "backend/services/ingestion_service.py (/dataops/upload)", "tests/sprint2/test_ingesta.py; tests/test_ingesta_sin_timeout.py; tests/test_fecha_corte_moodle.py; tests/test_formatos_genericos.py", "Tabla 3.34; Lote 1.387. Nota: el código limita a 50 MB (ingestion_service.py:515) y acepta solo .xlsx y .csv"],
    ["RF-03", "Funcional", "Clasificador agnóstico de fuente, descombinado de celdas, escala sobre 100 y texto plano", "backend/services/ingestion_service.py; pipeline/normalization/asymmetric_flattener.py; pipeline/semantic/formatter.py", "tests/test_agnostic_classifier_and_dw_reset.py; tests/sprint2/test_bloques_detector.py; tests/sprint3/test_formatter_gira40.py; tests/test_coherencia_estado_notas.py", "Tabla 3.30; Tabla 4.5"],
    ["RF-04", "Funcional", "NER con BETO sobre texto estructurado", "pipeline/semantic/ner_engine.py", "tests/sprint3/test_ner_engine_gira10.py", "Tabla 3.20 (F1 estricto 100 % Modo B / 97,57 % Modo C)"],
    ["RF-05", "Funcional", "Cascada de identidad A (CI exacta) / B (RapidFuzz o miembro nuevo TEMP) / C (revisión humana)", "backend/services/dw_loader.py (resolver estudiante); pipeline/normalization/person_resolver.py; fk_resolver.py", "tests/sprint4/test_dw_loader.py; tests/test_person_resolver.py; tests/test_fk_resolver_padron.py; tests/sprint3/test_area3_normalizacion_matching_fk.py", "Tabla 3.19 (umbral 0,92); DW: 13.667 A / 411 B"],
    ["RF-06", "Funcional", "Bandas de confianza: >= 0,85 directo; [0,60; 0,85) con requiere_revision; < 0,60 a stg_entidad_no_resuelta", "backend/services/dw_loader.py; backend/services/bandeja_grupos.py (/dataops/bandeja-grupos)", "tests/test_reduccion_hitl.py; tests/test_bandeja_grupos.py; tests/test_bandeja_hechos_en_revision.py; tests/sprint3/test_area2_confianza_telemetria.py", "Tabla 3.34; Tabla 4.3; 97,55 % directo / 2,45 % HITL / 0,00 % staging (1.387)"],
    ["RF-07", "Funcional", "Carga idempotente en el DW constelación en PostgreSQL", "backend/services/dw_loader.py; db/schema.sql", "tests/test_staging_idempotente.py; tests/test_esquema_alineado_ddl.py; tests/sprint1/test_esquema_constelacion_hefesto.py", "Figura 3.46; DW: 9 hechos + 7 dimensiones + 1 bridge. Nota: el RF dice 2 hechos núcleo + 5 de soporte (7); el DW tiene 9"],
    ["RF-08", "Funcional", "Alertas determinísticas: riesgo académico (<= 70), deserción (> 30 %), financiero (>= 2 cuotas) y crítica (>= 2 reglas)", "backend/services/risk_service.py; backend/services/alert_engine.py; backend/routers/riesgos.py", "tests/test_risk_service.py; tests/sprint4/test_alert_engine.py", "Tabla 3.30 (risk_service.py 94,4 %)"],
    ["RF-09", "Funcional", "Proyección de inscritos con Holt-Winters (m=12, N >= 24, IC 95 %), OLS anual y viabilidad de programas", "pipeline/analytics/forecasting_holtwinters.py; forecasting_ols.py; backend/services/forecast_service.py (/forecast)", "tests/test_forecasting.py; tests/test_holtwinters_cobertura.py", "Tabla 3.24; Tabla 4.7 (MAPE 13,89 %; IC ±94,79). Nota: el modelo en producción es amortiguado, no aditivo simple"],
    ["RF-10", "Funcional", "CMI en 4 perspectivas en React y conexión local a Power BI Desktop", "backend/services/kpi_service.py (/kpis/cmi-completo); backend/routers/cmi.py; backend/routers/powerbi.py", "tests/test_kpi_service.py; tests/sprint4/test_kpis_and_catalogs.py", "Tabla 3.27; Tabla 4.6; Figura 3.49"],
    ["RF-11", "Funcional", "Exportación XLSX/PDF de KPI, alertas y cierre; bitácora de auditoría", "backend/routers/reportes.py; backend/routers/audit.py", "tests/test_reportes_export.py", "Tabla 3.30 (reportes.py 84,7 %)"],
    ["RNF-01", "No Funcional", "Seguridad: JWT, mínimo privilegio, bcrypt, cabeceras defensivas, CORS, OWASP API", "backend/core/security.py; backend/main.py; gateway/nginx.conf", "tests/sprint4/test_rbac_enforcement.py; tests/test_sprint4_verification_loops.py", "Detalle G.1"],
    ["RNF-02", "No Funcional", "Privacidad: CI enmascarada, revelación solo ADMIN/AUDITOR con bitácora, corpus anonimizados", "backend/routers/dataops.py (ci_enmascarado / ci_real)", "tests/sprint4/test_anonimizacion.py; tests/test_sprint4_verification_loops.py (enmascaramiento de errores)", "Anexo B; Figura 3.47 (modo demo)"],
    ["RNF-03", "No Funcional", "Ciclo completo < 15 min y endpoints CMI/alertas < 3 s", "pipeline/ejecutar_sprint3.py; backend/routers/pipeline.py", "tests/readiness/test_production_readiness.py (parte live, skipped sin entorno); tests/load/locust_readiness.py (carga, fuera de pytest)", "Tabla 4.1; Tabla 4.8 (9,2 min postest)"],
    ["RNF-04", "No Funcional", "F1 de NER >= 0,85 y derivación de confianza < 0,85 a auditoría humana", "pipeline/semantic/ner_engine.py; backend/services/confianza_service.py", "tests/sprint3/test_ner_engine_gira10.py; tests/sprint3/test_area2_confianza_telemetria.py; tests/test_reduccion_hitl.py", "Tabla 3.20 (100 % Modo B / 97,57 % Modo C)"],
    ["RNF-05", "No Funcional", "ACID, unicidad e integridad referencial; recarga sin duplicar hechos", "backend/services/dw_loader.py; db/schema.sql", "tests/test_staging_idempotente.py; tests/test_esquema_alineado_ddl.py", "B-03 (0 filas en recarga)"],
    ["RNF-06", "No Funcional", "9 servicios contenerizados con docker-compose, sin licencias comerciales", "docker-compose.yml", "tests/sprint1/test_infraestructura_y_docker.py; tests/readiness/test_production_readiness.py", "Tabla G.1 (9 contenedores en ejecución)"],
    ["RNF-07", "No Funcional", "UI React responsiva, design tokens, modo claro/oscuro y navegación por rol", "frontend/src/context/ThemeContext.jsx; frontend/src/styles/", "Sin prueba pytest (verificación visual)", "Figuras de interfaz del Cap. III"]
]

# -----------------------------------------------------------------------------
# TABLAS DEL CAPÍTULO IV
# -----------------------------------------------------------------------------

# T4.1: Matriz de evaluación de indicadores
T4_1_TITULO = "Tabla 4.1 Evaluación final de indicadores de impacto y cumplimiento de metas operativas"
T4_1_HDR = ["N.º", "Indicador Técnico de Impacto", "Línea Base (Pretest)", "Valor Alcanzado (Postest)", "Meta Comprometida", "Evaluación de Cumplimiento"]
T4_1_DATA = [
    ["1", "Tasa de vinculación automática de entidades", "0,00 % (manual)", "97,55 % (1.353 de 1.387)", "≥ 85,00 %", "Cumple ampliamente (+12,55 pp)"],
    ["2", "Precisión de extracción NER en actas (gold_510)", "n. a. (sin inferencia IA)", "100,00 % (Modo B) / 97,57 % (Modo C)", "≥ 95,00 %", "Cumple (F1 micro estricto)"],
    ["3", "Precisión predictiva de matrícula (MAPE hold-out)", "n. a. (sin modelado cuantitativo)", "13,89 % (Benchmark naive: 10,32 %)", "< 20,00 %", "Cumple (Precisión calificada como buena)"],
    ["4", "Cobertura de pruebas automatizadas de software", "0,0 % (sin pruebas)", "60,7 % (8.062 de 13.278 sentencias)", "≥ 60,0 %", "Cumple (493 pruebas totales)"],
    ["5", "Tiempo medio de consolidación mensual", "600,0 min (8 a 12 horas)", "9,2 min (60,0 s máquina + 490,5 s KLM)", "< 15,0 min", "Cumple ampliamente (Δ = −590,8 min, −98,5 %)"],
    ["6a", "Consolidación directa automática del lote", "0 de 1.387 (0,00 %)", "1.353 de 1.387 (97,55 %)", "≥ 85,00 %", "Cumple (A-02)"],
    ["6b", "Unificación total y preservación documental", "n. a.", "100 % (1.387 de 1.387 procesados)", "100 %", "Cumple (1.353 directos + 34 HITL + 0 staging)"],
    ["7", "Excepciones de calidad abiertas en DW", "n. a. (contaminación directa)", "0 de 268 registros / 0 de 562 entidades", "0 registros sin control", "Cumple estrictamente (B-01, B-02)"]
]

# T4.3: Excepciones de calidad en corpus
T4_3_TITULO = "Tabla 4.3 Clasificación de excepciones de calidad e inconsistencias interceptadas en el corpus institucional"
T4_3_HDR = ["Nivel de Intercepción", "Categoría / Regla de Calidad", "Entidades Afectadas", "Registros Fuente / Grupos", "Proporción (%)", "Acción de Gobierno Aplicada"]
T4_3_DATA = [
    ["Preprocesamiento", "Etiqueta Likert (escala leída como persona)", "283", "148 registros", "50,36 %", "Descarte en memoria por expresión regular antes de inferencia."],
    ["Preprocesamiento", "Correo electrónico en celda de nombre", "139", "72 registros", "24,73 %", "Descarte en memoria; se preserva en campo email."],
    ["Preprocesamiento", "Comentario de texto / celda de texto libre", "87", "40 registros", "15,48 %", "Descarte en memoria; exclusión de dimensión personas."],
    ["Preprocesamiento", "Sin forma de nombre (PER_SIN_FORMA_NOMBRE)", "48", "6 registros", "8,54 %", "Filtrado y persistencia en log_inconsistencias en BD."],
    ["Preprocesamiento", "Persona sin coincidencia en catálogo", "5", "2 registros", "0,89 %", "Derivación a revisión humana HITL."],
    ["TOTAL EXCEPCIONES", "Excepciones interceptadas en lote 1.387", "562 entidades", "268 registros", "100,00 %", "0 de 562 ingresaron al DW sin control (100 % gobernadas)."],
    ["Bandeja HITL (Stock)", "Discordancia entre CI y Nombre (CI_NOMBRE_DISCORDANTE)", "756 casos", "725 grupos", "47,07 %", "Retención y agrupamiento para resolución interactiva."],
    ["Bandeja HITL (Stock)", "Baja confianza de asignación IA y hechos en revisión", "850 casos*", "61 grupos", "52,93 %", "288 IA en staging + 562 hechos en revisión de confianza."],
    ["TOTAL BANDEJA HITL", "Carga total consolidada en bandeja de resolución humana", "1.606 casos", "786 grupos", "100,00 %", "Stock total activo auditado en endpoint /dataops/bandeja-grupos."],
    ["Buffer Staging (BD)", "Entidades retenidas en capa stg_entidad_no_resuelta", "1.044 entidades", "786 grupos", "100,00 %", "756 CI discordante + 288 IA (aisladas sin corromper DW)."]
]
T4_3_NOTA = "Nota aclaratoria: Las 562 entidades del lote 1.387 corresponden a anomalías de forma detectadas en los libros de producción originarios de los repositorios y silos de información institucionales (Sheets, Excel, Forms y Moodle). La bandeja HITL global presenta 1.606 casos agrupados en 786 grupos funcionales (756 discordantes en 725 grupos y 850 de baja confianza en 61 grupos). El buffer físico de staging en BD almacena 1.044 entidades."

# T4.5: Balance por archivo
T4_5_TITULO = "Tabla 4.5 Balance consolidado de vinculación por archivo de producción y rendimiento del motor"
T4_5_HDR = ["Archivo de Producción Evaluado", "Registros Totales", "Consolidación Directa (≥ 0,85)", "Revisión Humana HITL (0,60–0,85)", "Retenido en Staging (< 0,60)", "Tasa Directa (%)"]
T4_5_DATA = [
    ["Base centralizada Académica ARCA (1).xlsx", "450", "448", "2", "0", "99,56 %"],
    ["BD Cobranzas.xlsx", "350", "349", "1", "0", "99,71 %"],
    ["TBL_INSCRITOS.xlsx", "250", "248", "2", "0", "99,20 %"],
    ["Evaluación Docente (Institución A).xlsx", "150", "137", "13", "0", "91,33 %"],
    ["Experiencia Docente 2.0.xlsx", "110", "95", "15", "0", "86,36 %"],
    ["BD Egresos.xlsx", "53", "53", "0", "0", "100,00 %"],
    ["EJECUTADO VS META.xlsx", "24", "23", "1", "0", "95,83 %"],
    ["TOTAL LOTE DE VALIDACIÓN (7 Archivos)", "1.387", "1.353", "34", "0", "97,55 %"],
    ["Rendimiento Motor BETO puro (Modo C - gold_510)", "510 entidades", "F1 micro estricto: 97,57 %", "P: 96,91 %; R: 98,24 %", "F1 relajado: 99,12 %", "97,57 %"],
    ["Rendimiento Motor Híbrido (Modo B - gold_510)", "510 entidades", "F1 micro estricto: 100,00 %", "P: 100,00 %; R: 100,00 %", "F1 relajado: 100,00 %", "100,00 %"],
    ["Rendimiento Híbrido en Layouts Adversos (layouts_5)", "72 entidades", "Modo B F1 relajado: 71,64 %", "Frente a Modo A (Reglas): 28,57 %", "Mejora relativa: +43,07 pp", "71,64 %"]
]
T4_5_NOTA = "Los motivos específicos de derivación a HITL desagregados por archivo individual no son provistos por el cargador (consignados como N/D). Se anonimiza el nombre de la institución como «Institución A»."

# T4.6: 11 KPI valores 2025
T4_6_TITULO = "Tabla 4.6 Resultados empíricos de los 11 indicadores clave de rendimiento del CMI (Gestión 2025 vs Global)"
T4_6_HDR = ["Código", "Indicador Institucional CMI", "Perspectiva", "Unidad", "Valor Gestión 2025", "Valor Consolidado Global", "Base de Cálculo y Evidencia Técnica"]
T4_6_DATA = [
    ["KPI-01", "Ticket promedio por estudiante", "Financiera", "Bs", "1.610,13", "1.626,99", "kpi_service.py: 1_ticket_promedio_por_programa"],
    ["KPI-02", "Cumplimiento de meta del último mes", "Financiera", "%", "157,48 %", "0,0 %*", "fact_rentabilidad.monto_meta (último mes ejecutado)"],
    ["KPI-03", "Cumplimiento de meta a la fecha", "Financiera", "%", "110,54 %", "96,67 %", "14.041.718,15 / 12.703.204,29 Bs en 2025 (DW total: 40.019.707,17 / 41.396.298,29 Bs)"],
    ["KPI-04", "Estudiantes con riesgo financiero", "Financiera", "Cantidad", "623", "1.765", "fact_situacion_financiera: ≥ 2 cuotas impagas o previsionable"],
    ["KPI-05", "Estado de cartera en mora", "Financiera", "%", "18,36 %", "26,62 %", "2025: 830 mora / 4.521 total (3.691 vigente); Global: 2.498 mora / 9.384 total"],
    ["KPI-06", "Conversión de admisiones", "Clientes", "%", "N/D**", "N/D**", "fact_marketing: leads = inscritos (4.737 / 4.737 en 2025; 15.196 / 15.196 global)"],
    ["KPI-07", "Promedio de calificaciones", "Aprendizaje y Crecimiento", "Puntos", "79,02", "78,98", "fact_rendimiento_academico: media aritmética de nota_final"],
    ["KPI-08", "Tasa de aprobación (nota ≥ 70)", "Aprendizaje y Crecimiento", "%", "85,61 %", "85,55 %", "2025: 8.502 aprobados / 1.429 reprobados; Global: 18.650 aprobados / 3.150 reprobados"],
    ["KPI-09", "Estudiantes en riesgo académico", "Aprendizaje y Crecimiento", "Cantidad", "588", "1.224", "kpi_service.py: estudiantes con promedio de calificaciones ≤ 70"],
    ["KPI-10", "Confianza media de extracción", "Procesos Internos", "Ratio / %", "0,9269 (92,69 %)", "0,9308 (93,08 %)", "DW general; Lote 1.387 alcanza 0,9618 (todas las entidades) y 0,9209 (solo BETO)"],
    ["KPI-11", "Automatización directa", "Procesos Internos", "%", "90,10 %", "91,06 %", "DW general; Lote 1.387 alcanza 97,55 % (1.353 directos de 1.387)"]
]
T4_6_NOTA = "* El valor 0,0 % global en KPI-02 se debe a la ausencia de metas para el mes de cierre final sin ejecución. ** KPI-06 se declara formalmente como N/D debido a que los registros de marketing no registran embudo previo de leads. Metas presupuestarias leídas de fact_rentabilidad.monto_meta."

# T4.7: Pronóstico y OLS anual
T4_7_TITULO = "Tabla 4.7 Comparación econométrica de modelos predictivos y proyecciones de recaudación"
T4_7_HDR = ["Modelo Predictivo / Econométrico", "Serie y Variable Modelada", "Horizonte Temporal", "Bondad de Ajuste (R² / AIC)", "Error Hold-Out (MAPE / RMSE)", "Estatus Académico"]
T4_7_DATA = [
    ["Holt-Winters amortiguado — Validación (m=12, φ=0,9858)", "fact_marketing.inscritos (Matrícula mensual)", "Entrenamiento 27 meses (sep-2023 a nov-2025); hold-out 6 meses (dic-2025 a may-2026)", "RMSE ajuste = 45,00; AIC = 239,56", "MAPE = 13,89 %; RMSE = 75,03", "Evaluación de error fuera de muestra del modelo"],
    ["Holt-Winters amortiguado — Producción (m=12, φ=0,9950)", "fact_marketing.inscritos (Matrícula mensual)", "Ajuste completo 33 meses (sep-2023 a may-2026)", "RMSE ajuste = 48,36; AIC = 290,00", "Sin hold-out (usa toda la serie); IC 95 % = ±94,79 (1,96 × 48,36)", "Modelo predictivo oficial de producción"],
    ["Naive Estacional (ŷ_t = y_{t-12})", "fact_marketing.inscritos (Matrícula mensual)", "Hold-out 6 meses (dic-2025 a may-2026)", "No aplica", "MAPE = 10,32 %", "Línea base comparativa (+3,57 pp favorable al naive)"],
    ["Regresión OLS Mensual Recaudación", "fact_rentabilidad (Recaudación programas)", "40 meses (2023-01 a 2026-04)", "R² = 0,7128; Pendiente = +16.212,88 Bs/mes", "MAPE = 17,01 %; RMSE = 118.783,06", "Tendencia mensual significativa"],
    ["Regresión OLS Anual Recaudación (DW)", "fact_rentabilidad.monto_ejecutado (Valores DW)", "3 gestiones (2023, 2024, 2025)", "R² = 0,9937; Pendiente = +2.267.633,83 Bs/año", "Ajuste exacto: 2023 = 8.035.694,25 Bs | 2024 = 9.989.730,09 Bs | 2025 = 12.570.961,91 Bs", "Modelo descriptivo anual (N = 3)"]
]

# T4.8: Resumen pre/post
T4_8_TITULO = "Tabla 4.8 Síntesis comparativa global de resultados pretest vs postest del sistema analítico"
T4_8_HDR = ["Parámetro de Evaluación", "Línea Base Manual (Pretest)", "Pipeline Analítico BI (Postest)", "Variación Relativa (Δ)", "Impacto Institucional"]
T4_8_DATA = [
    ["Tasa de vinculación automática directa", "0,00 % (100 % revisión humana en planillas)", "97,55 % (1.353 de 1.387)", "+97,55 pp", "Mitigación drástica de la fragmentación de datos."],
    ["Tiempo de consolidación de ciclo mensual", "600,0 min (media de 10,0 h; rango 8–12 h)", "9,2 min (60,0 s máquina + 490,5 s KLM)", "−590,8 min (−98,47 %)", "Aceleración analítica y disponibilidad ejecutiva oportuna."],
    ["Excepciones de calidad no gobernadas en DW", "No cuantificable (ingreso con errores en silos)", "0 de 562 entidades (0,00 % ingresadas sin control)", "−100,00 %", "Blindaje estricto de la consistencia transaccional y referencial."],
    ["Detección temprana de mora y cartera vencida", "Manual y reactiva al cierre de semestre", "Automática diaria (623 en riesgo / 18,36 % mora)", "Automatización total", "Mitigación del riesgo de incobrabilidad y soporte a decisiones."],
    ["Visibilidad ejecutiva del Cuadro de Mando", "Fragmentada en libros locales sin métricas", "Integral en tiempo real (11 KPI ejecutivos)", "100 % integrado", "Gobierno informacional alineado a los objetivos estratégicos."]
]

# -----------------------------------------------------------------------------
# CUADROS DE COSTOS (3.5 y Apéndice I)
# -----------------------------------------------------------------------------
C3_14_TITULO = "Cuadro 3.14 Resumen de Puntos de Función no ajustados por Sprint de desarrollo"
C3_14_HDR = ["Iteración / Sprint", "Componentes Principales Implementados", "Puntos de Función (PF) No Ajustados"]
C3_14_DATA = [
    ["Sprint 1", "Arquitectura, Infraestructura Base y Modelado Dimensional DW", "25"],
    ["Sprint 2", "Modelado Lógico y Físico de Catálogos Maestros (3NF)", "39"],
    ["Sprint 3", "Pipeline de Ingesta Documental y Serialización Multiarchivo", "75"],
    ["Sprint 4", "Motor Semántico PLN (BETO), Normalización y Calidad HITL", "78"],
    ["Sprint 5", "API Backend RESTful, Motor de Alertas y Plataforma Web React / CMI", "88"],
    ["Sprint 6", "Aseguramiento de Calidad, Pruebas E2E y Estabilización Final", "0*"],
    ["TOTAL PUNTOS DE FUNCIÓN NO AJUSTADOS", "Alcance total del sistema de software", "305"]
]
C3_14_NOTA = "* El Sprint 6 se dedicó exclusivamente a estabilización, pruebas y endurecimiento de seguridad, sin adición de funciones nuevas."

C3_15_TITULO = "Cuadro 3.15 Factores de Características Generales del Sistema (CGS) y Factor de Ajuste de Valor (VAF)"
C3_15_HDR = ["Factor de Complejidad General (CGS)", "Descripción Técnica del Entorno", "Puntaje Asignado (0 - 5)"]
C3_15_DATA = [
    ["1. Comunicación de datos", "Arquitectura distribuida API REST, microservicios y clientes web", "4"],
    ["2. Procesamiento distribuido", "Contenedores Docker independientes (Gateway, API, Pipeline, DB)", "4"],
    ["3. Rendimiento y tiempos de respuesta", "Requisito estricto de procesamiento mensual < 15 minutos", "4"],
    ["4. Configuración del equipamiento", "Despliegue sobre infraestructura local e híbrida en contenedores", "3"],
    ["5. Volumen de transacciones", "Carga masiva por lotes e inferencia paralela de embeddings BETO", "4"],
    ["6. Entrada de datos en línea", "Carga web multipart y resolución interactiva en bandeja HITL", "3"],
    ["7. Eficiencia del usuario final", "Interfaz SPA React optimizada para resolución ágil por grupos", "4"],
    ["8. Actualización en línea", "Actualización transaccional de estados y flags de revisión", "3"],
    ["9. Complejidad del procesamiento", "Inferencia NER con Transformers, RapidFuzz y modelos econométricos", "5"],
    ["10. Reusabilidad del código", "Módulos de normalización y reglas financieras reutilizables", "3"],
    ["11. Facilidad de instalación", "Automatización completa mediante docker-compose up --build", "4"],
    ["12. Facilidad de operación", "Procesos de backup, logs estructurados y auditoría", "3"],
    ["13. Múltiples sitios", "Uso centralizado en sede institucional con acceso web remoto", "2"],
    ["14. Facilidad de cambio", "Esquema modular y desacoplado para nuevas reglas y fuentes", "1"],
    ["TOTAL CARACTERÍSTICAS GENERALES (CGS)", "Suma aritmética de los 14 factores de complejidad", "47"],
    ["FACTOR DE AJUSTE DE VALOR (VAF)", "VAF = 0,65 + (0,01 × CGS) = 0,65 + (0,01 × 47)", "1,12"]
]

C3_16_TITULO = "Cuadro 3.16 Estimación del esfuerzo de desarrollo según benchmark ISBSG (2010)"
C3_16_HDR = ["Parámetro de Estimación", "Fórmula / Base de Referencia", "Valor Aplicado", "Resultado Obtenido"]
C3_16_DATA = [
    ["Puntos de Función no ajustados (UFP)", "Conteo acumulado Sprint 1 al 6", "305 PF", "305,00 PF"],
    ["Factor de Ajuste de Valor (VAF)", "CGS = 47 puntos", "1,12", "1,12"],
    ["Puntos de Función Ajustados (AFP)", "AFP = UFP × VAF", "305 × 1,12", "341,60 PF"],
    ["Ratio de productividad (PDR)", "Benchmark ISBSG (2010) para BI y analítica", "7,4 h/PF", "7,4 horas / PF"],
    ["Esfuerzo total de desarrollo", "Esfuerzo = AFP × PDR", "341,60 PF × 7,4 h/PF", "2.527,84 horas"]
]

C3_17_TITULO = "Cuadro 3.17 Estructura de tarifas y costo horario del personal de desarrollo"
C3_17_HDR = ["Rol Profesional", "Fuente Salarial de Referencia", "Salario Mensual (Bs)", "Jornada Laboral (h/mes)", "Costo por Hora (Bs/h)"]
C3_17_DATA = [
    ["Ingeniero de Datos / Desarrollador BI", "TalentUp Bolivia (2026) - Nivel Mid/Senior", "9.475,00", "160", "59,22*"]
]
C3_17_NOTA = "* Tarifa horaria exacta: 9.475 / 160 = 59,21875 Bs/h; redondeada formalmente a 59,22 Bs/h."

C3_18_TITULO = "Cuadro 3.18 Presupuesto de desarrollo del software analítico"
C3_18_HDR = ["Concepto de Desarrollo", "Esfuerzo Asignado (Horas)", "Tarifa Horaria (Bs/h)", "Costo Total (Bs)"]
C3_18_DATA = [
    ["Desarrollo de módulos de software (Sprint 1 a 6)", "2.527,84", "59,22", "149.698,68*"]
]
C3_18_NOTA = "* Nota de redondeo: El producto de 2.527,84 h × 59,22 Bs/h equivale exactamente a 149.698,68 Bs (frente a 149.695,52 Bs si se emplea la tasa no redondeada de 59,21875 Bs/h, existiendo una diferencia de +3,16 Bs)."

C3_19_TITULO = "Cuadro 3.19 Presupuesto de implementación y puesta en marcha"
C3_19_HDR = ["Actividad de Implementación", "Volumen / Duración", "Tarifa de Referencia", "Costo Total (Bs)"]
C3_19_DATA = [
    ["Migración y resolución inicial HITL de stock en staging", "1.606 casos (1,80 h estimadas)", "59,22 Bs/h", "106,60"],
    ["Capacitación técnica a usuarios clave y auditores", "4,00 horas de instrucción", "59,22 Bs/h", "236,88"],
    ["TOTAL IMPLEMENTACIÓN Y PUESTA EN MARCHA", "Puesta en producción y entrega", "Suma de partidas", "343,48"]
]

C3_20_TITULO = "Cuadro 3.20 Presupuesto consolidado de inversión inicial del proyecto"
C3_20_HDR = ["Componente del Presupuesto", "Partida de Origen", "Monto Invertido (Bs)", "Participación (%)"]
C3_20_DATA = [
    ["Costo de desarrollo de software", "Cuadro 3.18 (2.527,84 horas)", "149.698,68", "99,77 %"],
    ["Costo de implementación y capacitación", "Cuadro 3.19 (Migración + 4 h instrucción)", "343,48", "0,23 %"],
    ["INVERSIÓN TOTAL DEL PROYECTO", "Costo total de adquisición de mercado", "150.042,16", "100,00 %"]
]

C3_21_TITULO = "Cuadro 3.21 Costos operacionales recurrentes y mantenimiento (Infraestructura y hosting)"
C3_21_HDR = ["Rubro de Operación", "Servicio y Capacidad Asignada", "Costo Mensual (Bs)", "Costo Anual (Bs)"]
C3_21_DATA = [
    ["Servidor Cloud VPS / Hosting de Contenedores", "Instancia virtual 4 vCPU, 16 GB RAM, 100 GB SSD", "348,00", "4.176,00"],
    ["Almacenamiento de respaldos y logs (GCS / S3)", "Bucket cifrado con retención de 30 días (50 GB)", "34,80", "417,60"],
    ["Licencias de soporte y dominios SSL", "Certificados SSL, dominio corporativo y telemetría", "90,96", "1.091,52"],
    ["TOTAL OPERACIÓN Y MANTENIMIENTO", "Costo recurrente de operación del sistema", "473,76", "5.685,12"]
]

# Cuadros del Apéndice I: Estructura de Puntos de Función
CI_1_TITULO = "Cuadro I.1 Estimación detallada de funciones de datos (ILF y EIF) por Historia de Usuario"
CI_1_HDR = ["HU / Identificador", "Entidad / Componente de Datos", "Tipo (ILF / EIF)", "DET", "RET", "Complejidad", "Puntos de Función (PF)"]
CI_1_DATA = [
    ["HU-01", "Catálogo de Programas y Módulos", "ILF", "N/D*", "N/D*", "Baja", "7"],
    ["HU-02", "Catálogo de Docentes e Instituciones", "ILF", "N/D*", "N/D*", "Baja", "7"],
    ["HU-03", "Estructura Dimensional de Estudiantes", "ILF", "N/D*", "N/D*", "Media", "10"],
    ["HU-04", "Dimensión Temporal del Negocio", "ILF", "N/D*", "N/D*", "Baja", "7"],
    ["HU-05", "Hechos de Rendimiento Académico", "ILF", "N/D*", "N/D*", "Alta", "15"],
    ["HU-06", "Hechos de Situación Financiera", "ILF", "N/D*", "N/D*", "Alta", "15"],
    ["HU-07", "Hechos de Evaluación Docente y Metas", "ILF", "N/D*", "N/D*", "Media", "10"],
    ["HU-08", "Buffer de Staging y Entidades No Resueltas", "ILF", "N/D*", "N/D*", "Media", "10"],
    ["HU-09", "Tablas Maestras Externas de Catálogo (3NF)", "EIF", "N/D*", "N/D*", "Baja", "5"],
    ["HU-10", "Vistas del Cuadro de Mando Integral (CMI)", "ILF", "N/D*", "N/D*", "Media", "10"],
    ["TOTAL FUNCIONES DE DATOS", "Suma de funciones de datos ILF y EIF", "-", "-", "-", "-", "96 PF"]
]
CI_1_NOTA = "* Columnas DET y RET no parametrizadas atómicamente en el repositorio; se consignan como N/D preservando la complejidad y puntuación oficial."

CI_2_TITULO = "Cuadro I.2 Estimación detallada de funciones transaccionales (EI, EO y EQ) por Historia de Usuario"
CI_2_HDR = ["HU / Identificador", "Proceso Transaccional Implementado", "Tipo (EI / EO / EQ)", "DET", "FTR", "Complejidad", "Puntos de Función (PF)"]
CI_2_DATA = [
    ["HU-01", "Carga y validación multipart de hojas de cálculo", "EI", "N/D*", "N/D*", "Media", "4"],
    ["HU-02", "Inferencia NER y clasificación semántica BETO", "EI", "N/D*", "N/D*", "Alta", "6"],
    ["HU-03", "Normalización fonética y resolución difusa RapidFuzz", "EI", "N/D*", "N/D*", "Media", "4"],
    ["HU-04", "Resolución de llaves y carga atómica en DW", "EI", "N/D*", "N/D*", "Alta", "6"],
    ["HU-05", "Resolución interactiva en bandeja HITL agrupada", "EI", "N/D*", "N/D*", "Media", "4"],
    ["HU-06", "Consulta y filtrado de alertas tempranas", "EQ", "N/D*", "N/D*", "Media", "4"],
    ["HU-07", "Generación de proyecciones Holt-Winters amortiguado", "EO", "N/D*", "N/D*", "Alta", "7"],
    ["HU-08", "Cálculo econométrico de tendencia OLS", "EO", "N/D*", "N/D*", "Media", "5"],
    ["HU-09", "Cálculo dinámico de 11 KPI del CMI", "EO", "N/D*", "N/D*", "Alta", "7"],
    ["HU-10", "Autenticación segura JWT y control de acceso RBAC", "EI", "N/D*", "N/D*", "Baja", "3"],
    ["HU-11", "Exportación de reportes de calidad y logs", "EO", "N/D*", "N/D*", "Media", "5"],
    ["TOTAL TRANSACCIONALES", "Suma de funciones transaccionales (EI, EO, EQ)", "-", "-", "-", "-", "209 PF"]
]
CI_2_NOTA = "* Columnas DET y FTR no parametrizadas atómicamente en el repositorio; se consignan como N/D preservando la complejidad y puntuación oficial (Total 96 + 209 = 305 PF)."

CI_3_TITULO = "Cuadro I.3 Resumen general de la estimación de tamaño de software por Puntos de Función"
CI_3_HDR = ["Categoría de Función", "Puntos de Función (PF)", "Porcentaje de Participación (%)"]
CI_3_DATA = [
    ["Funciones de Datos (ILF y EIF)", "96", "31,48 %"],
    ["Funciones Transaccionales (EI, EO y EQ)", "209", "68,52 %"],
    ["TOTAL PUNTOS DE FUNCIÓN NO AJUSTADOS (UFP)", "305", "100,00 %"],
    ["Factor de Ajuste de Valor (VAF = 0,65 + 0,01 × 47)", "1,12", "-"],
    ["PUNTOS DE FUNCIÓN AJUSTADOS (AFP = 305 × 1,12)", "341,60", "-"],
    ["Esfuerzo total (341,60 PF × 7,4 h/PF)", "2.527,84 horas", "-"],
    ["Costo de desarrollo (2.527,84 h × 59,22 Bs/h)", "149.698,68 Bs", "-"]
]


# -----------------------------------------------------------------------------
# APÉNDICE F: DICCIONARIO DEL DATA WAREHOUSE (50 TABLAS + 9 VISTAS = 59 OBJETOS)
# APÉNDICE G: CATÁLOGO DE TABLAS DE giragroup_catalog_db (20 TABLAS)
# -----------------------------------------------------------------------------
APENDICE_F_TITULO = "Tabla F.1 Catálogo maestro de tablas y vistas del Data Warehouse (59 objetos)"
APENDICE_F_HDR = ["N.º", "Esquema", "Nombre del Objeto", "Tipo", "Filas en Snapshot", "Propósito Analítico / Transaccional"]
APENDICE_F_DATA = [
    ["1", "bi", "ref_kpi", "BASE TABLE", "22", "Catálogo maestro institucional de 22 KPI del Cuadro de Mando Integral"],
    ["2", "bi", "ref_perspectiva", "BASE TABLE", "4", "Las 4 perspectivas estratégicas del CMI institucional"],
    ["3", "bi", "vw_cartera_estado", "VIEW", "7", "Vista analítica de cartera clasificada por estado crediticio"],
    ["4", "bi", "vw_cmi_gestiones", "VIEW", "5", "Histórico de gestiones académicas consolidadas"],
    ["5", "bi", "vw_cmi_global", "VIEW", "5", "Indicadores de alto nivel por gestión anual"],
    ["6", "bi", "vw_cmi_perspectiva", "VIEW", "20", "Desempeño ponderado por perspectiva estratégica"],
    ["7", "bi", "vw_cmi_scorecard", "VIEW", "110", "Matriz consolidada del Cuadro de Mando Integral"],
    ["8", "bi", "vw_cmi_valores", "VIEW", "64", "Serie temporal de ejecuciones de KPI"],
    ["9", "bi", "vw_dataops_documento", "VIEW", "16", "Estado de procesamiento y trazabilidad por archivo fuente"],
    ["10", "bi", "vw_metas_mensual", "VIEW", "95", "Comparativo mensual de monto ejecutado vs presupuesto meta"],
    ["11", "bi", "vw_riesgo_estudiante", "VIEW", "6.602", "Clasificación de riesgo individual por estudiante"],
    ["12", "public", "fact_rendimiento_academico", "BASE TABLE", "22.618", "Hecho operativo: actas de calificaciones y rendimiento estudiantil"],
    ["13", "public", "fact_evaluacion_docente", "BASE TABLE", "14.234", "Hecho analítico: encuestas y evaluaciones estudiantiles de docentes"],
    ["14", "public", "fact_situacion_financiera", "BASE TABLE", "10.483", "Hecho operativo: cobranzas, planes de pago y cuotas en mora"],
    ["15", "public", "fact_marketing", "BASE TABLE", "8.946", "Hecho analítico: métricas de prospección, inscritos y demanda"],
    ["16", "public", "fact_costo_programa", "BASE TABLE", "1.371", "Hecho analítico: costos directos por módulo de posgrado"],
    ["17", "public", "fact_techo_convenio", "BASE TABLE", "206", "Hecho analítico: límites arancelarios de convenios interinstitucionales"],
    ["18", "public", "fact_rentabilidad", "BASE TABLE", "108", "Hecho estratégico: ingresos, egresos y metas presupuestarias"],
    ["19", "public", "fact_forecast", "BASE TABLE", "24", "Hecho predictivo: proyecciones mensuales de demanda persistidas"],
    ["20", "public", "fact_cobranzas_proyectadas", "BASE TABLE", "0", "Hecho analítico proyectado de recuperación de cartera"],
    ["21", "public", "dim_estudiante", "BASE TABLE", "14.078", "Dimensión conformada de estudiantes (13.667 CIs únicas)"],
    ["22", "public", "dim_modulo", "BASE TABLE", "3.585", "Dimensión conformada de asignaturas y módulos de posgrado"],
    ["23", "public", "dim_tiempo", "BASE TABLE", "2.230", "Dimensión temporal conformada diaria (2020 a 2026)"],
    ["24", "public", "bridge_modulo_docente", "BASE TABLE", "1.922", "Tabla puente asociativa de relación N:M módulo-docente"],
    ["25", "public", "dim_docente", "BASE TABLE", "638", "Dimensión conformada de docentes de posgrado"],
    ["26", "public", "dim_origen_documental", "BASE TABLE", "16", "Dimensión de trazabilidad y fuentes documentales cargadas"],
    ["27", "public", "dim_categoria_financiera", "BASE TABLE", "15", "Dimensión financiera de clasificación de ingresos y gastos"],
    ["28", "public", "dim_meta", "BASE TABLE", "0", "Estructura dimensional previa de metas (reemplazada por fact)"],
    ["29", "public", "cache_indice_beto", "BASE TABLE", "90.212", "Caché semántica local de inferencias del modelo BETO"],
    ["30", "public", "stg_entidad_no_resuelta", "BASE TABLE", "23.127", "Buffer de entidades retenidas en staging (1.044 activas en lote)"],
    ["31", "public", "carga_fila_origen", "BASE TABLE", "15.196", "Control de claves unívocas para idempotencia estricta"],
    ["32", "public", "log_pipeline_ingesta", "BASE TABLE", "2.544", "Bitácora transaccional de corridas del pipeline DataOps"],
    ["33", "public", "log_inconsistencias", "BASE TABLE", "1.528", "Bitácora de inconsistencias de datos y descarte de nombres"],
    ["34", "public", "log_auditoria_nlp", "BASE TABLE", "1.218", "Bitácora de inferencias y auditoría de decisiones del modelo BETO"],
    ["35", "public", "dataops_tarea", "BASE TABLE", "28", "Registro de tareas y lotes de procesamiento documental"],
    ["36", "public", "cat_origen_datos", "BASE TABLE", "17", "Catálogo local de tipos de repositorios fuente"],
    ["37", "public", "dim_origen_documental_backup", "BASE TABLE", "16", "Copia de resguardo de trazabilidad documental"],
    ["38", "public", "cat_entidad_tipo", "BASE TABLE", "10", "Catálogo de tipos de entidades reconocidas"],
    ["39", "public", "users", "BASE TABLE", "5", "Usuarios autenticados bajo el modelo de seguridad RBAC"],
    ["40", "public", "cat_categoria_financiera", "BASE TABLE", "5", "Catálogo de categorías contables en esquema DW"],
    ["41", "public", "cat_estado_proceso", "BASE TABLE", "5", "Estados de avance del procesamiento ETL"],
    ["42", "public", "cat_institucion", "BASE TABLE", "4", "Universidades e instituciones en convenio nacional"],
    ["43", "public", "cat_programa", "BASE TABLE", "4", "Programas canónicos homologados en DW"],
    ["44", "public", "notifications", "BASE TABLE", "3", "Registro de notificaciones de alertas y auditoría"],
    ["45", "public", "schema_migrations", "BASE TABLE", "1", "Historial de migraciones DDL de PostgreSQL"],
    ["46", "public", "lote", "BASE TABLE", "0", "Estructura de lotes previa (reemplazada por dataops_tarea)"],
    ["47", "public", "ref_metas_gestion", "BASE TABLE", "0", "Metas de gestión previas (consolidadas en fact_rentabilidad)"],
    ["48", "public", "staging_registros_crudos", "BASE TABLE", "0", "Buffer de staging crudo sin normalizar"],
    ["49", "public", "cat_combinacion_estado", "BASE TABLE", "0", "Catálogo auxiliar de combinación de estados"],
    ["50", "public", "cat_concepto_financiero", "BASE TABLE", "0", "Catálogo auxiliar de conceptos arancelarios"],
    ["51", "public", "cat_escuela", "BASE TABLE", "0", "Catálogo auxiliar de escuelas de posgrado"],
    ["52", "public", "cat_estado_academico", "BASE TABLE", "0", "Catálogo auxiliar de estados del alumno"],
    ["53", "public", "cat_estado_arca", "BASE TABLE", "0", "Catálogo auxiliar de estados del sistema ARCA"],
    ["54", "public", "cat_estado_reprobado", "BASE TABLE", "0", "Catálogo auxiliar de tipologías de reprobación"],
    ["55", "public", "cat_etiqueta_clasificacion", "BASE TABLE", "0", "Catálogo auxiliar de etiquetas semánticas"],
    ["56", "public", "cat_guia_texto_plano", "BASE TABLE", "0", "Catálogo auxiliar de plantillas regex"],
    ["57", "public", "cat_historico_equivalencia", "BASE TABLE", "0", "Catálogo auxiliar de equivalencias de programas"],
    ["58", "public", "cat_institucion_convenio", "BASE TABLE", "0", "Catálogo auxiliar de instituciones aliadas"],
    ["59", "public", "cat_mapeo_columna", "BASE TABLE", "0", "Catálogo auxiliar de sinónimos de encabezados"]
]

APENDICE_CAT_TITULO = "Tabla G.1 Catálogo de tablas maestras de la base de datos de catálogo (giragroup_catalog_db)"
APENDICE_CAT_HDR = ["N.º", "Nombre de la Tabla", "Tipo", "Filas en Snapshot", "Propósito Funcional en la Arquitectura"]
APENDICE_CAT_DATA = [
    ["1", "cat_modulo", "BASE TABLE", "1.747", "Catálogo canónico estandarizado de materias y módulos de posgrado"],
    ["2", "cat_programa", "BASE TABLE", "1.229", "Catálogo maestro de oferta académica de diplomados y maestrías"],
    ["3", "cat_convenio_programa", "BASE TABLE", "195", "Relación de convenios interinstitucionales por programa"],
    ["4", "cat_mapeo_columna", "BASE TABLE", "159", "Diccionario semántico de sinónimos para encabezados heterogéneos"],
    ["5", "cat_historico_equivalencia", "BASE TABLE", "67", "Matriz de equivalencias históricas entre versiones de programas"],
    ["6", "cat_etiqueta_clasificacion", "BASE TABLE", "66", "Etiquetas semánticas para entrenamiento de BETO y reglas"],
    ["7", "ref_metas_gestion", "BASE TABLE", "59", "Histórico de metas financieras y de matrícula presupuestadas"],
    ["8", "cat_institucion_convenio", "BASE TABLE", "22", "Catálogo de universidades e instituciones con convenio formal"],
    ["9", "cat_combinacion_estado", "BASE TABLE", "16", "Matriz de homologación de estados académicos y financieros"],
    ["10", "cat_concepto_financiero", "BASE TABLE", "16", "Conceptos arancelarios (matrícula, colegiatura, titulación)"],
    ["11", "cat_guia_texto_plano", "BASE TABLE", "6", "Plantillas de expresiones regulares y layout por tipo de archivo"],
    ["12", "cat_tipo_programa", "BASE TABLE", "6", "Tipologías de formación (Diplomado, Maestría, Especialidad)"],
    ["13", "cat_escuela", "BASE TABLE", "5", "Escuelas académicas de posgrado"],
    ["14", "cat_estado_academico", "BASE TABLE", "5", "Estados de cursado del estudiante (regular, baja, egresado)"],
    ["15", "cat_tipo_cartera", "BASE TABLE", "5", "Clasificación crediticia y riesgo de cartera"],
    ["16", "cat_modalidad", "BASE TABLE", "3", "Modalidades de enseñanza (virtual, presencial, semipresencial)"],
    ["17", "cat_categoria_financiera", "BASE TABLE", "2", "Categorías maestras contables (ingresos y egresos)"],
    ["18", "cat_estado_arca", "BASE TABLE", "2", "Estados homologados del sistema académico ARCA"],
    ["19", "cat_estado_reprobado", "BASE TABLE", "7", "Causales de reprobación (abandono, nota, inasistencia)"],
    ["20", "stg_entidad_no_resuelta", "BASE TABLE", "0", "Buffer transaccional de soporte en base de catálogo"]
]

PARRAFO_ALERTAS = (
    "En la evaluación sobre el universo de matrícula activa del Data Warehouse (N = 9.603 estudiantes analizados), "
    "el motor de alertas tempranas determinísticas identificó a 1.224 estudiantes con riesgo académico (promedio acumulado "
    "de calificaciones ≤ 70 puntos), 1.765 estudiantes con riesgo financiero (dos o más cuotas impagas o cartera previsionable, "
    "acumulando un saldo adeudado de 867.811,89 Bs), y 0 alertas de deserción por inasistencia, debido a que la métrica de "
    "incumplimiento de actividades virtuales registra 0,00 % en el corpus histórico de origen. Del total observado, 238 estudiantes "
    "se encuentran en prioridad crítica por presentar de manera simultánea dos o más condiciones de riesgo, alcanzando un total "
    "consolidado de 2.751 estudiantes únicos con al menos una alerta activa en el sistema."
)


# =============================================================================
# Generación de archivo Markdown
# =============================================================================
def tabla_to_markdown(titulo, headers, rows, nota=None):
    md = []
    md.append(f"### {titulo}\n")
    md.append("| " + " | ".join(headers) + " |")
    md.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for r in rows:
        md.append("| " + " | ".join([str(c) for c in r]) + " |")
    md.append(f"\n*{PIE_OFICIAL}*\n")
    if nota:
        md.append(f"> [!NOTE]\n> {nota}\n")
    md.append("\n---\n")
    return "\n".join(md)

def generar_markdown():
    with open(MD_PATH, "w", encoding="utf-8") as f:
        f.write("# COMPENDIO OFICIAL DE TABLAS Y CUADROS DE LA TESIS\n")
        f.write("**Sistema de Inteligencia de Negocios para GiraGroup S.R.L.**  \n")
        f.write("**Fuente de Verdad:** `snapshot_dw_20261110_1201`  \n\n")
        f.write("---\n\n")
        
        f.write("## 1. TABLAS DEL CAPÍTULO III: MARCO METODOLÓGICO Y DESARROLLO\n\n")
        f.write(tabla_to_markdown(T3_4_TITULO, T3_4_HDR, T3_4_DATA, T3_4_NOTA))
        f.write(tabla_to_markdown(T3_19_TITULO, T3_19_HDR, T3_19_DATA))
        f.write(tabla_to_markdown(T3_20_TITULO, T3_20_HDR_REAL, T3_20_DATA, T3_20_NOTA))
        f.write(tabla_to_markdown(T3_24_TITULO, T3_24_HDR, T3_24_DATA, T3_24_NOTA))
        f.write(tabla_to_markdown(T3_27_TITULO, T3_27_HDR, T3_27_DATA, T3_27_NOTA))
        f.write(tabla_to_markdown(T3_29_TITULO, T3_29_HDR, T3_29_DATA, T3_29_NOTA))
        f.write(tabla_to_markdown(T3_30_TITULO, T3_30_HDR, T3_30_DATA))
        f.write(tabla_to_markdown(T3_34_TITULO, T3_34_HDR, T3_34_DATA))
        f.write(tabla_to_markdown(T3_36_TITULO, T3_36_HDR, T3_36_DATA))
        f.write(tabla_to_markdown(T3_37_TITULO, T3_37_HDR, T3_37_DATA))
        
        f.write("## 2. TABLAS DEL CAPÍTULO IV: PRESENTACIÓN Y ANÁLISIS DE RESULTADOS\n\n")
        f.write(tabla_to_markdown(T4_1_TITULO, T4_1_HDR, T4_1_DATA))
        f.write(tabla_to_markdown(T4_3_TITULO, T4_3_HDR, T4_3_DATA, T4_3_NOTA))
        f.write(tabla_to_markdown(T4_5_TITULO, T4_5_HDR, T4_5_DATA, T4_5_NOTA))
        f.write(tabla_to_markdown(T4_6_TITULO, T4_6_HDR, T4_6_DATA, T4_6_NOTA))
        f.write(tabla_to_markdown(T4_7_TITULO, T4_7_HDR, T4_7_DATA))
        f.write(tabla_to_markdown(T4_8_TITULO, T4_8_HDR, T4_8_DATA))
        
        f.write("### Resultados del Motor de Alertas Tempranas (Cap. IV)\n\n")
        f.write(PARRAFO_ALERTAS + "\n\n")
        f.write(f"*{PIE_OFICIAL}*\n\n---\n\n")
        
        f.write("## 3. CUADROS DE COSTOS (SECCIÓN 3.5 Y APÉNDICE I)\n\n")
        f.write(tabla_to_markdown(C3_14_TITULO, C3_14_HDR, C3_14_DATA, C3_14_NOTA))
        f.write(tabla_to_markdown(C3_15_TITULO, C3_15_HDR, C3_15_DATA))
        f.write(tabla_to_markdown(C3_16_TITULO, C3_16_HDR, C3_16_DATA))
        f.write(tabla_to_markdown(C3_17_TITULO, C3_17_HDR, C3_17_DATA, C3_17_NOTA))
        f.write(tabla_to_markdown(C3_18_TITULO, C3_18_HDR, C3_18_DATA, C3_18_NOTA))
        f.write(tabla_to_markdown(C3_19_TITULO, C3_19_HDR, C3_19_DATA))
        f.write(tabla_to_markdown(C3_20_TITULO, C3_20_HDR, C3_20_DATA))
        f.write(tabla_to_markdown(C3_21_TITULO, C3_21_HDR, C3_21_DATA))
        f.write(tabla_to_markdown(CI_1_TITULO, CI_1_HDR, CI_1_DATA, CI_1_NOTA))
        f.write(tabla_to_markdown(CI_2_TITULO, CI_2_HDR, CI_2_DATA, CI_2_NOTA))
        f.write(tabla_to_markdown(CI_3_TITULO, CI_3_HDR, CI_3_DATA))
        
        f.write("## 4. APÉNDICES DE DICCIONARIO DE DATOS Y CATÁLOGO\n\n")
        f.write(tabla_to_markdown(APENDICE_F_TITULO, APENDICE_F_HDR, APENDICE_F_DATA))
        f.write(tabla_to_markdown(APENDICE_CAT_TITULO, APENDICE_CAT_HDR, APENDICE_CAT_DATA))
        
    print(f"[OK] Generado documento Markdown: {MD_PATH}")


# =============================================================================
# Generación de archivo Word (DOCX)
# =============================================================================
def generar_docx():
    doc = docx.Document()
    
    # Configurar márgenes estándar 2.5 cm (1 pulgada)
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)
        
    # Título principal
    p_main = doc.add_paragraph()
    p_main.paragraph_format.space_before = Pt(0)
    p_main.paragraph_format.space_after = Pt(4)
    run_main = p_main.add_run("COMPENDIO DE TABLAS Y CUADROS OFICIALES DE LA TESIS")
    run_main.font.name = 'Times New Roman'
    run_main.font.size = Pt(13)
    run_main.font.bold = True
    
    p_sub = doc.add_paragraph()
    p_sub.paragraph_format.space_before = Pt(0)
    p_sub.paragraph_format.space_after = Pt(14)
    run_sub = p_sub.add_run("Sistema de Inteligencia de Negocios para GiraGroup S.R.L. | Snapshot snapshot_dw_20261110_1201")
    run_sub.font.name = 'Times New Roman'
    run_sub.font.size = Pt(10)
    run_sub.font.italic = True

    # 1. Capítulo III
    agregar_tabla_docx(doc, T3_4_TITULO, T3_4_HDR, T3_4_DATA, nota_pie=T3_4_NOTA)
    agregar_tabla_docx(doc, T3_19_TITULO, T3_19_HDR, T3_19_DATA)
    agregar_tabla_docx(doc, T3_20_TITULO, T3_20_HDR_REAL, T3_20_DATA, nota_pie=T3_20_NOTA)
    agregar_tabla_docx(doc, T3_24_TITULO, T3_24_HDR, T3_24_DATA, nota_pie=T3_24_NOTA)
    agregar_tabla_docx(doc, T3_27_TITULO, T3_27_HDR, T3_27_DATA, nota_pie=T3_27_NOTA)
    agregar_tabla_docx(doc, T3_29_TITULO, T3_29_HDR, T3_29_DATA, nota_pie=T3_29_NOTA)
    agregar_tabla_docx(doc, T3_30_TITULO, T3_30_HDR, T3_30_DATA)
    agregar_tabla_docx(doc, T3_34_TITULO, T3_34_HDR, T3_34_DATA)
    agregar_tabla_docx(doc, T3_36_TITULO, T3_36_HDR, T3_36_DATA)
    agregar_tabla_docx(doc, T3_37_TITULO, T3_37_HDR, T3_37_DATA)

    # 2. Capítulo IV
    agregar_tabla_docx(doc, T4_1_TITULO, T4_1_HDR, T4_1_DATA)
    agregar_tabla_docx(doc, T4_3_TITULO, T4_3_HDR, T4_3_DATA, nota_pie=T4_3_NOTA)
    agregar_tabla_docx(doc, T4_5_TITULO, T4_5_HDR, T4_5_DATA, nota_pie=T4_5_NOTA)
    agregar_tabla_docx(doc, T4_6_TITULO, T4_6_HDR, T4_6_DATA, nota_pie=T4_6_NOTA)
    agregar_tabla_docx(doc, T4_7_TITULO, T4_7_HDR, T4_7_DATA)
    agregar_tabla_docx(doc, T4_8_TITULO, T4_8_HDR, T4_8_DATA)

    # Párrafo de alertas
    p_al_tit = doc.add_paragraph()
    p_al_tit.paragraph_format.space_before = Pt(12)
    p_al_tit.paragraph_format.space_after = Pt(4)
    run_altit = p_al_tit.add_run("Resultados del Motor de Alertas Tempranas (Cap. IV)")
    run_altit.font.name = 'Times New Roman'
    run_altit.font.size = Pt(10)
    run_altit.font.bold = True
    
    p_al = doc.add_paragraph()
    p_al.paragraph_format.space_before = Pt(2)
    p_al.paragraph_format.space_after = Pt(4)
    p_al.paragraph_format.line_spacing = 1.15
    run_al = p_al.add_run(PARRAFO_ALERTAS)
    run_al.font.name = 'Times New Roman'
    run_al.font.size = Pt(10)
    
    p_al_pie = doc.add_paragraph()
    p_al_pie.paragraph_format.space_before = Pt(2)
    p_al_pie.paragraph_format.space_after = Pt(12)
    run_alpie = p_al_pie.add_run(PIE_OFICIAL)
    run_alpie.font.name = 'Times New Roman'
    run_alpie.font.size = Pt(8.5)
    run_alpie.font.italic = True

    # 3. Cuadros de Costos
    agregar_tabla_docx(doc, C3_14_TITULO, C3_14_HDR, C3_14_DATA, nota_pie=C3_14_NOTA)
    agregar_tabla_docx(doc, C3_15_TITULO, C3_15_HDR, C3_15_DATA)
    agregar_tabla_docx(doc, C3_16_TITULO, C3_16_HDR, C3_16_DATA)
    agregar_tabla_docx(doc, C3_17_TITULO, C3_17_HDR, C3_17_DATA, nota_pie=C3_17_NOTA)
    agregar_tabla_docx(doc, C3_18_TITULO, C3_18_HDR, C3_18_DATA, nota_pie=C3_18_NOTA)
    agregar_tabla_docx(doc, C3_19_TITULO, C3_19_HDR, C3_19_DATA)
    agregar_tabla_docx(doc, C3_20_TITULO, C3_20_HDR, C3_20_DATA)
    agregar_tabla_docx(doc, C3_21_TITULO, C3_21_HDR, C3_21_DATA)
    agregar_tabla_docx(doc, CI_1_TITULO, CI_1_HDR, CI_1_DATA, nota_pie=CI_1_NOTA)
    agregar_tabla_docx(doc, CI_2_TITULO, CI_2_HDR, CI_2_DATA, nota_pie=CI_2_NOTA)
    agregar_tabla_docx(doc, CI_3_TITULO, CI_3_HDR, CI_3_DATA)

    # 4. Apéndices
    agregar_tabla_docx(doc, APENDICE_F_TITULO, APENDICE_F_HDR, APENDICE_F_DATA)
    agregar_tabla_docx(doc, APENDICE_CAT_TITULO, APENDICE_CAT_HDR, APENDICE_CAT_DATA)

    doc.save(DOCX_PATH)
    print(f"[OK] Generado documento Word: {DOCX_PATH}")


# =============================================================================
# Generación de manifiesto CSV
# =============================================================================
def generar_manifiesto():
    items = [
        ["Tabla 3.4", "docs/tablas_v2.docx", "D-01, Tabla 3.34", "Sprint 6: 382 pruebas (493 tras estabilización)", "scripts/generar_tablas_tesis_v2.py"],
        ["Tabla 3.19", "docs/tablas_v2.docx", "SFV C.1", "5 umbrales: 0,92 personas (person_resolver.py:27); 90 % homónimos (dw_loader.py:1020); 85 % variante CI (fuzzy_normalizer.py:88); 85 % docentes; 80 % módulos", "scripts/generar_tablas_tesis_v2.py"],
        ["Tabla 3.20", "docs/tablas_v2.docx", "C-01 a C-08", "Ablación Modo A / B / C en gold_510 (510 ent.) y layouts_5 (72 ent.): F1 estricto A 100 %, B 100 %, C 97,57 %; F1 relajado layouts_5 A 28,57 %, B 71,64 %, C 69,23 %", "scripts/generar_tablas_tesis_v2.py"],
        ["Tabla 3.24", "docs/tablas_v2.docx", "E-01 a E-14, Detalle E.1", "HW 27m (RMSE 45,00, MAPE 13,89 %); HW 33m (RMSE 48,36, AIC 290,00, IC ±94,79); Naive (MAPE 10,32 %); OLS mensual matrícula (+3,6541, R² 0,1921); Proy. jun-nov 2026: 426,37 a 461,97", "scripts/generar_tablas_tesis_v2.py"],
        ["Tabla 3.27", "docs/tablas_v2.docx", "Tabla F.1, Tabla F.2, Detalle F.1, Detalle F.3", "11 KPI del CMI: metas desde fact_rentabilidad.monto_meta; KPI-06 N/D; nota 11 de 22 KPI catalogados en bi.ref_kpi", "scripts/generar_tablas_tesis_v2.py"],
        ["Tabla 3.29", "docs/tablas_v2.docx", "D-01 a D-06", "Transversales 254 · sprint3 120 · sprint2 32 · sprint4 + loops 32 · sprint1 16 · readiness 39 (21/11/7) · TOTAL 493 / 475 / 60,7 % (8.062 de 13.278)", "scripts/generar_tablas_tesis_v2.py"],
        ["Tabla 3.30", "docs/tablas_v2.docx", "Tabla D.2, S-17", "22 módulos + TOTAL (13.278 stmts / 5.216 miss / 8.062 cover / 60,7 %); ner_engine.py 301 stmts, 64,1 %; dataops.py 2.176 stmts, 43,3 %", "scripts/generar_tablas_tesis_v2.py"],
        ["Tabla 3.34", "docs/tablas_v2.docx", "A-26, B-06, D-01, ciclo_r8_resumen.json", "Tiempo máquina 60,0 s (DE 0,8); BETO 5,4 s; carga DW 44,0 s; KLM 490,5 s (188 casos/37 grupos); 493 pruebas (475/11/7/0); staging 1.044", "scripts/generar_tablas_tesis_v2.py"],
        ["Tabla 3.36", "docs/tablas_v2.docx", "A.1, D.1, E.1, G.1, G.2", "Obj. 1 a 6: Lote 97,55 / 2,45 / 0,00 sobre 1.387; 50 tablas + 9 vistas; 493 pruebas; MAPE 13,89 % frente a naive 10,32 %; 128 rutas API", "scripts/generar_tablas_tesis_v2.py"],
        ["Tabla 3.37", "docs/tablas_v2.docx", "Trazabilidad RF/RNF", "11 RF (RF-01 a RF-11) y 7 RNF (RNF-01 a RNF-07) mapeados a endpoints, pruebas unitarias/integración y evidencias", "scripts/generar_tablas_tesis_v2.py"],
        ["Tabla 4.1", "docs/tablas_v2.docx", "A-02, B-01, B-02, D-02, D-08, E-09, E-12", "Fila 3 MAPE 13,89 % (naive 10,32 %); Fila 5 600,0 -> 9,2 min (Δ −590,8); Fila 6a 1.353 (97,55 %); Fila 6b 100 % (1.387); Fila 7 0 de 268 / 0 de 562", "scripts/generar_tablas_tesis_v2.py"],
        ["Tabla 4.3", "docs/tablas_v2.docx", "A-17, A-18, A-19, B-01, B-02", "Excepciones 562 entidades en 268 registros (0 al DW sin control); Staging 1.044 entidades en 786 grupos (756 CI / 288 IA); Nota 5 repositorios/fuentes", "scripts/generar_tablas_tesis_v2.py"],
        ["Tabla 4.5", "docs/tablas_v2.docx", "A.1, C-01, C-05", "Balance 7 archivos (ARCA 448/2, Cobranzas 349/1, Inscritos 248/2, Eval. Docente 137/13, Exp. Docente 95/15, Egresos 53/0, Metas 23/1) + Motor C 97,57 %, B 100 %, B 71,64 % vs A 28,57 %", "scripts/generar_tablas_tesis_v2.py"],
        ["Tabla 4.6", "docs/tablas_v2.docx", "Tabla F.1, Tabla F.2, Detalle F.3", "11 KPI 2025: Ticket 1.610,13 Bs; Cumplimiento 157,48 %; Acumulado 110,54 %; Riesgo fin. 623; Mora 18,36 %; KPI-06 N/D; Nota 79,02 pts; Aprobación 85,61 %; Riesgo acad. 588; Confianza 0,9269; Directo 90,10 %", "scripts/generar_tablas_tesis_v2.py"],
        ["Tabla 4.7", "docs/tablas_v2.docx", "E-09, E-12, E-15, E-16", "HW (13,89 %), naive (10,32 %), OLS mensual (+16.212,88 Bs/mes), OLS anual DW (+2.267.633,83 Bs/año; R² 0,9937; 2023 8,03M · 2024 9,98M · 2025 12,57M Bs, N = 3 descriptivo)", "scripts/generar_tablas_tesis_v2.py"],
        ["Tabla 4.8", "docs/tablas_v2.docx", "A-02, B-02, Regla r8/KLM", "Resumen pre/post: Vinculación 0 % -> 97,55 %; Tiempo 600,0 -> 9,2 min (Δ −590,8 min); Excepciones sin control 0 de 562", "scripts/generar_tablas_tesis_v2.py"],
        ["Cuadros 3.14-3.21 / I.1-I.3", "docs/tablas_v2.docx", "C3.14 a C3.21, TalentUp 2026, ISBSG 2010", "PF sin ajustar 305; CGS 47 -> VAF 1,12 -> 341,60 PF; ISBSG 7,4 h/PF -> 2.527,84 h; TalentUp 59,22 Bs/h -> Desarrollo 149.698,68 Bs; Impl. 343,48 Bs; Total 150.042,16 Bs; Operación 473,76 Bs/mes", "scripts/generar_tablas_tesis_v2.py"],
        ["Apéndice F", "docs/tablas_v2.docx", "Tabla G.2", "Diccionario Data Warehouse: 50 tablas base + 9 vistas (59 objetos totales) con esquema, filas en snapshot y propósito", "scripts/generar_tablas_tesis_v2.py"],
        ["Apéndice Catálogo", "docs/tablas_v2.docx", "Tabla G.3", "Catálogo giragroup_catalog_db: 20 tablas base con filas en snapshot y propósito funcional", "scripts/generar_tablas_tesis_v2.py"]
    ]
    
    with open(MANIFEST_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id_documento", "archivo", "ids_SFV_usados", "valores_mostrados", "script"])
        for item in items:
            writer.writerow(item)
            
    print(f"[OK] Generado manifiesto de evidencias: {MANIFEST_PATH}")


def main():
    print("Iniciando compilación oficial de tablas y cuadros de la tesis...")
    generar_markdown()
    generar_docx()
    generar_manifiesto()
    print("\n¡Proceso finalizado con éxito! Documentos y manifiesto listos.")


if __name__ == '__main__':
    main()
