# CIERRE DATAOPS_FLUJO — 2026-11-22
Rama / commit: `beto-integracion` `3e88499`
Hecho (máx. 10 líneas):
- **DF-L0 / DF-L6:** creado `docs/fuentes/MAPA_CAPACIDADES_DATAOPS.md` y franja `SystemCapabilitiesStrip.jsx` en los 3 pasos (sin números de tarea) + nota DD5 en `CmiDetalleKpi.jsx`.
- **DF-L1 (DD1):** eliminada la escritura automática al abrir ③ (`HumanReviewFlowView.jsx`); `PREPARACION_REVISION` se encadena al terminar `LECTURA_BETO` en `evaluacion.py`; conteo deduplicado en `consolidacion.py`; corregido `AnimatedNumberV2` en `BatchHistory.jsx` y `BatchFlowHeader.jsx`; período acotado en `asymmetric_flattener.py`.
- **DF-L2 / DF-L3 (DD2):** descriptor `acciones[]` por motivo y rol (`revision_acciones_descriptor.py`), ejecutor (`revision_acciones_ejecutor.py`), `SIN_LECTURA` separado de `BAJA_CONFIANZA_IA`, `/review-tray/avisos`, `/reabrir`, `APROBACION_BLOQUE`, candidatos RapidFuzz on-demand, vista maestro–detalle con atajos `A/D/↑/↓` y `ReviewActionRenderer.jsx`.
- **DF-L4 (DD7):** `beto_ents` persistido en `payload_json` de `staging_registro_crudo` sin crear tabla #52 (`CacheMemoria` por defecto en `beto_integracion.py`), sin hex fijos en `evaluacion.py`, texto `paso ②` en `lectura.py`, `EntityHighlightText.jsx`, paginación 20 y skeleton.
- **DF-L5 / DF-L7 / DF-L8 / DF-L9(f) / DF-L11:** bitácora timeline con SHA-256, lote = tipo + período, `fk_resolver.py` y `extraccion.py` sin listas fijas, `requirements-dev.txt`, DD3 enmascaramiento y `/riesgos/estudiante/{id}/revelar`, `AuditoriaSistema.jsx` con `GET /api/v1/health` y filtro de eventos, `CONTRATO_FUENTES.md` + fixtures sintéticas.

- **DF-L8 (b) completo:** todos los componentes de `frontend/src/modules/dataops/` quedaron `<= 300` líneas (`IngestView.jsx` 300, `HumanReviewFlowView.jsx` 264, `BetoReadingFlowView.jsx` 174, `BetoMetricasModal.jsx` 116) mediante extracción de subcomponentes (`IngestDropzonePanel`, `IngestRulesPanel`, `IngestQueueTable`, `IngestWorkbookPreview`, `IngestBatchFilesTable`, `BetoMetricasTablas`, `BetoCascadaResumen`, `RegistroBetoRow`).
- **DF-L9 (verificación visual Chrome CDP):** ejecutado `node e2e/dataops_flujo.mjs` con Chrome headless vía CDP sobre `/v2/dataops/ingesta`, `/v2/dataops/lote/46/beto`, `/v2/dataops/lote/46/revision`, `/v2/admin/auditoria` y `/v2/academico/rendimiento` en `1440`, `768` y `375` px (modos claro y oscuro): `0` errores de consola, `0` desbordamientos horizontales y `0` menciones de `tarea \d` en el DOM; capturas guardadas en `docs/mediciones/df_l9_capturas/`.
- **Correcciones de revisión:** corregido `page_size` `<= 50` en `lectura.py` (evitaba HTTP 422 en paso ② con `FILAS_BETO = 20`), corregidos atributos ORM (`ci`/`programa_origen` en `DimEstudiante`, `pos_code` en `DimModulo`) y `begin_nested()` en `revision_acciones_ejecutor.py` y `revision_consulta.py`, y añadida precarga `Programa`/`Módulo` desde texto plano (`R4`) + `por_que_detuvo` coherente en `SIN_LECTURA`.

No hecho y por qué:
- **DF-L10 (lote congelado v2 `df_lote_1387_v2.json`):** no ejecutado en este turno; requiere corrida controlada del lote completo y recongelado de SFV.

Invariantes cambiados: no (49 tablas `public` / 51 DW intactas, 10 vistas `bi`, cascada y umbrales 0,92/90/85/80 y bandas 0,85/0,60 sin cambios).

Pruebas:
- **Frontend (`vitest`):** 20 archivos / 106 passed / 0 failed + `vite build` OK (2.85 s).
- **Backend/Pipeline (`pytest` tras correcciones en `dataops_flujo`, `adw`, `f3v`, `f5c`):** 130 passed / 3 skipped / 0 failed (línea base completa previa: 1292 passed / 41 skipped / 7 xfailed).
- **E2E Chrome CDP (`node e2e/dataops_flujo.mjs`):** `ok: true` (`consoleErrors: []`, `overflowIssues: []`, `taskLeakIssues: []`).

Servicios reconstruidos + estado de docker compose ps:
- Reconstruidos y reiniciados `giragroup_web` (Up, :5173) y `giragroup_api` (Up, :8000).
- `GET http://localhost:8000/api/v1/health` → `{"status":"healthy","service":"giragroup-bi-api","database":"connected"}`.
- Los 9 contenedores de `docker-compose.yml` activos.

Cambios de esquema o API:
- Sin cambios de esquema en `giragroup_db` (DD7).
- Nuevos endpoints: `GET /api/v1/dataops/review-tray/avisos`, `POST /api/v1/dataops/review-tray/avisos/{id}/resolver`, `POST /api/v1/dataops/review-tray/{id}/reabrir`, `GET /api/v1/riesgos/estudiante/{id}/revelar`.
- `GET /api/v1/dataops/review-tray` incorpora `acciones[]`, `candidatos[]`, `page_size=20` y enmascaramiento DD3 en `/riesgos/*`.

Cifras nuevas (cifra | valor | archivo en docs/mediciones/):
- `KPI-22 2023` | `93` (coincide DW viva con `adw_l9_remedicion_final.csv`) | `docs/mediciones/df_l7_hallazgos.csv`
- `BAJA_CONFIANZA` origen | `74` filas (docs 45, 46, 53, 54; reclasificadas a `SIN_LECTURA` si conf=0) | `docs/mediciones/df_l7_hallazgos.csv`
- `Hechos sin id_tiempo` | `162` académicos, `34` financieros | `docs/mediciones/df_l7_hallazgos.csv`
- `N serie OLS mensual` | `40` (definición única frente a 33 / 43) | `docs/mediciones/df_l7_serie_n.csv`

Impacto en el documento (sección o tabla):
- Ningún cambio a invariantes ni cifras congeladas; `CONTRATO_FUENTES.md` ampliado con texto heterogéneo (`DF-L11`).

Riesgos abiertos:
- Ejecutar `node e2e/dataops_flujo.mjs` en un entorno con Playwright/Chromium instalado para validar visualmente 1440/768/375 px (claro/oscuro) y 0 errores de consola en vivo.
- Ejecutar `DF-L10` (`df_lote_1387_v2.json`) y completar la división de `IngestView.jsx`, `BetoMetricasModal.jsx` y `BetoReadingFlowView.jsx` si se exige estrictamente ≤ 300 líneas.

Pendiente para el chat 4:
- Capturas «después» a 1440 px de CMI, Académico, Financiero y Reportes tras este rebuild (per DD7) y capturas E2E de DataOps ①②③ + Auditoría con Playwright instalado.
