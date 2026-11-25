# F10-3a: Paso 2 y Modal de Métricas BETO

- `BetoReadingFlowView.jsx`: contenedor de acciones del header con `minHeight: 38`, `flexShrink: 0` y `minWidth: 112` en `Actualizar` para evitar layout shift.
- `RegistroBetoRow.jsx`: eliminada la duplicación de `rawText`; resumen compacto de chips en cabecera y línea original resaltada una sola vez dentro de `<details>`.
- `betoMetricas.json`, `BetoMetricasModal.jsx` y `BetoMetricasTablas.jsx`: añadida tabla **Estudio de ablación (Modo A vs. Modo B · lote 10 archivos, F9)** (`89,87 s` / `405` casos vs `119,82 s` / `141` casos, `100 %` acuerdo, fuente `f9_aporte_10archivos.json`) y perfil activo F9 (`10,93 min` < `15 min` RNF-03, `99,52 %` tasa de acuerdo de `f7_completo.json`).
