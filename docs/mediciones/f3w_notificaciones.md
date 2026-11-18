# W-7 — Notificaciones y botones (D-W8)

Fecha: 2026-11-17

## Cambios implementados

1. **Toast único por `tarea_id` (`frontend/src/services/sileoToast.js`, `notificationService.js`, `TareasSegundoPlano.jsx`)**:
   - `sileoToast.upsertTask(tareaId, ...)` y `notificationService.notifyTaskProgress(tarea)` actualizan/reemplazan el toast existente de la misma tarea en lugar de apilar múltiples toasts, mostrando porcentaje (`%`) y texto de etapa.
2. **Límite de 3 toasts visibles y agrupación (`+N más`)**:
   - `MAX_VISIBLE_TOASTS = 3`. Los avisos excedentes se agrupan en un único toast resumen `"+N más"`.
3. **Resumen de eliminaciones en bloque**:
   - `sileoToast.queueBulkDelete(...)`, `sileoToast.bulkDeleteSummary(count)` y `notificationService.notifyBulkBatchDelete(...)` consolidan eliminaciones múltiples en un solo toast (`"N lotes eliminados"`).
4. **Estado `"Procesando…"` + spinner en botones DataOps**:
   - `Button.jsx` usa `loadingText = 'Procesando…'` por defecto cuando `isLoading={true}` junto al ícono `.btn-spinner`.
   - `BatchHistory.jsx` y `HumanReviewFlowView.jsx` activan `isLoading` durante sus acciones asíncronas (V1 y V2, claro y oscuro).
   - `tokens.css` incluye `@media (prefers-reduced-motion: reduce)` para desactivar la animación de `.btn-spinner` y `.animate-spin`.

## Verificación Vitest

- Archivo: `frontend/src/modules/dataops/__tests__/w7NotificacionesBotones.test.jsx`
- Casos:
  1. 6 eventos de una misma `tarea_id` -> 1 toast activo actualizado con `%` y etapa (`PASS`).
  2. 5 eliminaciones en bloque -> 1 toast `"5 lotes eliminados"` (`PASS`).
  3. 7 toasts independientes -> máximo 3 visibles + 1 resumen `"+4 más"` (`PASS`).
  4. `Button` con `isLoading` renderiza `"Procesando…"`, `.btn-spinner`, `aria-busy="true"`, `disabled`, y `tokens.css` respeta `prefers-reduced-motion: reduce` (`PASS`).
