# FIGURAS F3 — GiraGroup BI (F3 CONGELADO 18-nov-2026)

Este documento contiene el catálogo oficial y la tabla de traspaso de figuras y gráficos generados a 300 DPI para la incorporación en el documento de tesis por el Chat 3 (`claude.ai`).

- **Estado:** CONGELADO (18 de noviembre de 2026)
- **Fuente única:** `docs/fuente_verdad_tesis.md` (181 cifras cuantitativas verificadas con `scripts/verificar_sfv.py`, `0 / 0 / 0`)
- **Bases declaradas:**
  1. `snapshot 10-nov`: Series históricas y KPIs de negocio no dependientes de BETO.
  2. `f3_base`: Ciclo mensual 2026-03 (10 archivos de corte), RNF-03 = 12,41 min (n = 3 corridas limpias).
  3. `f3v_completo`: Carga de los 10 libros completos en clon tmpfs; `fact_planificacion_programa` y KPI-23.
  4. `lote 1.387`: Validación controlada de 1.387 registros con el modelo BETO vigente.
- **Invariantes nuevos (DECISIÓN 3 F3V):**
  - **51** tablas base
  - **10** vistas en esquema `bi`
  - **10** tablas de hechos
  - **7** dimensiones conformadas
  - **1** tabla puente (`bridge_modulo_docente`)
  - **23** KPIs catalogados en `bi.ref_kpi`
- **Flujo DataOps:** Oficializado en **3 pasos** (① Carga -> ② Lectura de BETO -> ③ Revisión HITL). Toda figura o diagrama previo con 4 pasos debe reemplazarse en el `.docx`.

---

## 1. Tabla de Entrega y Traspaso de Figuras y Gráficos (300 DPI)

| Archivo | Figura o tabla del docx | Pie propuesto | Insertar después de | Datos de origen |
|---|---|---|---|---|
| `docs/figuras/f3/grafico_3_1_matriz_confusion_beto.png` | Gráfico 3.1 | Gráfico 3.1 Matriz de confusión normalizada y frecuencias absolutas del clasificador NER BETO sobre el conjunto de prueba *gold_510* bajo evaluación estricta seqeval (503 TP / 510 soporte; micro-F1 = 97,96 %). Fuente: Elaboración propia a partir de `docs/mediciones/f3r_matriz_confusion.json`. | Sección 3.3.3 (Evaluación del modelo de extracción de entidades) | `docs/mediciones/f3r_matriz_confusion.json` (TP 503, FN 7, FP 14, F1 estricto 97,96 %, F1 relajado 99,42 %) |
| `docs/figuras/f3/grafico_3_2_distribucion_lote_1387.png` | Gráfico 3.2 | Gráfico 3.2 Distribución de registros del lote de validación controlado (N = 1.387) por banda de confianza e integración de reglas de identidad: consolidación directa (1.360 registros; 98,05 %), revisión humana HITL (27 registros; 1,95 %) y retención en Staging (0 registros; 0,00 %). Fuente: Elaboración propia a partir de `docs/mediciones/f3v_lote_1387_r1.json`. | Sección 3.4 (Mecanismo de contención y flujo de revisión humana) | `docs/mediciones/f3v_lote_1387_r1.json` (`distribucion_bandas_con_regla_personas`) |
| `docs/figuras/f3/grafico_3_3_ablacion_modelos_ner.png` | Gráfico 3.3 | Gráfico 3.3 Comparativa de rendimiento F1 en el estudio de ablación entre el enfoque determinístico por reglas (Modo A), la arquitectura híbrida con cascada jerárquica (Modo B) y la inferencia lingüística BETO aislada (Modo C) sobre layouts estándar y adversarios. Fuente: Elaboración propia a partir de `docs/mediciones/f3r_ablacion.json`. | Sección 3.3.5 (Estudio de ablación y robustez ante variabilidad estructural) | `docs/mediciones/f3r_ablacion.json` (`filas` 0 a 11; Tabla C.1 SFV) |
| `docs/figuras/f3/grafico_3_4_serie_temporal_holt_winters.png` | Gráfico 3.4 | Gráfico 3.4 Serie histórica de matrícula mensual (N = 43 meses, nov-2022 a may-2026), evaluación hold-out de seis meses (MAPE = 15,67 %) y proyección indicativa semestral (junio a noviembre de 2026: 396,44 a 402,81 inscritos) mediante Holt-Winters con tendencia amortiguada ($\phi = 0,9072$) e intervalo de incertidumbre al 95 %. Fuente: Elaboración propia a partir de `docs/mediciones/f3r_hw_matricula.json`. | Sección 3.5.2 (Modelado predictivo de demanda estudiantil) | `docs/mediciones/f3r_hw_matricula.json` (`serie_observada`, `forecast`, `ic_legacy_95`) |
| `docs/figuras/f3/grafico_3_5_ols_matricula.png` | Gráfico 3.5 | Gráfico 3.5 Análisis de regresión lineal OLS sobre la serie longitudinal de matrícula mensual (N = 33 meses, septiembre de 2023 a mayo de 2026) con pendiente positiva de +3,6541 inscritos/mes ($R^2 = 0,1921$; $p = 0,0107$). Fuente: Elaboración propia a partir de `docs/mediciones/f3r_hw_matricula.json`. | Sección 3.5.3 (Evaluación de tendencias lineales descriptivas) | `docs/mediciones/f3r_hw_matricula.json`, SFV Tabla J.1 (E-14) |
| `docs/figuras/f3/figura_3_5_esquema_constelacion_fisico.png` | Figura 3.5 | Figura 3.5 Esquema físico relacional en constelación del Data Warehouse corporativo: 10 tablas de hechos (incluyendo la incorporación de `fact_planificacion_programa`), 7 dimensiones conformadas (`dim_meta` con trazabilidad a nivel de fila y celda de origen), 1 tabla puente relacional y 10 vistas analíticas en esquema *bi*. Fuente: Elaboración propia a partir de `docs/mediciones/f3v_invariantes.json` y migración `018_fact_planificacion_programa.sql`. | Sección 3.6.1 (Diseño de la arquitectura dimensional del almacén de datos) | `docs/figuras_src/figura_3_5_constelacion_dw.mmd`, `docs/mediciones/f3v_invariantes.json` |
| `docs/figuras/f3/figura_flujo_dataops_3pasos.png` | Figura 3.12 (o Flujo DataOps) | Figura 3.12 Arquitectura operacional del pipeline DataOps en tres pasos secuenciales: ① Carga documental y control de integridad, ② Lectura contextual BETO y cascada de cinco niveles, y ③ Revisión humana HITL agrupada con persistencia idempotente al Data Warehouse. Fuente: Elaboración propia a partir de `frontend/src/modules/dataops/components/BatchFlowStepper.jsx`. | Sección 3.2.2 (Ciclo de vida de integración de datos DataOps) | `frontend/src/modules/dataops/components/BatchFlowStepper.jsx`, `docs/cierres/PLAN_F3W.md` |
| `docs/figuras/f3/figura_3_40_captura_pytest_856.png` | Figura 3.40 | Figura 3.40 Registro de ejecución de la suite automatizada de pruebas con pytest: 875 pruebas colectadas, 856 aprobadas (passed), 0 fallidas (failed), 12 omitidas con justificación técnica (skipped) y 7 excepciones documentadas (xfailed). Fuente: Terminal de pruebas del sistema contra la base congelada (`docs/mediciones/f3v_pruebas.json`). | Sección 3.7.1 (Verificación y aseguramiento de calidad del software) | `docs/mediciones/f3v_pruebas.json` (`colectadas`, `passed`, `failed`, `skipped`, `xfailed`) |
| `docs/figuras/f3/figura_3_50_captura_cobertura_72_42.png` | Figura 3.50 | Figura 3.50 Reporte de análisis de cobertura estática y dinámica de código mediante pytest-cov sobre los módulos de backend y pipeline: 11.366 sentencias cubiertas de 15.694 (72,42 % de cobertura global sin fallos). Fuente: Ejecución de auditoría de cobertura (`docs/mediciones/f3v_pruebas.json`). | Sección 3.7.2 (Análisis de cobertura de sentencias por módulo) | `docs/mediciones/f3v_pruebas.json`, `docs/mediciones/f3v_cobertura_archivos.csv` |
| `docs/figuras/f3/figura_3_44_captura_docker_ps_9_servicios.png` | Figura 3.44 | Figura 3.44 Estado operativo de los 9 contenedores en la plataforma de orquestación Docker Compose sin licencias comerciales (giragroup_db, catalog_db, api, auth, pipeline, audit, notifications, web y gateway). Fuente: Registro de orquestación en servidor local (`docker compose ps`). | Sección 3.8 (Infraestructura de despliegue y contenedores) | `docs/mediciones/f3v_invariantes.json`, `docker-compose.yml` |
| `docs/figuras/f3/grafico_4_1_calidad_corpus.png` | Gráfico 4.1 | Gráfico 4.1 Análisis de calidad y excepciones de preprocesamiento: (a) Distribución de 1.044 registros retenidos en Staging durante el ciclo mensual por causa técnica (756 discordancias CI-nombre y 288 por baja confianza IA); (b) 550 entidades anómalas interceptadas en el lote controlado con 0 ingresos no controlados al Data Warehouse (0 de 264 registros afectados). Fuente: Elaboración propia a partir de `docs/mediciones/f3s_extraccion_f3base.json` y `f3v_lote_1387_r1.json`. | Sección 4.3.1 (Eficacia en la intercepción de anomalías estructurales) | `docs/mediciones/f3s_extraccion_f3base.json`, `docs/mediciones/f3v_lote_1387_r1.json` (`excepciones`) |
| `docs/figuras/f3/grafico_4_2_resoluciones_cascada.png` | Gráfico 4.2 | Gráfico 4.2 Resoluciones exitosas de entidades (Total N = 11.560) distribuidas por etapa de la cascada jerárquica: CI exacta (1.850; 16,00 %), encabezado posicional (3.079; 26,63 %), expresiones regulares (3.103; 26,84 %), modelo del lenguaje BETO (3.382; 29,26 %) y coincidencia difusa RapidFuzz (146; 1,26 %). Fuente: Elaboración propia a partir de `docs/mediciones/f3v_lote_1387_r1.json`. | Sección 4.3.2 (Contribución por nivel del motor de extracción híbrido) | `docs/mediciones/f3v_lote_1387_r1.json` (`conteos_fuente_resolucion`) |
| `docs/figuras/f3/grafico_4_3_vinculacion_por_archivo.png` | Gráfico 4.3 | Gráfico 4.3 Desglose de vinculación directa frente a derivación a revisión humana HITL por cada uno de los siete archivos del lote de validación controlado (Total 1.360 directos [98,05 %] y 27 en revisión [1,95 %]). Fuente: Elaboración propia a partir de `docs/mediciones/f3v_lote_1387_r1.json`. | Sección 4.3.3 (Desempeño del mecanismo de vinculación por libro fuente) | `docs/mediciones/f3v_lote_1387_r1.json` (`distribucion_por_archivo`) |
| `docs/figuras/f3/grafico_4_4_kpi_cmi_perspectivas.png` | Gráfico 4.4 | Gráfico 4.4 Disponibilidad de indicadores estratégicos por perspectiva de Kaplan y Norton (Pretest: 0 indicadores vs Postest: 23 KPI catalogados y operativos en `bi.ref_kpi`): Financiera (9), Clientes (5), Procesos Internos (4, incluyendo KPI-23) y Aprendizaje y Crecimiento (5). Fuente: Elaboración propia a partir de `docs/mediciones/f3v_invariantes.json` y `f3v_kpi23.json`. | Sección 4.4.1 (Disponibilidad y cobertura del Cuadro de Mando Integral) | `docs/mediciones/f3v_invariantes.json`, `docs/mediciones/f3v_kpi23.json` |
| `docs/figuras/f3/grafico_4_5_tiempo_consolidacion_semilog.png` | Gráfico 4.5 | Gráfico 4.5 Comparativa en escala semilogarítmica del tiempo de consolidación informacional mensual: reducción del −97,9 % (Δ = −587,59 min) desde la línea base manual de 600,0 min (8 a 12 horas) hasta 12,41 min en postest analítico (máquina 424,29 s / 7,07 min n=3 + revisión humana KLM 320,60 s / 5,34 min con $W = 2,5$ s), cumpliendo holgadamente el requisito RNF-03 (< 15 min). Fuente: Elaboración propia a partir de `docs/mediciones/f3v_b7_corridas.json` y `f3v_klm.json`. | Sección 4.4.2 (Evaluación de eficiencia temporal y cumplimiento de RNF-03) | `docs/mediciones/f3v_b7_corridas.json`, `docs/mediciones/f3v_klm.json` |
| `docs/figuras/f3/grafico_4_6_evaluacion_likert_pre_post.png` | Gráfico 4.6 | Gráfico 4.6 Evaluación comparativa de usabilidad y percepción técnica en escala Likert (1 a 5) entre la situación previa manual (media global 1,89) y la solución postest implementada (media global 4,62) aplicada a una muestra intencional de 10 usuarios clave en 9 dimensiones evaluadas. Fuente: Elaboración propia a partir de `docs/mediciones/f3r_evidencias_sueltas.json`. | Sección 4.5 (Evaluación cuasiexperimental de usabilidad y aceptación) | `docs/mediciones/f3r_evidencias_sueltas.json` (`J2-14`) |

---

## 2. Puntos Críticos para Revisión en el Documento (`.docx`) por Chat 3

1. **Flujo DataOps en 3 Pasos (Sustitución obligatoria):**
   - En borradores previos de diseño se mencionaban 4 pasos («Ingesta $\rightarrow$ Texto $\rightarrow$ BETO NER $\rightarrow$ HITL»).
   - La arquitectura e interfaz real (`BatchFlowStepper.jsx`) tiene **3 pasos**:
     - **Paso 1:** Carga de Archivos (`/dataops/ingesta`)
     - **Paso 2:** Lectura de BETO (`/dataops/beto`)
     - **Paso 3:** Revisión Humana HITL (`/dataops/revision`)
   - Se debe verificar que todo texto descriptivo, diagrama o captura en los Capítulos 3 y 4 refleje exclusivamente estos 3 pasos.

2. **Invariantes del Data Warehouse y Catálogo CMI (DECISIÓN 3 F3V):**
   - **51 tablas base** en PostgreSQL (esquemas `public` y `bi`).
   - **10 vistas** en esquema `bi` (incluye la nueva `bi.vw_planificacion_ejecucion_mensual`).
   - **10 tablas de hechos** (incluye `fact_planificacion_programa` como hecho número 10).
   - **7 dimensiones conformadas** (`dim_meta` incluye `carga_fila_origen` y `celda_origen`).
   - **1 tabla puente** (`bridge_modulo_docente`).
   - **23 KPIs** en `bi.ref_kpi` (la perspectiva de *Procesos Internos* pasa de 3 a **4 KPIs** con la adición de `KPI-23: Cumplimiento de inicios planificados`).

3. **Cifras Congeladas Clave:**
   - **RNF-03:** 12,41 min (n = 3 corridas idénticas sobre `f3_base`: 424,29 s máquina vacía + 320,6 s KLM con espera medida $W = 2,5$ s; cumple con creces < 15 min).
   - **KPI-23:** 100,00 % en gestión 2024 (VERDE), 99,77 % en gestión 2025 (VERDE) y 46,62 % en gestión 2026 (ROJO).
   - **Suite Pytest:** 875 colectadas / 856 passed / 0 failed / 12 skipped / 7 xfailed / 72,42 % cobertura sobre 15.694 sentencias.
