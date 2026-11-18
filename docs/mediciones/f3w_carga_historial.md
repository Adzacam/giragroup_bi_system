# Medición W-8 — Rediseño de la carga y del historial

- **Fecha**: 2026-11-17
- **Tarea**: W-8 (`docs/cierres/PLAN_F3W.md`)
- **Alcance**: `frontend/src/modules/dataops/IngestView.jsx`, `frontend/src/modules/dataops/components/BatchHistory.jsx`, `frontend/src/modules/dataops/utils/cargaHistorialHelpers.js`, `frontend/src/styles/dataops-flow.css` y `frontend/src/modules/dataops/__tests__/w8CargaHistorial.test.jsx`.
- **Restricciones verificadas**: Sin cambios en `backend/` ni en `HumanReviewFlowView.jsx`; preservados W-2 (selector de escala solo en `ACTA`/`MOODLE` y etiqueta detectada en `EVALUACION_DOCENTE`) y W-7 (botón `"Procesando…"` + spinner).

## Cambios realizados

1. **Cola de archivos en tabla con `"Seleccionar todo"` y acciones junto a la zona de carga (`IngestView.jsx`)**:
   - Los botones `"Procesar seleccionados (N)"` y `"Vaciar cola (N)"` se ubican junto al dropzone en el panel `"Cargar archivos"`.
   - La cola pasa a ser una tabla unificada (`"Cola de archivos"`) con casilla `"Seleccionar todo"` en cabecera, casillas por fila, selector de tipo documental (`TIPOS_FUENTE_DATAOPS`), selector de escala solo en `ACTA`/`MOODLE`, estado y acciones por fila (`Detalle` / `Ocultar` y `Quitar`).
   - La validación y el envío a `dataopsApi.uploadBatch` operan exclusivamente sobre los archivos seleccionados.
2. **Eliminación del panel `"Archivo seleccionado"` (`IngestView.jsx`)**:
   - Se removió el panel inferior `"Archivo seleccionado"`.
   - El detalle de cada archivo (tamaño, origen, registros, fechas, estado) quedó integrado en cada fila de la tabla con fila expandible inline (`Detalle`).
3. **Historial de lotes con selección y acciones en bloque por estado (`BatchHistory.jsx`)**:
   - Se añadieron casillas de selección por fila y `"Seleccionar todo"` en cabecera.
   - Las acciones en bloque (`"Reintentar seleccionados"` y `"Eliminar seleccionados"`) se habilitan **únicamente** cuando **todos** los lotes seleccionados tienen el estado permitido (`ERROR` con `puede_reintentar_lectura` o `puede_eliminar` respectivamente).
   - Ambas acciones requieren confirmación previa mediante `confirmar(...)` y usan únicamente los endpoints existentes (`DELETE /api/v1/dataops/lote/{id}/fallido` y `POST /api/v1/dataops/lote/{id}/reintentar-lectura`).
4. **Compatibilidad V1/V2, claro/oscuro y responsive 375 px (`dataops-flow.css`)**:
   - Se aprovechó la regla `@media (max-width: 960px)` para colapsar `.dataops-section-a` a `1fr`, `min-width: 0` en hijos de grid (`.dataops-section-a > *`), `white-space: normal` en `.dataops-row-detail` (para que el detalle expandido envuelva en móvil) y contenedores `overflowX: auto` con `maxWidth: 100%` en tablas para evitar scroll horizontal en 375 px.

## Verificación ejecutada

- **Pruebas W-8 (`cd frontend && npx vitest run src/modules/dataops/__tests__/w8CargaHistorial.test.jsx`)**: **8/8 pasaron** (selección individual y `"Seleccionar todo"` en cola, validación por selección y tipo documental incluyendo `ACTA`/`MOODLE`/`EVALUACION_DOCENTE` y límites de lote, permisos por estado en acciones en bloque del historial, renderizado SSR de `IngestView` sin `"Archivo seleccionado"` y `BatchHistory` con casillas, y reglas CSS responsive).
- **Suite completa (`cd frontend && npx vitest run`)**: **63 pasaron, 2 fallaron** (las 2 fallas corresponden exclusivamente a `src/v2/__tests__/v2Ronda5.test.jsx`, preexistentes antes de W-8; los archivos de DataOps `w2TipoDocumental`, `w4FormulariosPorMotivo`, `w7NotificacionesBotones` y `w8CargaHistorial` pasaron 100%).
- **Build de producción (`cd frontend && npm run build`)**: **exitoso** (`vite build` completado en 7.90 s, sin errores).
- **Verificación visual en navegador (V1/V2, claro/oscuro, 375 px)**: **pendiente** (no ejecutada en navegador real durante esta sesión; se verificó estáticamente mediante CSS responsive y tokens temáticos).
