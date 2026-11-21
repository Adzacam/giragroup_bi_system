# CIERRE RV2 (L0–L7) — 2026-11-20
Rama base: `beto-integracion` (`38e317f`)
Hecho:
- L0: Oráculos guardados (`docs/mediciones/rv2_l0_scorecard.json`, `rv2_l0_macro.json`, `rv2_l0_inventario_limpieza.csv`, `rv2_l0_pruebas.txt`).
- L1: Retirado Power BI de front (`CmiPowerBi.jsx`, `powerbiApi.js`, modo D), back (`powerbi.py`, `main.py`, docstrings), archivos (`powerbi/`, `uploads/powerbi/`, `_archivo/powerbi/`) y rol (`020_retirar_rol_powerbi_reader.sql` idempotente, conservando `public.powerbi_informe_version` según D1-b).
- L2: Partido `CuadroMandoIntegral.jsx` (1.206 líneas) en `CmiPage.jsx`, `CmiHeader.jsx`, `CmiModeSwitch.jsx`, `useExportarCmi.js`, `chartTheme.js`, `scorecard/*` y `prediccion/*` (todos < 300 líneas).
- L3: Mapa estratégico horizontal (`MapaHorizontalV2.jsx`: Aprendizaje → Procesos → Clientes → Financiera, carrusel scroll-snap en < 640 px) + `VistaGeneralCmi.jsx` (matriz 23 KPI, comparativa interanual, alertas prioritarias, serie global, cobertura) + `GET /api/v1/cmi/resumen`.
- L4: `DesglosePerspectiva.jsx` (botón Volver, filtros en memoria, tarjetas V1 arriba, gráficas por perspectiva abajo, enlace profundo `?p=`) + `GET /api/v1/cmi/perspectivas/{codigo}/detalle`.
- L5: Documentado `docs/contexto_datos_prediccion.md`; `PrediccionPage.jsx` con franja ejecutiva de 4 cards, `CachedSubTabsV2` y drawer lateral (`DetallePrediccion.jsx`, Esc + restauración de foco) + etiqueta «OLS anual — solo descriptiva».
- L6: `useActualizarCmi.js` con `sileoToast.promise`, bloqueo de doble disparo, sello temporal y spinner respetando `prefers-reduced-motion`.
- L7: `docs/adr/ADR_rv2_kpi_graficos.md`, migración `021_esquema_app_personalizacion.sql` (esquema `app` sin PII), `cmi_personalizacion_service.py` (solo lectura, timeout 5 s → 504, máscara `< 5`), RBAC por perspectiva (`ADMIN`, `ANALISTA_FINANCIERO`, `ANALISTA_MARKETING`), `ConfigKppTab.jsx` y `ConfigGraficosTab.jsx`.
No hecho (para siguiente paso / subagente browser):
- L8 (limpieza física de `frontend/borrador web/`, `node_modules/` raíz, etc.) y L9 (capturas visuales en navegador con login 2FA).
Invariantes cambiados: no (`{"tablas_public_bi": 51, "vistas_bi": 10, "kpis_ref": 23}` en `docs/mediciones/rv2_l7_invariantes.json`).
Pruebas:
- Frontend `vitest`: 17 files, 91 passed.
- Frontend `vite build`: 2056 modules, built in 2.56s.
- Backend `pytest tests/sprint5/test_rv2_cmi.py tests/sprint1/test_migraciones_arranque.py`: 10 passed.
Servicios reconstruidos: `web` y `api` (`docker compose ps`: 9 servicios Up/healthy).
