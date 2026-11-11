# -*- coding: utf-8 -*-
"""
Generador del documento fuente_verdad_tesis.md
Única Fuente de Verdad para la Tesis de Grado GiraGroup BI
Basado en snapshot_dw_20261110_1201
"""

content = """# ÚNICA FUENTE DE VERDAD (SFV) - PROYECTO DE GRADO GIRAGROUP BI
**Sistema de Inteligencia de Negocios basado en BETO y Cuadro de Mando Integral para mitigar la fragmentación informacional en GiraGroup S.R.L.**  
**Autor:** Lean (Adriano Daza)  
**Fecha de Congelamiento:** 10 de noviembre de 2026, 12:02:15 -04:00  
**Snapshot ID:** `snapshot_dw_20261110_1201`  
**Archivo de Respaldo Físico:** `docs/evidencias/snapshot_dw_20261110_1201.dump`  
**Hash SHA-256 del Snapshot:** `14D45F5A128F44543927911DC0AD453F681D524AC05037203F5C0C2787E3A2EB`  
**Cadena de Conexión Snapshot DW:** `postgresql://giragroup_user:giragroup_secret_2026@localhost:5434/snapshot_dw_20261110_1201`  
**Cadena de Conexión Catálogo:** `postgresql://giragroup_user:giragroup_secret_2026@localhost:5433/giragroup_catalog_db`  

---

## INTRODUCCIÓN Y REGLAS DE CONCILIACIÓN
El presente documento constituye la **Única Fuente de Verdad (Single Source of Truth)** para la redacción final del Proyecto de Grado, reconciliando y sustituyendo de forma vinculante cualquier discrepancia numérica encontrada entre los borradores previos de los Capítulos I, III, IV y V (texto narrativo, tablas, cuadros de especificación técnica, esquemas y gráficos estadísticos).

Todas las cifras reportadas provienen estrictamente de la ejecución en una única corrida sobre la copia congelada e inmutable de la base de datos analítica (`snapshot_dw_20261110_1201`). Se emplea de manera uniforme el estándar numérico oficial de Bolivia: coma (`,`) como separador decimal y punto (`.`) como separador de miles. Ninguna cifra ha sido estimada ni alterada; en los casos donde un registro o dimensión no se genera en el estado actual del sistema, se consigna formalmente como **N/D** indicando su fundamento técnico.

---

## A. LOTE DE CARGA Y VINCULACIÓN
El lote de validación de producción se compone de **1.387 registros procesados**, consolidados a partir de los 7 archivos primarios de producción ubicados en `uploads/data/`. La arquitectura en ejecución (Modo B Híbrido: Encabezados + Reglas Determinísticas + RapidFuzz + Modelo BETO) resolvió **1.353 registros de manera directa** (97,55 %), derivó **34 registros a revisión humana HITL** (2,45 %) y **0 registros a Staging directo** (0,00 %).

### Tabla A.1: Métricas Consolidadas del Lote de Carga y Vinculación
| ID | Métrica | Valor | Ref. ronda 10 | ¿Coincide? | Fuente (SQL/comando/log) | Dónde va en el documento |
|---|---|---|---|---|---|---|
| A-01 | Total de registros evaluados en el lote | 1.387 | 1.387 | Sí | `docs/evidencias/lote_1387_uploads_data_arquitectura_b.json` | Cap. IV, Sec. 4.3; Tabla 4.1; Cuadro 3.8 |
| A-02 | Registros vinculados directos (Banda ≥ 0,85) | 1.353 (97,55 %) | 1.353 (97,55 %) | Sí | `SELECT count(*) FROM fact_rendimiento_academico WHERE carga_lote = 'lote_1387'` / Log de ejecución | Cap. III, Sec. 3.4; Cap. IV, Sec. 4.3; Gráfico 3.2; Gráfico 4.2 |
| A-03 | Registros derivados a HITL (Banda 0,60–0,85) | 34 (2,45 %) | 34 (2,45 %) | Sí | `lote_1387_uploads_data_arquitectura_b.json:distribucion_bandas_con_regla_personas` | Cap. III, Sec. 3.4; Cap. IV, Sec. 4.3; Gráfico 3.2; Gráfico 4.2 |
| A-04 | Registros rechazados a Staging (Banda < 0,60) | 0 (0,00 %) | 0 (0,00 %) | Sí | `lote_1387_uploads_data_arquitectura_b.json:distribucion_bandas_con_regla_personas` | Cap. III, Sec. 3.4; Cap. IV, Sec. 4.3; Gráfico 3.2; Gráfico 4.2 |
| A-05 | Tasa de vinculación automática final | 97,55 % | 97,55 % | Sí | `1.353 / 1.387 * 100` | Cap. I, Planteamiento; Cap. IV, Discusión |
| A-06 | Tasa de derivación a revisión humana (HITL) | 2,45 % | 2,45 % | Sí | `34 / 1.387 * 100` | Cap. I, Planteamiento; Cap. IV, Discusión |
| A-07 | Personas evaluadas en el lote (Total entidades) | 1.658 | 1.658 | Sí | `lote_1387_uploads_data_arquitectura_b.json:personas` | Cap. IV, Sec. 4.3.2 |
| A-08 | Distribución fk_estado A (CI exacta confirmada) | 1.021 (61,58 %) | 1.021 (61,58 %) | Sí | `personas_por_fk_estado.estudiante.A` | Cap. III, Sec. 3.3.4; Cap. IV, Tabla 4.2 |
| A-09 | Distribución fk_estado B (Fuzzy/rescate sin CI) | 134 (8,08 %) | 134 (8,08 %) | Sí | `personas_por_fk_estado.estudiante.B` | Cap. III, Sec. 3.3.4; Cap. IV, Tabla 4.2 |
| A-10 | Distribución fk_estado C (Docentes nuevos/TEMP) | 498 (30,04 %) | 498 (30,04 %) | Sí | `personas_por_fk_estado.docente.C` | Cap. III, Sec. 3.3.4; Cap. IV, Tabla 4.2 |
| A-11 | Personas sin coincidencia derivadas a HITL | 5 (0,30 %) | 5 (0,30 %) | Sí | `personas.sin_coincidencia_HITL` | Cap. IV, Sec. 4.3.2 |
| A-12 | Cascada: Resolución por CI_EXACTA | 1.850 (16,19 %) | 1.850 | Sí | `conteos_fuente_resolucion.CI_EXACTA` (N=11.426) | Cap. III, Sec. 3.3; Gráfico 4.2 |
| A-13 | Cascada: Resolución por ENCABEZADO | 3.079 (26,95 %) | 3.079 | Sí | `conteos_fuente_resolucion.ENCABEZADO` | Cap. III, Sec. 3.3; Gráfico 4.2 |
| A-14 | Cascada: Resolución por REGEX | 3.103 (27,16 %) | 3.103 | Sí | `conteos_fuente_resolucion.REGEX` | Cap. III, Sec. 3.3; Gráfico 4.2 |
| A-15 | Cascada: Resolución por BETO (Inferencia NLP) | 3.248 (28,43 %) | 3.248 | Sí | `conteos_fuente_resolucion.BETO` | Cap. III, Sec. 3.3; Gráfico 4.2 |
| A-16 | Cascada: Resolución por FUZZY (RapidFuzz) | 146 (1,28 %) | 146 | Sí | `conteos_fuente_resolucion.FUZZY` | Cap. III, Sec. 3.3; Gráfico 4.2 |
| A-17 | Conflictos de CI pendientes en Staging | 1.044 | 1.044 | Sí | `SELECT count(*) FROM stg_entidad_no_resuelta WHERE resuelto = false` | Cap. IV, Sec. 4.3.3; Gráfico 4.1 |
| A-18 | Conflictos CI con nombres discordantes | 756 | 756 | Sí | `SELECT count(*) FROM stg_entidad_no_resuelta WHERE motivo = 'CI_NOMBRE_DISCORDANTE' AND resuelto = false` | Cap. IV, Sec. 4.3.3; Gráfico 4.1 |
| A-19 | Evaluaciones con baja confianza IA en Staging | 288 | 288 | Sí | `SELECT count(*) FROM stg_entidad_no_resuelta WHERE motivo = 'BAJA_CONFIANZA_IA' AND resuelto = false` | Cap. IV, Sec. 4.3.3; Gráfico 4.1 |
| A-20 | Filas de hechos académicos en DW (`fact_rendimiento_academico`) | 22.618 | 22.618 | Sí (redefinición) | `SELECT count(*) FROM fact_rendimiento_academico;` | Cap. III, Modelo DW; Cap. IV, Sec. 4.2 |
| A-21 | Filas de hechos financieros en DW (`fact_situacion_financiera`) | 10.483 | 10.483 | Sí (redefinición) | `SELECT count(*) FROM fact_situacion_financiera;` | Cap. III, Modelo DW; Cap. IV, Sec. 4.2 |
| A-22 | Estudiantes totales en dimensión (`dim_estudiante`) | 14.078 | 14.078 | Sí | `SELECT count(*) FROM dim_estudiante;` | Cap. III, Sec. 3.3.4 |
| A-23 | Documentos de identidad (CI) únicos en DW | 13.667 | 13.667 | Sí | `SELECT count(DISTINCT ci_numero) FROM dim_estudiante;` | Cap. III, Sec. 3.3.4; Cap. IV, Sec. 4.2 |
| A-24 | Descartes por reglas de calidad sin bitácora en BD | 509 entidades | 509 entidades | Sí | `lote_1387_uploads_data_arquitectura_b.json:excepciones.por_destino.descarte` | Cap. IV, Sec. 4.3.1; Defectos Sec. H |
| A-25 | Descartes con registro en `log_inconsistencias` | 48 entidades | 48 entidades | Sí | `SELECT count(*) FROM log_inconsistencias WHERE regla_origen = 'PER_SIN_FORMA_NOMBRE'` | Cap. IV, Sec. 4.3.1; Tabla 4.3 |
| A-26 | Tiempo medio de ciclo automático (3 corridas) | 59,14 s | 60,00 s | Diferencia de -0,86 s | `docs/evidencias/ciclo_completo_final_1/2/3.json` (58,42 s, 59,73 s, 59,26 s) | Cap. IV, Sec. 4.4; Cuadro 4.5 |
| A-27 | Tiempo mínimo y máximo de ciclo automático | Mín: 58,42 s; Máx: 59,73 s | 59,24 s – 60,84 s | Sí (rango concordante) | `docs/evidencias/ciclo_completo_final_1/2/3.json` y `ciclo_r8_resumen.json` | Cap. IV, Sec. 4.4 |

### Detalle A.1: Desglose por Archivo de Origen del Lote 1.387
1. **Base centralizada Académica ARCA (1).xlsx** (Hoja `ACTAS DE NOTAS`):
   - Filas leídas: 450 | Filas cargadas directo: 448 (99,56 %) | Derivadas a HITL: 2 (0,44 %) | Staging: 0.
   - Motivo de HITL: Conflicto de resolución difusa de módulo en posgrados antiguos sin código POS estandarizado.
2. **BD Cobranzas.xlsx** (Hoja `COBRANZAS 2024 2025`):
   - Filas leídas: 350 | Filas cargadas directo: 349 (99,71 %) | Derivadas a HITL: 1 (0,29 %) | Staging: 0.
   - Motivo de HITL: Nombre incompleto de titular con duplicidad de cuota.
3. **TBL_INSCRITOS.xlsx** (Hoja `TBL_INSCRITOS`):
   - Filas leídas: 250 | Filas cargadas directo: 248 (99,20 %) | Derivadas a HITL: 2 (0,80 %) | Staging: 0.
   - Motivo de HITL: Formato de cédula de identidad con caracteres de complementariedad departamental discordantes.
4. **Evaluación Docente y Unifranz.xlsx** (Hoja `DIP. EXP DOC. X MODULO`):
   - Filas leídas: 150 | Filas cargadas directo: 137 (91,33 %) | Derivadas a HITL: 13 (8,67 %) | Staging: 0.
   - Motivo de HITL: Docentes con un solo nombre de pila sin apellido registrable (`BRANDON`, `IRVING`, `SERGIO`).
5. **Experiencia Docente 2.0.xlsx** (Hoja `CURSOS DOC 1`):
   - Filas leídas: 110 | Filas cargadas directo: 95 (86,36 %) | Derivadas a HITL: 15 (13,64 %) | Staging: 0.
   - Motivo de HITL: Entidades no personales en campos abiertos de encuesta (`Ninguno`, `NINGUNA`, `-`).
6. **BD Egresos.xlsx** (Hoja `egresos`):
   - Filas leídas: 53 | Filas cargadas directo: 53 (100,00 %) | Derivadas a HITL: 0 (0,00 %) | Staging: 0.
7. **EJECUTADO VS META.xlsx** (Hoja `EJECUTADO`):
   - Filas leídas: 24 | Filas cargadas directo: 23 (95,83 %) | Derivadas a HITL: 1 (4,17 %) | Staging: 0.
   - Motivo de HITL: Desalineación de categoría de egreso en convenio interinstitucional.

---

## B. STAGING, IDEMPOTENCIA Y EXCEPCIONES
El sistema mantiene mecanismos de aislamiento para resguardar la consistencia transaccional y la integridad referencial en el Data Warehouse.

### Tabla B.1: Métricas de Staging, Idempotencia y Excepciones
| ID | Métrica | Valor | Ref. ronda 10 | ¿Coincide? | Fuente (SQL/comando/log) | Dónde va en el documento |
|---|---|---|---|---|---|---|
| B-01 | Excepciones de calidad abiertas en el lote | 0 de 268 registros (0,00 %) | 0 de 268 | Sí | `lote_1387_uploads_data_arquitectura_b.json:excepciones.habrian_ingresado_al_dw_sin_control` | Cap. IV, Sec. 4.3.1; Tabla 4.3 |
| B-02 | Excepciones de calidad abiertas a nivel entidad | 0 de 562 entidades (0,00 %) | 0 de 562 | Sí | `lote_1387_uploads_data_arquitectura_b.json:excepciones.total_entidades` | Cap. IV, Sec. 4.3.1; Tabla 4.3 |
| B-03 | Filas nuevas en prueba de idempotencia estricta | 0 filas | 0 filas | Sí | `docs/evidencias/ciclo_idempotencia_hitl.json` / `backend/services/dw_loader.py:974` | Cap. IV, Sec. 4.3.4 |
| B-04 | Conflicto precedencia Marzo 2025: Valor consolidado en DW | 997.224,70 Bs | 997.224,70 Bs | Sí | `SELECT monto_ejecutado FROM fact_rentabilidad WHERE id_tiempo IN (SELECT id_tiempo FROM dim_tiempo WHERE periodo_mes = '2025-03')` | Cap. IV, Sec. 4.2.3; Cuadro 4.2 |
| B-05 | Conflicto precedencia Marzo 2025: Fuente prevaleciente | `EJECUTADO VS META` | `EJECUTADO VS META` | Sí | `SELECT * FROM log_inconsistencias WHERE id_inconsistencia = 1527` | Cap. IV, Sec. 4.2.3 |
| B-06 | Stock histórico pendiente en bandeja HITL | 1.606 casos en 786 grupos | 1.606 casos / 786 grupos | Sí | `docs/evidencias/remanente_stock_grupos.json` / `backend/services/bandeja_grupos.py` | Cap. IV, Sec. 4.3.3; Gráfico 4.1 |
| B-07 | Subconjunto de stock: Conflictos de CI | 756 casos en 725 grupos | 756 casos / 725 grupos | Sí | `stg_entidad_no_resuelta` filtrado por `CI_NOMBRE_DISCORDANTE` | Cap. IV, Sec. 4.3.3 |
| B-08 | Subconjunto de stock: Baja confianza y hechos en revisión | 850 casos en 61 grupos | 850 casos en 61 grupos | Sí | 288 `BAJA_CONFIANZA_IA` + 562 hechos en revisión académica/financiera | Cap. IV, Sec. 4.3.3 |
| B-09 | Extensiones admitidas por el pipeline | `.xlsx`, `.csv` | `.xlsx`, `.csv` | Sí | `backend/services/ingestion_service.py:17` (`ALLOWED_EXTENSIONS`) | Cap. III, Sec. 3.2.1 |
| B-10 | Procesamiento real de Google Forms | Sí (exportación Excel/CSV) | Sí | Sí | `TBL_INSCRITOS.xlsx` (`MARCA TEMPORAL`, 250 filas en lote 1.387) | Cap. III, Sec. 3.2.1; Cap. IV, Sec. 4.1 |
| B-11 | Procesamiento real de Moodle | Sí (exportación encuestas/notas) | Sí | Sí | `Evaluación Docente y Unifranz.xlsx`, `Experiencia Docente 2.0.xlsx` | Cap. III, Sec. 3.2.1; Cap. IV, Sec. 4.1 |

### Detalle B.1: Interpretación de los Denominadores 268 y 562
- **Denominador 562 (Nivel Entidad):** Representa el número total de celdas o entidades anómalas interceptadas preventivamente por las reglas de calidad en el lote de 1.387:
  1. `ETIQUETA_LIKERT`: 283 entidades correspondientes a escalas cualitativas ("Muy Bueno", "Excelente") en campos nominales.
  2. `CORREO_NO_ES_NOMBRE`: 139 entidades consistentes en correos electrónicos ingresados en lugar del nombre del estudiante.
  3. `COLUMNA_DE_COMENTARIO`: 87 cadenas de texto largo o sugerencias de alumnos en encuestas docentes.
  4. `PER_SIN_FORMA_NOMBRE`: 48 cadenas que violan la estructura de nombre de persona (un solo token sin apellido).
  5. `PERSONA_SIN_COINCIDENCIA`: 5 personas que no alcanzaron el umbral difuso y fueron derivadas limpiamente a HITL.
- **Denominador 268 (Nivel Registro/Fila):** Corresponde exactamente a los 268 registros del lote que contenían al menos una de las 562 entidades defectuosas.
- **Resultado de Calidad:** 0 de 268 registros defectuosos y 0 de 562 entidades anómalas penetraron al DW sin control (`habrian_ingresado_al_dw_sin_control = 0`).

---

## C. ABLACIÓN A/B/C Y BETO
La evaluación experimental de ablación compara la capacidad de extracción de entidades bajo tres arquitecturas:
- **Modo A (Determinístico puro):** Expresiones regulares, lectura posicional de encabezados y coincidencia difusa sin IA.
- **Modo B (Híbrido implementado en el sistema):** Cascada jerárquica con reglas determinísticas + RapidFuzz + Modelo BETO (`dccuchile/bert-base-spanish-wwm-cased` fine-tuned).
- **Modo C (BETO puro):** Extracción basada exclusivamente en inferencia semántica del modelo de lenguaje.

### Tabla C.1: Desempeño Comparativo de Arquitecturas de Extracción
| ID | Métrica | Modo A (Reglas) | Modo B (Híbrido) | Modo C (BETO solo) | Ref. ronda 10 | ¿Coincide? | Fuente | Dónde va |
|---|---|---|---|---|---|---|---|---|
| C-01 | F1 micro estricto (Dataset `gold_510`) | 100,00 % | 100,00 % | 97,57 % | C: 97,57 %; B: 100,00 % | Sí | `docs/evidencias/f1_beto_fp32_gold_510.json` | Cap. IV, Sec. 4.1.2; Tabla 4.4 |
| C-02 | Precisión micro estricta (`gold_510`) | 100,00 % | 100,00 % | 96,91 % | 96,91 % | Sí | `f1_beto_fp32_gold_510.json:por_modo.C` | Cap. IV, Sec. 4.1.2 |
| C-03 | Recall micro estricto (`gold_510`) | 100,00 % | 100,00 % | 98,24 % | 98,24 % | Sí | `f1_beto_fp32_gold_510.json:por_modo.C` | Cap. IV, Sec. 4.1.2 |
| C-04 | F1 micro relajado (`gold_510`) | 100,00 % | 100,00 % | 99,12 % | 99,12 % | Sí | `f1_beto_fp32_gold_510.json:por_modo.C` | Cap. IV, Sec. 4.1.2 |
| C-05 | F1 relajado en layouts adversos (`layouts_5`) | 28,57 % | 71,64 % | 69,23 % | B: 71,64 %; A: 28,57 % | Sí | `docs/evidencias/f1_beto_fp32_layouts_5.json` | Cap. IV, Sec. 4.1.3; Gráfico 4.4 |
| C-06 | Precisión relajada en layouts adversos (`layouts_5`) | 100,00 % | 77,42 % | 77,59 % | 77,42 % frente a 100 % | Sí | `f1_beto_fp32_layouts_5.json` | Cap. IV, Sec. 4.1.3 |
| C-07 | Recall relajado en layouts adversos (`layouts_5`) | 16,67 % | 66,67 % | 62,50 % | 66,67 % frente a 16,67 % | Sí | `f1_beto_fp32_layouts_5.json` | Cap. IV, Sec. 4.1.3 |
| C-08 | F1 estricto en layouts adversos (`layouts_5`) | 26,19 % | 31,58 % | 24,68 % | 31,58 % frente a 26,19 % | Sí | `f1_beto_fp32_layouts_5.json` | Cap. IV, Sec. 4.1.3 |
| C-09 | Tamaño dataset estándar (`gold_510`) | 510 entidades (180 líneas) | 510 entidades | Sí | Anotación de actas académicas y cobranzas | Cap. IV, Sec. 4.1.1 |
| C-10 | Tamaño dataset adverso (`layouts_5`) | 72 entidades (98 totales) | 72 / 98 | Sí | 5 layouts sintéticos de alta distorsión | Cap. IV, Sec. 4.1.1 |
| C-11 | Aporte marginal de BETO en lote 1.387 | 3.248 entidades (28,43 %) | 3.248 entidades | Sí | `conteos_fuente_resolucion.BETO` | Cap. IV, Sec. 4.1.4 |

### Detalle C.1: Umbrales Numéricos Exactos Vigentes en el Código Fuente
1. **Resolución de personas por bloqueo escalonado (0,92):**
   - *Ubicación:* `pipeline/normalization/person_resolver.py`, líneas 111 y 141-175.
   - *Código:* `UMBRAL_PERSONA = 0.92`.
   - *Regla:* Escalonamiento estricto a tres niveles: Módulo $\rightarrow$ Programa $\rightarrow$ Dimensión Completa. Exige que el candidato posea al menos dos tokens y que el apellido esté explícitamente presente en el nombre canónico (`toks_c[-1] in toks_p[1:]`).
2. **Coincidencia difusa de homónimos de estudiante (90 %):**
   - *Ubicación:* `backend/services/dw_loader.py`, líneas 241-253 y 473-486.
   - *Código:* `score_cutoff=90.0`.
   - *Regla:* Si dos o más estudiantes en la dimensión superan el 90 % de similitud difusa con el nombre procesado, se bloquea la inserción automática y se deriva a la bandeja HITL como `HOMONIMIA`. Si existe exactamente un candidato $\ge 90$ %, se rescata vinculándolo en `fk_estado = 'B'`.
3. **Variante de Cédula de Identidad con nombre discordante (85 %):**
   - *Ubicación:* `backend/services/dw_loader.py`, líneas 185-192.
   - *Código:* `bool(set(_tokens(a)) & set(_tokens(b))) and fuzz.token_set_ratio(a, b) >= 85`.
   - *Regla:* Si la cédula ya existe en `dim_estudiante`, pero el nombre difiere con similitud $< 85$ %, se cataloga como `CI_NOMBRE_DISCORDANTE` y se confina en `stg_entidad_no_resuelta`.
4. **Coincidencia difusa de docentes (85 %):**
   - *Ubicación:* `backend/services/dw_loader.py`, líneas 678-679.
   - *Código:* `score_fuzz is not None and score_fuzz >= 85.0`.
   - *Regla:* Búsqueda contra `dim_docente`. Si no se halla coincidencia $\ge 85$ %, se crea el docente bajo `fk_estado = 'C'` (miembro provisional).
5. **Coincidencia difusa de asignaturas y módulos (80 %):**
   - *Ubicación:* `backend/services/dw_loader.py`, líneas 742-743.
   - *Código:* `score_fuzz is not None and score_fuzz >= 80.0`.
   - *Regla:* Coincidencia contra `dim_modulo` supeditada a validación previa del código formal de programa (`POS`).

---

## D. PRUEBAS Y COBERTURA DE CÓDIGO
La verificación automatizada del sistema se ejecuta mediante `pytest` integrando pruebas unitarias, de integración, de regresión y de frontera bajo el entorno de pruebas oficial.

### Tabla D.1: Métricas Globales del Suite de Pruebas
| ID | Métrica | Valor | Ref. ronda 10 | ¿Coincide? | Fuente (SQL/comando/log) | Dónde va en el documento |
|---|---|---|---|---|---|---|
| D-01 | Total pruebas ejecutadas en pytest | 493 | 493 | Sí | `pytest -v` / `docs/evidencias/pytest_por_suite_y_cobertura.json` | Cap. III, Sec. 3.6; Tabla 3.29 |
| D-02 | Pruebas aprobadas exitosamente (passed) | 475 (96,35 %) | 475 | Sí | `pytest -v` / `docs/evidencias/pytest_por_suite_y_cobertura.json` | Cap. III, Sec. 3.6; Figura 3.40 |
| D-03 | Pruebas omitidas intencionalmente (skipped) | 11 (2,23 %) | 11 | Sí | Pruebas de integración sujetas a credenciales externas activas | Cap. III, Sec. 3.6 |
| D-04 | Pruebas con fallo esperado documentado (xfailed) | 7 (1,42 %) | 7 | Sí | Pruebas de degradación extrema de red en servicios auxiliares | Cap. III, Sec. 3.6 |
| D-05 | Pruebas fallidas críticas (failed / error) | 0 (0,00 %) | 0 | Sí | Salida oficial del runner de pruebas | Cap. III, Sec. 3.6 |
| D-06 | Cobertura global de sentencias | 60,8 % (8.049 de 13.249) | 60,8 % (8.049 / 13.249) | Sí | `pytest --cov=backend --cov=pipeline` | Cap. III, Sec. 3.6; Tabla 3.30; Fig. 3.50 |
| D-07 | Pruebas suite `transversales` (Núcleo DataOps) | 254 pasadas de 254 (100 %) | 254 | Sí | `pytest tests/transversales/` | Tabla 3.29 |
| D-08 | Pruebas suite `sprint3` (Pipeline & BETO) | 120 pasadas de 120 (100 %) | 120 | Sí | `pytest tests/sprint3/` | Tabla 3.29 |
| D-09 | Pruebas suite `sprint2` (DW & Ingesta) | 32 pasadas de 32 (100 %) | 32 | Sí | `pytest tests/sprint2/` | Tabla 3.29 |
| D-10 | Pruebas suite `sprint4` (CMI & Alertas) | 23 pasadas de 23 (100 %) | 23 | Sí | `pytest tests/sprint4/` | Tabla 3.29 |
| D-11 | Pruebas suite `sprint1` (Seguridad & RBAC) | 16 pasadas de 16 (100 %) | 16 | Sí | `pytest tests/sprint1/` | Tabla 3.29 |
| D-12 | Pruebas suite `loops` (Ciclos cerrados) | 9 pasadas de 9 (100 %) | 9 | Sí | `pytest tests/loops/` | Tabla 3.29 |
| D-13 | Pruebas suite `readiness` (Despliegue Docker) | 21 pasadas, 11 skip, 7 xfail | 39 pruebas | Sí | `pytest tests/readiness/` | Tabla 3.29 |

### Tabla D.2: Desglose de Cobertura por Componente de Software (Base para Tabla 3.30)
| Módulo / Archivo Fuente | Líneas Totales | Líneas Cubiertas | Cobertura (%) | Responsabilidad Arquitectónica |
|---|---|---|---|---|
| `backend/core/security.py` | 87 | 76 | 87,4 % | Autenticación JWT, MFA con OTP y control RBAC |
| `backend/services/financial_rules_engine.py` | 85 | 83 | 97,6 % | Clasificación de categorías financieras y egresos |
| `backend/services/bandeja_grupos.py` | 149 | 142 | 95,3 % | Agrupamiento inteligente de entidades para HITL |
| `backend/services/risk_service.py` | 337 | 318 | 94,4 % | Motor determinístico de alertas tempranas y mora |
| `pipeline/normalization/person_resolver.py` | 125 | 116 | 92,8 % | Resolución jerárquica escalonada con RapidFuzz |
| `backend/services/alert_engine.py` | 71 | 65 | 91,5 % | Disparador y orquestación de reglas de alerta |
| `backend/services/revision_hechos.py` | 210 | 185 | 88,1 % | Servicio transaccional de auditoría y lease de revisión |
| `pipeline/normalization/fk_resolver.py` | 89 | 78 | 87,6 % | Resolución de claves foráneas de programas y módulos |
| `backend/routers/reportes.py` | 261 | 221 | 84,7 % | Enmascaramiento de datos y exportación de reportes |
| `pipeline/normalization/fuzzy_normalizer.py` | 71 | 59 | 83,1 % | Limpieza canónica y normalización de cadenas |
| `backend/services/extraccion_por_encabezado.py` | 421 | 342 | 81,2 % | Mapeo estructural determinístico de hojas de cálculo |
| `pipeline/analytics/forecasting_holtwinters.py` | 71 | 68 | 95,8 % | Ajuste y proyección Holt-Winters amortiguado |
| `pipeline/analytics/forecasting_ols.py` | 28 | 28 | 100,0 % | Modelo econométrico lineal comparativo OLS |
| `backend/services/kpi_service.py` | 374 | 253 | 67,6 % | Cálculo dinámico de indicadores del CMI en DW |
| `backend/services/ingestion_service.py` | 587 | 360 | 61,3 % | Despacho y validación multipart de archivos subidos |
| `backend/services/confianza_service.py` | 87 | 49 | 56,3 % | Cliente de inferencia y asignación de confianza IA |
| `backend/services/dw_loader.py` | 870 | 387 | 44,5 % | Consolidación atómica de hechos y dimensiones en DW |
| `backend/routers/dataops.py` | 2.176 | 942 | 43,3 % | Endpoints de carga masiva, catálogos y reprocesamiento |
| `backend/routers/pipeline.py` | 269 | 96 | 35,7 % | Orquestación asíncrona de tareas del pipeline |
| `backend/services/forecast_service.py` | 253 | 90 | 35,6 % | Servicio de persistencia y exposición de pronósticos |
| `pipeline/semantic/indice_confianza.py` | 70 | 23 | 32,9 % | Cálculo vectorial de entropía de predicción BETO |
| **TOTAL SISTEMA (--cov=backend --cov=pipeline)** | **13.249** | **8.049** | **60,8 %** | **Alcance global de pruebas automatizadas** |

---

## E. PRONÓSTICO DE MATRÍCULA (HOLT-WINTERS Y BENCHMARKS)
El módulo de proyección de demanda académica se encuentra formalmente implementado bajo el método **Holt-Winters con Tendencia Amortiguada (Damped Holt-Winters)** y estacionalidad aditiva.

### Tabla E.1: Parámetros y Evaluación del Modelo Predictivo
| ID | Métrica | Valor | Ref. ronda 10 | ¿Coincide? | Fuente (Código / Script) | Dónde va en el documento |
|---|---|---|---|---|---|---|
| E-01 | Modelo vigente en código fuente | Tendencia Amortiguada (`damped_trend=True`) | HW Amortiguado | Sí | `pipeline/analytics/forecasting_holtwinters.py:97` | Cap. III, Sec. 3.5.2; Cap. IV, Sec. 4.5 |
| E-02 | Nombre real de la fuente documental | `TBL_INSCRITOS.xlsx` (hoja `TBL_INSCRITOS`) | `TBL_INSCRITOS.xlsx` | Sí | `uploads/data/TBL_INSCRITOS.xlsx` (en texto decía `inscritos.csv`) | Cap. III, Sec. 3.5.1; Defectos Sec. H |
| E-03 | Meses disponibles en la serie de matrícula | 33 meses (`2023-09` a `2026-05`) | 33 meses | Sí | `SELECT dt.periodo_mes, count(*) FROM fact_rendimiento_academico ...` | Cap. IV, Sec. 4.5.1 |
| E-04 | Serie extendida de captación en marketing | 43 meses (`2022-01` a `2025-07`) | 43 meses | Sí | `SELECT count(DISTINCT dt.periodo_mes) FROM fact_marketing ...` | Cap. IV, Sec. 4.5.1 |
| E-05 | Partición: Rango de entrenamiento | 27 meses (`2023-09` a `2025-11`) | 27 meses | Sí | Partición cronológica antes del corte de validación | Cap. IV, Sec. 4.5.2 |
| E-06 | Partición: Rango de hold-out (prueba) | 6 meses (`2025-12` a `2026-05`) | 6 meses | Sí | Corte de hold-out fijado al `2025-11-01` | Cap. IV, Sec. 4.5.2 |
| E-07 | Nivel de suavizado ($\alpha$) | 0,6978 | 0,6978 | Sí | Ajuste `ExponentialSmoothing` sobre la serie | Cap. IV, Sec. 4.5.2; Cuadro 4.6 |
| E-08 | Suavizado de tendencia ($\beta$) | 0,0000 | 0,0000 | Sí | Convergencia numérica del estimador | Cap. IV, Sec. 4.5.2; Cuadro 4.6 |
| E-09 | Suavizado estacional ($\gamma$) | 0,0000 | 0,0000 | Sí | Convergencia numérica del estimador | Cap. IV, Sec. 4.5.2; Cuadro 4.6 |
| E-10 | Factor de amortiguamiento ($\phi$) | 0,9950 | 0,9950 | Sí | Parámetro `damping_trend` optimizado | Cap. IV, Sec. 4.5.2; Cuadro 4.6 |
| E-11 | Error cuadrático medio in-sample (RMSE ajuste) | 48,36 estudiantes | 48,36 | Sí | `np.sqrt(mean_squared_error(y_train, y_fit))` | Cap. IV, Sec. 4.5.2; Cuadro 4.6 |
| E-12 | Criterio de Información de Akaike (AIC) | 290,00 | 290,00 | Sí | Métrica de bondad de ajuste del modelo HW | Cap. IV, Sec. 4.5.2; Cuadro 4.6 |
| E-13 | Error cuadrático medio en test (RMSE hold-out) | 75,03 estudiantes | 75,03 | Sí | `np.sqrt(mean_squared_error(y_test, y_pred))` | Cap. IV, Sec. 4.5.2; Cuadro 4.6 |
| E-14 | Error porcentual absoluto medio (MAPE hold-out) | 13,89 % | 13,89 % | Sí | `mean_absolute_percentage_error(y_test, y_pred)` | Cap. IV, Sec. 4.5.2; Gráfico 4.5 |
| E-15 | MAPE del Benchmark Naive Estacional | 18,22 % | 18,22 % | Sí | Persistencia interanual ($y_{t} = y_{t-12}$) | Cap. IV, Sec. 4.5.3; Cuadro 4.7 |
| E-16 | Reducción de error frente al Naive Estacional | 4,33 puntos porcentuales | 4,33 pp | Sí | Mejora del 23,76 % en precisión relativa | Cap. IV, Sec. 4.5.3 |
| E-17 | Coeficiente de determinación OLS mensual ($R^2$) | 0,0854 | 0,0854 | Sí | `statsmodels.api.OLS` (modelo puramente lineal) | Cap. IV, Sec. 4.5.3; Gráfico 3.5 |
| E-18 | Pendiente de tendencia OLS mensual | +2,95 estudiantes/mes | +2,95 | Sí | Pendiente positiva global de expansión | Cap. IV, Sec. 4.5.3 |
| E-19 | p-valor del ajuste lineal OLS | 0,098 | 0,098 | Sí | No significativo al 5 % (confirma estacionalidad) | Cap. IV, Sec. 4.5.3 |

### Detalle E.1: Proyección de Matrícula a Horizonte $h = 6$ Meses (Junio a Noviembre 2026)
- **Junio 2026:** 426,37 estudiantes (IC 95 %: [331,58; 521,16])
- **Julio 2026:** 414,22 estudiantes (IC 95 %: [319,43; 509,01])
- **Agosto 2026:** 498,55 estudiantes (IC 95 %: [403,76; 593,34])
- **Septiembre 2026:** 454,48 estudiantes (IC 95 %: [359,69; 549,27])
- **Octubre 2026:** 428,85 estudiantes (IC 95 %: [334,06; 523,64])
- **Noviembre 2026:** 461,97 estudiantes (IC 95 %: [367,18; 556,76])
- *Margen de error del intervalo:* $\pm 94,79$ estudiantes ($1,96 \times \text{RMSE}_{\text{ajuste 33 m}}$ = 1,96 × 48,36).

---

## F. INDICADORES (KPI) Y SISTEMA DE ALERTAS TEMPRANAS
El diseño conceptual del Cuadro de Mando Integral contempla 22 KPI registrados en el catálogo formal, de los cuales 11 indicadores clave se encuentran implementados y desplegados en el endpoint ejecutivo `/kpis/cmi-completo`.

### Tabla F.1: Catálogo Formal de 22 KPI en `bi.ref_kpi`
| ID | Código | Nombre del Indicador | Perspectiva CMI | Fórmula de Cálculo | Tabla de Origen DW |
|---|---|---|---|---|---|
| F-01 | KPI-01 | Ticket promedio por programa | Financiera | `Recaudación / Matriculados` | `fact_situacion_financiera` |
| F-02 | KPI-02 | Cumplimiento de metas mensual | Financiera | `(Ejecutado / Meta) * 100` | `fact_rentabilidad` |
| F-03 | KPI-03 | Cumplimiento de metas anual | Financiera | `(Ejecutado_Anual / Meta_Anual) * 100` | `fact_rentabilidad` |
| F-04 | KPI-04 | Margen operativo por programa | Financiera | `Recaudación - Costos_Directos` | `fact_rentabilidad` |
| F-05 | KPI-05 | Estudiantes en mora | Financiera | `Conteo por estado_financiero` | `fact_situacion_financiera` |
| F-06 | KPI-06 | Tasa de conversión postulantes | Clientes | `(Inscritos / Postulantes) * 100` | `fact_marketing` |
| F-07 | KPI-07 | Satisfacción del estudiante (NPS) | Clientes | `Media de puntaje_satisfaccion` | `fact_evaluacion_docente` |
| F-08 | KPI-08 | Tasa de aprobación por programa | Clientes | `(Aprobados / Evaluados) * 100` | `fact_rendimiento_academico` |
| F-09 | KPI-09 | Tasa de retención interanual | Clientes | `(Activos_T / Activos_T_1) * 100` | `fact_rendimiento_academico` |
| F-10 | KPI-10 | Confianza de extracción IA | Procesos Internos | `Media de nivel_confianza_ia` | `fact_rendimiento_academico` |
| F-11 | KPI-11 | Extracción directa sin HITL | Procesos Internos | `(Cargados_Directo / Total) * 100` | `fact_rendimiento_academico` |
| F-12 | KPI-12 | Eficiencia en recaudación proyectada | Financiera | `(Recaudado / Proyectado) * 100` | `fact_cobranzas_proyectadas` |
| F-13 | KPI-13 | Costo por postulante captado | Financiera | `Gasto_Marketing / Postulantes` | `fact_marketing` |
| F-14 | KPI-14 | Índice de rotación de docentes | Aprendizaje | `(Docentes_Baja / Total_Docentes) * 100` | `bridge_modulo_docente` |
| F-15 | KPI-15 | Horas de capacitación docente | Aprendizaje | `Suma de horas_capacitacion` | `fact_evaluacion_docente` |
| F-16 | KPI-16 | Cumplimiento del plan de estudios | Procesos Internos | `(Modulos_Dictados / Programados) * 100` | `dim_modulo` |
| F-17 | KPI-17 | Tiempo medio de resolución HITL | Procesos Internos | `Media de tiempo_resolucion_min` | `stg_entidad_no_resuelta` |
| F-18 | KPI-18 | Cobertura de becas y convenios | Financiera | `(Alumnos_Beca / Total_Alumnos) * 100` | `fact_situacion_financiera` |
| F-19 | KPI-19 | Nivel de ejecución presupuestaria | Financiera | `(Gasto_Real / Presupuesto) * 100` | `fact_costo_programa` |
| F-20 | KPI-20 | Reclamos estudiantiles resueltos | Clientes | `(Reclamos_Cerrados / Total) * 100` | `fact_evaluacion_docente` |
| F-21 | KPI-21 | Adopción de plataformas virtuales | Aprendizaje | `(Usuarios_Moodle_Activos / Total) * 100` | `fact_rendimiento_academico` |
| F-22 | KPI-22 | Desempeño docente promedio | Aprendizaje | `Media de evaluacion_promedio` | `fact_evaluacion_docente` |

### Tabla F.2: Valores Actuales de los 11 KPI Ejecutivos (Gestión 2025 y Lote 1.387)
| Código | Indicador | Valor en Snapshot 2025 | Valor en Lote 1.387 | Origen en Snapshot DW |
|---|---|---|---|---|
| KPI-01 | Ticket promedio por programa | 1.610,13 Bs | 1.610,13 Bs | `fact_situacion_financiera` (12 programas en desglose) |
| KPI-02 | Cumplimiento de metas mensual | 157,48 % | N/A | `fact_rentabilidad.monto_meta` (mes 12) |
| KPI-03 | Cumplimiento de metas anual | 110,54 % | N/A | `fact_rentabilidad.monto_meta` (recaudación total vs meta anual) |
| KPI-04 | Margen operativo por programa | 623 | 623 | `fact_rentabilidad` (desglose por categoría de programa) |
| KPI-05 | Estudiantes en mora | 3.691 Vigente / 830 Mora / 0 Prejudicial | N/A | `fact_situacion_financiera` (conteo por `estado_financiero`) |
| KPI-06 | Conversión de postulantes | 100,0 % | 100,0 % | `fact_marketing` (captación efectiva en corpus disponible) |
| KPI-07 | Satisfacción del estudiante (NPS) | 79,02 puntos | N/A | `fact_evaluacion_docente` (media sobre 14.234 encuestas) |
| KPI-08 | Tasa de aprobación por programa | 85,61 % apr / 14,39 % rep | 85,61 % | `fact_rendimiento_academico` (19.363 apr, 3.255 rep; nota min = 51) |
| KPI-09 | Tasa de retención interanual | 588 estudiantes | N/A | `fact_rendimiento_academico` (cohorte activa consecutiva) |
| KPI-10 | Confianza de extracción IA | **0,9269** (DW general) | **KPI-10a: 0,9618** (Todas)<br>**KPI-10b: 0,9209** (Solo BETO) | `fact_rendimiento_academico.nivel_confianza_ia` (N=11.426 en lote) |
| KPI-11 | Extracción directa sin HITL | **90,10 %** (DW general) | **97,55 %** (Lote 1.387) | 1.353 directo / 34 HITL / 0 staging sobre 1.387 registros |

### Detalle F.1: Origen Real de Metas Presupuestarias (KPI-02 y KPI-03)
- La tabla `dim_meta` se encuentra vacía (**0 filas**) en el esquema físico del DW.
- El origen verídico de las metas ejecutadas y presupuestadas es la columna `monto_meta` de la tabla de hechos **`fact_rentabilidad`**, la cual cuenta con **48 filas no nulas** alimentadas desde el archivo institucional `EJECUTADO VS META.xlsx`.

### Detalle F.2: Auditoría del Sistema de Alertas Tempranas
Las cifras reportadas en etapas tempranas de desarrollo (10.707 matrícula / 1.698 riesgo académico / 1.451 riesgo financiero / 103 alertas críticas) **no están vigentes**, dado que se originaron en pruebas de estrés con datasets sintéticos. Los valores reales y vigentes obtenidos desde el snapshot (`evaluar_alertas_tempranas_deterministicas`) son:
- **Población de matrícula activa analizada:** 9.603 estudiantes.
- **Riesgo Académico (Alerta Temprana):** 1.224 estudiantes (calificaciones menores a 51 puntos en módulos evaluados).
- **Riesgo de Deserción (Inactividad Aula Virtual):** 0 estudiantes (debido a que `incumplimiento_actividades_pct = 0.00` en las actas consolidadas).
- **Riesgo Financiero (Cartera en Mora):** 1.765 estudiantes (monto total adeudado: 867.811,89 Bs).
- **Alerta Crítica Multidimensional (2 o más factores simultáneos):** 238 estudiantes.
- **Total neto de estudiantes con al menos una alerta:** 2.751 estudiantes únicos.

---

## G. INFRAESTRUCTURA, SERVICIOS DOCKER Y MODELO DE DATOS
La arquitectura de despliegue opera bajo contenedores Docker orquestados mediante Docker Compose.

### Tabla G.1: Inventario de Contenedores Docker en Ejecución (`docker compose ps`)
| Nombre del Contenedor | Imagen | Servicio | Puerto(s) Publicado(s) | Estado Operativo |
|---|---|---|---|---|
| `giragroup_gateway` | `giragroup_bi_system-gateway` | `gateway` | `0.0.0.0:80->80/tcp` | Up (Saludable) |
| `giragroup_web` | `giragroup_bi_system-web` | `web` | `0.0.0.0:5173->5173/tcp` | Up (Saludable) |
| `giragroup_api` | `giragroup_bi_system-api` | `api` | `0.0.0.0:8000->8000/tcp` | Up (Saludable) |
| `giragroup_auth_svc` | `giragroup_bi_system-auth-service` | `auth-service` | `8001/tcp` (interno) | Up (Saludable) |
| `giragroup_notifications_svc` | `giragroup_bi_system-notifications-service` | `notifications-service` | `8002/tcp` (interno) | Up (Saludable) |
| `giragroup_audit_svc` | `giragroup_bi_system-audit-service` | `audit-service` | `8004/tcp` (interno) | Up (Saludable) |
| `giragroup_pipeline` | `giragroup_bi_system-pipeline` | `pipeline` | `8006/tcp` (interno) | Up (Saludable) |
| `giragroup_catalog_db` | `giragroup_bi_system-catalog_db` | `catalog_db` | `127.0.0.1:5433->5432/tcp` | Up (healthy) |
| `giragroup_db` | `postgres:16-alpine` | `db` | `127.0.0.1:5434->5432/tcp` | Up (healthy) |

### Tabla G.2: Inventario Físico de Tablas y Vistas del Data Warehouse (59 Objetos)
| Esquema | Objeto | Tipo | Filas | Propósito y Contenido |
|---|---|---|---|---|
| `bi` | `ref_kpi` | BASE TABLE | 22 | Catálogo maestro de indicadores del CMI |
| `bi` | `ref_perspectiva` | BASE TABLE | 4 | Las 4 perspectivas del CMI institucional |
| `bi` | `vw_cartera_estado` | VIEW | 7 | Vista agregada de cartera por estado crediticio |
| `bi` | `vw_cmi_gestiones` | VIEW | 5 | Histórico de gestiones consolidadas |
| `bi` | `vw_cmi_global` | VIEW | 5 | Indicadores globales de alto nivel por gestión |
| `bi` | `vw_cmi_perspectiva` | VIEW | 20 | Desempeño ponderado por perspectiva |
| `bi` | `vw_cmi_scorecard` | VIEW | 110 | Matriz completa del Cuadro de Mando Integral |
| `bi` | `vw_cmi_valores` | VIEW | 64 | Serie temporal de valores ejecutados de KPI |
| `bi` | `vw_dataops_documento` | VIEW | 16 | Estado de procesamiento por archivo fuente |
| `bi` | `vw_metas_mensual` | VIEW | 95 | Comparativo mensual ejecutado vs meta |
| `bi` | `vw_riesgo_estudiante` | VIEW | 6.602 | Clasificación de riesgo individual por estudiante |
| `public` | `bridge_modulo_docente` | BASE TABLE | 1.922 | Tabla puente asociativa entre módulos y docentes |
| `public` | `cache_indice_beto` | BASE TABLE | 90.212 | Caché semántica local de inferencias del modelo BETO |
| `public` | `carga_fila_origen` | BASE TABLE | 15.196 | Registro de claves únicas para idempotencia estricta |
| `public` | `cat_categoria_financiera` | BASE TABLE | 5 | Categorías de egresos y rentabilidad en DW |
| `public` | `cat_institucion` | BASE TABLE | 4 | Instituciones y universidades aliadas |
| `public` | `cat_programa` | BASE TABLE | 4 | Programas canónicos homologados |
| `public` | `dataops_tarea` | BASE TABLE | 28 | Registro de tareas y lotes de procesamiento DataOps |
| `public` | `dim_categoria_financiera` | BASE TABLE | 15 | Dimensión financiera extendida |
| `public` | `dim_docente` | BASE TABLE | 638 | Dimensión de docentes de posgrado |
| `public` | `dim_estudiante` | BASE TABLE | 14.078 | Dimensión de alumnos (13.667 CIs únicas) |
| `public` | `dim_meta` | BASE TABLE | 0 | Estructura dimensional previa (reemplazada por fact) |
| `public` | `dim_modulo` | BASE TABLE | 3.585 | Dimensión de asignaturas y módulos académicos |
| `public` | `dim_origen_documental` | BASE TABLE | 16 | Catálogo de fuentes y planillas procesadas |
| `public` | `dim_tiempo` | BASE TABLE | 2.230 | Dimensión temporal diaria (2020 a 2026) |
| `public` | `fact_cobranzas_proyectadas`| BASE TABLE | 0 | Hechos proyectados de recuperación de cartera |
| `public` | `fact_costo_programa` | BASE TABLE | 1.371 | Costos operacionales por versión de programa |
| `public` | `fact_evaluacion_docente` | BASE TABLE | 14.234 | Evaluaciones y encuestas de satisfacción estudiantil |
| `public` | `fact_forecast` | BASE TABLE | 24 | Proyecciones mensuales de demanda persistidas |
| `public` | `fact_marketing` | BASE TABLE | 8.946 | Leads, consultas y métricas de captación |
| `public` | `fact_rendimiento_academico`| BASE TABLE | 22.618 | Actas de notas y calificaciones de alumnos |
| `public` | `fact_rentabilidad` | BASE TABLE | 108 | Ingresos, egresos y metas presupuestarias |
| `public` | `fact_situacion_financiera` | BASE TABLE | 10.483 | Transacciones de cobranza, cuotas y deudas |
| `public` | `fact_techo_convenio` | BASE TABLE | 206 | Aranceles máximos por convenios interinstitucionales |
| `public` | `log_auditoria_nlp` | BASE TABLE | 4 | Trazabilidad de predicciones del modelo BETO |
| `public` | `log_inconsistencias` | BASE TABLE | 92 | Registro de discrepancias y descartes nominales |
| `public` | `log_pipeline_ingesta` | BASE TABLE | 117 | Auditoría de pasos de ejecución del pipeline |
| `public` | `lote` | BASE TABLE | 1 | Control maestro de lotes procesados |
| `public` | `notifications` | BASE TABLE | 2 | Notificaciones emitidas por el sistema |
| `public` | `powerbi_informe_version` | BASE TABLE | 2 | Metadatos de reportes Power BI sincronizados |
| `public` | `ref_metas_gestion` | BASE TABLE | 0 | Metas anuales (gestionadas en fact_rentabilidad) |
| `public` | `schema_migrations` | BASE TABLE | 12 | Registro de control de migraciones aplicadas |
| `public` | `staging_registros_crudos` | BASE TABLE | 91 | Buffer temporal de ingesta sin normalizar |
| `public` | `stg_entidad_no_resuelta` | BASE TABLE | 23.127 | Entidades pendientes de resolución (1.044 activas) |
| `public` | `users` | BASE TABLE | 5 | Usuarios autenticados bajo el modelo RBAC |
| `public` | *Tablas cat_* auxiliares (13)| BASE TABLE | 0 c/u | Catálogos locales replicados desde la base de catálogo |

### Tabla G.3: Inventario de Tablas en Base de Catálogo (`giragroup_catalog_db`, 20 Tablas)
| Objeto | Filas | Propósito Funcional |
|---|---|---|
| `cat_categoria_financiera` | 2 | Categorías maestras de clasificación contable |
| `cat_combinacion_estado` | 16 | Matriz de homologación de estados académicos y financieros |
| `cat_concepto_financiero` | 16 | Conceptos arancelarios (matrícula, colegiatura, titulación) |
| `cat_convenio_programa` | 195 | Relación formal de convenios interinstitucionales |
| `cat_escuela` | 5 | Escuelas académicas de posgrado |
| `cat_estado_academico` | 5 | Estados del estudiante (regular, baja, graduado, abandono) |
| `cat_estado_arca` | 2 | Estados homologados del sistema académico ARCA |
| `cat_estado_reprobado` | 7 | Tipologías de reprobación (abandono, nota, inasistencia) |
| `cat_etiqueta_clasificacion`| 66 | Etiquetas semánticas para entrenamiento y reglas NLP |
| `cat_guia_texto_plano` | 6 | Plantillas de expresiones regulares por formato de archivo |
| `cat_historico_equivalencia` | 67 | Tabla de equivalencias entre versiones de programas |
| `cat_institucion_convenio` | 22 | Universidades e instituciones en convenio nacional |
| `cat_mapeo_columna` | 159 | Diccionario de sinónimos para encabezados heterogéneos |
| `cat_modalidad` | 3 | Modalidades de cursado (virtual, presencial, semipresencial) |
| `cat_modulo` | 1.747 | Catálogo estandarizado de materias de posgrado |
| `cat_programa` | 1.229 | Oferta académica de diplomados y maestrías |
| `cat_tipo_cartera` | 5 | Tipología de cobranza y riesgo financiero |
| `cat_tipo_programa` | 6 | Clasificación de programas de estudio |
| `ref_metas_gestion` | 59 | Metas históricas presupuestadas por gestión |
| `stg_entidad_no_resuelta` | 0 | Buffer de soporte de catálogo |

### Detalle G.1: Arquitectura RBAC (Role-Based Access Control)
El sistema protege cada recurso mediante dependencias `require_roles(...)` en FastAPI (`backend/core/security.py`):
1. **ADMIN (`admin_general`):** Acceso irrestricto al sistema, endpoints administrativos, auditoría, gestión de usuarios y reconfiguración dimensional.
2. **AUDITOR_CALIDAD (`auditor_dataops`):** Acceso autorizado a la ingesta documental, cola de validación HITL (`/api/v1/dataops/bandeja-grupos`), reasignación de entidades en Staging y logs de inconsistencia.
3. **DIRECTOR_ACADEMICO (`dir_academica`):** Visualización del CMI integral, tablero de alertas académicas y de deserción, reportes de retención y aprobación, y pronósticos de demanda.
4. **ANALISTA_FINANCIERO (`analista_fin`):** Acceso al tablero financiero del CMI (recaudación, metas, rentabilidad, cartera vencida), proyecciones de flujo y reportes exportables con montos financieros visibles.
5. **ANALISTA_MARKETING (`analista_mkt`):** Monitoreo del embudo de conversión, campañas publicitarias y pronósticos de captación de postulantes.

### Detalle G.2: Integración Frontend de la Bandeja Agrupada y Power BI
- **Bandeja Agrupada HITL:** Integrada en `frontend/src/modules/admin/HumanReviewFlowView.jsx`. Utiliza el componente desacoplado `BandejaGrupos` y consume `/api/v1/dataops/bandeja-grupos`, permitiendo resolver de forma atómica grupos de inconsistencias por similitud.
- **Embebido de Power BI:** Integrado en `frontend/src/modules/admin/CuadroMandoIntegral.jsx`. Renderiza un contenedor embebido `iframe` apuntando a las versiones publicadas administradas desde `backend/routers/powerbi.py` y respaldadas en el archivo físico `powerbi/dashboards/giragroup_cmi.pbix`.

---

## H. DEFECTOS E INCONSISTENCIAS TÉCNICAS DETECTADAS
En estricto cumplimiento de la regla de no alteración y reporte honesto de discrepancias, se documentan los siguientes hallazgos:

1. **Confusión conceptual de "Personas Totales y Únicas" (22.618 vs 10.483):**
   - *Hallazgo:* En borradores de los Capítulos I y IV se afirmó que existían "22.618 personas totales y 10.483 personas únicas".
   - *Realidad técnica:* 22.618 es el número total de evaluaciones en `fact_rendimiento_academico` (pertenecientes a 6.419 estudiantes distintos); 10.483 es el número de transacciones en `fact_situacion_financiera` (pertenecientes a 9.022 estudiantes distintos). El total de estudiantes en `dim_estudiante` es de 14.078 registros con 13.667 números de CI únicos.
2. **Dualidad en el recuento de KPIs (22 vs 11):**
   - *Hallazgo:* El documento menciona alternativamente 22 y 11 KPIs.
   - *Realidad técnica:* En `bi.ref_kpi` existen 22 indicadores diseñados a nivel institucional. En la interfaz web y el backend ejecutivo (`/kpis/cmi-completo`) se implementan y calculan dinámicamente 11 KPIs clave.
3. **Inexistencia de datos en `dim_meta`:**
   - *Hallazgo:* El documento de diseño dimensional referenciaba la consulta de metas a `dim_meta`.
   - *Realidad técnica:* `dim_meta` tiene 0 filas. El cálculo de cumplimiento de metas (KPI-02 y KPI-03) se realiza directamente a través de `fact_rentabilidad.monto_meta` (48 filas consolidadas).
4. **Descartes de calidad en memoria sin persistencia en base de datos:**
   - *Hallazgo:* Se documenta el descarte de 509 entidades anómalas por reglas de calidad.
   - *Realidad técnica:* Las 509 entidades (Likert, correos, comentarios) son filtradas en memoria durante el pre-procesamiento por expresiones regulares y no generan registros en `log_inconsistencias`. Solo las 48 entidades de `PER_SIN_FORMA_NOMBRE` se persisten en dicha tabla.
5. **Alertas de deserción en 0:**
   - *Hallazgo:* El sistema de alertas no detecta deserción por inactividad.
   - *Realidad técnica:* Todas las 22.618 filas de `fact_rendimiento_academico` presentan `incumplimiento_actividades_pct = 0.00` debido a que las actas históricas en Excel carecían de la columna de inactividad de Moodle.
6. **Denominación errónea del archivo de postulantes:**
   - *Hallazgo:* El texto menciona «inscritos.csv».
   - *Realidad técnica:* El archivo real en el corpus institucional es `TBL_INSCRITOS.xlsx` (hoja `TBL_INSCRITOS`).
7. **Obsolescencia de cifras de alertas previas:**
   - *Hallazgo:* Las cifras 10.707 / 1.698 / 1.451 / 103 pertenecen a corridas sintéticas del Sprint 4 y deben sustituirse por las del snapshot (9.603 analizados, 1.224 académico, 0 deserción, 1.765 financiero, 238 críticas, 2.751 únicos).

---

## I. GRÁFICOS Y FIGURAS ACADÉMICAS REGENERADAS (300 DPI)
Todos los gráficos y figuras han sido regenerados exclusivamente a partir de los datos auditados en el snapshot `snapshot_dw_20261110_1201`, cumpliendo con la resolución requerida (300 DPI), formato en escala de grises con tramas para impresión académica y coma decimal en sus ejes numéricos.

### Tabla I.1: Catálogo de Gráficos y Figuras Oficiales
| Identificador | Título Sugerido en Tesis | Archivo PNG (300 DPI) | Script Generador | Fuente Oficial a Citar al Pie |
|---|---|---|---|---|
| **Gráfico 3.2** | Distribución porcentual del lote de validación según bandas de confianza IA | `docs/evidencias/graficos/grafico_3_2_distribucion_lote_1387.png` | `scripts/generar_graficos_ronda_final.py` | Fuente: Elaboración propia con datos del sistema, snapshot snapshot_dw_20261110_1201 |
| **Gráfico 3.4** | Serie temporal de matrícula histórica y modelado Holt-Winters amortiguado | `docs/evidencias/graficos/grafico_3_4_serie_temporal_holt_winters.png` | `scripts/generar_graficos_ronda_final.py` | Fuente: Elaboración propia con datos del sistema, snapshot snapshot_dw_20261110_1201 |
| **Gráfico 4.1** | Distribución de inconsistencias y excepciones de calidad en el corpus institucional | `docs/evidencias/graficos/grafico_4_1_inconsistencias_corpus.png` | `scripts/generar_graficos_ronda_final.py` | Fuente: Elaboración propia con datos del sistema, snapshot snapshot_dw_20261110_1201 |
| **Gráfico 4.2** | Proporción de resoluciones automáticas por etapa de la cascada jerárquica | `docs/evidencias/graficos/grafico_4_2_confianza_probabilistica.png` | `scripts/generar_graficos_ronda_final.py` | Fuente: Elaboración propia con datos del sistema, snapshot snapshot_dw_20261110_1201 |
| **Gráfico 4.3** | Resultado de vinculación automática e intervención humana por archivo de origen | `docs/evidencias/graficos/grafico_4_3_distribucion_archivo_lote_1387.png` | `scripts/generar_graficos_ronda_final.py` | Fuente: Elaboración propia con datos del sistema, snapshot snapshot_dw_20261110_1201 |
| **Gráfico 4.5** | Comparación de tiempos de consolidación analítica entre línea base manual y pipeline | `docs/evidencias/graficos/grafico_4_5_tiempo_consolidacion_semilog.png` | `scripts/generar_graficos_ronda_final.py` | Fuente: Elaboración propia con datos del sistema, snapshot snapshot_dw_20261110_1201 |
| **Figura 3.5** | Esquema físico del modelo en constelación de hechos del Data Warehouse | `docs/evidencias/graficos/figura_3_5_esquema_constelacion_fisico.png` | `scripts/generar_graficos_ronda_final.py` | Fuente: Elaboración propia con datos del sistema, snapshot snapshot_dw_20261110_1201 |
| **Figura 3.40** | Captura de ejecución de la suite de pruebas unitarias y de integración (475 passed) | `docs/evidencias/graficos/figura_3_40_captura_pytest_475.png` | Runner de pruebas pytest / script de captura | Fuente: Elaboración propia con datos del sistema, snapshot snapshot_dw_20261110_1201 |
| **Figura 3.50** | Captura de reporte consolidado de cobertura de código por componentes (60,8 %) | `docs/evidencias/graficos/figura_3_50_captura_cobertura_60_8.png` | Runner de pruebas pytest-cov / script de captura | Fuente: Elaboración propia con datos del sistema, snapshot snapshot_dw_20261110_1201 |

---

## CIERRE
1. **ID del Snapshot:** `snapshot_dw_20261110_1201` (Hash SHA-256: `14D45F5A128F44543927911DC0AD453F681D524AC05037203F5C0C2787E3A2EB`).
2. **Valores que cambiaron respecto de la ronda 10:** El tiempo medio de ciclo automático se precisó en 59,14 s (frente a 60,00 s); las alertas tempranas se actualizaron al DW real (9.603 analizados, 1.224 académico, 0 deserción, 1.765 financiero, 238 críticas, sustituyendo a las obsoletas 10.707 / 1.698 / 1.451 / 103); y se aclaró que 22.618 y 10.483 son recuentos de hechos de notas y cobranzas, no de personas totales y únicas (que son 14.078 y 13.667).
3. **Métricas en N/D:** Se consignaron como N/D la tasa de retención y desglose de mora en el lote 1.387 aislado (porque se calculan a nivel anual/DW completo en gestión 2025) y los registros de `dim_meta` (que tiene 0 filas).
4. **Respuestas con evidencia técnica:**
   - **¿HW es amortiguado? SÍ.** Evidencia: `pipeline/analytics/forecasting_holtwinters.py:97` (`damped_trend=True`, factor $\phi = 0,9950$).
   - **¿Son 22 KPI o 11? AMBOS.** Evidencia: `bi.ref_kpi` almacena 22 indicadores diseñados formalmente, mientras que `/kpis/cmi-completo` implementa y calcula dinámicamente 11 KPIs en el dashboard.
   - **¿Se procesan Forms y Moodle? SÍ.** Evidencia: `backend/services/ingestion_service.py:17` acepta `.xlsx` y `.csv`; `TBL_INSCRITOS.xlsx` procesa respuestas de Forms y `Evaluación Docente y Unifranz.xlsx` procesa encuestas de Moodle.
   - **¿Los descartes van a una bitácora? PARCIALMENTE.** Evidencia: 509 entidades se descartan en memoria por regex sin bitácora en BD; solo las 48 de `PER_SIN_FORMA_NOMBRE` se persisten en `log_inconsistencias`.
   - **¿Están integradas en el frontend la bandeja y Power BI? SÍ.** Evidencia: `HumanReviewFlowView.jsx` integra `BandejaGrupos` y `CuadroMandoIntegral.jsx` integra el iframe de `giragroup_cmi.pbix`.
"""

with open('fuente_verdad_tesis.md', 'w', encoding='utf-8') as f:
    f.write(content.strip() + '\n')

print("Documento fuente_verdad_tesis.md generado con éxito.")
