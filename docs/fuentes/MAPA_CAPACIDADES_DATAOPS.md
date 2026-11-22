# Mapa Interno de Capacidades DataOps (Solo Defensa / Trazabilidad)

> **Uso interno:** este documento relaciona las tareas del cronograma con las tarjetas visibles en el flujo **① Carga → ② BETO → ③ Revisión**.
> **Regla de UI:** la interfaz web **no** muestra números de tarea ni la palabra «tarea»; muestra únicamente el título de capacidad, la cifra, una frase corta y el enlace a la evidencia.

## 1. Las 17 tareas del flujo DataOps + Tarea 33

| Tarea | Paso | Tarjeta visible en UI | Componente Frontend | Endpoint / Servicio Backend |
|---:|:---:|---|---|---|
| 7 | ① Carga | **Archivos leídos y limpiados** (hojas usadas/ignoradas y por qué, cabeceras normalizadas) | `IngestView.jsx` / `QueuePreviewTable.jsx` | `POST /api/v1/pipeline/preview-workbook`, `pipeline/ingesta.py` |
| 8 | ① Carga | **Formularios en línea (CSV)** reconocidos | `IngestView.jsx` (insignia por archivo en cola) | `pipeline/ingesta.py`, `backend/services/ingestion_service.py` |
| 9 | ① Carga | **Exportes de aula virtual** reconocidos | `IngestView.jsx` (insignia por archivo en cola) | `backend/services/readers/moodle_adapter.py`, `pipeline/ingesta.py` |
| 10 | ① Carga | **Tipo de fuente detectado** (tipo, 3 señales, confianza y corrección previa) | `IngestView.jsx`, `BatchHistory.jsx` | `POST /api/v1/pipeline/preview-workbook`, `pipeline/ingesta.py` (`LECTORES`) |
| 13 | ① Carga | **Bitácora del procesamiento** (etapas, tiempos, huella SHA-256) | `IngestView.jsx` / `BatchLogTimeline.jsx` | `GET /api/v1/dataops/lotes/{id}/bitacora`, `backend/services/bitacora_dataops.py` |
| 23 | ① Carga | **Procesar ahora** (disparo bajo demanda con progreso) | `IngestView.jsx`, `TareasSegundoPlano.jsx` | `POST /api/v1/pipeline/process` |
| 11 | ② BETO | **Texto preparado** (registro → texto plano bajo contrato único) | `BetoReadingFlowView.jsx` (pestaña «Texto preparado» con ejemplo antes/después) | `GET /api/v1/dataops/lotes/{id}/texto-preparado`, `backend/services/texto_preparado_service.py` |
| 15 | ② BETO | **Entidades reconocidas** (personas, docentes, módulos y programas resaltados IOB2) | `BetoReadingFlowView.jsx` / `EntityHighlightText.jsx` | `GET /api/v1/dataops/lotes/{id}/lectura-beto`, `backend/services/lectura_beto_service.py` (`beto_ents` en `payload_json`) |
| 18 | ② BETO | **Certeza por registro** (distribución de confianza y bandas 0,85 / 0,60) | `BetoReadingFlowView.jsx` (histograma de confianza) | `GET /api/v1/dataops/lotes/{id}/lectura-beto`, `pipeline/semantic/indice_confianza.py` |
| 22 | ② BETO | **Calidad del modelo** (matriz de confusión y F1 sobre `gold_510`) | `BetoReadingFlowView.jsx` → `BetoMetricasModal.jsx` | `GET /api/v1/dataops/beto/metricas` / artefactos `pipeline/semantic/beto_local/` |
| 28 | ② BETO | **Datos personales protegidos** (cédulas y nombres enmascarados; revelación auditada) | `BetoReadingFlowView.jsx`, `HumanReviewFlowView.jsx`, `useRevealCi.js` | `POST /api/v1/dataops/revelar-ci`, `backend/services/dataops_privacy.py` |
| 16 | ③ Revisión | **Variaciones de escritura resueltas** (similitud tipográfica) | `HumanReviewFlowView.jsx` (`CandidateSelector`) | `pipeline/normalization/fuzzy_normalizer.py`, `backend/services/revision_consulta.py` |
| 17 | ③ Revisión | **Coincidencias entre registros sin identificador común** | `HumanReviewFlowView.jsx` (`CandidateSelector` con score combinado) | `pipeline/normalization/semantic_matcher.py`, `backend/services/cross_source_reconciler.py` |
| 19 | ③ Revisión | **Marcados para revisión** (motivos, bandas y contador deduplicado) | `HumanReviewFlowView.jsx` (encabezado de bandeja maestro–detalle) | `GET /api/v1/dataops/lotes/{id}/review-tray`, `backend/services/bandeja_grupos.py` |
| 20 | ③ Revisión | **Inconsistencias registradas** (avisos de `log_inconsistencias` y su estado) | `HumanReviewFlowView.jsx` (pestaña «Avisos») | `GET /api/v1/dataops/lotes/{id}/review-tray/avisos`, `backend/models/log_inconsistencia.py` |
| 21 | ③ Revisión | **Guardado en el almacén de datos** (hechos académicos y financieros cargados) | `HumanReviewFlowView.jsx` (resultado de «Consolidar» con cifras) | `POST /api/v1/dataops/lotes/{id}/consolidar`, `backend/services/dw_loader.py` |
| 27 | ③ Revisión | **Claves validadas por similitud** (POS y módulos vinculados) | `HumanReviewFlowView.jsx` (`ModuleSearch` en `POS_NO_EN_DIM_MODULO`) | `pipeline/normalization/fk_resolver.py`, `backend/services/revision_acciones.py` |
| 33 | ① ② ③ | **Calidad integral del pipeline DataOps** (resumen transversal de lotes, confianza e inconsistencias) | Franja «Qué hizo el sistema en este paso» (`SystemCapabilitiesStrip.jsx`) | `GET /api/v1/dataops/lotes`, `backend/routers/dataops/*` |

## 2. Alcance de tareas fuera del flujo DataOps (DD7)

- **Tarea 6** (`GET /api/v1/health` en `AuditoriaSistema.jsx`): incluida en el loop **DF-L9 (f)** dentro del módulo de Auditoría (`/v2/admin/auditoria`).
- **Tarea 37** (pestaña Pretest–Postest en `CuadroMandoIntegral.jsx`): **fuera de este plan** por decisión `DD7` (pertenece al módulo CMI).
