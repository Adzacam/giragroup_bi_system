# Revisión del documento de tesis: Caps. 1, 3, 4 y 5 vs `fuente_verdad_tesis.md` (SFV)

Alcance: contradicciones, incongruencias y tablas/figuras/cifras por actualizar. Índices excluidos. No se generan figuras (solo se listan las que hay que rehacer).
Convención: "SFV" = `fuente_verdad_tesis.md` (snapshot `snapshot_dw_20261110_1201`). Formato numérico boliviano (coma decimal, punto de miles).
Prioridad: 🔴 contradice la SFV o se contradice dentro del documento · 🟠 inconsistencia/verificar · 🟡 forma.

---

## 0. DECISIÓN PREVIA (afecta Caps. 3, 4 y 5)

El documento maneja **dos lotes distintos sin distinguirlos**:

| | Lote "1.414" (documento actual) | Lote "1.387" (SFV) |
|---|---|---|
| Base | 1.590 líneas leídas − 176 sin entidad = 1.414 | 1.387 registros, 7 archivos `.xlsx` de `uploads/data/` |
| Directo | 1.307 (92,4 %) | 1.353 (97,55 %) |
| HITL | 103 (7,3 %) | 34 (2,45 %) |
| Staging | 4 (0,3 %) | 0 (0,00 %) |

Además el Cap. 4 mezcla ambos: "1.354 / 33 / 1.387" (97,62 %) junto con "103 en HITL / 4 en staging / 1.414". Ninguna de esas cifras coincide con la SFV (1.353 / 34 / 0).
**Acción recomendada:** rebasar todo a 1.387 con las cifras de la SFV (secciones A y B). La "107 inconsistencias" del pretest (basada en 1.414) debe reemplazarse o re-justificarse: la SFV da 268 registros / 562 entidades defectuosas interceptadas, 0 entraron al DW sin control (B-01, B-02).

---

## CAPÍTULO 1

| ID | Ubicación | Problema | Cambio |
|---|---|---|---|
| C1-01 🔴 | Introducción §3; Delimitación temática (último párrafo); Alcances viñeta 6 | "Holt-Winters aditivo" | El código usa `damped_trend=True` (tendencia amortiguada, estacionalidad aditiva). Escribir "Holt-Winters con tendencia amortiguada y estacionalidad aditiva". |
| C1-02 🟠 | Delimitación temática; Alcances viñeta 6 | OLS descrito solo sobre recaudación **anual** 2023–2025. El Cap. 3 (Tabla 3.24) añade OLS **mensual** de recaudación (N = 40, R² = 0,713) y la SFV (E-17) reporta OLS mensual de **matrícula** (R² = 0,0854; p = 0,098). | Decidir qué regresiones OLS existen y declararlas igual en Cap. 1, 3 y 4. |
| C1-03 🔴 | Justificación técnica §4 (cascada A/B/C); Alcances viñeta 3 | Estado B = similitud RapidFuzz ≥ 0,85 o miembro nuevo; C = revisión humana. En Cap. 3 hay dos descripciones distintas (párrafo previo a CRISP-DM Fase 2: "B = miembro nuevo con id temporal, C = revisión humana"; GCB-25: "B = herencia por similitud ≥ 0,85, C = no vinculada"). SFV: A = CI exacta (1.021); B = rescate difuso sin CI, único candidato ≥ 90 % (134); C = docentes nuevos/TEMP (498). | Una sola definición de A/B/C en los tres sitios y alinear con la SFV (A-08 a A-10). |
| C1-04 🔴 | Alcances viñeta 3 ("RapidFuzz ≥ 0,85") y Límites viñeta 5 (umbral 0,85) | Los umbrales vigentes en código son 5: 0,92 personas (`person_resolver.py`), 90 % homónimos estudiante, 85 % variante de CI y docentes, 80 % módulos (SFV, Detalle C.1). | No resumir todo en "0,85"; remitir a la Tabla 3.19 actualizada (ver C3-09). |
| C1-05 🟠 | Contextualización §2; Tabla/GCB-12 | "Catálogo canónico de 748 programas". SFV: `cat_programa` del catálogo = 1.229; `dim_modulo` = 3.585; `cat_programa` del DW = 4. | Verificar de dónde sale 748 y citar la tabla/fecha exacta, o corregir. |
| C1-06 🟠 | Contextualización (4 viñetas de fuentes) vs Tabla 4.3 fila 2 ("5 repositorios aislados") | Se listan 4 tipos de fuente (Sheets, Excel, Forms, Moodle) y luego 5 silos. | Alinear el número o enumerar los 5. |
| C1-07 🟠 | Delimitación temporal, Fase III (Sept–Oct 2026) | El Cap. 3 describe una "iteración de estabilización en noviembre de 2026" y el snapshot es del 10-nov-2026. | Extender la Fase III o declarar la iteración posterior. |
| C1-08 🟠 | Delimitación temporal ("desde 2023 para inscritos y recaudación") | HW usa 33 meses desde sep-2023 (descarta nov-2022 a ago-2023); la serie de marketing tiene 43 meses desde 2022-01 (SFV E-04). | Precisar rangos por serie. |
| C1-09 🔴 | Muestra ("censo de 33" + Likert a 10 usuarios, selección intencional) | El Cap. 4 llama "panel censal (N = 10)" al Likert. 10 de 33 no es censo. | Cap. 1 correcto; corregir término en Cap. 4 (ver C4-12). |
| C1-10 🟠 | Objetivo específico 1 ("registro cronométrico de línea base") | Cap. 1 (Instrumentos F-1), Tabla 4.3 y Limitaciones dicen que el pretest se reconstruyó de bitácoras, sin cronómetro. | "registro de línea base reconstruido a partir de bitácoras y entrevistas". |
| C1-11 🔴 | Objetivo específico 3 ("panel de calidad de datos") | El Cap. 4 (Resultados Obj. 3) no presenta ningún panel de calidad de datos. | Quitarlo del objetivo o agregar el resultado en Cap. 4. |
| C1-12 🟠 | Alcances viñeta 7 (alertas: riesgo académico ≤ 70; deserción > 30 %) | El código usa ≤ 70 (`alert_engine.py:6`) pero la SFV (F.2) dice "< 51". Deserción = 0 porque `incumplimiento_actividades_pct = 0,00` en las 22.618 filas (SFV H.5). | Mantener ≤ 70 (código) y declarar en Límites que la regla de deserción existe pero sin dato fuente. Corregir la SFV (ver T-01). |
| C1-13 🟡 | Alcances / Tabla 1.1 (KPI) | Cap. 1 nunca dice que `bi.ref_kpi` define 22 KPI y solo 11 están implementados (SFV H.2). | Agregar una frase en Alcances: "22 KPI catalogados, 11 implementados". |
| C1-14 🟡 | Citas | Se cita Hernández-Sampieri y Mendoza como 2018 y como 2023 indistintamente (ambas en referencias). | Verificar que cada cita (y página: p. 151, p. 175) corresponda a la edición correcta. |
| C1-15 🟡 | Títulos de capítulo | "CAPÍTULO II" con tilde vs "CAPITULO IV/V" sin tilde; Cap. IV se titula "MARCO PRÁCTICO" y el Cap. 1 lo describe como "evaluación cuasiexperimental". | Unificar formato y nombre. |
| C1-16 🟡 | Justificación económica ("< 15 minutos") | Coherente con 9,2 min (Tabla 4.8) pero contradice la Tabla 4.1 (20,6 min). | Se resuelve con C4-01. |

---

## CAPÍTULO 3

### 3A. Pronóstico (Holt-Winters / OLS)
| ID | Ubicación | Dice | Debe decir (SFV E) |
|---|---|---|---|
| C3-01 🔴 | Tabla 3.24 fila HW; párrafo "Codificación del Módulo Predictivo"; RF-09; Fig. 3.24 (pie); Gráfico 3.4 (pie); Tabla 3.36 fila Obj. 4 | HW **aditivo**; α = 0,6358; β = 0; γ = 0,1918; RMSE ajuste 65,85; AIC 308,37; hold-out RMSE 53,38 / MAPE 10,3 %; ±129,1 | HW **amortiguado**; α = 0,6978; β = 0,0000; γ = 0,0000; **φ = 0,9950**; RMSE ajuste 48,36; AIC 290,00; hold-out **RMSE 75,03 / MAPE 13,89 %**; IC ±94,79 |
| C3-02 🔴 | Tabla 3.24 (proyección h = 6) | 448,0; 468,4; 602,2; 561,9; 534,5; 514,3 | jun 426,37 · jul 414,22 · ago 498,55 · sep 454,48 · oct 428,85 · nov 461,97 (IC 95 %: ±94,79) |
| C3-03 🟠 | Tabla 3.24 / párrafo posterior | No hay benchmark. | Agregar naive estacional MAPE 18,22 % → mejora de 4,33 pp (23,76 % relativo) (E-15, E-16). |
| C3-04 🟠 | Tabla 3.24, columna "Serie y fuente" | "TBL_INSCRITOS.xlsx → inscritos.csv" | "TBL_INSCRITOS.xlsx (hoja TBL_INSCRITOS)"; no existe `inscritos.csv` (E-02, H.6). |
| C3-05 🟠 | Tabla 3.24 fila OLS mensual (N = 40, R² = 0,713) vs SFV E-17 (R² = 0,0854, p = 0,098, +2,95 est./mes) | Series distintas (recaudación vs matrícula). | Nombrar la serie de cada OLS y verificar que 0,713 siga vigente. |

### 3B. Lote, cascada y ablación
| ID | Ubicación | Problema | Cambio |
|---|---|---|---|
| C3-06 🔴 | CRISP-DM Fase 6 (párrafo tras Fig. 3.17): "1.590 líneas, 176 descartadas, 1.414: 92,4 % (1.307), 7,3 % (103), 0,3 % (4)" y "28.321 hechos académicos" | Ver decisión §0. SFV: 1.387 → 1.353 / 34 / 0; hechos en DW = 22.618. | Reescribir con SFV A.1 (7 archivos) y A-20. |
| C3-07 🔴 | Tabla 3.36 fila Obj. 3 ("92,4 % / 7,3 % / 0,3 % sobre 1.414") y evidencias Fig. 3.47, Gráfico 3.2 | Idem. | 97,55 % / 2,45 % / 0,00 % sobre 1.387. |
| C3-08 🔴 | Párrafo de ablación (tras Gráfico 3.3): "en el lote de 1.387 la cascada aumentó la consolidación directa de 99,50 % a 99,64 %" | Un tercer valor de consolidación directa; contradice 97,55 %. Además remite a "Tabla 4.5", que es el balance de unificación, no la ablación. | Eliminar o recalcular; citar Tabla de ablación (SFV C.1: gold_510 A 100 / B 100 / C 97,57; layouts_5 relajado A 28,57 / B 71,64 / C 69,23). Conviene una tabla de ablación explícita. |
| C3-09 🔴 | Tabla 3.19 (umbrales) | Solo lista 0,85 (catálogo y herencia de CI), < 0,80 revisión y `token_sort_ratio`. | Agregar/actualizar: 0,92 personas (+ apellido, ≥ 2 tokens, escalonado módulo→programa→dimensión); 90 % homónimos (≥ 2 candidatos → HITL `HOMONIMIA`; 1 → estado B); 85 % variante CI (`token_set_ratio`) y docentes; 80 % módulos (SFV C.1). |
| C3-10 🟠 | Tabla 3.20 vs SFV C-01 | "Gold total micro 97,47 % (P 96,72 / R 98,24)" vs "Modo C (BETO solo) 97,57 % (P 96,91 / R 98,24)". Cap. 4 (Tabla 4.5) lo llama "motor completo 97,47 %", pero el motor completo (Modo B) es 100 %. | Aclarar qué mide cada cifra (clasificador seqeval vs evaluador de ablación) y unificar o justificar la diferencia 97,47/97,57. |
| C3-11 🟠 | Sección BETO | No se muestra la contribución por etapa de la cascada (SFV A-12 a A-16: CI 1.850 / Encabezado 3.079 / Regex 3.103 / BETO 3.248 (28,43 %) / Fuzzy 146 sobre N = 11.426). | Agregar (alimenta Gráfico 4.2 de la SFV). |

### 3C. Pruebas y cobertura
| ID | Ubicación | Dice | Debe decir |
|---|---|---|---|
| C3-12 🔴 | Tabla 3.29, fila Transversales | 242 | **254** |
| C3-13 🔴 | Tabla 3.29, fila Total | 481 / 463 aprobadas; "60,7 % (8.040 de 13.243)" | **493 / 475**; **60,8 % (8.049 de 13.249)** |
| C3-14 🔴 | GCB-42; Tabla 3.36 fila Obj. 6 ("481 pruebas… 463 aprobadas… 60,7 %") | 481 | 493 (475 aprobadas, 11 omitidas, 7 xfail, 0 fallidas); 60,8 %. La propia Tabla 3.34 ya dice 493 → hoy el capítulo se contradice. |
| C3-15 🔴 | Párrafo bajo Tabla 3.29: "61 %… router DataOps 1.937 sentencias, 34 %… módulos alcanzan o superan 85 %" | Valores previos | 60,8 %; `dataops.py` 2.176 sentencias, 43,3 %; "superan el 80 %" (fuzzy_normalizer 83,1; extraccion_por_encabezado 81,2). |
| C3-16 🔴 | Tabla 3.30 completa | Stmts/Cover desactualizados | Reemplazar por SFV D.2: security 87 (87,4 %); dataops 2.176 (43,3 %); forecast_service 253 (35,6 %); ingestion 587 (61,3 %); kpi 374 (67,6 %); risk 337 (94,4 %); HW 71 (**95,8 %**, hoy dice 80 %); fk_resolver 89 (87,6 %); reportes 261 (84,7 %); alert_engine 71 (91,5 %); financial_rules 85 (97,6 %); fuzzy 71 (83,1 %); OLS 28 (100 %); TOTAL 13.249 / Miss 5.200 / 60,8 %. `ner_engine.py` no figura en la SFV: verificar o quitar. Opcional sumar person_resolver, bandeja_grupos, dw_loader, etc. |
| C3-17 🟠 | Tabla 3.34 fila "Pruebas automatizadas: 382 → 493, sin fallos" | "sin fallos" omite 11 skipped y 7 xfail. | "493 (475 aprobadas, 11 omitidas, 7 xfail, 0 fallos)". |
| C3-18 🟠 | Pies de Fig. 3.40 y Fig. 3.50 | SFV I.1: Fig. 3.40 = captura pytest (475 passed); Fig. 3.50 = captura de cobertura (60,8 %). En el documento Fig. 3.40 = ejecución y cobertura; Fig. 3.50 = "Evidencia Obj. 6". | Alinear pies y contenido. |

### 3D. Tiempos del ciclo
| ID | Ubicación | Dice | Debe decir |
|---|---|---|---|
| C3-19 🔴 | Tabla 3.34, fila "Tiempo de máquina (10 archivos)" | 60,0 s (DE = 0,8 s) | 59,14 s (corridas 58,42; 59,73; 59,26; DE muestral ≈ 0,66 s, recalcular). El rango "59,24–60,84" del Cap. 4 pasa a 58,42–59,73 s. |
| C3-20 🟠 | Tabla 3.34, "188 casos en 37 grupos" y tiempos de BETO 5,4 s / carga 44,0 s | No aparecen en la SFV; el lote 1.387 tiene 34 HITL y el stock es 1.606 casos / 786 grupos. | Aclarar que "188/37" es del ciclo de diez archivos (no del lote 1.387) y verificar las cifras contra `ciclo_*.json`. |

### 3E. KPI, alertas, modelo de datos, infraestructura
| ID | Ubicación | Problema | Cambio |
|---|---|---|---|
| C3-21 🔴 | Tabla 3.27 (columna "Tabla de origen", KPI de metas); Tabla 3.36 | Cita `dim_meta`, que tiene 0 filas. | Origen real: `fact_rentabilidad.monto_meta` (48 filas no nulas, desde `EJECUTADO VS META.xlsx`). `dim_meta` queda como "modelo previo sin carga" (ya dicho en Tabla 3.9). |
| C3-22 🔴 | Tabla 3.27 (y HU-10/HU-11) vs SFV F.2 | Los 11 KPI no coinciden: documento = estudiantes con riesgo financiero, estado de cartera, promedio acumulado, riesgo académico; SFV = KPI-04 margen operativo, KPI-05 estudiantes en mora, KPI-07 NPS, KPI-09 retención. Perspectivas también difieren (KPI-07/08/09 en Clientes en la SFV; en el documento van en Aprendizaje). | Verificar contra `kpi_service.py` / `/kpis/cmi-completo` y dejar un único listado de 11 (+ mención de los 22 de `bi.ref_kpi`). |
| C3-23 🟠 | Tabla 3.27 ("Aprobado: nota ≥ 70") | La SFV reporta aprobación 85,61 % con nota mínima 51; el código usa `NOTA_APROBACION`. | Verificar `pipeline/config.py` y corregir el umbral de aprobación citado. |
| C3-24 🔴 | Tabla 3.36 fila Obj. 2 ("50 tablas: 9 hechos + 7 dim + 1 puente + 18 cat + 13 soporte + 2 CMI") | SFV G.2: 59 objetos (tablas + 11 vistas `bi`); hechos 9 y dimensiones 7 sí coinciden. | Reconciliar el 50 con el inventario real y mencionar las vistas `bi.vw_*`. |
| C3-25 🟠 | Tabla 3.35 (Healthcheck "No" en api, auth, notifications, audit, pipeline, web, gateway) vs SFV G.1 (9 contenedores "Up (Saludable)"); Tabla 3.33 | Si no hay healthcheck, Docker no reporta "healthy". | Verificar `docker-compose.yml` y alinear tabla y figura 3.44. |
| C3-26 🔴 | Párrafo Tabla 3.32: "carga de ARCA generó 27.692 hechos"; Fase 6: "28.321 hechos académicos" | El DW final tiene 22.618 hechos académicos (SFV A-20). | Aclarar a qué corrida pertenece o actualizar. |
| C3-27 🟠 | Resultados de la propuesta, Obj. 4 ("20 rutas") | No verificable con la SFV. | Contar contra Tabla 3.22. |
| C3-28 🟠 | Tabla 3.17, "Evaluación Docente Institución A.xlsx" | La SFV nombra el archivo "Evaluación Docente y Unifranz.xlsx". El documento anonimiza. | Mantener el nombre anonimizado en todo el documento (Cap. 3 y 4) y tener presente el acuerdo de confidencialidad (Anexo B). |
| C3-29 🟠 | Alertas (Tabla 3.23, HU-07/08) | Regla de deserción implementada pero siempre 0; el Cap. 3/4 no reporta resultados de alertas. | Agregar resultados SFV F.2 (9.603 analizados; 1.224 académico; 0 deserción; 1.765 financiero, 867.811,89 Bs; 238 críticas; 2.751 únicos) y nota de limitación. |

### 3F. Numeración y referencias cruzadas
| ID | Ubicación | Dice | Debe decir |
|---|---|---|---|
| C3-30 🔴 | Párrafo previo a la Tabla 3.35 | "La Tabla 3.36 resume la configuración…" | Tabla 3.35 |
| C3-31 🔴 | Primer párrafo de "Resultados de la propuesta" | "La Tabla 3.37 sintetiza…" | Tabla 3.36 |
| C3-32 🔴 | Tabla 3.36, fila Obj. 6, evidencias | "Tablas 3.29 a 3.36" | Tablas 3.29 a 3.35 |
| C3-33 🔴 | GCB-46 ("Tablas 3.34 y 3.35"), GCB-47 ("Tabla 3.36"), Costo total ("Subtotal… (Tabla 3.35)") | Referencias corridas; 3.34 es estabilización y 3.35 es Docker; los costos son Cuadros. | GCB-46 → Cuadros de costeo; GCB-47 → Tabla 3.35; Costo total → Cuadro correspondiente. |
| C3-34 🟡 | Costos | Cuadros 3.19–3.21 sin estilo "Descripción" (y Cuadros 3.14–3.18 no visibles como caption) mientras que HU usan "Cuadro 3.1–3.13". | Verificar la secuencia de Cuadros y aplicar el mismo estilo de pie. |

---

## CAPÍTULO 4

### 4A. Tiempos y lote
| ID | Ubicación | Dice | Debe decir |
|---|---|---|---|
| C4-01 🔴 | Tabla 4.1 fila 5 | 20,6 min (1,50 + 19,1 para 103 casos); −96,6 %; Δ −579,4; "la meta RNF-03 no se alcanza" | Contradice Tabla 4.8, texto del Obj. 4, Análisis Obj. 4 y Cap. 5 (9,2 min = 1,0 + 8,2; −98,5 %; Δ −590,8; cumple < 15). Unificar en 9,2 min. |
| C4-02 🔴 | Obj. 4 texto, "componente de máquina" | "media de 60,0 s (DE = 0,8 s; 59,24 a 60,84 s)" | 59,14 s (58,42; 59,73; 59,26). El total sigue ≈ 9,2 min (59,14 + 1,7 + 490,5 s = 551,3 s). |
| C4-03 🔴 | Tabla 4.1 filas 6a, 6b, 7; Tabla 4.5; Obj. 2 texto; Tabla 4.8; Análisis Obj. 2 | 1.354 (97,62 %) / 33 (2,38 %); 6b = 99,7 % (1.410/1.414); 107 = 103 HITL + 4 staging; "100 % (1.387 de 1.387)" | 1.353 (97,55 %) / 34 (2,45 %) / 0 staging; resto según decisión §0. Hoy el mismo capítulo dice 99,7 % y 100 % para la unificación total y "0 en staging" y "4 en staging". |
| C4-04 🔴 | Obj. 2 texto: "la bandeja reunió 541 casos: 501 en bloque, 40 manuales (10 cédulas + 30 cobros)"; "las 103 líneas en revisión" | Incompatible con 34 HITL del lote; la SFV reporta stock 1.606 casos / 786 grupos (B-06). | Reescribir con SFV B-06 a B-08 y A.1. |
| C4-05 🔴 | Obj. 2 texto + Tabla 4.5 + Análisis Obj. 2: desglose por archivo "Excel 92,6 % (1.245/1.344), Moodle 100 % (35/35), Forms 77,1 % (27/35)"; "solo 70 registros .csv" | Suma 1.344 + 35 + 35 = 1.414, no 1.387; la SFV dice que Forms y Moodle se procesan como `.xlsx` y da el desglose por 7 archivos (ARCA 448/450 · Cobranzas 349/350 · Inscritos 248/250 · Eval. Docente 137/150 · Exp. Docente 95/110 · Egresos 53/53 · Ejecutado vs Meta 23/24). | Reemplazar por SFV A.1; revisar la afirmación "muestra estratificada de siete libros (.xlsx)" frente a "Forms/Moodle .csv". Gráfico 4.3 se rehace. |
| C4-06 🟠 | Obj. 2 texto: "Forms: los 8 registros derivados tienen cédula válida…" | Sin base en SFV (Inscritos: 2 HITL por complementariedad de CI discordante). | Reescribir con motivos de HITL por archivo (SFV A.1). |

### 4B. Diagnóstico (Obj. 1)
| ID | Ubicación | Dice | Debe decir |
|---|---|---|---|
| C4-07 🔴 | Obj. 1 texto ("2.548 de los 2.824 registros pendientes en staging…") | 2.824 / 2.548 | SFV A-17, A-18: **1.044** pendientes, **756** `CI_NOMBRE_DISCORDANTE`, 288 baja confianza IA. (Tabla 3.34 ya dice 1.044.) |
| C4-08 🔴 | Obj. 1 texto, Tabla 4.3 filas 4-5, Análisis Obj. 1 (107; 96/9/1/1; 176 = 115/40/21), Limitaciones | Base 1.414 | Ver §0. Si se conserva la medición retroactiva, etiquetarla como "muestra de evaluación previa" distinta del lote de producción. |
| C4-09 🟠 | Tabla 4.2 y Tabla 3.17 ("2022–2027"), Cap. 1 y Obj. 1 ("2022–2026") | Rango de gestiones inconsistente. | Unificar (BD Cobranzas llega a 2027). |
| C4-10 🟠 | Obj. 1/2 | No se menciona que 509 entidades (Likert 283, correos 139, comentarios 87) se descartan en memoria sin bitácora y solo 48 `PER_SIN_FORMA_NOMBRE` se persisten (SFV H.4); 562 entidades / 268 registros interceptados. | Agregar a resultados y a Limitaciones. |

### 4C. KPI y pronóstico (Obj. 3)
| ID | Ubicación | Dice | Debe decir |
|---|---|---|---|
| C4-11 🔴 | Tabla 4.1 fila 3; Tabla 4.7; Obj. 3 texto; Análisis Obj. 3; Conclusión 3 | HW aditivo; α 0,6358; γ 0,1918; MAPE 10,3 %; RMSE 53,38; proyección 448…514; "buena precisión (10–20 %)… por debajo del 20 %" | Valores de C3-01/C3-02. Con 13,89 % sigue siendo "buena" (10–20 %) y < 20 %. Agregar naive 18,22 % y reducción de 4,33 pp. |
| C4-12 🔴 | Tabla 4.6 (columna "Tabla de origen" metas); nombres de KPI-04/05/07/09; "cinco financieros, uno de clientes, dos de procesos, tres de aprendizaje"; "10 de 11 KPI con valor en 2025; 6 de 11 en 2026" | Ver C3-21 y C3-22. | Rehacer con SFV F.2 y agregar columna de valor (ticket 1.610,13 Bs; cumplimiento mensual 157,48 %; anual 110,54 %; mora 3.691 vigente / 830 mora / 0 prejudicial; NPS 79,02; aprobación 85,61 %; confianza IA 0,9269 DW / 0,9618 lote; extracción directa 90,10 % DW / 97,55 % lote). Explicar la dualidad 22 catalogados / 11 implementados. |
| C4-13 🟠 | Tabla 4.7 columna OLS (recaudación anual, R² 0,987, N = 3) vs SFV E-17 | Ver C3-05. | Aclarar series. |
| C4-14 🟠 | Obj. 3 | Faltan los resultados del motor de alertas (aparecen solo en Cap. 5 y con cifras viejas). | Incorporar SFV F.2 (ver C3-29). |

### 4D. Comparación pre/post (Obj. 4) y formato
| ID | Ubicación | Problema | Cambio |
|---|---|---|---|
| C4-15 🔴 | Tablas 4.1, 4.4, 4.9; Gráfico 4.6; Limitaciones ("Panel censal, N = 10") | 10 usuarios de 33 no son censo (Cap. 1 Muestra: selección intencional). | "Panel de 10 usuarios (muestra intencional)". |
| C4-16 🟡 | Gráfico 4.6 (pie): "(Pretest vs Postest = 10)" | Texto roto. | "(Pretest vs Postest, N = 10)". |
| C4-17 🟡 | Obj. 4 texto: "Todas las dimensiones superaron 4,3 puntos" | El mínimo es 4,30 (ítem 8). | "alcanzaron al menos 4,30". |
| C4-18 🟡 | Análisis Obj. 4: "modelo KLM.." | Doble punto. | Corregir. |
| C4-19 🟠 | Limitaciones, "Tiempo postest estimado… 37 grupos HITL" | Ver C3-20: 37 grupos no coincide con la base del lote 1.387. | Definir en una nota metodológica que el ciclo de tiempos usa diez archivos y el lote de calidad usa siete. |
| C4-20 🟠 | Limitaciones | Faltan limitaciones propias de la SFV: deserción sin dato (inactividad Moodle ausente), descartes sin bitácora en BD, `dim_meta` vacía, `fact_cobranzas_proyectadas` vacía. | Agregar. |
| C4-21 🟠 | Gráficos 4.2 y 4.4: pies del documento vs SFV I.1 | Doc: 4.2 = distribución por umbrales de confianza; 4.4 = KPI por perspectiva. SFV: 4.2 = resoluciones por etapa de cascada; F1 en layouts adversos = "Gráfico 4.4". | Decidir numeración y pie definitivos antes de insertar las figuras nuevas. |
| C4-22 🟡 | Tabla 4.9 | Aritmética revisada (promedios 1,91 y 4,57; Δ y %Δ por ítem) **correcta**. | Sin cambio. |

---

## CAPÍTULO 5

| ID | Ubicación | Dice | Debe decir |
|---|---|---|---|
| C5-01 🔴 | Conclusión general | "97,62 % de los registros se unifica de forma automática" | 97,55 % |
| C5-02 🔴 | Conclusión 1.º obj. | "2.548 de los 2.824 registros pendientes en staging"; "107 inconsistencias (7,6 %)… 89,7 %" | 756 de 1.044 (SFV A-17/A-18); inconsistencias según decisión §0. |
| C5-03 🔴 | Conclusión 2.º obj. | "Sobre 1.414 registros… 1.307 directo, 103 HITL, 4 staging" (y en el mismo párrafo F1 98,18 %/96,47 %) | Sobre 1.387: 1.353 / 34 / 0. |
| C5-04 🔴 | Conclusión 3.º obj. | "matrícula activa de 10.707; 1.698 riesgo académico; 1.451 financiero; 103 críticos"; MAPE 10,3 % | 9.603 analizados; 1.224 académico; 0 deserción; 1.765 financiero; 238 críticos; 2.751 únicos (SFV F.2; las anteriores son corridas sintéticas, H.7). MAPE 13,89 %. |
| C5-05 🔴 | Conclusión 4.º obj. | "Δ = −[600 − T] min" (placeholder sin completar) | "Δ = −590,8 min (600,0 → 9,2 min; −98,5 %)". |
| C5-06 🟠 | Conclusión 3.º obj. ("11 de 11 KPI") | No menciona los 22 catalogados. | "11 de los 22 KPI catalogados en `bi.ref_kpi`". |
| C5-07 🔴 | Recomendación 3 | "2.548 de los 2.824 registros pendientes en staging" | 756 de 1.044. |
| C5-08 🟠 | Recomendaciones (nuevas) | Faltan las derivadas de la SFV. | Agregar: incorporar columna de inactividad de Moodle (deserción = 0); persistir en BD los descartes (509 entidades); poblar o retirar `dim_meta`; ampliar de 11 a 22 KPI; cronometrar la revisión HITL con usuarios. |
| C5-09 🟡 | Título del capítulo | "CAPITULO V" sin tilde | Ver C1-15. |

---

## TRANSVERSALES

| ID | Tema | Detalle |
|---|---|---|
| T-01 🟠 | Errores a corregir **en la SFV** | (a) F.2 dice riesgo académico "< 51" pero el código usa ≤ 70 (`alert_engine.py:6`); verificar con cuál se obtuvo 1.224. (b) cita `forecasting_holtwinters.py:97` para `damped_trend`; en el código está en la línea 118. (c) la columna "Dónde va" usa numeración (Tabla 4.4, Cuadros 4.5–4.7, Sec. 4.1.x) que no existe en el documento actual. |
| T-02 🔴 | Seguridad | `fuente_verdad_tesis.md` contiene usuario y contraseña de PostgreSQL y ya está en `origin/main`. Quitar las cadenas de conexión y rotar la contraseña. |
| T-03 🟠 | Figuras/gráficos a rehacer (solo lista) | Gráfico 3.2 (lote 1.387), 3.4 (HW amortiguado), 3.5 (si cambia el OLS), 4.1, 4.2, 4.3, 4.5 (59,14 s); Figura 3.5 (constelación 9 hechos), 3.17 (log de extracción), 3.40 y 3.50 (pytest 493/475 y cobertura 60,8 %), 3.44 (contenedores y estado de salud), 3.46, 3.47, 3.48. Gráfico 4.4 según C3-22. |
| T-04 🟠 | Tablas que se actualizan por completo | 3.19, 3.24, 3.27, 3.29, 3.30, 3.34, 3.36; 4.1, 4.3, 4.5, 4.6, 4.7, 4.8. |
| T-05 🟡 | Fuera de este alcance | Cap. 2, Apéndices (D, E, F, J) y Anexos no se revisaron; Apéndices D/E/F deberán actualizarse con la SFV (inventario de 59 objetos, 22 KPI). El contenido de las imágenes no es legible desde el texto. |
| T-06 🟡 | Referencias cruzadas por sección | "apartado 1.8.1", "1.8.5" y "1.7.2" son coherentes solo si "Introducción" cuenta como 1.1; confirmarlo al regenerar el índice. |
