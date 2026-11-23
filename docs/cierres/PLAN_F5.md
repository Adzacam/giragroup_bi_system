# PLAN F5 — 2026-11-19
Objetivo: unificar el docx de la tesis con la SFV congelada (F3) y las figuras de F4. Lo ejecuta el **chat 3** (claude.ai); este repositorio no toca el docx.
Entrada: `docs/fuente_verdad_tesis.md` (CONGELADO, 181 cifras, 0/0/0), `docs/cierres/FIGURAS_F4.md`, docx `PROYECTO GRADO DAZA CAMPERO ADRIANO LEANDRO (3).docx` (leído en solo lectura por el chat 1 el 19-nov). Rama `beto-integracion` `595e40f`.

Regla: cada cifra que se cambia en el docx sale de la SFV (columna «Fuente»). Si una cifra del docx no está en la SFV, se marca «retirar» o «dato de Lean»; nunca se estima.

## 1. Cambios estructurales (afectan varias secciones)
| Tema | Docx hoy | Valor congelado | Dónde (docx) | Fuente SFV |
|---|---|---|---|---|
| Invariantes del DW | 50 tablas + 9 vistas (59 objetos); 9 hechos | **51 tablas + 10 vistas `bi`; 10 hechos**, 7 dimensiones, 1 puente; hecho nuevo `fact_planificacion_programa` | Tabla 3.9; Fase 3 de Hefesto (párrafo del modelo constelación); Tabla 3.36 (fila Obj. 2); Resultados Obj. 2 («almacén de 50 tablas…»); Apéndice F (párrafo inicial, «nueve tablas de hechos», Tabla F.1) | `f3v_invariantes.json` |
| CMI | 22 KPI; «3 de procesos internos»; «10 con valor en 2025» | **23 KPI**; procesos internos = 4 (se agrega **KPI-23**, cumplimiento de inicios planificados); KPI con valor = recontar desde la Tabla F.1 de la SFV | Tabla 3.22 (scorecard «22 KPI»); Sprint 5 (párrafo «El CMI integra 22…»); Tabla 3.27 (+ fila KPI-23); Tabla 3.36 (Obj. 5); Resultados Obj. 5; Tabla 4.6 (título y fila KPI-23); Sección 4 Obj. 3 (párrafo «define 22 indicadores»); Tabla 4.8 (fila de visibilidad); Análisis Obj. 3; Conclusiones (objetivo 3); Apéndice F (fila `ref_kpi`) | Tabla F.1; `f3v_kpi23.json`, `f3v_kpi23_serie.json` |
| KPI-23 | — | 2024 = **100,00 %**, 2025 = **99,77 %**, 2026 = **46,62 %**; bandas 85 / 60; base `f3v_completo` | Tabla 3.27, Tabla 4.6, texto de Resultados Obj. 3 | `f3v_kpi23_serie.json` |
| Flujo DataOps | 4 pasos (ingesta, texto plano, lectura BETO, revisión) | **3 pasos**: ① Carga, ② Lectura de BETO (con la pestaña «Texto preparado»), ③ Revisión | Sprint 5 (párrafo de `IngestView`…`HumanReviewFlowView`); Tabla 3.25 (GCB-35); Tabla 3.26 (`PlainTextTransformationView` pasa a ser una pestaña); Resultados Obj. 5; Figuras 3.32 y 3.33 (capturas nuevas de F4-4) | FIGURAS_F4 / `f3w_flujo_3_pasos.md` |
| PLANIFICACION como fuente | Sin aporte | Las 18 hojas mensuales y Programas Notificados → `fact_planificacion_programa` (1.663 filas en la carga completa); Informe Gestión → `dim_meta` (58) | Tabla 3.8 (data sources); Fase 2/3 de Hefesto; Tabla 4.2 (inventario del corpus) | `f3v_planificacion_carga.json`, `f3v_completo.json` |
| Tres bases de medición | Una sola base implícita | snapshot 10-nov (series de negocio y KPI de negocio) · f3_base (ciclo mensual 2026-03, RNF-03) · f3v_completo (10 libros completos; KPI-23 y planificación) · lote 1.387 (evaluación de BETO) | Metodología (Cap. I, diseño o instrumentos) y nota al inicio del Cap. IV | SFV, encabezado |

## 2. Capítulo III — tablas y texto
| Elemento | Docx hoy | Valor congelado | Fuente SFV |
|---|---|---|---|
| Tabla 3.24 y texto del módulo predictivo | HW sobre **33 meses** (2023-09 a 2026-05), φ 0,9858/0,9950, MAPE 13,89 %, naive 10,32 %; nota «con N = 43, MAPE 15,31 %» | HW sobre **43 meses** (2022-11 a 2026-05): α/β/γ = 0, **φ 0,9072**, RMSE **59,57**, AIC **385,49**, MAPE hold-out **15,67 %**, cobertura de IC 80/95 = 66,67 / 100 %, proyección 396,44–402,81 | Tabla E.1 (E-01 a E-07) — **ver DECISIÓN 1** |
| Tabla 3.24, fila «OLS matrícula» (N = 33, +3,6541, R² 0,1921) | presente | **Retirar** (sin medición; el Gráfico 3.5 se retira) | `f4_cifras_sin_trazar.json` |
| Tabla 3.24 / 4.7, OLS recaudación mensual (N = 40, +16.212,88 Bs/mes, R² 0,7128, MAPE 17,01 %) | presente | No está en la SFV (la SFV tiene `META_MENSUAL_PROGRAMAS` con HW: RMSE 184.571,04 · AIC 1.198,08) → **DECISIÓN 2** | Tabla E.2 (E-08) |
| Tabla 4.7, OLS anual | +2.267.633,83 Bs/año, R² 0,9937 | **+2.436.141,68 Bs/año**, CAGR **26,76 %**; proyección 2026/2027 = 15.183.417,34 / 17.619.559,02 Bs | Tabla E.2 (E-09, E-10) |
| Tabla 3.29 + Figura 3.40 (pytest) | 652 pruebas / 634 passed / 11 skipped / 7 xfail; total por sprint | **875 colectadas / 856 passed / 0 failed / 12 skipped / 7 xfailed** (rehacer el desglose por carpeta desde `f3v_pruebas.json`) | Tabla D (pruebas), `f3v_pruebas.json` |
| Tabla 3.30 + texto (cobertura) | 68,4 % (9.628 / 14.066); por módulo | **72,42 % (11.366 / 15.694)**; cada fila desde `f3v_cobertura_archivos.csv` | `f3v_pruebas.json`, `f3v_cobertura_archivos.csv` |
| Tabla 3.31 + Figura 3.41 (Postman/Newman) | valores previos | **11 peticiones, 24 aserciones, 0 fallidas** | `f3v_newman.json` |
| Tabla 3.32 + Figura 3.42 + texto (Locust) | 8.081 peticiones, 136,4 RPS, 50 usuarios | **1.121 peticiones, 0 fallos, 41,27 RPS, p95 34,0 ms**; por endpoint desde el JSON; condiciones según la nota de la SFV | `f3v_locust.json` |
| Figura 3.17 y texto (auditoría del lote 1.387) | resumen previo | **1.360 directos (98,05 %), 27 HITL, 0 staging** | Tabla A.1 |
| Tabla 3.34 (estabilización) | iteración previa | Agregar lo corregido en F3: archivo de evaluación docente completo (D-A4), filas de metas fuera de BETO (D-A8a), convenios fuera de revisión (D-T1), borrado completo de documentos, asignación determinista de módulos, metas reconocidas por estructura | Sección H de la SFV |
| Tabla 3.37 (RF/RNF), fila RNF-03 | «Ciclo completo < 15 min» con la evidencia anterior | Evidencia: **12,41 min** (n = 3) | Tabla A.3 |

## 3. Capítulo IV — resultados y análisis
| Elemento | Docx hoy | Valor congelado | Fuente SFV |
|---|---|---|---|
| Tabla 4.1 (fila 5: tiempo) y Tabla 4.8 (tiempo de consolidación) | 9,2 min = 60,0 s de máquina + 490,5 s de KLM (188 casos, 37 grupos); Δ −590,8 min (−98,5 %) | **12,41 min = 424,29 ± 22,24 s de máquina (n = 3, caché vacía) + 320,6 s de KLM (W = 2,5 s)**; Δ = −587,59 min (**−97,9 %**) frente a 600 min; sensibilidad W = 0 / 10 → 10,41 / 18,41 min | Tabla A.3, `f3v_b7_corridas.json`, `f3v_klm.json` |
| Texto del cálculo KLM (decisiones, 188 casos, 37 grupos) | valores previos | Desglose de `f3v_klm.json` (bloque, corregir fecha, manual, paginación) | `f3v_klm.json` |
| Tabla 4.1 (fila 7) y Tabla 4.3, Gráfico 4.1 (excepciones) | 562 entidades / 268 registros | **550 entidades / 264 registros**, 0 ingresan al DW sin control; staging del ciclo con los valores de la Tabla B | Tabla B.1, `f3s_extraccion_f3base.json` |
| Tabla 4.3, fila «Bandeja HITL (stock)» | 850 casos / 61 grupos | Bandeja del ciclo: **676 casos / 17 grupos**; staging 3.935 (32 pendientes) | `f3s_extraccion_f3base.json` (J2-10) |
| Tabla 4.5 + Gráficos 4.2 y 4.3 (lote por archivo) | total 1.353 directos / 34 HITL (97,55 %); ARCA 448/2, Evaluación 137/13, EJECUTADO 23/1… | **1.360 / 27 (98,05 %)**: ARCA 449/1, Cobranzas 349/1, Inscritos 249/1, Evaluación 146/4, Experiencia 95/15, Egresos 53/0, EJECUTADO 19/5 | Tabla A.2 |
| Tabla 4.8 (vinculación) | 97,55 % (1.353 de 1.387) | **98,05 % (1.360 de 1.387)** | Tabla A.1 |
| Tabla 4.8 (mora) y texto de alertas | 623 estudiantes en riesgo financiero; mora 18,36 %; 9.603 evaluados; 1.224 en riesgo académico… | KPI-05 = 18,36 % (se mantiene); alertas **7.094** (4.201 CRITICAL / 2.893 WARNING; 3.942 académico / 1.806 financiero / 1.044 calidad / 302 cruzado); mora **2.498 est., 2.574 filas, 692.957,88 Bs**. Verificar el 623 y el 9.603 contra la Tabla F.3; si no están, se retiran | Tabla F.1, F.3 |
| Tabla 4.6 (22 KPI) | 22 filas | 23 filas, con los valores de 2024/2025/2026 de la Tabla F.1 (KPI-15 = 20,56 % en 2025; KPI-02 2024 = 6,25 % con la nota de meta solo en diciembre) | Tabla F.1 |
| Tabla 4.7 | ver Cap. III | igual que Tabla 3.24 | Tabla E |
| Gráfico 4.4 | 22 KPI | 23 KPI por perspectiva (9 / 5 / 4 / 5) | `f3v_invariantes.json`, figura de F4 |
| Tabla 4.4, Tabla 4.9 y Gráfico 4.6 (Likert) | Tabla 4.9: 1,91 → 4,57; Gráfico 4.6 de F4: 1,89 → 4,62 | **Dato de Lean** (J2-14, no lo produce el sistema). Hay que dejar **un solo** par de valores: la tabla y el gráfico se contradicen → DECISIÓN 3 | J2-14 |
| Pretest de 600 min | 600 min (punto medio de 8–12 h) | Dato de Lean (J2-15); se mantiene | J2-15 |
| Análisis (Obj. 2, 3, 4), Limitaciones, Conclusiones, Recomendaciones, Resumen/Abstract | 97,55 %, 9,2 min, −98,5 %, 22 KPI, MAPE 13,89 %, 652 pruebas, 68,4 % | 98,05 %, 12,41 min, −97,9 %, 23 KPI, MAPE 15,67 %, 856/875, 72,42 %; Limitaciones: agregar D-A4b, D-A5 y D-A2 (Sección H) y la declaración de las tres bases | SFV completa |

## 4. Figuras y gráficos (desde FIGURAS_F4.md)
| Docx | Acción | Archivo |
|---|---|---|
| Gráfico 3.1 | reemplazar | `docs/figuras/f4/grafico_3_1_matriz_confusion_beto.png` |
| Gráfico 3.2 | reemplazar (98,05 / 1,95 / 0) | `grafico_3_2_distribucion_lote_1387.png` |
| Gráfico 3.3 | reemplazar | `grafico_3_3_ablacion_modelos_ner.png` |
| Gráfico 3.4 | reemplazar (N = 43) | `grafico_3_4_serie_temporal_holt_winters.png` |
| **Gráfico 3.5** | **retirar**, junto con su referencia en el texto y la fila OLS de matrícula | — |
| Figura 3.5 | reemplazar (10 hechos, `fact_planificacion_programa`) | `figura_3_5_esquema_constelacion_fisico.png` |
| Figura del flujo DataOps (3 pasos) | agregar o reemplazar la de 4 pasos (si existe) | `figura_flujo_dataops_3pasos.png` |
| Figuras 3.40, 3.44 y 3.50 | reemplazar por las **capturas reales de Lean** (pendientes) | mismos nombres en `docs/figuras/f4/` |
| Figuras 3.32, 3.33, 3.49 (pantallas) | reemplazar por las capturas de F4-4 (clon, 3 pasos, scorecard de 23 KPI) | pendiente F4-4 |
| Gráficos 4.1 a 4.5 | reemplazar | `grafico_4_*.png` |
| Gráfico 4.6 | reemplazar después de la DECISIÓN 3 | `grafico_4_6_evaluacion_likert_pre_post.png` |
| Nuevos | agregar: serie de KPI-23, RNF-03 n = 3 con sensibilidad, Locust/Newman, hechos de `f3v_completo` | `grafico_kpi23_serie.png`, `grafico_rnf03_n3_sensibilidad.png`, `grafico_rendimiento_locust_newman.png`, `grafico_f3v_completo_hechos.png` |
| Índices de tablas, figuras y gráficos | renumerar después de retirar el Gráfico 3.5 y agregar los nuevos | — |

## 5. Verificación del chat 3 al terminar
1. Buscar en el docx y que dé **0**: «50 tablas», «9 vistas», «nueve tablas de hechos», «22 KPI», «22 indicadores», «cuatro pasos» (salvo los 4 pasos de Hefesto), «97,55», «9,2 min», «−98,5», «13,89», «652», «68,4», «8.081», «562 entidades», «Gráfico 3.5».
2. Cada cifra cambiada coincide con su fila de la SFV.
3. Ninguna figura del docx queda sin archivo en `docs/figuras/f4/` o en las capturas de Lean.

## DECISIONES PENDIENTES PARA LEAN
1. ~~Holt-Winters~~ **Respondida (19-nov): el principal es 33 meses de operación regular**, con 43 meses como sensibilidad y el naive como referencia. Se mide en `PLAN_F3Y.md`; F5 usa las cifras de F3Y para la Tabla 3.24, la Tabla 4.7, el Gráfico 3.4 y el texto.
2. ~~OLS mensual~~ **Se mide en PLAN_F3Y (Y-3)** y entra a la Tabla E.2 de la SFV.
3. **Likert (revisado por el chat 1 el 19-nov):**
   - Con las medias por ítem de la Tabla 4.9 se obtiene pre **1,91**, post **4,57** y Δ **+2,66**: la tabla es coherente consigo misma.
   - El Gráfico 4.6 de F4 (1,89 → 4,62) usa valores **escritos a mano** en `scripts/generar_figuras_f4.py:614-626`, con 9 dimensiones que no existen en el docx. Se **retira**.
   - Ningún valor tiene respaldo en datos crudos:
     - el Apéndice C.3 («Matriz anonimizada de respuestas») está **vacío**;
     - los 9 ítems del instrumento (Apéndice C, Sección B: disponibilidad, automatización, eficiencia temporal, integración, alertas, CMI, ticket promedio, metas, conversión) **no coinciden** con las 9 dimensiones de las Tablas 4.4 y 4.9.
   - Lean entrega las respuestas originales: 10 participantes × 9 ítems, antes y después, anonimizadas, en `docs/mediciones/likert_respuestas.csv`. El chat 2 o el chat 4 calcula medias y DE muestrales por ítem. De ahí salen las Tablas 4.4 y 4.9, el Apéndice C.3 y el Gráfico 4.6.
   - Si las respuestas originales no existen, el resultado Likert no puede presentarse como medido.
   - **Actualización (19-nov, tarde):** apareció el pretest real (`Encuestas_F2_Pretest_P01-P10_GiraGroup.docx`, 15–18/04/2026), transcrito en `docs/mediciones/f5_likert_pretest.csv` / `.json`. Promedio de las medias por ítem = **1,91** (coincide con el docx), pero **las medias por ítem y las dimensiones de la Tabla 4.4 no coinciden**: la tabla nueva usa los 9 ítems del instrumento, con su n (de 4 a 9, porque las respuestas «–» se excluyen). C1 (3 coordinadores: 12 / 8 / 10 h) → media **10 h = 600 min**, que respalda el pretest de 600 min. **El postest se aplica a las mismas 10 personas cuando la DW viva tenga los 10 libros**; mientras tanto, la Tabla 4.9, el Gráfico 4.6 y la Δ del Likert quedan «pendientes de postest».
   - (Nota anterior:) Lean no tiene las respuestas originales y va a aplicar de nuevo el instrumento del Apéndice C a 10 personas (`docs/encuestas/encuesta_usabilidad_pre_post.md`, plantilla `likert_respuestas_plantilla.csv`). Las medias actuales (1,91 / 4,57) **no se usan** y tampoco se derivan respuestas a partir de ellas. Las Tablas 4.4 y 4.9 pasan a los **9 ítems del instrumento** (disponibilidad … conversión). Si el «antes» se responde de memoria, se declara como pretest retrospectivo. La Sección A (C1–C4) sirve también como respaldo del pretest de 600 min.
