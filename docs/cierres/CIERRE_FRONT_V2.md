# CIERRE FRONT_V2 (Ronda 4) — 2026-11-16
Rama / commit: beto-integracion (pendiente de commit tras validación visual en navegador)
Hecho (máx. 10 líneas):
- Loop 1 (L1-R4): Creados `frontend/src/v2/motion/useCountUpV2.js` (`parseFormattedMetric`, `formatParsedMetric`, `useCountUpV2`, duración `900 ms`, curva `cubic-bezier(0.22, 1, 0.36, 1)`), `AnimatedNumberV2.jsx` (`tabular-nums`) y `AnimatedProgressBarV2.jsx` (`0% -> X%`), entregando el valor final exacto en `prefers-reduced-motion: reduce` y SSR.
- Loop 2 (L2-R4): Creado `frontend/src/v2/motion/chartAnimationsV2.js` (`progressiveLineClipPlugin`, `getSequentialAnimationConfig` con `dataIndex * 45ms` y crecimiento vertical), conectado en `CuadroMandoIntegral.jsx` (Casos 1, 3 y 4), `ProyeccionAlumnos.jsx` y `ProyeccionFinanciera.jsx`; animada la curva SVG (`pathLength="100"`, `stroke-dashoffset: 100 -> 0`) y los `<circle>` escalonados en `CmiDetalleKpi.jsx` + `cmi.css`.
- Loop 3 (L3-R4): Integrados `AnimatedNumberV2` y `AnimatedProgressBarV2` en **CMI** (`CmiScorecard.jsx`, `CardFolderV2.jsx`, `CmiDetalleKpi.jsx`), **Académica/Financiera** (`KpiCard.jsx`, `RendimientoAlertas.jsx`, `ProyeccionAlumnos.jsx`, `MetasGestion.jsx`, `ProyeccionFinanciera.jsx`) y **DataOps** (`BatchFlowHeader.jsx`, `BatchHistory.jsx`, `BetoReadingFlowView.jsx`, `HumanReviewFlowView.jsx`, `PipelineTelemetryDrawer.jsx`, `ProgresoTarea.jsx`).

No hecho y por qué:
- Validación visual interactiva en navegador (`/browser`) queda lista para ejecutarse por el coordinador sobre el contenedor `web` recién reconstruido.

Invariantes cambiados: no (cero alteración de cifras del backend; `db`, `catalog_db` y `api` intactas).
Pruebas:
- `cd frontend && npx vitest run`: 4 archivos / 27 passed / 0 failed / 0 skipped (`v2Architecture.test.js`, `v2Components.test.jsx`, `v2Ronda3.test.jsx`, `v2Ronda4.test.jsx`).
- `cd frontend && npm run build`: exitoso (0 errores).
Servicios reconstruidos + estado de docker compose ps: `web` reconstruido con `docker compose up -d --build --no-deps web`.
Cambios de esquema o API: ninguno.
Cifras nuevas (cifra | valor | archivo en docs/mediciones/): ninguna.
Impacto en el documento (sección o tabla): `docs/cierres/PLAN_FRONT_V2.md` y `docs/cierres/CIERRE_FRONT_V2.md`.
Riesgos abiertos: verificar visualmente en navegador `/v2/dashboard`, `/v2/academico/proyeccion`, `/v2/financiero/proyeccion` y `/v2/dataops/*` el conteo, trazado de gráficas y llenado de barras.
Pendiente para el coordinador: validación visual en `/browser http://localhost:5173/v2/dashboard`.
