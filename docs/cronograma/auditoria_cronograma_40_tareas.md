# Auditoría del Cronograma de Actividades (40 Tareas · 24 de Agosto – 19 de Noviembre)

> **Alcance:** Verificación integral del cumplimiento técnico de las 40 actividades del cronograma del proyecto **GiraGroup BI System** (*Sistema de Inteligencia de Negocios basado en BETO y Cuadro de Mando Integral*), contrastando su existencia en código fuente (`frontend/src/`, `backend/`, `pipeline/`, `scripts/`, `docs/`), su visibilidad en la interfaz web (`http://localhost:5173`) y los prompts de implementación para las tareas web faltantes.

---

## 1. Resumen Ejecutivo de Verificación en Vivo (`http://localhost:5173`)

Durante la inspección en vivo sobre el entorno local (`frontend` en `http://localhost:5173` y `backend` FastAPI en `http://localhost:8000`):

- **Cobertura de rutas del menú lateral:** Las **19 rutas** del menú lateral definidas en `frontend/src/components/layout/Sidebar.jsx` y mapeadas en `frontend/src/App.jsx` (árbol V1 `/` y árbol paralelo V2 `/v2/*`) responden operativamente con **HTTP 200**.
- **Flujo DataOps en vivo (`/dataops/ingesta`):** El panel muestra `Historial de lotes (15)`, incluyendo `Lote #15 · BD Egresos.xlsx`, `Lote #13 · Experiencia Docente 2.0.xlsx`, `Lote #12` y `Lote #11`, junto con la pestaña `Bitácora` con huella criptográfica **SHA-256** por archivo ingestado.
- **Trazabilidad del Lote #15:** Las vistas `/dataops/lote/15/texto`, `/dataops/lote/15/beto` y `/dataops/lote/15/revision` operan correctamente; el paso de revisión humana muestra **`1.409` registros** asociados al flujo.
- **Módulos analíticos y administrativos:** Operativos en `/dashboard` (y `/cmi`), `/academico/rendimiento` (`/alertas-tempranas`), `/academico/docente`, `/academico/catalogo`, `/academico/proyeccion`, `/financiero/recaudacion`, `/financiero/cartera`, `/financiero/metas`, `/financiero/proyeccion`, `/admin/usuarios`, `/admin/catalogos`, `/admin/auditoria`, `/reportes`, `/notificaciones` y `/ajustes`.

---

## 2. Tabla Auditada de las 40 Actividades del Cronograma

| # | Actividad | Cumple | ¿Vista Web? | Ubicación Exacta (Frontend / Backend / Docs) | Qué se ve en Web / Qué mostrar en Código | Prompt (si es web y falta) |
|---:|---|---|---|---|---|---|
| 1 | Configuración de contenedores Docker (API, pipeline, base de datos y frontend) y orquestación con docker-compose | Sí | No (Infraestructura) | `docker-compose.yml`, `docker-compose.gpu.yml`, `iniciar_sistema.bat`, `apagar_sistema.bat` | En código: orquestación de contenedores para API, pipeline, base de datos PostgreSQL y frontend con scripts de arranque y apagado. | N/A (Infraestructura) |
| 2 | Modelado dimensional del Data Warehouse: definición de hechos, dimensiones e indicadores de gestión | Sí | Parcial (Datos Maestros / CMI) | `db/schema.sql`, `backend/models/` (`dim_*.py`, `fact_*.py`), `docs/fuente_verdad_tesis.md` | En código: modelo constelación (`dim_estudiante`, `dim_docente`, `dim_modulo`, `dim_tiempo`, `fact_rendimiento`, `fact_financiero`, `fact_cobranzas`, `fact_evaluacion`). En web: `/dataops/datos-maestros` y `/dashboard`. | N/A |
| 3 | Implementación del esquema relacional inicial en PostgreSQL (tablas de dimensión y hechos) | Sí | No (Base de datos) | `db/schema.sql`, `db/schema_catalogos.sql`, `backend/scripts/migrations/001_initial_constellation_baseline.sql`, `db/migrations/` | En código: DDL inicial en PostgreSQL y migraciones idempotentes (`001`–`016`) ejecutadas en arranque con `pg_advisory_lock`. | N/A (Base de datos) |
| 4 | Definición del marco de trabajo Scrum: backlog priorizado, roles del equipo y tablero de seguimiento semanal | Sí | No (Documental) | `docs/tesis/revision_tesis_cap1_3_4_5.md`, `docs/fuente_verdad_tesis.md`, `docs/cronograma/auditoria_cronograma_40_tareas.md` | En docs: planificación iterativa por sprints/loops documentada en la tesis y seguimiento del cronograma de 40 actividades. | N/A (Gestión documental) |
| 5 | Mapeo objeto-relacional (ORM) de las entidades académicas y financieras en SQLAlchemy | Sí | No (Backend ORM) | `backend/models/dim_estudiante.py`, `dim_docente.py`, `dim_modulo.py`, `fact_rendimiento.py`, `fact_financiero.py`, `fact_cobranzas.py`, `fact_evaluacion.py` | En código: modelos declarativos SQLAlchemy para dimensiones, hechos, staging (`staging_entidad.py`, `staging_registro.py`) y bitácoras. | N/A (Backend ORM) |
| 6 | Implementación del endpoint base de monitoreo (health check) y validación de conectividad entre contenedores | Parcial (Solo API) | **No** (Falta en UI) | `backend/main.py:261-281` (`GET /api/v1/health`, `GET /health`), `frontend/src/modules/admin/AuditoriaSistema.jsx` | En código: el endpoint `GET /api/v1/health` verifica conectividad DW sin fugar credenciales. **En web no se muestra** el estado de salud en tiempo real. | **Ver Prompt 1 (Sección 3)** |
| 7 | Desarrollo del lector de archivos Excel/Google Sheets con limpieza estructural y normalización de cabeceras | Sí | Sí | `pipeline/ingesta.py` (`_leer_xlsx`), `pipeline/normalization/normalizer.py`, `backend/services/ingestion_service.py`, `frontend/src/modules/dataops/IngestView.jsx` | En código: lectura multi-hoja `.xlsx`/`.xls` y normalización estructural de cabeceras. En web (`/dataops/ingesta`): carga drag & drop y `Historial de lotes (15)`. | N/A |
| 8 | Desarrollo del lector de formularios Google Forms (CSV) para datos de admisión | Sí | Sí | `pipeline/ingesta.py` (lector `.csv`), `backend/services/ingestion_service.py` (`ALLOWED_EXTENSIONS`), `frontend/src/modules/dataops/IngestView.jsx` | En código: lectura CSV con detección de delimitador y codificación para formularios. En web (`/dataops/ingesta`): soporte `.csv` en la carga de lotes. | N/A |
| 9 | Desarrollo del lector de reportes exportados de Moodle (CSV/XLSX) | Sí | Parcial (Flujo de ingesta) | `backend/services/readers/moodle_adapter.py`, `pipeline/ingesta.py`, `frontend/src/modules/dataops/IngestView.jsx` | En código: adaptador específico para reportes exportados de Moodle (CSV/XLSX). En web (`/dataops/ingesta`): trazabilidad dentro del historial de lotes. | N/A |
| 10 | Construcción del dispatcher que identifica el tipo de fuente documental y enruta al lector correspondiente | Sí | Parcial (Estado de ingesta) | `pipeline/ingesta.py` (`LECTORES`), `backend/services/ingestion_service.py` | En código: registro dinámico `LECTORES` que identifica la fuente documental y enruta al lector correspondiente. En web: detalle de fuente por lote en `/dataops/ingesta`. | N/A |
| 11 | Conversión estandarizada de los registros crudos a texto plano bajo el contrato de salida único del pipeline | Sí | Sí | `pipeline/semantic/formatter.py`, `backend/services/texto_preparado_service.py`, `frontend/src/modules/dataops/PlainTextTransformationView.jsx` | En web (`/dataops/texto` y `/dataops/lote/15/texto`): visualización de líneas estandarizadas (`col: val \| col: val`) bajo contrato único antes de inferencia BETO. | N/A |
| 12 | Ajuste del esquema constelación en PostgreSQL según los campos reales identificados en la etapa de ingesta | Sí | No (Base de datos) | `db/migrations/V005__add_nlp_quality_financial_columns.sql` .. `V012__fact_eval_respuesta_por_pregunta.sql`, `backend/scripts/migrations/` | En código: migraciones SQL que amplían dimensiones y hechos según columnas reales identificadas en las fuentes de ingesta. | N/A (Base de datos) |
| 13 | Registro de logs técnicos del pipeline de ingesta para trazabilidad de los archivos procesados | Sí | Sí | `pipeline/pipeline_logger.py`, `backend/models/log_pipeline.py`, `backend/services/bitacora_dataops.py`, `frontend/src/modules/dataops/IngestView.jsx` | En código: bitácora técnica y huella SHA-256 por archivo. En web (`/dataops/ingesta`): pestaña `Bitácora` con trazabilidad de lotes procesados. | N/A |
| 14 | Prototipado del modelo BETO en entorno aislado para pruebas de tokenización y generación de embeddings | Sí | No (Script offline) | `scripts/preparar_corpus_robusto.py`, `scripts/entrenar_beto_robusto.py`, `pipeline/semantic/beto_local/` (`tokenizer.json`, `config.json`) | En código: tokenización WordPiece (`dccuchile/bert-base-spanish-wwm-cased`, `max_length=128`) y entrenamiento reproducible con 9 etiquetas IOB2 (`best_dev_f1 = 0.9979`). | N/A (Proceso offline) |
| 15 | Desarrollo del extractor de entidades nombradas (NER) para estudiantes, docentes y módulos | Sí | Sí | `pipeline/semantic/ner_engine.py`, `pipeline/semantic/ner_schema.py`, `backend/services/lectura_beto_service.py`, `frontend/src/modules/dataops/BetoReadingFlowView.jsx` | En web (`/dataops/beto` y `/dataops/lote/15/beto`): extracción de `PER_ESTUDIANTE`, `PER_DOCENTE`, `MODULO` y `PROGRAMA` fila por fila. | N/A |
| 16 | Implementación de la normalización de cadenas con rapidfuzz para resolver variaciones tipográficas | Sí | Parcial (Datos Maestros) | `pipeline/normalization/fuzzy_normalizer.py`, `pipeline/normalization/person_resolver.py`, `scripts/demo_beto_rapidfuzz.py` | En código: limpieza Unicode y similitud con `rapidfuzz` para variaciones tipográficas de nombres, módulos y programas. | N/A |
| 17 | Desarrollo del matching semántico entre registros dispersos sin identificador común confiable | Sí | Sí | `pipeline/normalization/semantic_matcher.py`, `backend/services/cross_source_reconciler.py`, `frontend/src/modules/dataops/MasterDataView.jsx` | En código: emparejamiento entre fuentes dispersas sin CI confiable (`Estado A/B/C`). En web (`/dataops/datos-maestros`): consulta de entidades consolidadas. | N/A |
| 18 | Cálculo del nivel de confianza probabilístico por registro extraído | Sí | Sí | `pipeline/semantic/indice_confianza.py`, `backend/services/confianza_service.py`, `frontend/src/modules/dataops/BetoReadingFlowView.jsx` | En web (`/dataops/lote/15/beto`): índice de confianza (`indice_registro`), estado y explicación llana por cada registro extraído. | N/A |
| 19 | Implementación del indicador "requiere revisión" para clasificaciones de baja confianza | Sí | Sí | `backend/services/bandeja_grupos.py`, `backend/services/revision_consulta.py`, `frontend/src/modules/dataops/HumanReviewFlowView.jsx` | En web (`/dataops/revision` y `/dataops/lote/15/revision`): bandeja HITL con `1.409` registros agrupados por motivo (`BAJA_CONFIANZA_IA`, `CI_DUDOSA`, `HOMONIMIA`). | N/A |
| 20 | Registro estructurado de inconsistencias detectadas durante el procesamiento semántico | Sí | Sí | `backend/models/log_inconsistencia.py`, `backend/services/bitacora_dataops.py`, `backend/services/integridad_dataops.py`, `frontend/src/modules/dataops/IngestView.jsx` | En código: `5.090` filas registradas en `log_inconsistencias` (`0` descartes sin bitácora). En web: pestaña `Bitácora` y motivos en `/dataops/lote/:id/revision`. | N/A |
| 21 | Persistencia de los resultados del PLN en las tablas de hechos académico y financiero | Sí | Parcial (Estado de lote) | `backend/services/dw_loader.py`, `backend/services/clave_fila.py`, `docs/evidencias/ciclo_idempotencia_hitl.json` | En código: carga idempotente a `fact_rendimiento`, `fact_financiero`, `fact_cobranzas` y `fact_evaluacion` (`0` duplicados en re-ejecución). En web: contadores en `/dataops/ingesta`. | N/A |
| 22 | Evaluación del modelo mediante matriz de confusión y cálculo de F1-score | Parcial (Solo JSON/PNG) | **No** (Falta en UI) | `scripts/matriz_confusion_ner.py`, `docs/mediciones/f3r_matriz_confusion.json`, `docs/mediciones/f1_d3b_calidad_v2_gold.json`, `frontend/src/modules/dataops/BetoReadingFlowView.jsx` | En código/docs: F1 estricto `0,9796` / relajado `0,9942` y matriz sobre `510` entidades (`gold_510`). **En web no se muestra** el resumen de calidad del modelo ni su matriz de confusión. | **Ver Prompt 2 (Sección 3)** |
| 23 | Desarrollo del endpoint de ingesta manual (POST /pipeline/process) para disparar el procesamiento bajo demanda | Sí | Sí | `backend/routers/pipeline.py:264-281` (`POST /api/v1/pipeline/process`), `frontend/src/modules/dataops/IngestView.jsx`, `frontend/src/components/shared/TareasSegundoPlano.jsx` | En web (`/dataops/ingesta`): disparo de procesamiento bajo demanda y barra flotante persistente de tareas en segundo plano. | N/A |
| 24 | Implementación de la lógica de reglas de negocio para las alertas de riesgo académico, deserción y financiero | Sí | Sí | `backend/services/alert_engine.py`, `backend/services/financial_rules_engine.py`, `backend/routers/riesgos.py`, `frontend/src/modules/academic/RendimientoAlertas.jsx` | En web (`/academico/rendimiento`, `/academico/alertas`, `/alertas-tempranas`): listado de estudiantes en riesgo, severidad y reglas activadas. | N/A |
| 25 | Desarrollo de endpoints de consulta (KPIs y alertas cruzadas) y su consumo desde el portal de auditoría web | Sí | Sí | `backend/routers/kpis.py`, `backend/routers/riesgos.py`, `backend/routers/audit.py`, `frontend/src/modules/admin/AuditoriaSistema.jsx`, `frontend/src/modules/admin/CuadroMandoIntegral.jsx` | En web (`/admin/auditoria`, `/dashboard`, `/academico/*`, `/financiero/*`): consumo de KPIs, alertas cruzadas y bitácora de auditoría. | N/A |
| 26 | Implementación de autenticación JWT y control de acceso basado en roles | Sí | Sí | `backend/routers/auth.py`, `frontend/src/modules/auth/LoginPage.jsx`, `frontend/src/App.jsx` (`ProtectedRoute`, `RoleRoute`) | En web (`/login`): autenticación JWT y redirección RBAC para 5 roles (`ADMIN`, `AUDITOR_CALIDAD`, `DIRECTOR_ACADEMICO`, `ANALISTA_FINANCIERO`, `ANALISTA_MARKETING`). | N/A |
| 27 | Validación de llaves foráneas con respaldo por coincidencia difusa (fuzzy matching) | Sí | Parcial (Datos Maestros / HITL) | `pipeline/normalization/fk_resolver.py`, `backend/services/dw_loader.py`, `frontend/src/modules/dataops/HumanReviewFlowView.jsx` | En código: resolución de llaves foráneas con respaldo `rapidfuzz` antes de derivar registros no resueltos a revisión humana. | N/A |
| 28 | Anonimización de los datos reales utilizados en las pruebas del sistema | Sí | Sí (Enmascaramiento CI) | `scripts/anonimizar.py`, `backend/services/dataops_privacy.py`, `frontend/src/modules/dataops/BetoReadingFlowView.jsx` (`useRevealCi`) | En código: script de anonimización para pruebas. En web (`/dataops/lote/15/beto`): enmascaramiento de CI y botón `Revelar con auditoría`. | N/A |
| 29 | Conexión de Power BI al Data Warehouse y modelado del esquema tabular del Cuadro de Mando Integral | Sí | Sí (Integración CMI) | `powerbi/dashboards/giragroup_cmi.pbix`, `powerbi/dashboards/guia_integracion_powerbi_forecasting.md`, `backend/routers/powerbi.py`, `frontend/src/modules/admin/cmi/CmiPowerBi.jsx` | En artefacto `.pbix`: modelo tabular conectado al DW. En web (`/dashboard` -> `CmiPowerBi.jsx`): integración y descarga/enlace de vistas Power BI. | N/A |
| 30 | Construcción del dashboard de la perspectiva académica (rendimiento, aprobación y riesgo) | Sí | Sí | `frontend/src/modules/academic/RendimientoAlertas.jsx`, `frontend/src/modules/academic/CatalogoCurricular.jsx`, `frontend/src/modules/admin/cmi/CmiScorecard.jsx`, `powerbi/dashboards/giragroup_cmi.pbix` | En web (`/academico/rendimiento`, `/academico/catalogo` y CMI): tasas de aprobación, rendimiento académico y alertas de riesgo. | N/A |
| 31 | Construcción del dashboard de la perspectiva financiera (mora, cartera y cumplimiento de metas) | Sí | Sí | `frontend/src/modules/finance/RecaudacionCobranzas.jsx`, `CarteraMora.jsx`, `MetasGestion.jsx`, `ProyeccionFinanciera.jsx`, `powerbi/dashboards/giragroup_cmi.pbix` | En web (`/financiero/recaudacion`, `/financiero/cartera`, `/financiero/metas`, `/financiero/proyeccion`): mora, cartera, recaudación y cumplimiento de metas. | N/A |
| 32 | Construcción de los dashboards de las perspectivas docente y estudiantil | Sí | Sí | `frontend/src/modules/academic/DesempenoDocente.jsx`, `frontend/src/modules/academic/ProyeccionAlumnos.jsx`, `frontend/src/modules/admin/cmi/CmiScorecard.jsx`, `powerbi/dashboards/giragroup_cmi.pbix` | En web (`/academico/docente`, `/academico/proyeccion` y CMI): evaluación/ranking docente y proyección/retención estudiantil. | N/A |
| 33 | Construcción del dashboard de calidad del pipeline (documentos procesados, confianza e inconsistencias) | Sí | Sí | `frontend/src/modules/dataops/IngestView.jsx`, `BetoReadingFlowView.jsx`, `HumanReviewFlowView.jsx`, `frontend/src/modules/admin/AuditoriaSistema.jsx` | En web (`/dataops/ingesta`, `/dataops/beto`, `/dataops/revision`, `/admin/auditoria`): documentos procesados, confianza BETO e inconsistencias (`Bitácora`). | N/A |
| 34 | Definición de medidas DAX para indicadores de tiempo e inteligencia temporal | Sí | Parcial (Detalle KPI CMI) | `powerbi/dashboards/giragroup_cmi.pbix`, `powerbi/dashboards/guia_integracion_powerbi_forecasting.md`, `backend/routers/cmi.py`, `frontend/src/modules/admin/cmi/CmiDetalleKpi.jsx` | En Power BI: medidas DAX de inteligencia temporal. En web (`/dashboard` -> `CmiDetalleKpi.jsx`): series históricas y comparativas por gestión. | N/A |
| 35 | Elaboración del checklist de verificación de KPIs disponibles en el Cuadro de Mando Integral | Sí | Sí | `frontend/src/modules/admin/cmi/CmiScorecard.jsx`, `GlosarioCmi.jsx`, `CmiConfiguracion.jsx`, `docs/fuente_verdad_tesis.md` | En web (`/dashboard` y `/cmi`): scorecard completo de KPIs por perspectiva, glosario de fórmulas (`GlosarioCmi.jsx`) y verificación de umbrales (`CmiConfiguracion.jsx`). | N/A |
| 36 | Ejecución de pruebas funcionales integrales (caja negra y caja blanca) sobre pipeline, API y dashboards | Sí | No (CLI / CI) | `backend/tests/`, `tests/`, `e2e/`, `docs/mediciones/f3s_newman.json`, `docs/mediciones/f3s_locust.json`, `docs/mediciones/f3s_b7_corridas.json` | En código/docs: pruebas Pytest (caja blanca), colecciones Newman y pruebas de carga Locust RNF-03 (caja negra) sobre API y pipeline. | N/A (Suite de pruebas) |
| 37 | Medición postest de indicadores estratégicos y comparación con la línea base (pretest-postest) | Parcial (Solo Docs/Gráfico) | **No** (Falta en UI) | `docs/evidencias/graficos_v2/grafico_4_6_evaluacion_likert_pre_post.png`, `docs/mediciones/f3s_klm.json`, `frontend/src/modules/admin/CuadroMandoIntegral.jsx` | En docs: evidencia gráfica Likert Pre-Post y tiempos KLM. **En web no existe** una vista o pestaña comparativa Pretest–Postest dentro del CMI. | **Ver Prompt 3 (Sección 3)** |
| 38 | Calibración final de los umbrales de riesgo según retroalimentación del Comité Directivo | Sí | Sí | `frontend/src/modules/admin/cmi/CmiConfiguracion.jsx`, `backend/routers/cmi.py`, `backend/services/alert_engine.py` | En web (`/dashboard` -> pestaña Configuración): ajuste y calibración de umbrales de semáforo (verde/amarillo/rojo) y reglas de riesgo. | N/A |
| 39 | Despliegue del sistema en el entorno de la organización y verificación de estabilidad de contenedores | Sí | No (Infraestructura) | `docker-compose.yml`, `iniciar_sistema.bat`, `reconstruir_sistema.bat`, `apagar_sistema.bat`, `docs/cierres/CIERRE_F3S.md` | En código/docs: despliegue contenedorizado reproducible y verificación de estabilidad operativa entre `frontend`, `backend` y `db`. | N/A (Infraestructura) |
| 40 | Últimas funcionalidades y ajuste del producto: revisión general, documentación técnica y cierre operativo | Sí | Sí | `frontend/src/modules/settings/AjustesSistema.jsx`, `frontend/src/modules/reports/CentroReportes.jsx`, `docs/tesis/tablas_v2.md`, `docs/cronograma/` | En web (`/ajustes`, `/reportes`, `/notificaciones`): ajustes finales y tema V1/V2. En docs: tablas finales, gráficos v2 y auditoría del cronograma. | N/A |

---

## 3. Prompts para Tareas Web Faltantes

### Prompt 1 — Tarea 6: Indicador de Salud del Sistema (`GET /api/v1/health`) en `AuditoriaSistema.jsx`

> **Objetivo:** Mostrar en `frontend/src/modules/admin/AuditoriaSistema.jsx` el estado en vivo de conectividad con el Data Warehouse consumiendo el endpoint ya existente `GET /api/v1/health` (`backend/main.py:261-281`).

```text
En `frontend/src/modules/admin/AuditoriaSistema.jsx`, agrega un indicador de salud del sistema en la cabecera superior (junto a los KPIs de auditoría) que consulte `GET /api/v1/health` al montar el componente y permita refrescarlo manualmente con un botón.
Requisitos:
1. Crea o reutiliza una función en `frontend/src/api/auditApi.js` que haga `GET /api/v1/health` y maneje errores de red sin romper la vista.
2. Muestra un badge de estado ("DW Conectado" en verde si `status === 'healthy'`, o "DW Sin Conexión" en rojo si falla), la latencia de respuesta en ms y la marca de tiempo de la última verificación.
3. No modifiques la lógica de autenticación ni el contrato del backend en `backend/main.py`.
```

### Prompt 2 — Tarea 22: Panel de Métricas y Matriz de Confusión de BETO (`beto-v2`) en `BetoReadingFlowView.jsx`

> **Objetivo:** Incorporar en `frontend/src/modules/dataops/BetoReadingFlowView.jsx` un modal o panel colapsable ("Calidad del Modelo BETO") con las métricas verificadas del modelo vigente (`beto-v2`), sin alterar el flujo de inferencia por lote.

```text
En `frontend/src/modules/dataops/BetoReadingFlowView.jsx`, agrega un botón secundario "Métricas del Modelo BETO" en el encabezado del flujo que abra un panel/modal informativo de solo lectura con los indicadores del modelo vigente (`dccuchile/bert-base-spanish-wwm-cased`, 9 etiquetas IOB2):
1. Mostrar métricas globales sobre `gold_510` (Modo C): F1 estricto `97,96%` (Precisión `97,29%`, Recall `98,63%`) y F1 relajado `99,42%`, además de `best_dev_f1 = 0,9979`.
2. Renderizar una tabla compacta de desglose por clase (`MODULO`: F1 100%, `PER_DOCENTE`: F1 100%, `PER_ESTUDIANTE`: F1 99,23%, `PROGRAMA`: F1 94,82%) y la matriz de confusión a nivel token (`O`, `MODULO`, `PER_DOCENTE`, `PER_ESTUDIANTE`, `PROGRAMA`) destacando que la única confusión residual es de frontera en `PER_ESTUDIANTE` -> `PROGRAMA` (1 token en `gold_510`).
3. Mantén el diseño institucional y los tokens CSS existentes del módulo DataOps sin modificar el backend.
```

### Prompt 3 — Tarea 37: Pestaña Comparativa Pretest–Postest en `CuadroMandoIntegral.jsx`

> **Objetivo:** Añadir una pestaña o sección comparativa Pretest vs. Postest dentro de `frontend/src/modules/admin/CuadroMandoIntegral.jsx` para visualizar en web el impacto medido antes y después de la implantación del sistema BI + BETO.

```text
En `frontend/src/modules/admin/CuadroMandoIntegral.jsx`, agrega una nueva pestaña llamada "Comparativa Pretest–Postest" junto a las vistas actuales (Scorecard, Configuración, Glosario, Power BI).
Requisitos:
1. Renderiza tarjetas comparativas (Antes / Después / Variación) para: tiempo de consolidación mensual, tasa de automatización directa (98,05% en lote controlado), cobertura de trazabilidad de inconsistencias (100% con bitácora B-9) y resultados de evaluación de usabilidad/percepción (Pretest vs. Postest).
2. Incluye un gráfico comparativo de barras agrupadas usando `react-chartjs-2` (ya importado en `CuadroMandoIntegral.jsx`) respetando el tema claro/oscuro (`useTheme`) y los estilos de `frontend/src/modules/admin/cmi/cmi.css`.
3. Marca claramente la fuente de cada dato (medición operativa del sistema vs. encuesta de evaluación externa) sin alterar las consultas existentes del CMI.
```

---

## 4. Archivo de Entrenamiento de BETO y Visibilidad Web

1. **Script de entrenamiento vigente:** `scripts/entrenar_beto_robusto.py`
   - **Modelo base:** `dccuchile/bert-base-spanish-wwm-cased`.
   - **Esquema de etiquetas (9 clases IOB2):** `O`, `B-PER_ESTUDIANTE`, `I-PER_ESTUDIANTE`, `B-PER_DOCENTE`, `I-PER_DOCENTE`, `B-MODULO`, `I-MODULO`, `B-PROGRAMA`, `I-PROGRAMA`.
   - **Hiperparámetros:** 3 épocas fijas con optimizador `AdamW` (`lr = 2.5e-5`, `weight_decay = 0.01`, `batch_size = 16`, `max_length = 128`, CPU determinístico con semilla `42` y `PYTHONHASHSEED=0`), seleccionando el mejor checkpoint por F1 estricto en `dev` sin early stopping.
   - **Resultado registrado:** `best_dev_f1 = 0.9979` en la época 2 (`train_duration_sec = 4537.58`).
2. **Script de generación de corpus:** `scripts/preparar_corpus_robusto.py` (genera `train_robusto.jsonl` con 1.400 ejemplos, `dev_robusto.jsonl` con 350 y `test_gold_real.jsonl` con 180 líneas / 510 entidades, garantizando partición disjunta por persona).
3. **Artefactos del modelo entrenado (`pipeline/semantic/beto_local/`):**
   - `model.safetensors` (SHA-256: `9ff7fb9d914aca9eaa0618d9603d869a30808d9218369aef7b12dd92362b5f92`)
   - `training_info.json`
   - `metricas_ner_robusto.json`
   - `predicciones_test_gold.json`
   - `config.json`, `tokenizer.json`, `tokenizer_config.json`
4. **Aclaración sobre script legado:** `scripts/finetune_beto_ner.py` es **código legado no usado** para entrenar el modelo vigente; se conserva únicamente porque `tests/transversales/test_agnostic_classifier_and_dw_reset.py` importa `RelationalExtractor` y `LABEL_LIST` desde ese archivo.
5. **Visibilidad en la web:**
   - **No se ve en la web:** el proceso de entrenamiento (`entrenar_beto_robusto.py`), los logs por época ni las métricas globales/matriz de confusión de `training_info.json` o `metricas_ner_robusto.json`.
   - **Sí se ve en la web:** la **inferencia por lote** en `/dataops/beto` y `/dataops/lote/:id/beto` (`BetoReadingFlowView.jsx`), donde se muestran fila por fila las entidades detectadas, el índice de confianza, la explicación llana de decisión y la revelación auditada de cédulas.

---

## 5. Observaciones de la Verificación en Vivo

Durante la navegación por la aplicación en `http://localhost:5173`, se observaron valores en `0` o `Sin dato` para el periodo **2026** en:
- `/dashboard` (indicadores de corte 2026 sin hechos cargados para ese año),
- `/financiero/cartera` (métricas de mora/cartera en `0` / `Sin dato` al filtrar 2026),
- `/financiero/metas` (ejecutado vs. meta en `0` / `Sin dato` para 2026),
- `/dataops/lote/15/beto` (campos opcionales de registro mostrados como `Sin dato` cuando la fila de origen —por ejemplo `BD Egresos.xlsx`— no contiene cédula, nota o módulo académico).

Esto responde al alcance temporal de los datos históricos cargados en el Data Warehouse y a la naturaleza heterogénea de las fuentes financieras frente a las académicas, no a fallos de renderizado de las vistas.
