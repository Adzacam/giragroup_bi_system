# CIERRE FRONT_V3_HEURISTICAS — 2026-11-24
Rama / commit: `main` (ver commit `FRONT_V3_HEURISTICAS`)
Hecho:
- FV3-1: Auditoría visual y técnica en vivo en modo claro (`data-theme="light"`) y oscuro (`data-theme="dark"`) sobre 16 rutas (`/v2/dashboard`, `/v2/dataops/*`, `/v2/academico/*`, `/v2/financiero/*`, `/v2/reportes`, `/v2/ajustes`, `/v2/admin/usuarios`) registrada en `docs/mediciones/fv3_auditoria_visual.md` y `docs/mediciones/fv3_metricas_lcp.json`.
- FV3-2: Añadido `<meta name="color-scheme" content="light dark" />` en `frontend/index.html`; `color-scheme: light` y foco visible global `:focus-visible` (`2px solid var(--color-gira-gold)`) en `frontend/src/v2/styles/v2-tokens.css`; corregido icono dorado-sobre-dorado de `Exportar CMI` en `CmiHeader.jsx`; adaptados `Cerrar Sesión` (tokens oscuros en lugar de `#fee2e2`), ancho/wrap del popover en `UserProfileDropdown.jsx` y contraste de `ALERTA CRÍTICA` en `RendimientoAlertas.jsx`.
- FV3-3: Añadido `role="dialog"`, `aria-modal="true"`, `aria-labelledby`, cierre con `Escape`, foco inicial/retorno y `whiteSpace: 'nowrap'` en `(Tu sesión)` en `GestionUsuarios.jsx`; `retry: 1` + botón accionable `Reintentar` en `MasterDataView.jsx`; enlace directo `Ir al historial de carga` en `HumanReviewFlowView.jsx`; `padding-bottom: 112px` en `@media (max-width: 960px)` en `v2-layout.css`.
- FV3-4: `npx vitest run` (`25` archivos, `129` pruebas passed, `0` failed), `npm run build` (`✓ built in 3.79s`) y rebuild de `giragroup_web` (`9` servicios Up).
- FV3-5: Re-verificación visual en `/browser` (modos claro y oscuro) confirmando los 5 grupos de ajustes con `0` errores de consola y sin regresiones.
No hecho y por qué:
- Lectura numérica de LCP/CLS/TTFB vía `PerformanceObserver` en página y `document.cookie`: el sandbox `webview_browser` bloquea `page.evaluate()` por aislamiento; se verificó ausencia de cookies HTTP en red (`localStorage` = `11.7 KB`) y estados de carga/error en vivo.
Invariantes cambiados: no (sin cambios de esquema, API, DW ni invariantes de tesis).
Pruebas: 25 files / 129 passed / 0 failed (`npx vitest run`, `docs/mediciones/fv3_pruebas_front.txt`) · `vite build` 2075 modules, built in 3.79s.
Servicios reconstruidos + estado de docker compose ps: `web` reconstruido (`giragroup_web` Up; 9 servicios Up/healthy).
Cambios de esquema o API: ninguno.
Cifras nuevas (cifra | valor | archivo en docs/mediciones/):
- `Pruebas frontend vitest` | `25 archivos / 129 passed / 0 failed` | `docs/mediciones/fv3_pruebas_front.txt`
- `Errores de consola en navegador (FV3-1 y FV3-5)` | `0` | `docs/mediciones/fv3_metricas_lcp_despues.json`
- `Rutas auditadas en claro y oscuro` | `16` | `docs/mediciones/fv3_auditoria_visual.md`
Impacto en el documento (sección o tabla): Ninguno en cifras congeladas de tesis; mejora evidencia visual de usabilidad (Heurísticas de Nielsen / WCAG AA) para capturas de interfaz en Cap. 3/4.
Riesgos abiertos:
- En `1280×800`, el avatar del popover `UserProfileDropdown` puede comprimirse levemente (`flex-shrink`) y la columna `Acciones` de `GestionUsuarios` requiere scroll horizontal; la barra inferior móvil (`MobileBottomNavV2`) permanece visible en ciertos breakpoints y puede solapar el pie de tarjeta en `/v2/academico/rendimiento`.
- Durante la auditoría local hubo respuestas `HTTP 502` intermitentes desde `/api/v1/*` hacia el proxy `5173`.
Pendiente para el chat 4:
- Tomar capturas finales en modo claro/oscuro con el backend poblado si se requieren nuevas figuras de interfaz.
