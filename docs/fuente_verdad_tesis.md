# ÚNICA FUENTE DE VERDAD (SFV) — PROYECTO DE GRADO GIRAGROUP BI

**Estado:** **CONGELADO** — 25 de noviembre de 2026 (recongelado tras F9–F12)  
**Título del Proyecto:** *Sistema de Inteligencia de Negocios basado en BETO y Cuadro de Mando Integral para mitigar la fragmentación informacional en GiraGroup S.R.L.*  
**Autor:** Lean (Adriano Daza)  
**Rama / Commit base:** `main` (`13b6173`)  
**Lote congelado (10 archivos en `uploads/data/`, SHA-256):** `aafde8adc246af13c4eeb9ffbf766eda4348cfb6e855860d0bf00bcd24cbdb60`  
**Modelo BETO vigente (SHA-256):** `9ff7fb9d914aca9eaa0618d9603d869a30808d9218369aef7b12dd92362b5f92`  
**Huella de `f3_base` (SHA-256):** `8afad01159f63bfd84f75d9f5ba32736024a4902d894b23def555fe880745c94` (`docs/mediciones/f5c_base.json.huella.json`). Coincide en 2 de 2 corridas de `f3_base` (`docs/mediciones/f5c_base.json`) y en 6 de 6 corridas de B-7 (`docs/mediciones/f5c_b7_corridas.json`).  
**Flags de integración BETO:** `BETO_CASCADA_FINAL=True`, `BETO_ACUERDO_QC=True` (acotado a `FUZZY`), `BETO_SUGERENCIA_HITL=True` (corte `80,0`), `BETO_RESCATE_ACADEMICO=True` (acotado a hojas sin columna estructurada), `BETO_VENTANA=False` (`pipeline/config.py:52-56`)  
**Snapshot histórico (10-nov-2026):** `snapshot_dw_20261110_1201` (`docs/evidencias/snapshot_dw_20261110_1201.dump`, SHA-256 `14D45F5A128F44543927911DC0AD453F681D524AC05037203F5C0C2787E3A2EB`)  
**Acceso a las bases:** Las credenciales y cadenas de conexión se leen únicamente desde variables de entorno (`DATABASE_URL` / `docker-compose.yml`). Ninguna medición altera la DW viva ni el archivo `.dump` del snapshot.

---

## REGLAS DE PRECEDENCIA, BASES Y CONCILIACIÓN

1. **Regla de precedencia:** Este documento constituye la **Única Fuente de Verdad (SFV)** unificada y vinculante para la redacción final de los Capítulos I, III, IV y V. Sustituye y anula cualquier borrador, anexo o cifra previa que lo contradiga.
2. **Regla de tres bases declaradas:**
   - **Base `snapshot 10-nov` (`snapshot_dw_20261110_1201`):** Fuente exclusiva de las series históricas y cifras de negocio que **no dependen del modelo BETO de extracción** (KPIs de negocio `KPI-01`..`09`, `KPI-12`..`17`, `KPI-19`..`22`, alertas tempranas, serie histórica de matrícula de 43 meses, recaudación, metas y conteos históricos del DW).
   - **Base `f3_base` (ciclo mensual 2026-03 sobre recortes `output/backups/f0_lote/slices/`):** Fuente exclusiva de las métricas operativas del ciclo vigente (tiempos de RNF-03, KLM, bandeja HITL del ciclo, staging, `log_inconsistencias`, KPI-10, KPI-11, KPI-18 y cuadre de cobranzas).
   - **Base `f5v_completo` (`docs/mediciones/f5v_completo.json`):** Carga completa de los 10 libros del lote en clon tmpfs con el código final; fuente exclusiva de `fact_planificacion_programa`, `dim_meta` de planificación y `KPI-23` (`docs/mediciones/f5v_kpi23_serie.json`).
   - **Base `lote 1.387` (`docs/mediciones/f5c_lote_1387_r1.json`):** Fuente exclusiva de la evaluación controlada de 1.387 registros ejecutada con el modelo BETO vigente (2 corridas idénticas).
   - **Base `f9_completo` (`docs/mediciones/f9_completo.json`, `f9_aporte_10archivos.json`, `f9_kpi10_check.json`):** Medición final de rendimiento RNF-03 en carga histórica fría de los 10 libros (clon `beto_pg_tmpfs`) y ablación Modo A vs. Modo B tras la optimización de `fila_resuelta_por_regla` (F9).
   - **Base `f11_lote1_predefensa` (`docs/mediciones/f11_carga_limpia.json`, `f11_backup_verificacion.json`, `f11_beto_check.json`):** Carga limpia pre-defensa del Lote #1 (10 libros de `uploads/data/`) sobre `giragroup_db`, pronósticos Holt-Winters / OLS y snapshot semilla reproducible (`backups/snapshot_pre_defensa.dump`).
   - **Base `f12_bandeja_lote1` (`docs/mediciones/f12_grupos_api_test.txt`, `f12_gobernanza_batch_test.txt`):** Medición de la bandeja HITL agrupada por bandas `patron`, prioridad, selección múltiple y guardrail `HTTP 422` sobre el Lote #1.
   - **Regla de no mezcla:** Dentro de una misma tabla **nunca se mezclan bases**. El título de cada tabla declara explícitamente la única base a la que pertenecen sus filas.
3. **Regla de modelo único (Decisión 4, 16-nov-2026):** La tesis describe únicamente el modelo BETO vigente (`9ff7fb9d…5f92`). No se citan versiones anteriores ni se realizan comparaciones entre versiones del modelo.
4. **Estándar numérico:** Se emplea de forma uniforme el estándar oficial de Bolivia: **coma (`,`) como separador decimal y punto (`.`) como separador de miles**. Toda cifra cuantitativa está trazada a un archivo y ruta JSON en `docs/mediciones/` y verificada por `scripts/verificar_sfv.py`. Los valores sin respaldo medible o externos al código se declaran como **N/D**, **RETIRADA** o **Dato de Lean**.
5. **Metodología de las mediciones:** «las mediciones parten de dw_vacio, que conserva las dimensiones del snapshot (por ejemplo dim_estudiante = 14.078) y vacía hechos, staging, logs y carga_fila_origen; reproduce un ciclo mensual sobre registros maestros existentes» (`docs/mediciones/f3s_dw_vacio.json`).

---

## A. LOTE 1.387, CICLO OPERATIVO (`f3_base`) Y RENDIMIENTO (RNF-03)

### Tabla A.1: Lote de Validación Controlado — Base: `lote 1.387` (`f5c_lote_1387_r1.json`)

| ID | Métrica | Valor | `valor_docx` | Fuente (`docs/mediciones/` y ruta JSON) | Dónde va en tesis |
|---|---|---|---|---|---|
| A-01 | Total de registros evaluados en el lote | 1.387 | 1.387 | `docs/mediciones/f5c_lote_1387_r1.json` → `lote_evaluado.total_registros` | Cap. IV Sec. 4.3; Tabla 4.1; Cuadro 3.8 |
| A-02 | Registros vinculados directos (con regla personas) | 1.356 (97,76 %) | 1.356 (97,76 %) | `docs/mediciones/f5c_lote_1387_r1.json` → `distribucion_bandas_con_regla_personas.directo` | Cap. III Sec. 3.4; Cap. IV Sec. 4.3; Gráf. 3.2 |
| A-03 | Registros derivados a HITL (con regla personas) | 31 (2,24 %) | 31 (2,24 %) | `docs/mediciones/f5c_lote_1387_r1.json` → `distribucion_bandas_con_regla_personas.hitl` | Cap. III Sec. 3.4; Cap. IV Sec. 4.3; Gráf. 3.2 |
| A-04 | Registros rechazados a Staging directo | 0 (0,00 %) | 0 (0,00 %) | `docs/mediciones/f5c_lote_1387_r1.json` → `distribucion_bandas_con_regla_personas.staging` | Cap. III Sec. 3.4; Cap. IV Sec. 4.3 |
| A-05 | Registros directos sin regla de personas (solo banda) | 1.384 (99,78 %) | 1.384 (99,78 %) | `docs/mediciones/f5c_lote_1387_r1.json` → `distribucion_bandas_sin_regla_personas.directo` | Cap. IV Sec. 4.3 |
| A-06 | Movidos de directo a HITL por persona sin resolver | 28 | 28 | `docs/mediciones/f5c_lote_1387_r1.json` → `registros_directo_movidos_a_hitl_por_persona_sin_resolver` | Cap. IV Sec. 4.3 |
| A-07 | Personas evaluadas en el lote (total entidades) | 1.744 | 1.744 | `docs/mediciones/f5c_lote_1387_r1.json` → `personas.total` | Cap. IV Sec. 4.3.2 |
| A-08 | Personas resueltas por CI exacta (Estado A) | 1.033 (59,23 %) | 1.033 (59,23 %) | `docs/mediciones/f5c_lote_1387_r1.json` → `personas.resueltas_CI_EXACTA` | Cap. III Sec. 3.3.4; Tabla 4.2 |
| A-09 | Personas resueltas por coincidencia difusa (Estado B) | 182 (10,44 %) | 182 (10,44 %) | `docs/mediciones/f5c_lote_1387_r1.json` → `personas.resueltas_FUZZY` | Cap. III Sec. 3.3.4; Tabla 4.2 |
| A-10 | Docentes nuevos provisionales (Estado C) | 524 (30,05 %) | 524 (30,05 %) | `docs/mediciones/f5c_lote_1387_r1.json` → `personas.nuevos_estado_C` | Cap. III Sec. 3.3.4; Tabla 4.2 |
| A-11 | Personas sin coincidencia derivadas a HITL | 5 (0,29 %) | 5 (0,29 %) | `docs/mediciones/f5c_lote_1387_r1.json` → `personas.sin_coincidencia_HITL` | Cap. IV Sec. 4.3.2 |
| A-12 | Cascada: Resolución por `CI_EXACTA` | 1.850 (16,00 %) | 1.850 | `docs/mediciones/f5c_lote_1387_r1.json` → `conteos_fuente_resolucion.CI_EXACTA` | Cap. III Sec. 3.3; Gráf. 4.2 |
| A-13 | Cascada: Resolución por `ENCABEZADO` | 3.079 (26,63 %) | 3.079 | `docs/mediciones/f5c_lote_1387_r1.json` → `conteos_fuente_resolucion.ENCABEZADO` | Cap. III Sec. 3.3; Gráf. 4.2 |
| A-14 | Cascada: Resolución por `REGEX` | 3.103 (26,84 %) | 3.103 | `docs/mediciones/f5c_lote_1387_r1.json` → `conteos_fuente_resolucion.REGEX` | Cap. III Sec. 3.3; Gráf. 4.2 |
| A-15 | Cascada: Resolución por `BETO` (inferencia NLP) | 3.382 (29,26 %) | 3.382 | `docs/mediciones/f5c_lote_1387_r1.json` → `conteos_fuente_resolucion.BETO` | Cap. III Sec. 3.3; Gráf. 4.2 |
| A-16 | Cascada: Resolución por `FUZZY` (RapidFuzz) | 146 (1,26 %) | 146 | `docs/mediciones/f5c_lote_1387_r1.json` → `conteos_fuente_resolucion.FUZZY` | Cap. III Sec. 3.3; Gráf. 4.2 |
| A-17 | KPI-10a: Confianza media (todas las entidades, N=11.560) | 0,9538 | 0,9538 | `docs/mediciones/f5c_lote_1387_r1.json` → `kpis.KPI_10a_media_todas_las_entidades` | Cap. IV Sec. 4.3 |
| A-18 | KPI-10b: Confianza media (solo entidades BETO, N=3.382) | 0,8953 | 0,8953 | `docs/mediciones/f5c_lote_1387_r1.json` → `kpis.KPI_10b_media_solo_entidades_BETO` | Cap. IV Sec. 4.3 |
| A-19 | KPI-11: Automatización directa (con regla de personas) | 97,76 % | 97,76 % | `docs/mediciones/f5c_lote_1387_r1.json` → `kpis.KPI_11_directo_con_regla_personas_pct` | Cap. IV Sec. 4.3 |

### Tabla A.2: Desglose por Archivo del Lote Controlado — Base: `lote 1.387` (`f5c_lote_1387_r1.json`)

| Archivo (`uploads/data/`) | Hoja | Filas leídas | Directo | HITL | Staging | `valor_docx` (Directo / HITL) | Fuente (`docs/mediciones/` y ruta JSON) |
|---|---|---|---|---|---|---|---|
| `Base centralizada Académica ARCA (1).xlsx` | `ACTAS DE NOTAS` | 450 | 449 (99,78 %) | 1 (0,22 %) | 0 | 449 / 1 | `docs/mediciones/f5c_lote_1387_r1.json` → `distribucion_por_archivo` |
| `BD Cobranzas.xlsx` | `COBRANZAS 2024 2025` | 350 | 349 (99,71 %) | 1 (0,29 %) | 0 | 349 / 1 | `docs/mediciones/f5c_lote_1387_r1.json` → `distribucion_por_archivo` |
| `TBL_INSCRITOS.xlsx` | `TBL_INSCRITOS` | 250 | 249 (99,60 %) | 1 (0,40 %) | 0 | 249 / 1 | `docs/mediciones/f5c_lote_1387_r1.json` → `distribucion_por_archivo` |
| `Evaluación Docente y Unifranz.xlsx` | `DIP. EXP DOC. X MODULO` | 150 | 146 (97,33 %) | 4 (2,67 %) | 0 | 146 / 4 | `docs/mediciones/f5c_lote_1387_r1.json` → `distribucion_por_archivo` |
| `Experiencia Docente 2.0.xlsx` | `CURSOS DOC 1` | 110 | 95 (86,36 %) | 15 (13,64 %) | 0 | 95 / 15 | `docs/mediciones/f5c_lote_1387_r1.json` → `distribucion_por_archivo` |
| `BD Egresos.xlsx` | `egresos` | 53 | 53 (100,00 %) | 0 (0,00 %) | 0 | 53 / 0 | `docs/mediciones/f5c_lote_1387_r1.json` → `distribucion_por_archivo` |
| `EJECUTADO VS META.xlsx` | `EJECUTADO` | 24 | 15 (62,50 %) | 9 (37,50 %) | 0 | 15 / 9 | `docs/mediciones/f5c_lote_1387_r1.json` → `distribucion_por_archivo` |

*Nota de muestreo:* `muestreo_por_archivo.criterio_documentado = false` (`docs/mediciones/f5c_lote_1387_r1.json`). Los topes `450/350/250/150/110/53/24` toman las primeras $N$ filas no vacías en orden de archivo, sin aleatorización ni estratificación.

### Tabla A.3: Ciclo Mensual Completo y Cumplimiento RNF-03 — Base: `f3_base` (`f5c_base.json`, `f5c_b7_corridas.json`, `f5c_klm.json`)

| ID | Métrica | Valor | `valor_docx` | Fuente (`docs/mediciones/` y ruta JSON) | Dónde va en tesis |
|---|---|---|---|---|---|
| A-20 | Archivos procesados en el ciclo mensual | 10 archivos (14.343 registros; 14.408 líneas BETO) | 10 / 14.343 / 14.408 | `docs/mediciones/f5c_base.json` → `carga.archivos_exitosos`, `carga.registros_detectados`, `corridas.0.etapas_s.lineas_leidas_beto` | Cap. IV Sec. 4.4 |
| A-21 | Hechos persistidos en el ciclo (`f3_base`) | 168.013 (166.983 acad. + 1.030 fin.) | 168.013 | `docs/mediciones/f5c_base.json` → `consolidacion.inserted_dw`, `consolidacion.inserted_academico`, `consolidacion.inserted_financiero` | Cap. IV Sec. 4.4 |
| A-22 | Bandeja HITL generada en el ciclo | 700 casos en 10 grupos | 700 / 10 | `docs/mediciones/f5c_base.json.huella.json` → `bandeja` | Cap. IV Sec. 4.4 |
| A-23 | Solo máquina, caché vacía (n = 3, media ± desv.) | **1.430,98 ± 365,09 s** (23,85 min) | 1.430,98 ± 365,09 s (23,85 min) | `docs/mediciones/f5c_b7_corridas.json` → `resumen.vacia_maquina_s` | Cap. IV Sec. 4.4; RNF-03 |
| A-24 | Solo máquina, caché llena (n = 3, media ± desv.) | **757,46 ± 15,39 s** (12,62 min) | 757,46 ± 15,39 s (12,62 min) | `docs/mediciones/f5c_b7_corridas.json` → `resumen.llena_maquina_s` | Cap. IV Sec. 4.4; RNF-03 |
| A-25 | Corridas limpias por condición | **n = 3** (huella idéntica en todas) | n = 3 | `docs/mediciones/f5c_b7_corridas.json` → `resumen.vacia_maquina_s.n`, `huella_unica_en_todas` | Cap. IV Sec. 4.4; RNF-03 |
| A-26 | Tiempo KLM con espera medida (`W = 2,5 s`, p95 `approve-group` Locust) | **474,0 s** (bloque 26,0 · fecha 11,2 · manual 435,5 · pag. 1,3) | 474,0 s | `docs/mediciones/f5c_klm.json` → `W_medido_p95_s`, `W_medido.klm_s` (de `docs/mediciones/f3v_locust.json` → `por_endpoint["POST /api/v1/dataops/review-tray/approve-group"].p95_ms` = 2.500,0 ms; `review-tray/grupos` = 35,0 ms; `agregado.p95_ms` = 34,0 ms) | Cap. IV Sec. 4.4; RNF-03 |
| A-27 | RNF-03 total (caché vacía + KLM, `W = 2,5 s`) | **1.904,98 s** (31,75 min; supera umbral 15/20 min) | 1.904,98 s (31,75 min) | `docs/mediciones/f5c_b7_corridas.json` → `resumen.vacia_mas_klm_s` | Cap. IV Sec. 4.4; RNF-03 |
| A-28 | RNF-03 total (caché llena + KLM, `W = 2,5 s`) | **1.231,46 s** (20,52 min; supera umbral 15/20 min) | 1.231,46 s (20,52 min) | `docs/mediciones/f5c_b7_corridas.json` → `resumen.llena_mas_klm_s` | Cap. IV Sec. 4.4; RNF-03 |
| A-29 | Sensibilidad KLM (`W = 0 s` / `W = 10 s`) | KLM: 294,0 s / 1.014,0 s | 294,0 s / 1.014,0 s | `docs/mediciones/f5c_klm.json` → `W_0.klm_s`, `W_10.klm_s` | Cap. IV Sec. 4.4 |
| A-30 | Filas en el DW al terminar el ciclo | `fact_evaluacion_docente` 163.182 · `fact_costo_programa` 1.371 · `fact_rendimiento_academico` 1.392 · `fact_situacion_financiera` 1.030 · `fact_marketing` 336 · `fact_rentabilidad` 95 · `fact_techo_convenio` 1 · `fact_planificacion_programa` 647 · `dim_origen_documental` 10 | 163.182 / 1.371 / 1.392 / 1.030 / 336 / 95 / 1 / 647 / 10 | `docs/mediciones/f5c_base.json` → `corridas.0.dw_despues` | Cap. IV Sec. 4.4 |

*Condiciones de la medición de tiempos:* 3 corridas limpias por condición (**n = 3**) sobre la copia tmpfs `dw_vacio` con la caché BETO vacía o llena, plan de energía «Alto rendimiento», equipo en corriente alterna y sin procesos ajenos pesados (`docs/mediciones/f3v_estado_maquina.json`, `docs/mediciones/f5c_b7_corridas.json`). Las cifras con `W = 10 s` son un escenario de sensibilidad, no la condición medida.

*Veredicto RNF-03 (< 15 min; aceptable < 20 min):* En `f3_base` (`docs/mediciones/f5c_b7_corridas.json`), solo máquina cumple con caché llena (`757,46 ± 15,39 s` = 12,62 min < 15 min), pero supera el umbral con caché vacía (`1.430,98 ± 365,09 s` = 23,85 min). Al sumar la intervención humana KLM (`474,0 s` con `W = 2,5 s`, impulsada por `67` casos manuales tras C-2/C-3), la caché llena da `1.231,46 s` (20,52 min) y la caché vacía `1.904,98 s` (31,75 min). **Actualización F9 (`docs/mediciones/f9_completo.json`):** tras optimizar `fila_resuelta_por_regla`, la carga histórica completa en caché fría (10 libros) baja a **`655,91 s` (`10,93 min` < `15 min`, `rnf03_cumplido_15m = true`)** (ver Tabla K.1).

---

## B. STAGING, IDEMPOTENCIA, EXCEPCIONES Y CONTENCIÓN DE CALIDAD

### Tabla B.1: Excepciones y Calidad en Lote Controlado — Base: `lote 1.387` (`f5c_lote_1387_r1.json`)

| ID | Métrica | Valor | `valor_docx` | Fuente (`docs/mediciones/` y ruta JSON) | Dónde va en tesis |
|---|---|---|---|---|---|
| B-01 | Excepciones de calidad que ingresaron al DW sin control | **0** de 268 registros (0,00 %) | 0 de 268 | `docs/mediciones/f5c_lote_1387_r1.json` → `excepciones.habrian_ingresado_al_dw_sin_control`, `excepciones.registros_afectados` | Cap. IV Sec. 4.3.1; Tabla 4.3 |
| B-02 | Total de entidades anómalas interceptadas | **554** entidades | 554 | `docs/mediciones/f5c_lote_1387_r1.json` → `excepciones.total_entidades` | Cap. IV Sec. 4.3.1; Tabla 4.3 |
| B-03 | Desglose por regla: `ETIQUETA_LIKERT` (descarte) | 283 entidades (110 registros) | 283 | `docs/mediciones/f5c_lote_1387_r1.json` → `excepciones.por_regla.ETIQUETA_LIKERT` | Tabla 4.3 |
| B-04 | Desglose por regla: `CORREO_NO_ES_NOMBRE` (descarte) | 154 entidades (154 registros) | 154 | `docs/mediciones/f5c_lote_1387_r1.json` → `excepciones.por_regla.CORREO_NO_ES_NOMBRE` | Tabla 4.3 |
| B-05 | Desglose por regla: `COLUMNA_DE_COMENTARIO` (descarte) | 87 entidades (87 registros) | 87 | `docs/mediciones/f5c_lote_1387_r1.json` → `excepciones.por_regla.COLUMNA_DE_COMENTARIO` | Tabla 4.3 |
| B-06 | Desglose por regla: `PER_SIN_FORMA_NOMBRE` (log+descarte) | 25 entidades (25 registros) | 25 | `docs/mediciones/f5c_lote_1387_r1.json` → `excepciones.por_regla.PER_SIN_FORMA_NOMBRE` | Tabla 4.3 |
| B-07 | Desglose por regla: `PERSONA_SIN_COINCIDENCIA` (HITL) | 5 entidades (5 registros) | 5 | `docs/mediciones/f5c_lote_1387_r1.json` → `excepciones.por_regla.PERSONA_SIN_COINCIDENCIA` | Tabla 4.3 |

### Tabla B.2: Staging, Bitácora B-9, `fk_estado` e Idempotencia — Base: `f3_base` (`f3s_extraccion_f3base.json`, `f3s_cobertura_por_archivo.json`)

| ID | Métrica | Valor | `valor_docx` | Fuente (`docs/mediciones/` y ruta JSON) | Dónde va en tesis |
|---|---|---|---|---|---|
| B-08 | Filas totales en `stg_entidad_no_resuelta` | **3.935** (32 pendientes `resuelto=false`, 3.903 resueltas) | 3.935 (32 pend.) | `docs/mediciones/f3s_extraccion_f3base.json` → `stg_entidad_no_resuelta` | Cap. IV Sec. 4.3.3; Gráf. 4.1 |
| B-09 | Pendientes por motivo (`resuelto=false`): `BAJA_CONFIANZA_IA` / `CI_DUDOSA` / `CI_NOMBRE_DISCORDANTE` / `HOMONIMIA` | 27 / 2 / 2 / 1 (total 32 = KPI-18) | 27 / 2 / 2 / 1 | `docs/mediciones/f3s_extraccion_f3base.json` → `stg_entidad_no_resuelta` | Cap. IV Sec. 4.3.3 |
| B-10 | Filas en `log_inconsistencias` (bitácora B-9) | **5.090** (0 descartes sin bitácora) | 5.090 | `docs/mediciones/f3s_extraccion_f3base.json` → `log_inconsistencias`; `docs/mediciones/f3s_cobertura_por_archivo.json` → `totales.sin_explicar` | Cap. IV Sec. 4.3.1 |
| B-11 | Distribución `fk_estado` en `fact_rendimiento_academico` | Estado A: 1.385 · Estado B: 7 (total 1.392) | 1.385 / 7 | `docs/mediciones/f3s_extraccion_f3base.json` → `fk_estado.fact_rendimiento_academico` | Cap. III Sec. 3.3.4 |
| B-12 | Distribución `fk_estado` en `fact_situacion_financiera` | Estado A: 725 (total 725) | 725 | `docs/mediciones/f3s_extraccion_f3base.json` → `fk_estado.fact_situacion_financiera` | Cap. III Sec. 3.3.4 |
| B-13 | Distribución `fk_estado` en `dim_estudiante` / `dim_docente` | Est.: A 14.566, B 412 (14.978) · Doc.: A 638, B 35 (673) | 14.978 / 673 | `docs/mediciones/f3s_extraccion_f3base.json` → `fk_estado.dim_estudiante`, `fk_estado.dim_docente` | Cap. III Sec. 3.3.4 |
| B-14 | Filas nuevas en prueba de idempotencia estricta | 0 filas | 0 | `docs/evidencias/ciclo_idempotencia_hitl.json` (`backend/services/dw_loader.py:974`) | Cap. IV Sec. 4.3.4 |
| B-15 | Extensiones admitidas por el pipeline | `.xlsx`, `.csv` | `.xlsx`, `.csv` | `backend/services/ingestion_service.py:17` (`ALLOWED_EXTENSIONS`) | Cap. III Sec. 3.2.1 |
| B-16 | Cobertura por archivo del ciclo (10 de 10 libros con balance cerrado) | 12.992 líneas leídas = 8.643 con registros + 4.318 ruido con motivo + 31 en bandeja; **0 sin explicar** | 12.992 / 0 | `docs/mediciones/f3s_cobertura_por_archivo.json` → `totales` | Cap. IV Sec. 4.3.1 |

---

## C. ABLACIÓN A/B/C, MATRIZ DE CONFUSIÓN Y CORPUS BETO

### Tabla C.1: Evaluación de Ablación (Semilla 42) — Base: `evaluación BETO` (`f3r_ablacion.json`)

| Dataset | Modo | Criterio | TP | FP | FN | Soporte | Precisión | Recall | F1 (`valor_docx`) | Fuente (`docs/mediciones/` y ruta JSON) |
|---|---|---|---|---|---|---|---|---|---|---|
| `gold_510` | A (Reglas) | Estricto | 510 | 0 | 0 | 510 | 100,00 % | 100,00 % | **100,00 %** | `docs/mediciones/f3r_ablacion.json` → `filas.0.f1` |
| `gold_510` | A (Reglas) | Relajado | 510 | 0 | 0 | 510 | 100,00 % | 100,00 % | **100,00 %** | `docs/mediciones/f3r_ablacion.json` → `filas.1.f1` |
| `gold_510` | B (Híbrido) | Estricto | 510 | 0 | 0 | 510 | 100,00 % | 100,00 % | **100,00 %** | `docs/mediciones/f3r_ablacion.json` → `filas.2.f1` |
| `gold_510` | B (Híbrido) | Relajado | 510 | 0 | 0 | 510 | 100,00 % | 100,00 % | **100,00 %** | `docs/mediciones/f3r_ablacion.json` → `filas.3.f1` |
| `gold_510` | C (BETO) | Estricto | 503 | 14 | 7 | 510 | 97,29 % | 98,63 % | **97,96 %** (`0,979552`) | `docs/mediciones/f3r_ablacion.json` → `filas.4.f1` |
| `gold_510` | C (BETO) | Relajado | 510 | 6 | 0 | 510 | 98,84 % | 100,00 % | **99,42 %** (`0,9942`) | `docs/mediciones/f3r_ablacion.json` → `filas.5.f1` |
| `layouts_5` | A (Reglas) | Estricto | 11 | 1 | 61 | 72 | 91,67 % | 15,28 % | **26,19 %** | `docs/mediciones/f3r_ablacion.json` → `filas.6.f1` |
| `layouts_5` | A (Reglas) | Relajado | 12 | 0 | 60 | 72 | 100,00 % | 16,67 % | **28,57 %** | `docs/mediciones/f3r_ablacion.json` → `filas.7.f1` |
| `layouts_5` | B (Híbrido) | Estricto | 31 | 51 | 41 | 72 | 37,80 % | 43,06 % | **40,26 %** | `docs/mediciones/f3r_ablacion.json` → `filas.8.f1` |
| `layouts_5` | B (Híbrido) | Relajado | 52 | 17 | 20 | 72 | 75,36 % | 72,22 % | **73,76 %** | `docs/mediciones/f3r_ablacion.json` → `filas.9.f1` |
| `layouts_5` | C (BETO) | Estricto | 26 | 59 | 46 | 72 | 30,59 % | 36,11 % | **33,12 %** | `docs/mediciones/f3r_ablacion.json` → `filas.10.f1` |
| `layouts_5` | C (BETO) | Relajado | 49 | 15 | 23 | 72 | 76,56 % | 68,06 % | **72,06 %** | `docs/mediciones/f3r_ablacion.json` → `filas.11.f1` |

*Nota sobre F1 = 75,66 % (J1-15):* **RETIRADA**. No existe en `docs/mediciones/` ni corresponde al modelo BETO vigente (`docs/mediciones/f3r_evidencias_sueltas.json` → `f1_75_66_pct.dictamen`).

### Tabla C.2: Matriz de Confusión por Tipo de Entidad (`gold_510`, Modo C estricto, Gráfico 3.1) — Base: `evaluación BETO` (`f3r_matriz_confusion.json`)

| Tipo de entidad | Soporte | TP | FN | FP | Precisión | Recall | F1 estricto | F1 relajado | Fuente (`docs/mediciones/` y ruta JSON) |
|---|---|---|---|---|---|---|---|---|---|
| `MODULO` | 150 | 150 | 0 | 0 | 100,00 % | 100,00 % | 100,00 % | 100,00 % | `docs/mediciones/f3r_matriz_confusion.json` → `por_tipo_estricto.MODULO` |
| `PER_DOCENTE` | 50 | 50 | 0 | 0 | 100,00 % | 100,00 % | 100,00 % | 100,00 % | `docs/mediciones/f3r_matriz_confusion.json` → `por_tipo_estricto.PER_DOCENTE` |
| `PER_ESTUDIANTE` | 130 | 129 | 1 | 1 | 99,23 % | 99,23 % | 99,23 % | 100,00 % | `docs/mediciones/f3r_matriz_confusion.json` → `por_tipo_estricto.PER_ESTUDIANTE` |
| `PROGRAMA` | 180 | 174 | 6 | 13 | 93,05 % | 96,67 % | 94,82 % | 98,36 % | `docs/mediciones/f3r_matriz_confusion.json` → `por_tipo_estricto.PROGRAMA` |
| **TOTAL** | **510** | **503** | **7** | **14** | **97,29 %** | **98,63 %** | **97,96 %** | **99,42 %** | `docs/mediciones/f3r_matriz_confusion.json` → `suma_tp_estricto` |

*Explicación 503 vs 510:* Bajo criterio estricto `seqeval`, los 7 FN corresponden a límites de *span* en `PROGRAMA` (6) y `PER_ESTUDIANTE` (1); bajo criterio relajado, las 510 entidades `gold` coinciden (`TP=510`, `FN=0`).

### Tabla C.3: Corpus de Entrenamiento, `gold_510` e Inventario de Producción — Base: `corpus BETO` (`f3r_evidencias_sueltas.json`)

| Conjunto / Inventario | Filas / Libros | Entidades / Hojas | Detalle verificado | Fuente (`docs/mediciones/` y ruta JSON) |
|---|---|---|---|---|
| `train` (corpus vigente) | 1.400 filas | 5.600 entidades (1.400 c/u) | 2.447 personas únicas IOB2; partición por persona antes del aumento (`preparar_corpus_robusto.py:101-110`) | `docs/mediciones/f3r_evidencias_sueltas.json` → `anotacion_y_corpus_modelo_vigente.train` |
| `dev` (corpus vigente) | 350 filas | 1.400 entidades (350 c/u) | 597 personas únicas IOB2; fuga = 0 en 4 niveles | `docs/mediciones/f3r_evidencias_sueltas.json` → `anotacion_y_corpus_modelo_vigente.dev` |
| `gold_510` | 180 filas | 510 entidades | 83 personas únicas; `PER_ESTUDIANTE` 130, `PROGRAMA` 180, `MODULO` 150, `PER_DOCENTE` 50 | `docs/mediciones/f3r_evidencias_sueltas.json` → `anotacion_y_corpus_modelo_vigente.gold_510` |
| Corpus `uploads/data/` | 10 libros | 60 hojas · 90.538 procesables | Inventario actual con `scripts/inventario_corpus.py` | `docs/mediciones/f3r_evidencias_sueltas.json` → `inventario_corpus_uploads_data` |

---

## D. PRUEBAS AUTOMATIZADAS, COBERTURA Y PRUEBAS DE CARGA / CAJA NEGRA

### Tabla D.1: Suite `pytest` y Cobertura — Base: `suite pytest` sobre el commit `84cd352` en worktree limpio (`f5c_pruebas.json`)

| Métrica | Valor | `valor_docx` | Fuente (`docs/mediciones/` y ruta JSON) | Dónde va en tesis |
|---|---|---|---|---|
| Pruebas colectadas | 943 | 943 | `docs/mediciones/f5c_pruebas.json` → `colectadas` | Cap. III / Cap. IV; Tabla 3.29 |
| Aprobadas (`passed`) | **924** | 924 | `docs/mediciones/f5c_pruebas.json` → `passed` | Tabla 3.29 |
| Fallidas (`failed`) | **0** | 0 | `docs/mediciones/f5c_pruebas.json` → `failed` | Tabla 3.29 |
| Omitidas (`skipped`) | 12 (11 `test_production_readiness.py` por `READINESS_*`; 1 `test_purga_cache.py` por puerto tmpfs) | 12 | `docs/mediciones/f5c_pruebas.json` → `skipped`, `skips_con_motivo` | Tabla 3.29 |
| Esperadas fallidas (`xfailed`) | 7 (hallazgos `HW-IC`, `HW-GAP`, `OLS-CAGR`, `FK-*`) | 7 | `docs/mediciones/f5c_pruebas.json` → `xfailed` | Tabla 3.29 |
| Cobertura total (`backend` + `pipeline`) | **72,69 %** (11.535 / 15.869 sentencias) | 72,69 % | `docs/mediciones/f5c_pruebas.json` → `cobertura_total` | Cap. IV; Tabla 3.30 |
| Frontend (`vitest` / `vite build`) | 16 archivos (87/87 passed) · 2.035 módulos (0 errores) | 87 / 87 | `docs/mediciones/f5c_pruebas.json` → `frontend` | Cap. IV |

*Condiciones de la suite:* se ejecuta en un worktree limpio contra `beto_pg_tmpfs/giragroup_dw` y los 10 archivos de `uploads/data/`. El detalle por archivo está en `docs/mediciones/f3v_cobertura_archivos.csv`.

### Tabla D.2: Pruebas de Carga (Locust) y Caja Negra (Newman) — Base: `f3v_completo` (`f3v_locust.json`, `f3v_newman.json`)

| Herramienta | Métrica | Valor | `valor_docx` | Fuente (`docs/mediciones/` y ruta JSON) |
|---|---|---|---|---|
| Locust (50 usuarios, rampa 5/s, 30 s) | Peticiones totales / Fallos | 1.121 / 0 (0,00 %) | 1.121 / 0 | `docs/mediciones/f3v_locust.json` → `agregado.requests`, `agregado.failures` |
| Locust | RPS / Latencia p50 / p95 / p99 | 41,27 RPS · 10,0 / 34,0 / 290,0 ms | 41,27 RPS · 34 ms p95 | `docs/mediciones/f3v_locust.json` → `agregado.rps`, `agregado.p50_ms`, `agregado.p95_ms`, `agregado.p99_ms` |
| Newman (`postman_collection.json`) | Solicitudes / Aserciones totales / Fallidas | 11 req · 24 aserciones · 0 fallidas | 11 / 24 / 0 | `docs/mediciones/f3v_newman.json` → `run_stats` |

*Condiciones de Locust:* escenario de `tests/carga/locustfile.py` (Tabla 3.32) contra uvicorn local sobre la copia tmpfs resultante de la corrida con caché llena, no sobre la DW viva (`docs/mediciones/f3v_locust.json` → `parametros`).

*Condiciones de Newman:* la colección `docs/api/postman_collection.json` se corre contra una API de prueba (`APP_ENV=test`) sobre la copia tmpfs, con un usuario QA sembrado solo en la copia y con las cabeceras de seguridad que agrega el gateway (`gateway/nginx.conf`, líneas 61-64), a través de un proxy de prueba. La credencial de prueba (`qa_password`) se pasa como variable de entorno de Newman (`--env-var`) y no se escribe en archivos; sin ella el login responde 401. La sonda de cabeceras OWASP apunta al gateway, no a uvicorn, porque las cabeceras las agrega el gateway. La colección no tiene peticiones ni aserciones modificadas (`docs/mediciones/f3s_newman_diff.txt`); la petición 2 ejecuta la rama de verificación 2FA con OTP de pruebas y aporta 3 aserciones (`docs/mediciones/f3v_newman.json` → `run_stats`).

---

## E. PRONÓSTICO DE MATRÍCULA (HOLT-WINTERS) Y RECAUDACIÓN (OLS)

**Decisión confirmada (Opción 1):** La Sección E se calcula sobre el `snapshot 10-nov` (`n = 43` meses en `fact_marketing`, `2022-11` a `2026-05`).  
**Nota obligatoria:** *«f3_base corresponde al ciclo mensual 2026-03 (recortes en output/backups/f0_lote/slices/) que mide RNF-03; no contiene serie histórica»* (`docs/mediciones/f3r_matricula_lote.json`).

### Tabla E.1: Pronóstico de Matrícula (`ALUMNOS_GLOBAL`) — Base: `snapshot 10-nov` (`f3r_hw_matricula.json`)

| ID | Métrica | Valor | `valor_docx` | Fuente (`docs/mediciones/` y ruta JSON) | Dónde va en tesis |
|---|---|---|---|---|---|
| E-01 | Método vigente | Holt-Winters tendencia aditiva amortiguada, estacionalidad aditiva ($m=12$) | HW amortiguado | `pipeline/analytics/forecasting_holtwinters.py:117-119` (`damped_trend=True`) | Cap. III; Tabla 3.24 |
| E-02 | Observaciones históricas (`fact_marketing`) | **43 meses** (`2022-11` a `2026-05`) | 43 meses | `docs/mediciones/f3r_hw_matricula.json` → `n_observaciones` | Tabla 3.24; Cap. IV |
| E-03 | Parámetros ajustados ($\alpha / \beta / \gamma / \phi$) | 0,0000 / 0,0000 / 0,0000 / **0,9072** | 0,0 / 0,0 / 0,0 / 0,9072 | `docs/mediciones/f3r_hw_matricula.json` → `parametros_hw` | Tabla 3.24 |
| E-04 | RMSE / AIC del ajuste | **59,57** / **385,49** | 59,57 / 385,49 | `docs/mediciones/f3r_hw_matricula.json` → `rmse`, `aic` | Tabla 3.24 |
| E-05 | MAPE en hold-out (6 meses) | **15,67 %** | 15,67 % | `docs/mediciones/f3r_hw_matricula.json` → `mape_holdout_6m_pct` | Tabla 3.24; Tabla 4.7 |
| E-06 | Cobertura empírica hold-out IC 80 % / IC 95 % | **66,67 %** (4/6) / **100,00 %** (6/6) | 66,67 % / 100,00 % | `docs/mediciones/f3r_hw_matricula.json` → `cobertura_empirica_holdout_6m` | Cap. IV |
| E-07 | Proyección `2026-06` a `2026-11` (`forecast`) | 396,44 · 423,55 · 479,38 · 440,72 · 416,17 · 402,81 | 396,44–402,81 | `docs/mediciones/f3r_hw_matricula.json` → `forecast` | Cap. IV; Gráf. 3.4 |

### Tabla E.2: Pronóstico de Recaudación (`META_MENSUAL_PROGRAMAS` y `META_ANUAL`) — Base: `snapshot 10-nov` (`f3r_ols_snapshot.json`, `f3r_b5_snapshot_sql.txt`)

| ID | Serie / Métrica | Valor | `valor_docx` | Fuente (`docs/mediciones/` y ruta JSON) |
|---|---|---|---|---|
| E-08 | `META_MENSUAL_PROGRAMAS` (HW, `simulacion_param_aditivo_n1000`) | RMSE **184.571,04** · AIC **1.198,08** | 184.571,04 / 1.198,08 | `docs/mediciones/f3r_ols_snapshot.json` → `mensual.data.rmse`, `mensual.data.aic` |
| E-09 | `META_ANUAL` (OLS descriptiva, $N=3$: 2023–2025) | Pendiente **+2.436.141,68 Bs/año** · CAGR **26,76 %** | +2.436.141,68 Bs/año | `docs/mediciones/f3r_ols_snapshot.json` → `anual.data.pendiente_anual_bs`, `cagr_historico_pct` |
| E-10 | Proyección OLS anual `2026` / `2027` (banda ±5 %) | **15.183.417,34 Bs** / **17.619.559,02 Bs** | 15.183.417,34 / 17.619.559,02 | `docs/mediciones/f3r_ols_snapshot.json` → `anual.data.proyecciones` |
| E-11 | Conciliación SQL 2025 (`PROGRAMAS`, `f0_b5_consultas.sql`) | Observado **12.907.977,61 Bs** · Ajustado **12.747.275,66 Bs** ($\Delta = -1,24\%$) | 12.907.977,61 Bs | `docs/mediciones/f3r_b5_snapshot_sql.txt` |

---

## F. INDICADORES (KPI) Y SISTEMA DE ALERTAS TEMPRANAS

De acuerdo con la **Decisión 1**, los indicadores de negocio (`KPI-01`..`09`, `KPI-12`..`17`, `KPI-19`..`22`) provienen del `snapshot 10-nov` (`f3r_snapshot_kpi.json`), mientras que los dependientes del modelo (`KPI-10`, `KPI-11`, `KPI-18`) y el cuadre de `KPI-15` por fila de origen provienen de `f3_base` / `lote 1.387`. En el snapshot, `KPI-10`, `KPI-11` y `KPI-18` están marcados `no_usar_dependiente_del_modelo`.

### Tabla F.1: KPIs de Negocio (Gestiones 2024, 2025 y 2026) — Base: `giragroup_db` recarga `FU-L9` (`adw_l9_remedicion_final.csv`)

| Código | Indicador | Gestión 2024 | Gestión 2025 | Gestión 2026 | `valor_docx` (2025) | Fuente (`docs/mediciones/`) |
|---|---|---|---|---|---|---|
| KPI-01 | Ticket promedio por estudiante (Bs) | 2.279,51 | **2.571,95** | 2.325,62 | 2.571,95 | `docs/mediciones/adw_l9_remedicion_final.csv` (denominador `pagantes`) |
| KPI-02 | Cumplimiento de meta del último mes (%) | N/D (sin meta mensual) | **157,48 %** | 100,99 % | 157,48 % | `docs/mediciones/adw_l9_remedicion_final.csv` |
| KPI-03 | Cumplimiento de meta a la fecha (%) | 102,26 % | **110,54 %** | 109,08 % | 110,54 % | `docs/mediciones/adw_l9_remedicion_final.csv` |
| KPI-04 | Estudiantes con riesgo financiero (cant.) | 362 | **808** | 641 | 808 | `docs/mediciones/adw_l9_remedicion_final.csv` |
| KPI-05 | Estudiantes en mora (%) | 10,60 % | **18,46 %** | 37,75 % | 18,46 % | `docs/mediciones/adw_l9_remedicion_final.csv` |
| KPI-06 | Conversión de admisiones (%) | N/D | **3,85 %** | 2,94 % | 3,85 % | `docs/mediciones/adw_l9_remedicion_final.csv` |
| KPI-07 | Promedio de calificaciones (pts) | 82,32 | **81,81** | N/D | 81,81 | `docs/mediciones/adw_l9_remedicion_final.csv` |
| KPI-08 | Tasa de aprobación (nota ≥ 70) | 84,98 % | **85,62 %** | N/D | 85,62 % | `docs/mediciones/adw_l9_remedicion_final.csv` |
| KPI-09 | Estudiantes en riesgo académico (cant.) | 667 | **445** | N/D | 445 | `docs/mediciones/adw_l9_remedicion_final.csv` |
| KPI-10 | Confianza media de extracción (%) | 84,09 % | **83,92 %** | N/D | 83,92 % | `docs/mediciones/adw_l9_remedicion_final.csv` |
| KPI-11 | Automatización directa (%) | 54,34 % | **51,51 %** | N/D | 51,51 % | `docs/mediciones/adw_l9_remedicion_final.csv` |
| KPI-12 | Variación interanual de ingresos (%) | 17,60 % | **28,10 %** | 20,61 % | 28,10 % | `docs/mediciones/adw_l9_remedicion_final.csv` |
| KPI-13 | Avance sobre la meta anual (%) | 102,26 % | **110,54 %** | 31,69 % | 110,54 % | `docs/mediciones/adw_l9_remedicion_final.csv` |
| KPI-14 | Brecha a la meta anual (Bs) | 0,00 | **0,00** | 12.278.356,22 | 0,00 | `docs/mediciones/adw_l9_remedicion_final.csv` |
| KPI-15 | Cartera vencida (%) | 69,61 % | **78,06 %** | 23,07 % | 78,06 % | `docs/mediciones/adw_l9_remedicion_final.csv` |
| KPI-16 | Tasa de deserción (%) | 5,38 % | **6,47 %** | N/D | 6,47 % | `docs/mediciones/adw_l9_remedicion_final.csv` |
| KPI-17 | Estudiantes en prioridad crítica (cant.) | 66 | **116** | N/D | 116 | `docs/mediciones/adw_l9_remedicion_final.csv` |
| KPI-18 | Pendientes de revisión humana (cant.) | 204 | **948** | 364 | 948 | `docs/mediciones/adw_l9_remedicion_final.csv` |
| KPI-19 | Satisfacción con los docentes (%) | 81,10 % | **82,00 %** | 84,01 % | 82,00 % | `docs/mediciones/adw_l9_remedicion_final.csv` |
| KPI-20 | Satisfacción institucional (%) | 79,72 % | **77,75 %** | 80,20 % | 77,75 % | `docs/mediciones/adw_l9_remedicion_final.csv` |
| KPI-21 | Matrícula efectiva (cant.) | 3.773 | **3.571** | N/D | 3.571 | `docs/mediciones/adw_l9_remedicion_final.csv` |
| KPI-22 | Inscritos por convenio (cant.) | 1.631 | **2.609** | N/D | 2.609 | `docs/mediciones/adw_l9_remedicion_final.csv` |
| KPI-23 | Cumplimiento de inicios planificados (%) | 100,00 % | **99,77 %** | 46,62 % | 99,77 % | `docs/mediciones/adw_l9_remedicion_final.csv` |

*Notas de recongelado (`FU-L9 + ADW-L9`, 21-nov-2026):* `KPI-01` usa `pagantes` como denominador único (2023–2026); `KPI-02` 2024 es N/D por ausencia de meta mensual en la fuente (DA4); `KPI-09` y `KPI-17` en 2026 son N/D por ausencia de registros académicos (guarda NULL en `bi.vw_cmi_valores`); respuestas de encuestas sin fecha quedan con `id_tiempo = NULL` (`12.937` filas fuera de gestión); NPS queda solo informativo (`23` KPI en `bi.ref_kpi`); los 9 KPI sin umbral y `KPI-13` se mantienen sin cambios (DA5). **DA8 (pronóstico financiero todas las categorías):** pendiente OLS anual `+2.360.251,66 Bs/año`, CAGR `22,85 %`, meta anual 2026 `17.973.400 Bs`, recaudado acumulado 2026 `5.695.043,78 Bs` (`docs/mediciones/adw_da8_forecast_despues.json`).

### Tabla F.2: KPIs Operativos y Cuadre de KPI-15 — Base: `f3_base` (`f3s_extraccion_f3base.json`, `f3s_kpi15_cuadre.json`)

| Código / Métrica | Valor | `valor_docx` | Fuente (`docs/mediciones/` y ruta JSON) |
|---|---|---|---|
| KPI-10 (`f3_base` 2024 / 2025) | 84,32 % / 84,64 % | 84,32 % / 84,64 % | `docs/mediciones/f3s_extraccion_f3base.json` → `kpis_vw_cmi_valores` |
| KPI-11 (`f3_base` 2024 / 2025) | 56,39 % / 54,85 % | 56,39 % / 54,85 % | `docs/mediciones/f3s_extraccion_f3base.json` → `kpis_vw_cmi_valores` |
| KPI-15 (gestión 2025 en `f3_base`, vista `vw_cmi_valores`) | **73,44 %** | 73,44 % | `docs/mediciones/f3s_extraccion_f3base.json` → `kpis_vw_cmi_valores`; `docs/mediciones/f3s_kpi15_cuadre.json` → `kpi_15_vw_cmi_valores` |
| Cuadre KPI-15 por fila de origen (`fact_situacion_financiera`; `estado_cartera` derivado de `TIPO DE CARTERA`, `DIAS DE MORA` y `RANGO MORA`, `consolidacion.py::derivar_estado_cartera`) | **500** Mora · **7** Previsionable · **218** Vigente (total 725; $\Delta=0$) | 500 / 7 / 218 | `docs/mediciones/f3s_kpi15_cuadre.json` → `por_estado_cartera`, `desajuste_conteo` |
| KPI-18 (`f3_base` 2026) | **32** | 32 | `docs/mediciones/f3s_extraccion_f3base.json` → `kpis_vw_cmi_valores` |

**Fórmula oficial de `KPI-15` (`T-4`):** `bi.vw_cmi_valores` (`006_capa_semantica_cmi.sql:73,268-269`) calcula `100,0 * SUM(monto_deuda)` en `Mora`/`En Mora`/`Previsionable` sobre `SUM(monto_deuda)` por gestión (`73,44 %` en 2025 sobre `f3_base`); el conteo `(500+7)/725 = 69,93 %` corresponde únicamente a filas acumuladas de `fact_situacion_financiera` (`docs/mediciones/f3t_kpi15_formula.json`).

### Tabla F.3: Alertas Tempranas y Cartera en Mora — Base: `snapshot 10-nov` (`f3r_snapshot_alertas.json`)

| Métrica | Valor | `valor_docx` | Fuente (`docs/mediciones/` y ruta JSON) |
|---|---|---|---|
| Total de alertas emitidas | **7.094** | 7.094 | `docs/mediciones/f3r_snapshot_alertas.json` → `total_alertas` |
| Por severidad (`CRITICAL` / `WARNING`) | 4.201 / 2.893 | 4.201 / 2.893 | `docs/mediciones/f3r_snapshot_alertas.json` → `por_severidad` |
| Por tipo (`ACADEMICO` / `FINANCIERO` / `DATAOPS_CALIDAD` / `RIESGO_CRUZADO`) | 3.942 / 1.806 / 1.044 / 302 | 3.942 / 1.806 / 1.044 / 302 | `docs/mediciones/f3r_snapshot_alertas.json` → `por_tipo` |
| Cartera en mora: estudiantes distintos / filas / deuda | **2.498** est. · **2.574** filas · **692.957,88 Bs** | 2.498 / 692.957,88 Bs | `docs/mediciones/f3r_snapshot_alertas.json` → `mora_estudiantes_distintos`, `mora_monto_deuda` |

### Tabla F.4: Planificación y KPI-23 — Base: `f5v_completo` (`f5v_completo.json`, `f5v_kpi23_serie.json`)

| Métrica | Valor | `valor_docx` | Fuente (`docs/mediciones/` y ruta JSON) |
|---|---|---|---|
| `fact_planificacion_programa` (filas cargadas) | **1.663** (18 hojas mensuales + `Programas Notificados`; 0 borradores) | 1.663 | `docs/mediciones/f5v_completo.json` → `conteos.fact_planificacion_programa` |
| `dim_meta` (Informe Gestión) | **58** (`PLAN_INGRESO_TOTAL` 24 · `PLAN_INGRESO_TECHOS_PROYECTADO` 10 · `OKR_APERTURAS` 24) | 58 | `docs/mediciones/f5v_completo.json` → `conteos.dim_meta` |
| `KPI-23` Gestión 2024 / 2025 / 2026 | **100,00 %** (VERDE) / **99,77 %** (VERDE) / **46,62 %** (ROJO) | 100,00 % / 99,77 % / 46,62 % | `docs/mediciones/f5v_kpi23_serie.json` → `kpi23_por_gestion` |

---

## G. INFRAESTRUCTURA, INVENTARIO DE TABLAS Y RUTAS DE LA API

### Tabla G.1: Inventario del Data Warehouse y API (`f3v_invariantes.json`, `f3r_inventario_api.json`)

| Componente | Valor | `valor_docx` | Fuente (`docs/mediciones/` y ruta JSON) |
|---|---|---|---|
| Tablas base y vistas del DW | **51** tablas base + **10** vistas `bi` (10 hechos, 7 dimensiones, 1 puente; 23 KPI en `bi.ref_kpi`) | 51 tablas + 10 vistas + 23 KPI | `docs/mediciones/f3v_invariantes.json` → `invariantes_declarados` |
| `dim_tiempo` (filas y rango) | **2.230** filas (`2005-02-05` a `2034-01-12`) | 2.230 (2005–2034) | `docs/mediciones/f3s_extraccion_f3base.json` → `dim_tiempo` |
| `schema_migrations` | **17** migraciones (incluye `018` y `019` de Diseño B; solo varía `applied_at`, no afecta datos) | 17 | `docs/mediciones/f5c_base.json.huella.json` → `tablas.schema_migrations.filas` |
| Decoradores de rutas API | **136** (`backend/routers` 115 + `main.py` 2 + `auth` 11 + `notif` 6 + `audit` 2) | 136 | `docs/mediciones/f3r_inventario_api.json` → `total_decoradores_ruta` |
| Healthchecks Docker (`docker-compose.yml`) | 2 de 9 contenedores (`db` y `catalog_db`) | 2 de 9 | `docker-compose.yml:17,41` |

---

## H. DEFECTOS, INCONSISTENCIAS Y LIMITACIONES REGISTRADAS

### Tabla H.1: Defectos corregidos — Base: `f3_base` (`f3s_dw_vacio.json`, `f3s_d_a4.json`, `f3s_d_a8a.json`)

| ID | Componente / Archivo | Estado | Comportamiento vigente | Cifras en `f3_base` | Fuente (`docs/mediciones/` / código) |
|---|---|---|---|---|---|
| `D-A9` | `dw_vacio` y `public.carga_fila_origen` | Corregido | `scripts/aislada_tmpfs.sh` (subcomando `vacio`) trunca `public.carga_fila_origen`, `fact_costo_programa`, `fact_techo_convenio` y `cache_indice_beto`; `dw_vacio` conserva las dimensiones del snapshot (por ejemplo `dim_estudiante` = 14.078) y deja en 0 hechos, staging, logs y `carga_fila_origen`. | `carga_fila_origen` parte en 0 y termina el ciclo con 782 filas. | `docs/mediciones/f3s_dw_vacio.json`; `docs/mediciones/f3s_base.json.huella.json` → `tablas.carga_fila_origen` |
| `D-A4` | `Experiencia Docente 2.0.xlsx` | Corregido | Las hojas con `staging_registros_crudos.categoria = 'evaluacion_docente'` se rutean como `EVALUACION_DOCENTE` aunque el libro esté registrado con `tipo_fuente='ACTA'` (`consolidacion.py:179-182`). Cascada y umbrales intactos. Prueba: `tests/f3s/test_d_a4_evaluacion_en_libro_acta.py`. | El archivo aporta 29.866 hechos a `fact_evaluacion_docente` (104.939 en total) desde 1.137 filas del recorte, con 0 sin explicar. | `docs/mediciones/f3s_d_a4.json` |
| `D-A8a` | `EJECUTADO VS META.xlsx` | Corregido | Las filas agregadas (`PROGRAMAS JUNIO`, `TECHOS/CERRADOS FEBRERO/ABRIL/OCTUBRE`) las resuelve la regla de rentabilidad (`fila_resuelta_por_regla` en `extraccion_por_encabezado.py`, `indices_cascada` en `confianza_service.py`): BETO no las recibe y toman la banda CONSOLIDADO. Prueba: `tests/f3s/test_d_a8a_metas_no_van_a_beto.py`. | `fact_rentabilidad` = 95 (esperado 95); 0 filas `ESTUDIANTE` de ese archivo en `stg_entidad_no_resuelta`. | `docs/mediciones/f3s_d_a8a.json` → `resultado` |
| `D-T1` | `BD Techos.xlsx` y `fila_resuelta_por_regla` | Corregido | `fila_resuelta_por_regla` (`extraccion_por_encabezado.py:767-780`) exime del índice de persona a toda fila convertida en hecho por regla estructural en `rentabilidad`, `marketing` o `admision` (incluida `registros_techo_convenio`). Prueba: `tests/f3t/test_d_t1_convenios_en_marketing.py`. | `BD Techos.xlsx` completo en tmpfs: 207 filas procesadas (`207` `inserted_dw`, `206` `fact_techo_convenio`, `0` staging `ESTUDIANTE`, `0` sin explicar). | `docs/mediciones/f3t_d_t1.json`; `docs/mediciones/f3t_huella_post_d_t1.json` |
| `V-1` | `dim_modulo` determinista (`dw_loader.py`) | Corregido | `ORDER BY id_modulo` en cada `.first()` de `resolver_o_crear_modulo` y desempate estable `(puntaje -> id_modulo menor)` en `_fuzzy_best_match`; aplicado también a docente, estudiante, institución y categoría. | `fact_marketing` determinista (15.183 inscritos invariantes; 4/4 pruebas en `tests/f3v/test_determinismo_f3v.py`). | `docs/mediciones/f3v_determinismo.json` |
| `V-2` | Metas financieras por estructura (`dw_loader.py`) | Corregido | Precedencia por estructura (`metas y ejecutado por categoría y mes` = 2; otras = 1; `PLANIFICACION` = 0) y por fecha más reciente entre libros del mismo tipo, registrada en `log_inconsistencias`. | 0 condiciones por nombre de archivo (`EJECUTADO VS META`); 8/8 pruebas en `tests/f3v/test_metas_por_estructura.py`. | `docs/mediciones/f3v_metas_por_estructura.json` |
| `V-3/4` | `PLANIFICACION` y `KPI-23` | Implementado | `fact_planificacion_programa`, `bi.vw_planificacion_ejecucion_mensual` y `KPI-23` en `bi.ref_kpi` (85 % / 60 %); `Informe Gestión` en `dim_meta` sin sumarse a `fact_rentabilidad`. | `1.663` filas y `58` metas en `f3v_completo`; 23 KPI en `/api/v1/cmi/scorecard`. | `docs/mediciones/f3v_planificacion_carga.json`; `docs/mediciones/f3v_kpi23.json` |

### Tabla H.2: Limitaciones declaradas — Base: `f3_base` (`f3s_extraccion_f3base.json`, `f3s_cobertura_por_archivo.json`, `f3r_cobertura_resumen.md`)

| ID | Componente / Archivo | Síntoma y causa raíz | Impacto en SFV y KPIs | Fuente (`docs/mediciones/` / código) |
|---|---|---|---|---|
| `D-A4b` | `TBL EXPERIENCIA UNIFRANZ` (`doc 10`) | `18` filas usan la 1.ª fila de datos como cabecera (`BAJA_CONFIANZA_IA`). | Derivación a staging/bandeja en `doc 10` (18 casos `ESTUDIANTE`). | `docs/mediciones/f3s_cobertura_por_archivo.json` → `documentos.10.bandeja_por_tipo_entidad`; `docs/mediciones/f3r_cobertura_resumen.md` |
| `D-A5` | `dim_tiempo` fuera de rango 2022–2027 | Incluye `2034-01-12` (`BD Techos.xlsx` f.26, `1` hecho en `fact_techo_convenio` `id=25`) y `2005-02-05` / `2005-02-14` (`ARCA MODULOS`, `0` hechos). | Amplía el rango de `dim_tiempo` a `2005-02-05`..`2034-01-12`. | `docs/mediciones/f3s_extraccion_f3base.json` → `dim_tiempo` |
| `D-A2` | `fact_cobranzas_proyectadas` | `0` filas en el DW por ausencia de extractor implementado. | Tabla sin datos (`0`). | `docs/mediciones/f3s_extraccion_f3base.json` → `conteos_tablas` |
| Nota Cobranzas | `Copia de COBRANZAS 2024 2025` | No es duplicado de `COBRANZAS 2024 2025` (`overlap_CIs = 0`). | Aporta `446` de `725` hechos financieros en `f3_base`. | `docs/mediciones/f3s_cobertura_por_archivo.json` → `documentos.1.por_hoja`; `docs/mediciones/f3r_cobertura_resumen.md` |
| Lim. KPI-06 | `KPI-06` tautológico | `leads = inscritos` en el `100 %` de las filas con `leads > 0`. | Debe declararse como **N/D** en la tesis. | `docs/mediciones/f3r_snapshot_kpi.json` → `gestiones.2025.KPI-06.api` |
| Lim. Metas/Des. | `dim_meta` y deserción | `dim_meta = 0` (metas provienen de `fact_rentabilidad.monto_meta`); `incumplimiento_actividades_pct = 0,00` en `fact_rendimiento_academico`. | Alertas de deserción = `0`. | `docs/mediciones/f3s_extraccion_f3base.json` → `conteos_tablas`; `docs/mediciones/f3r_extraccion_f3base.json` |
| Lim. Revisión | Inclusión de `requiere_revision = true` | Se mantiene por decisión de Lean (`632/1.392` en `fact_rendimiento_academico`, nota media `87,0312` con revisión frente a `86,9062` sin ella). | Impacto documentado en KPIs académicos. | `docs/mediciones/f3_kpi.json` → `sensibilidad_requiere_revision` |
| Bitácora B-9 | `log_inconsistencias` | `5.090` filas en `log_inconsistencias` (`0` descartes sin bitácora en `f3_base`). | Trazabilidad completa de descartes. | `docs/mediciones/f3s_extraccion_f3base.json` → `log_inconsistencias`; `docs/mediciones/f3s_cobertura_por_archivo.json` → `totales.sin_explicar` |

---

## I. GRÁFICOS Y FIGURAS ACADÉMICAS (300 DPI)

| Identificador | Archivo / Estado | Fuente a citar al pie |
|---|---|---|
| Gráficos 3.2, 3.4, 4.1, 4.2, 4.3, 4.5 y Figura 3.5 | Generados en `docs/evidencias/` por `scripts/generar_graficos_ronda_final.py` | Elaboración propia (`docs/evidencias/` con datos de `snapshot_dw_20261110_1201` / `f3_base`) |
| Gráfico 3.1 (Matriz de confusión) | Datos en `docs/mediciones/f3r_matriz_confusion.json` (pendiente de generación final) | `docs/mediciones/f3r_matriz_confusion.json` |

---

## J. MAPA RESUELTO DOCX ↔ SISTEMA (`f3r_mapa_j.json`)

Todos los ítems de la Sección J (`J1-01`..`J1-22` y `J2-01`..`J2-15`) quedaron resueltos (`sin_resolver = 0` en `docs/mediciones/f3r_mapa_j.json`):

| ID | Tema | Estado | Valor resumen | Fuente (`docs/mediciones/` y ruta JSON) |
|---|---|---|---|---|
| J1-01 | Pruebas colectadas y estado | RESUELTO | 943 / 924 passed / 0 failed / 12 skip / 7 xfail | `docs/mediciones/f5c_pruebas.json` → `colectadas` |
| J1-02 | Cobertura total a 2 decimales | RESUELTO | 72,69 % (11.535 / 15.869) | `docs/mediciones/f5c_pruebas.json` → `cobertura_total.percent_covered` |
| J1-03 | Cobertura archivos | RESUELTO | `f3v_cobertura_archivos.csv` | `docs/mediciones/f3v_cobertura_archivos.csv` |
| J1-04 | Detalle `xfail` y `skipped` | RESUELTO | 7 `xfail` + 12 `skipped` | `docs/mediciones/f5c_pruebas.json` → `skips_con_motivo` |
| J1-05 | RNF-03 solo máquina (n = 3) | RESUELTO | 1.430,98 ± 365,09 s (vacía) / 757,46 ± 15,39 s (llena) | `docs/mediciones/f5c_b7_corridas.json` → `resumen` |
| J1-06 | KLM con $W$ medido y sensibilidad | RESUELTO | 474,0 s ($W=2,5$ s); 294,0 / 1.014,0 s | `docs/mediciones/f5c_klm.json` → `W_medido` |
| J1-07 | Ciclo operativo `f3_base` | RESUELTO | 168.013 hechos; bandeja 700/10 | `docs/mediciones/f5c_base.json` → `consolidacion` |
| J1-08 | Lote 1.387 con modelo vigente (2 corridas) | RESUELTO | 97,76 % directo (1.356/1.387); 31 HITL | `docs/mediciones/f5c_lote_1387_r1.json` → `distribucion_bandas_con_regla_personas` |
| J1-09 | Inventario corpus `uploads/data/` | RESUELTO | 10 libros, 60 hojas, 90.538 procesables | `docs/mediciones/f3r_evidencias_sueltas.json` → `inventario_corpus_uploads_data` |
| J1-10 | Anotación `gold_510` | RESUELTO | 180 filas, 83 personas, 510 entidades | `docs/mediciones/f3r_evidencias_sueltas.json` → `anotacion_y_corpus_modelo_vigente.gold_510` |
| J1-11 | Partición corpus y fuga = 0 | RESUELTO | 1.400 train / 350 dev; fuga 0 (4 niveles) | `docs/mediciones/f3r_evidencias_sueltas.json` → `anotacion_y_corpus_modelo_vigente` |
| J1-12 | Ablación A/B/C | RESUELTO | 12 filas (`gold_510` y `layouts_5`) | `docs/mediciones/f3r_ablacion.json` → `filas` |
| J1-13 | Matriz confusión Gráfico 3.1 | RESUELTO | 503 TP estricto / 510 relajado | `docs/mediciones/f3r_matriz_confusion.json` → `por_tipo_estricto` |
| J1-14 | Lote 1.387 con modelo vigente | RESUELTO | 97,76 % directo (1.356/1.387); 31 HITL | `docs/mediciones/f5c_lote_1387_r1.json` → `distribucion_bandas_con_regla_personas` |
| J1-15 | Cifra F1 = 75,66 % | **RETIRADA** | No pertenece al modelo vigente | `docs/mediciones/f3r_evidencias_sueltas.json` → `f1_75_66_pct.dictamen` |
| J1-16 | Cuadre KPI-15 en `f3_base` | RESUELTO | 725 filas (500 Mora / 7 Prev / 218 Vigente) | `docs/mediciones/f3s_kpi15_cuadre.json` → `por_estado_cartera` |
| J1-17 | `schema_migrations` en corridas llenas | RESUELTO | 17 filas; incluye `018`/`019`, solo difiere `applied_at` | `docs/mediciones/f5c_base.json.huella.json` → `tablas.schema_migrations.filas` |
| J1-18 | Recuento de rutas API | RESUELTO | 136 decoradores | `docs/mediciones/f3r_inventario_api.json` → `total_decoradores_ruta` |
| J1-19 | Prueba de carga Locust | RESUELTO | 1.121 req, 0 fallos, 41,27 RPS, p95 34 ms | `docs/mediciones/f3v_locust.json` → `agregado` |
| J1-20 | Pruebas Newman | RESUELTO | 11 req, 24 aserciones (0 fallidas) | `docs/mediciones/f3v_newman.json` → `run_stats` |
| J1-21 | Inventario de tablas DW | RESUELTO | 51 tablas base, 10 vistas, 23 KPI | `docs/mediciones/f3v_invariantes.json` → `invariantes_declarados` |
| J1-22 | Conteo y rango `dim_tiempo` | RESUELTO | 2.230 filas (`2005-02-05` a `2034-01-12`) | `docs/mediciones/f3s_extraccion_f3base.json` → `dim_tiempo` |
| J2-01 | Integridad snapshot en tmpfs | RESUELTO | SHA-256 intacto | `docs/mediciones/f3r_snapshot_kpi.json` → `etiqueta` |
| J2-02 | Pronóstico HW matrícula | RESUELTO | `n_obs=43`, RMSE 59,57, MAPE 15,67 % | `docs/mediciones/f3r_hw_matricula.json` → `rmse` |
| J2-03 | Pronóstico HW `META_MENSUAL_PROGRAMAS` | RESUELTO | RMSE 184.571,04, AIC 1.198,08 | `docs/mediciones/f3r_ols_snapshot.json` → `mensual.data` |
| J2-04 | Pronóstico OLS anual ($N=3$) | RESUELTO | +2.436.141,68 Bs/año, CAGR 26,76 % | `docs/mediciones/f3r_ols_snapshot.json` → `anual.data` |
| J2-05 | Conciliación SQL `f0_b5_consultas.sql` | RESUELTO | KPI-03 = 110,54 %; 2025 = 12.907.977,61 Bs | `docs/mediciones/f3r_b5_snapshot_sql.txt` |
| J2-06 | KPIs 2024 y 2025 del snapshot | RESUELTO | 22 KPIs (sin usar 10, 11, 18) | `docs/mediciones/f3r_snapshot_kpi.json` → `gestiones` |
| J2-07 | Alertas tempranas en snapshot | RESUELTO | 7.094 alertas (4.201 CRITICAL / 2.893 WARNING) | `docs/mediciones/f3r_snapshot_alertas.json` → `total_alertas` |
| J2-08 | Mora en snapshot | RESUELTO | 2.498 est., 2.574 filas, 692.957,88 Bs | `docs/mediciones/f3r_snapshot_alertas.json` → `mora_monto_deuda` |
| J2-09 | Distribución `fk_estado` en `f3_base` | RESUELTO | Acad. 1.385 A / 7 B · Fin. 725 A | `docs/mediciones/f3s_extraccion_f3base.json` → `fk_estado` |
| J2-10 | Staging en `f3_base` | RESUELTO | 3.935 filas (32 pendientes) | `docs/mediciones/f3s_extraccion_f3base.json` → `stg_entidad_no_resuelta` |
| J2-11 | Bitácora `log_inconsistencias` B-9 | RESUELTO | 5.090 filas | `docs/mediciones/f3s_extraccion_f3base.json` → `log_inconsistencias` |
| J2-12 | Inclusión `requiere_revision` en KPIs | RESUELTO | 632/1.392 incluidas (nota 87,0312) | `docs/mediciones/f3_kpi.json` → `sensibilidad_requiere_revision` |
| J2-13 | Trazabilidad automática SFV | RESUELTO | 0 / 0 / 0 | `docs/mediciones/f5c_sfv_verificacion.txt` |
| J2-14 | Encuesta Likert de usabilidad | DATO_DE_LEAN | Evaluación humana externa | N/D (Dato de Lean) |
| J2-15 | Línea base manual de consolidación | DATO_DE_LEAN | Referencia externa J0-6 | N/D (Dato de Lean) |

---

## K. SINCRONIZACIÓN F9–F12 (RENDIMIENTO RNF-03, IDEMPOTENCIA, SEMILLA PRE-DEFENSA Y BANDEJA HITL)

### Tabla K.1: Rendimiento RNF-03 y Ablación — Base: `f9_completo` (`f9_completo.json`, `f9_aporte_10archivos.json`, `f9_kpi10_check.json`)

| ID | Métrica | Valor | `valor_docx` | Fuente (`docs/mediciones/` y ruta JSON) |
|---|---|---|---|---|
| K-01 | Carga histórica completa en caché fría (10 libros) | **`655,91 s`** (`10,93 min` < `15 min`; `rnf03_cumplido_15m = true`) | 655,91 s (10,93 min) | `docs/mediciones/f9_completo.json` → `tiempo_total_seg`, `rnf03_cumplido_15m` |
| K-02 | Lote de 10 archivos en Modo B | **`119,82 s`** (`2,00 min`) con **`141`** casos en bandeja | 119,82 s / 141 | `docs/mediciones/f9_aporte_10archivos.json` → `modos.B.tiempo_total_seg`; `docs/cierres/CIERRE_F9_RNF03_INDICE.md` |
| K-03 | `KPI-10` en scorecard (gestión 2025) | **`99,99`** (`VERDE`, `puntaje: 100,0`) | 99,99 | `docs/mediciones/f9_kpi10_check.json` → `scorecard_kpi_10_2025.valor` |
| K-04 | Cobertura de confianza en `fact_situacion_financiera` | **`27.190 / 27.190`** poblados (`0` `NULL`; media `0,9836`) | 27.190 / 0,9836 | `docs/mediciones/f9_kpi10_check.json` → `fact_situacion_financiera` |
| K-05 | Suite `pytest` en F9 | **`121 passed, 1 skipped, 0 failed`** | 121 passed | `docs/mediciones/f9_pruebas.txt` |

### Tabla K.2: Idempotencia Paso 2 ↔ Paso 3 y UX DataOps — Base: `f10` (`f10_p0_idempotencia_test.txt`, `f10_pruebas_back.txt`, `f10_pruebas_front.txt`)

| ID | Métrica | Valor | `valor_docx` | Fuente (`docs/mediciones/` / archivo) |
|---|---|---|---|---|
| K-06 | Duplicación en `stg_entidad_no_resuelta` al navegar Paso 2 ↔ Paso 3 | **`0`** duplicados (`2` pruebas P0 en verde) | 0 | `docs/mediciones/f10_p0_idempotencia_test.txt` |
| K-07 | Pruebas F10 (`pytest` / `vitest`) | **`119 passed`** backend · **`25/25`** archivos frontend | 119 / 25 | `docs/mediciones/f10_pruebas_back.txt`; `docs/mediciones/f10_pruebas_front.txt` |

### Tabla K.3: Carga Limpia Lote #1 y Semilla Pre-Defensa — Base: `f11_lote1_predefensa` (`f11_carga_limpia.json`, `f11_backup_verificacion.json`, `f11_beto_check.json`)

| ID | Métrica | Valor | `valor_docx` | Fuente (`docs/mediciones/` y ruta JSON) |
|---|---|---|---|---|
| K-08 | Motor BETO activo en inferencia | `BETO_PYTORCH_REAL` (`dccuchile/bert-base-spanish-wwm-cased`, `/app/pipeline/semantic/beto_local`) | BETO_PYTORCH_REAL | `docs/mediciones/f11_beto_check.json` → `health` |
| K-09 | Hechos insertados en DW (Lote #1 limpio, 10 libros) | **`490.549`** (`14.365` en revisión, **`1.573`** staging HITL) | 490.549 / 1.573 | `docs/mediciones/f11_carga_limpia.json` → `consolidacion` |
| K-10 | Conteos restaurados en `fact_*` y `bi.ref_kpi` | `fact_rendimiento_academico` **`23.773`** · `fact_situacion_financiera` **`27.150`** · `fact_evaluacion_docente` **`409.645`** · `fact_forecast` **`32`** (`n_observaciones = 43`) · `bi.ref_kpi` **`23`** · vistas `bi` **`10`** | 23.773 / 27.150 / 409.645 / 32 / 23 / 10 | `docs/mediciones/f11_backup_verificacion.json` → `prueba_restauracion_tmpfs.conteos_restaurados`; `docs/mediciones/f11_carga_limpia.json` → `forecast.ALUMNOS_GLOBAL.n_observaciones` |
| K-11 | Snapshot semilla pre-defensa (`backups/snapshot_pre_defensa.dump` / `.sql`) | **`65,01 MB`** (`.dump`) / **`322,44 MB`** (`.sql`); restauración en `beto_pg_tmpfs` en **`9,99 s`** (`pg_restore_returncode = 0`) | 65,01 MB / 9,99 s | `docs/mediciones/f11_backup_verificacion.json` → `archivos`, `prueba_restauracion_tmpfs` |
| K-12 | Interfaz oficial en rutas raíz (`/`) sin selector de versión heredada | **`25`** archivos / **`129`** tests Vitest en verde + `vite build` limpio | 25 / 129 | `docs/mediciones/f11_pruebas_front.txt` |

### Tabla K.4: Bandeja HITL Agrupada, Prioridad y Guardrail `HTTP 422` — Base: `f12_bandeja_lote1` (`f12_grupos_api_test.txt`, `f12_gobernanza_batch_test.txt`, `f12_pruebas_back.txt`, `f12_pruebas_front.txt`)

| ID | Métrica | Valor | `valor_docx` | Fuente (`docs/mediciones/` / archivo) |
|---|---|---|---|---|
| K-13 | Reducción de grupos en bandeja HITL (Lote #1) | De `839` grupos (`168` págs.) a **`126` grupos (`26` págs.)** sobre **`1.578`** casos (`1.573` staging + `5` hechos) | 126 grupos (26 págs.) / 1.578 | `docs/mediciones/f12_grupos_api_test.txt` |
| K-14 | Bandas de `CI_NOMBRE_DISCORDANTE` y paginación sin truncamiento | `parcial` **`609`** (`31` págs.) · `muy_distinto` **`121`** · `casi_igual` **`12`**; **8 reglas** activas en resumen | 609 / 121 / 12 | `docs/mediciones/f12_grupos_api_test.txt` |
| K-15 | Filtro por `prioridad` y guardrail `HTTP 422` | **`251`** casos `ALTA`; rechazo `HTTP 422` en `/batch-resolve` y `/approve-group` para `CI_NOMBRE_DISCORDANTE < 30`; `justificacion` en auditoría | 251 ALTA / HTTP 422 | `docs/mediciones/f12_gobernanza_batch_test.txt` |
| K-16 | Pruebas F12 (`pytest` / `vitest`) | **`17 passed`** (`0 failed`) backend · **`25/25`** (`129 passed`) frontend | 17 / 129 | `docs/mediciones/f12_pruebas_back.txt`; `docs/mediciones/f12_pruebas_front.txt` |
