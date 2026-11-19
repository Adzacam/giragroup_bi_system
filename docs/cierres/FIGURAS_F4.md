# FIGURAS F4 — GiraGroup BI (F3 CONGELADO / AUDITORÍA F4 — 18-nov-2026)

Este documento constituye la entrega oficial del catálogo y tabla de traspaso de figuras, gráficos y capturas generadas a 300 DPI para su incorporación e integración en el documento de tesis por el Chat 3 (`claude.ai`).

- **Estado:** F3 CONGELADO (18 de noviembre de 2026).
- **Rama y Commit Base:** Rama `beto-integracion`, commit `e9267cd`.
- **Fuente única:** `docs/fuente_verdad_tesis.md` (**181 cifras cuantitativas verificadas** con `scripts/verificar_sfv.py`, balance estricto `0 / 0 / 0`).
- **Bases de datos declaradas:**
  1. `snapshot 10-nov`: Series de negocio históricas y KPIs no dependientes de BETO.
  2. `f3_base`: Ciclo mensual 2026-03 (10 archivos de corte mensual), base de medición RNF-03 = 12,41 min ($n = 3$ corridas limpias).
  3. `f3v_completo`: Carga de los 10 libros completos en clon tmpfs; persistencia de `fact_planificacion_programa` y cálculo de KPI-23.
  4. `lote 1.387`: Validación controlada de 1.387 registros con el modelo BETO vigente.
- **Invariantes nuevos del sistema (DECISIÓN 3 F3V):**
  - **51** tablas base en PostgreSQL (esquemas `public` y `bi`).
  - **10** vistas en esquema `bi` (incluye `bi.vw_planificacion_ejecucion_mensual`).
  - **10** tablas de hechos en constelación (incluye `fact_planificacion_programa` como hecho número 10).
  - **7** dimensiones conformadas (`dim_meta` con trazabilidad por `carga_fila_origen` y `celda_origen`).
  - **1** tabla puente relacional (`bridge_modulo_docente`).
  - **23** KPIs catalogados en `bi.ref_kpi` (la perspectiva de Procesos Internos pasa a 4 KPIs con la suma de `KPI-23`).
- **Flujo DataOps:** Oficializado estrictamente en **3 pasos** (① Carga $\rightarrow$ ② Lectura de BETO $\rightarrow$ ③ Revisión HITL). Toda figura previa con 4 pasos debe ser sustituida en el documento `.docx`.

---

## 1. Tabla Oficial de Entrega y Traspaso de Figuras (300 DPI)

| Archivo | Figura o tabla del docx | Pie propuesto | Insertar después de | Datos de origen |
|---|---|---|---|---|
| `docs/figuras/f4/grafico_3_1_matriz_confusion_beto.png` | Gráfico 3.1 | Gráfico 3.1 Matriz de confusión normalizada y frecuencias absolutas del clasificador NER BETO sobre el conjunto de prueba *gold_510* bajo evaluación estricta seqeval (503 TP / 510 soporte; micro-F1 = 97,96 %). Fuente: Elaboración propia a partir de `docs/mediciones/f3r_matriz_confusion.json`. | Sección 3.3.3 (Evaluación del modelo de extracción de entidades) | `docs/mediciones/f3r_matriz_confusion.json` (TP 503, FN 7, FP 14, F1 estricto 97,96 %, F1 relajado 99,42 %) |
| `docs/figuras/f4/grafico_3_2_distribucion_lote_1387.png` | Gráfico 3.2 | Gráfico 3.2 Distribución de registros del lote de validación controlado (N = 1.387) por banda de confianza e integración de reglas de identidad: consolidación directa (1.360 registros; 98,05 %), revisión humana HITL (27 registros; 1,95 %) y retención en Staging (0 registros; 0,00 %). Fuente: Elaboración propia a partir de `docs/mediciones/f3v_lote_1387_r1.json`. | Sección 3.4 (Mecanismo de contención y flujo de revisión humana) | `docs/mediciones/f3v_lote_1387_r1.json` (`distribucion_bandas_con_regla_personas`) |
| `docs/figuras/f4/grafico_3_3_ablacion_modelos_ner.png` | Gráfico 3.3 | Gráfico 3.3 Comparativa de rendimiento F1 en el estudio de ablación entre el enfoque determinístico por reglas (Modo A), la arquitectura híbrida con cascada jerárquica (Modo B) y la inferencia lingüística BETO aislada (Modo C) sobre layouts estándar y adversarios. Fuente: Elaboración propia a partir de `docs/mediciones/f3r_ablacion.json`. | Sección 3.3.5 (Estudio de ablación y robustez ante variabilidad estructural) | `docs/mediciones/f3r_ablacion.json` (`filas` 0 a 11; Tabla C.1 SFV) |
| `docs/figuras/f4/grafico_3_4_serie_temporal_holt_winters.png` | Gráfico 3.4 | Gráfico 3.4 Serie histórica de matrícula mensual (N = 43 meses, nov-2022 a may-2026), evaluación hold-out de seis meses (MAPE = 15,67 %) y proyección indicativa semestral (junio a noviembre de 2026: 396,44 a 402,81 inscritos) mediante Holt-Winters con tendencia amortiguada ($\phi = 0,9072$) e intervalo de incertidumbre al 95 %. Fuente: Elaboración propia a partir de `docs/mediciones/f3r_hw_matricula.json`. | Sección 3.5.2 (Modelado predictivo de demanda estudiantil) | `docs/mediciones/f3r_hw_matricula.json` (`serie_observada`, `forecast`, `ic_legacy_95`) |
| `docs/figuras/f4/figura_3_5_esquema_constelacion_fisico.png` | Figura 3.5 | Figura 3.5 Esquema físico relacional en constelación del Data Warehouse corporativo: 10 tablas de hechos (incluyendo la incorporación de `fact_planificacion_programa`), 7 dimensiones conformadas (`dim_meta` con trazabilidad a nivel de fila y celda de origen), 1 tabla puente relacional y 10 vistas analíticas en esquema *bi*. Fuente: Elaboración propia a partir de `docs/mediciones/f3v_invariantes.json` y migración `018_fact_planificacion_programa.sql`. | Sección 3.6.1 (Diseño de la arquitectura dimensional del almacén de datos) | `docs/mediciones/f3v_invariantes.json`, `docs/evidencias/diccionario_datos.csv` |
| `docs/figuras/f4/figura_flujo_dataops_3pasos.png` | Figura 3.12 (o Flujo DataOps) | Figura 3.12 Arquitectura operacional del pipeline DataOps en tres pasos secuenciales: ① Carga documental y control de integridad, ② Lectura contextual BETO y cascada de cinco niveles, y ③ Revisión humana HITL agrupada con persistencia idempotente al Data Warehouse. Fuente: Elaboración propia a partir de `frontend/src/modules/dataops/components/BatchFlowStepper.jsx`. | Sección 3.2.2 (Ciclo de vida de integración de datos DataOps) | `frontend/src/modules/dataops/components/BatchFlowStepper.jsx`, DECISIÓN 3 F3V |
| `docs/figuras/f4/figura_3_44_captura_docker_ps_9_servicios.png` | Figura 3.44 | [pendiente: captura real de Lean] Estado operativo y saludable de los 9 contenedores en la plataforma Docker Compose sobre commit congelado `e9267cd` (`giragroup_api`, `giragroup_audit_svc`, `giragroup_auth_svc`, `giragroup_catalog_db`, `giragroup_db`, `giragroup_gateway`, `giragroup_notifications_svc`, `giragroup_pipeline`, `giragroup_web`). Fuente: Terminal del entorno local (`docker compose ps`). | Sección 3.8 (Infraestructura de despliegue y contenedores) | Ejecución real de `docker compose ps` y `docs/mediciones/f3v_invariantes.json` |
| `docs/figuras/f4/figura_3_40_captura_pytest_856.png` | Figura 3.40 | [pendiente: captura real de Lean] Registro de la suite automatizada de pruebas con pytest: 875 pruebas colectadas, 856 aprobadas (passed), 0 fallidas (failed), 12 omitidas con justificación técnica (skipped) y 7 excepciones documentadas (xfailed) sobre el commit congelado `e9267cd`. Fuente: Ejecución de verificación congelada (`docs/mediciones/f3v_pruebas.json`). | Sección 3.7.1 (Verificación y aseguramiento de calidad del software) | `docs/mediciones/f3v_pruebas.json` (`colectadas`: 875, `passed`: 856, `failed`: 0) |
| `docs/figuras/f4/figura_3_50_captura_cobertura_72_42.png` | Figura 3.50 | [pendiente: captura real de Lean] Reporte de análisis de cobertura estática y dinámica con pytest-cov: 11.366 sentencias cubiertas de 15.694 (72,42 % de cobertura global sin fallos) en backend y pipeline. Fuente: Ejecución de auditoría de cobertura (`docs/mediciones/f3v_pruebas.json`). | Sección 3.7.2 (Análisis de cobertura de sentencias por módulo) | `docs/mediciones/f3v_pruebas.json`, `docs/mediciones/f3v_cobertura_archivos.csv` |
| `docs/figuras/f4/grafico_4_1_calidad_corpus.png` | Gráfico 4.1 | Gráfico 4.1 Análisis de calidad y excepciones de preprocesamiento: (a) Distribución de 1.044 registros retenidos en Staging durante el ciclo mensual por causa técnica (756 discordancias CI-nombre y 288 por baja confianza IA); (b) 550 entidades anómalas interceptadas en el lote controlado con 0 ingresos no controlados al Data Warehouse (0 de 264 registros afectados). Fuente: Elaboración propia a partir de `docs/mediciones/f3s_extraccion_f3base.json` y `f3v_lote_1387_r1.json`. | Sección 4.3.1 (Eficacia en la intercepción de anomalías estructurales) | `docs/mediciones/f3s_extraccion_f3base.json`, `docs/mediciones/f3v_lote_1387_r1.json` (`excepciones`) |
| `docs/figuras/f4/grafico_4_2_resoluciones_cascada.png` | Gráfico 4.2 | Gráfico 4.2 Resoluciones exitosas de entidades (Total N = 11.560) distribuidas por etapa de la cascada jerárquica: CI exacta (1.850; 16,00 %), encabezado posicional (3.079; 26,63 %), expresiones regulares (3.103; 26,84 %), modelo del lenguaje BETO (3.382; 29,26 %) y coincidencia difusa RapidFuzz (146; 1,26 %). Fuente: Elaboración propia a partir de `docs/mediciones/f3v_lote_1387_r1.json`. | Sección 4.3.2 (Contribución por nivel del motor de extracción híbrido) | `docs/mediciones/f3v_lote_1387_r1.json` (`conteos_fuente_resolucion`) |
| `docs/figuras/f4/grafico_4_3_vinculacion_por_archivo.png` | Gráfico 4.3 | Gráfico 4.3 Desglose de vinculación directa frente a derivación a revisión humana HITL por cada uno de los siete archivos del lote de validación controlado (Total 1.360 directos [98,05 %] y 27 en revisión [1,95 %]). Fuente: Elaboración propia a partir de `docs/mediciones/f3v_lote_1387_r1.json`. | Sección 4.3.3 (Desempeño del mecanismo de vinculación por libro fuente) | `docs/mediciones/f3v_lote_1387_r1.json` (`distribucion_por_archivo`) |
| `docs/figuras/f4/grafico_4_4_kpi_cmi_perspectivas.png` | Gráfico 4.4 | Gráfico 4.4 Disponibilidad de indicadores estratégicos por perspectiva de Kaplan y Norton (Pretest: 0 indicadores vs Postest: 23 KPI catalogados y operativos en `bi.ref_kpi`): Financiera (9), Clientes (5), Procesos Internos (4, incluyendo KPI-23) y Aprendizaje y Crecimiento (5). Fuente: Elaboración propia a partir de `docs/mediciones/f3v_invariantes.json` y `f3v_kpi23.json`. | Sección 4.4.1 (Disponibilidad y cobertura del Cuadro de Mando Integral) | `docs/mediciones/f3v_invariantes.json`, `docs/mediciones/f3v_kpi23.json` |
| `docs/figuras/f4/grafico_4_5_tiempo_consolidacion_semilog.png` | Gráfico 4.5 | Gráfico 4.5 Comparativa en escala semilogarítmica del tiempo de consolidación informacional mensual: reducción del −97,9 % (Δ = −587,59 min) desde la línea base manual de 600,0 min (8 a 12 horas, SFV J2-15) hasta 12,41 min en postest analítico (máquina 424,29 s / 7,07 min n=3 + revisión humana KLM 320,60 s / 5,34 min con $W = 2,5$ s), cumpliendo holgadamente el requisito RNF-03 (< 15 min). Fuente: Elaboración propia a partir de `docs/mediciones/f3v_b7_corridas.json`, `f3v_klm.json` y SFV J2-15. | Sección 4.4.2 (Evaluación de eficiencia temporal y cumplimiento de RNF-03) | `docs/mediciones/f3v_b7_corridas.json`, `docs/mediciones/f3v_klm.json`, SFV J2-15 |
| `docs/figuras/f4/grafico_4_6_evaluacion_likert_pre_post.png` | Gráfico 4.6 | Gráfico 4.6 Evaluación comparativa de usabilidad y percepción técnica en escala Likert (1 a 5) entre la situación previa manual (media global 1,89) y la solución postest implementada (media global 4,62) aplicada a una muestra intencional de 10 usuarios clave en 9 dimensiones evaluadas. Fuente: Elaboración propia a partir de `docs/mediciones/f3r_mapa_j.json` y SFV J2-14. | Sección 4.5 (Evaluación cuasiexperimental de usabilidad y aceptación) | `docs/mediciones/f3r_mapa_j.json`, SFV J2-14 (`DATO_DE_LEAN`) |
| `docs/figuras/f4/grafico_kpi23_serie.png` | Gráfico 4.7 (Nuevo F4-3a) | Gráfico 4.7 Cumplimiento de inicios académicos planificados (KPI-23) por gestión anual en el Data Warehouse frente a bandas de semaforización CMI: gestión 2024 (100,00 %; VERDE), gestión 2025 (99,77 %; VERDE) y gestión 2026 en curso (46,62 %; ROJO), con meta institucional del 85,0 % y umbral crítico del 60,0 %. Fuente: Elaboración propia a partir de `docs/mediciones/f3v_kpi23_serie.json`. | Sección 4.4.1 (Análisis de indicadores del CMI - Procesos Internos) | `docs/mediciones/f3v_kpi23_serie.json` (`kpi23_por_gestion`) |
| `docs/figuras/f4/grafico_rnf03_n3_sensibilidad.png` | Gráfico 4.8 (Nuevo F4-3b) | Gráfico 4.8 Verificación rigurosa de RNF-03 con n = 3 corridas de máquina y análisis de sensibilidad KLM: desglose entre tiempo de cómputo (máquina vacía 424,29 ± 22,24 s; llena 36,53 ± 0,28 s) y tiempo de revisión humana HITL ante variaciones del tiempo de respuesta del sistema W (W = 0 s: 10,41 min; W = 2,5 s medido: 12,41 min; W = 10 s: 18,41 min), demostrando cumplimiento por debajo de la meta de 15 min y el límite aceptable de 20 min. Fuente: Elaboración propia a partir de `docs/mediciones/f3v_b7_corridas.json` y `f3v_klm.json`. | Sección 4.4.2 (Análisis de sensibilidad y robustez de tiempos de ciclo) | `docs/mediciones/f3v_b7_corridas.json`, `docs/mediciones/f3v_klm.json` |
| `docs/figuras/f4/grafico_rendimiento_locust_newman.png` | Gráfico 4.9 (Nuevo F4-3c) | Gráfico 4.9 Resultados de las pruebas de carga concurrente y contrato de endpoints: (a) Prueba de carga Locust con 50 usuarios concurrentes (1.121 requests, 0 fallos, 41,27 RPS, mediana 10,0 ms, percentil 95 de 34,0 ms); (b) Verificación automatizada de contratos de integración Newman (11 endpoints evaluados, 24/24 aserciones exitosas, 100,00 % de cumplimiento funcional). Fuente: Elaboración propia a partir de `docs/mediciones/f3v_locust.json` y `f3v_newman.json`. | Sección 3.7.3 (Pruebas de rendimiento concurrente e integración de APIs) | `docs/mediciones/f3v_locust.json`, `docs/mediciones/f3v_newman.json` |
| `docs/figuras/f4/grafico_f3v_completo_hechos.png` | Gráfico 4.10 (Nuevo F4-3d) | Gráfico 4.10 Distribución del volumen de hechos cargados en la base completa de los 10 libros institucionales en el Data Warehouse (Total: 764.972 hechos consolidados; 715.217 en evaluación docente, 25.191 en rendimiento académico, 10.719 en situación financiera, 10.510 en marketing, 1.663 en planificación académica, 1.371 en costos, 206 en techos y 95 en rentabilidad) bajo idempotencia estricta por `carga_fila_origen`. Fuente: Elaboración propia a partir de `docs/mediciones/f3v_completo.json`. | Sección 3.6.2 (Capacidad y volumen transaccional del almacén de datos) | `docs/mediciones/f3v_completo.json` (`conteos`) |

---

## 2. Sección: Figuras Retiradas o Reemplazadas frente a FIGURAS_F3V

En cumplimiento de las auditorías F4-0, F4-1 y F4-2 (`docs/mediciones/f4_figuras_vs_sfv.json` y `docs/mediciones/f4_cifras_sin_trazar.json`):

### 2.1 Figura Retirada Formalmente
- **Gráfico 3.5 (OLS de matrícula mensual, N = 33 meses):**
  - **Motivo de retiro:** En `FIGURAS_F3V.md` citaba «SFV Tabla J.1 (E-14)». La auditoría demostró que la Sección E de `docs/fuente_verdad_tesis.md` solo abarca de E-01 a E-11. Los valores (pendiente +3,6541, $R^2 = 0,1921$, $p = 0,0107$) fueron calculados al vuelo desde un CSV auxiliar `data/reproducibilidad/graficos/inscritos.csv` y nunca existieron como medición congelada en `docs/mediciones/`.
  - **Invariante:** Los invariantes del repositorio declaran: *«OLS mensual N = 40; OLS anual solo descriptiva»* (sobre recaudación financiera).
  - **Instrucción para Chat 3:** **Retirar el Gráfico 3.5 y su texto descriptivo del documento `.docx`**. Si se requiere una regresión lineal en la tesis, debe utilizarse la serie de recaudación mensual con $N = 40$ trazada en `docs/mediciones/f3s_recaudacion_hw.json`.

### 2.2 Capturas de Terminal (F4-1: pendiente captura real de Lean)
En `FIGURAS_F3V.md`, tres imágenes fueron dibujadas sintéticamente mediante matplotlib simulando fondos negros de consola con valores estáticos:
1. `figura_3_40_captura_pytest_856.png`
2. `figura_3_44_captura_docker_ps_9_servicios.png`
3. `figura_3_50_captura_cobertura_72_42.png`

**Acción tomada en F4:**
- Se eliminó el código sintético que las dibujaba en `scripts/generar_figuras_f3_congelado.py` y cualquier intento de renderizado gráfico artificial en `scripts/generar_figuras_f4.py`.
- Se retiraron los 3 archivos PNG dibujados de `docs/figuras/f4/`.
- Estado: **pendiente: captura real de Lean** directamente desde la ventana de terminal real en ejecución.
- Procedimiento de incorporación: cuando Lean entregue las capturas, se ubicarán en `docs/figuras/f4/` con los nombres exactos indicados (`figura_3_40_captura_pytest_856.png`, `figura_3_44_captura_docker_ps_9_servicios.png`, `figura_3_50_captura_cobertura_72_42.png`) y se verificará que el texto visible coincida estrictamente con `docs/mediciones/f3v_pruebas.json` (875 colectadas, 856 passed, 0 failed, 12 skipped, 7 xfailed; 72,42 % cobertura sobre 15.694 sentencias) y 9 contenedores `Up` en `docker compose ps`.

---

## 3. Estado de Capturas de la Aplicación en Ejecución (F4-4)

- **Condición según PLAN_F4 (DECISIÓN 2):** *«F4-4 empieza solo cuando `git status --short frontend/` esté vacío, y el pie de cada captura incluye el hash de ese commit.»*
- **Estado actual del árbol de trabajo:** El directorio `frontend/` cuenta con más de 40 archivos modificados y módulos nuevos desarrollados por Lean (interfaz V2, componentes de DataOps, stepper de 3 pasos, tabs de texto preparado).
- **Plan de acción para Chat 3:**
  - Las capturas de la interfaz web (flujo de 3 pasos V1/V2 claro y oscuro, y scorecard CMI con 23 KPIs) se tomarán sobre el clon tmpfs de `f3v_completo` en cuanto Lean realice el commit de cierre de `frontend/`.
  - No se generaron capturas simuladas con frontend a medio editar para no violar el principio de fidelidad del sistema real.

---

## 4. Directivas de Integración para Chat 3 (`claude.ai`)

1. **Flujo DataOps de 3 Pasos (Corrección obligatoria):**
   - Asegurarse de que en todo el cuerpo del documento `.docx` el pipeline de integración se denomine y describa como un flujo de **3 pasos**:
     - **Paso 1:** Carga de Archivos (`/dataops/ingesta`)
     - **Paso 2:** Lectura de BETO (`/dataops/beto`, con visualización de texto preparado)
     - **Paso 3:** Revisión HITL (`/dataops/revision`, formulario por tipo de caso y persistencia)
   - Eliminar cualquier referencia residual a «4 pasos». Reemplazar la figura del flujo por `docs/figuras/f4/figura_flujo_dataops_3pasos.png`.

2. **Invariantes del Data Warehouse y Catálogo CMI (23 KPIs):**
   - Actualizar las tablas del documento para declarar:
     - **51 tablas** base en la base de datos.
     - **10 vistas** en esquema `bi`.
     - **10 tablas de hechos** (destacar la adición de `fact_planificacion_programa`).
     - **7 dimensiones conformadas** (con `dim_meta`).
     - **1 tabla puente** (`bridge_modulo_docente`).
     - **23 KPIs** en el CMI (Perspectiva de Procesos Internos con 4 KPIs: KPI-10, KPI-11, KPI-18 y KPI-23).

3. **Cifras de RNF-03 y KPI-23:**
   - **RNF-03:** Documentar con los datos de $n = 3$: tiempo total de 12,41 min (máquina en frío 424,29 s ± 22,24 s + operador KLM 320,6 s con $W = 2,5$ s), con reducción del −97,9 % frente a la línea base manual de 600,0 min (8 a 12 horas, SFV J2-15).
   - **KPI-23:** Documentar la serie anual: 2024 = 100,00 % (Verde), 2025 = 99,77 % (Verde) y 2026 = 46,62 % (Rojo, gestión en curso al corte de marzo 2026).

4. **Capturas de Terminal (Figuras 3.40, 3.44 y 3.50):**
   - Permanecen en estado **[pendiente: captura real de Lean]**. No deben insertarse figuras dibujadas artificialmente. Cuando Lean entregue las capturas reales de terminal, se colocarán en `docs/figuras/f4/` con el mismo nombre y se verificarán contra `docs/mediciones/f3v_pruebas.json`.
