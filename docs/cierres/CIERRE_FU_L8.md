# CIERRE FU-L8 — 2026-11-21
Rama / commit: beto-integracion (pendiente de commit acotado)

Hecho (máx. 10 líneas):
- Backend (`FU-M3a`): `POST /api/v1/dataops/preview-workbook` en `backend/routers/dataops/ingesta.py` (hojas usadas/ignoradas/ocultas + motivo + filas estimadas + mapeo editable `columna -> campo canónico`, 0 PII) y `resumen_cascada` (`CI_EXACTA`, `ENCABEZADO`, `FUZZY`, `REGEX`, `BETO`) en `/resumen` y `/beto-reading` de `backend/routers/dataops/lectura.py`.
- Frontend (`FU-M3b`): actualizados `IngestView.jsx` (vista previa por hoja y tabla editable de mapeo), `BetoReadingFlowView.jsx` (cascada con `ORIGEN_INFO` + `AnimatedProgressBarV2` + bloque `"Qué significa:"`), `HumanReviewFlowView.jsx`, `GruposBandeja.jsx` (`patrones`, `patron`, `"Por qué está aquí"`) y `motivosBandeja.js` (8 motivos nuevos + `MOTIVOS_INFORMATIVOS`).
- Tests (`FU-B3`): `tests/fu_l8/test_contratos_dataops_l8.py` (**2 passed**) y Vitest DataOps (`fuL8Dataops.test.jsx` + suite completa: **12 archivos / 56 tests passed**), guardia **0 hex sueltos** y **0 PII**; `vite build` verde.
- Evidencias en `docs/mediciones/fu_l8_contratos_dataops.json`, `fu_l8_componentes_dataops.json` y `fu_l8_vitest_dataops.txt`.

No hecho y por qué:
- Verificación interactiva con clic en navegador (Playwright/Chrome DevTools MCP no disponibles en este entorno); `http://localhost/` verificado por HTTP 200 tras reconstruir `api` y `web`.

Invariantes cambiados: no

Pruebas: `pytest tests/fu_l8 -v` (2 passed) · `npx vitest run src/modules/dataops/__tests__` (56 passed / 12 files) · `npm run build` (passed).

Servicios reconstruidos + estado de docker compose ps: `giragroup_api`, `giragroup_web`, `giragroup_catalog_db` reconstruidos y reiniciados; `giragroup_gateway` reiniciado.

Cambios de esquema o API: nuevo `POST /api/v1/dataops/preview-workbook`; campo `resumen_cascada` en `/resumen` y `/beto-reading`.

Cifras nuevas (cifra | valor | archivo en docs/mediciones/):
- Vitest DataOps | 12 archivos / 56 tests passed | `fu_l8_vitest_dataops.txt`
- Hex sueltos en archivos DataOps modificados | 0 | `fu_l8_componentes_dataops.json`

Impacto en el documento (sección o tabla): capturas/flujo DataOps 3 pasos (cuando se valide visualmente).

Riesgos abiertos: verificar visualmente en navegador autenticado `http://localhost/` los 3 pasos (claro/oscuro y móvil).

Pendiente para el chat 4: ninguno.
