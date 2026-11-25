# F10-2b: Flujo en vivo Paso 2 → Paso 3

- `useLecturaBeto.js`: polling cada 2 s cuando `status === 'processing'` o `tarea.estado === 'EN_CURSO'`.
- `BetoReadingFlowView.jsx`: consulta de `CONSOLIDACION` en vivo con `ProgresoTarea`, botón `Consolidar / Insertar al DW`, banner con botón `Ir a Revisión` hacia `?vista=PENDIENTES` y soporte de `vista` por query string en `HumanReviewFlowView.jsx`.
