# CIERRE ADW_L6 (PARTE B: ADW-B1..B4, ADW-M1..M2) — 2026-11-21
Rama / commit: `beto-integracion` (pendiente commit acotado PARTE B tras revisión visual)
Hecho:
- **ADW-B1:** Auditoría SQL de solo lectura de la serie predictiva (`N=43` en `fact_marketing` / `time_series_extractor.py`, `N=33` en `forecast_service.py` por `SERIE_ALUMNOS_INICIO=2023-09`, `N=40/41` en `fact_rentabilidad` con ejecutado) → `docs/mediciones/adw_l9_auditoria_n_predictiva.csv`.
- **ADW-B2:** Diagnóstico de entorno (`seqeval`/`statsmodels`/`torch`/`transformers` ausentes en Python local 3.14 → 4 fallas en `tests/sprint3/test_beto_entrenamiento_endurecimiento.py`; `statsmodels 0.15.0` presente en `giragroup_api`) y causa del HTTP 502 en `http://localhost/api/v1/*` (ventana de reinicio/rebuild de `giragroup_api` frente a `giragroup_gateway`) → `docs/mediciones/adw_diagnostico_entorno_api.json`.
- **ADW-M1 (`ADW-L6` no bloqueado por DA5):** Migración idempotente `backend/scripts/migrations/027_adw_l6_cmi_config.sql` (solo tmpfs): KPI-18 asignado a gestión del dato (sin `created_at`: `2022=4, 2023=18, 2024=26, 2025=818, 2026=769`) y `bi.vw_cmi_gestiones` filtrando gestiones residuales (`2023` oculta) → `docs/mediciones/adw_l6_cmi_config_antes_despues.csv`, `tests/adw/test_l6_cmi_config.py`.
- **ADW-B3:** Backup preventivo `backups/giragroup_db_pre_adw_l6_20261121.dump` (121,1 MB), doble aplicación idempotente `022..027` en tmpfs limpia (exit code 0), verificación `51 / 10 / 23`, inventario de 5 contenedores huérfanos → `docs/mediciones/adw_precheck_dw.json`.
- **ADW-M2 + ADW-B4:** Exposición de `n_respuestas` en `backend/routers/cmi.py` (KPI-19/20), sustitución de `conversion_fuente` por `captacion_mensual` + `captacion_cobertura` en `DesglosePerspectiva.jsx`, visualización de `n_respuestas` en `TarjetaKpi.jsx` y `CmiDetalleKpi.jsx`, 0 hex sueltos en `frontend/src/modules/admin/cmi/` y tests Vitest → `docs/mediciones/adw_perspectivas_front_revision.json`, `docs/mediciones/adw_cmi_vitest_resumen.txt`.
- **Rebuild:** `api` y `web` reconstruidos; `docker compose ps` 9/9 Up; `/api/v1/health`, `:8000/health` y `/` en 200.

No hecho y por qué:
- Metas/umbrales de los 9 KPI (DA5), definición KPI-13 vs KPI-03, KPI-01 (A7) y `bi.vw_riesgo_estudiante` (`52ecec0`): bloqueados por decisiones pendientes de Lean.
- Agregado de `027_adw_l6_cmi_config.sql` a `backend/core/migraciones.py`, aplicación sobre `giragroup_db` viva, recongelado `ADW-L9` y capturas finales `ADW-B5`: reservados al cierre coordinado `FU-L9`/`ADW-L9` (`dev-alta`).

Invariantes cambiados: no (51 tablas `public+bi`, 10 vistas `bi`, 23 KPI en `bi.ref_kpi` intactos).
Pruebas:
- `pytest tests/adw/`: 46 passed, 1 skipped (skip esperado en `test_l7_pipeline.py` sin `ADW_DB_URL`).
- `pytest tests/adw/test_l6_cmi_config.py`: 3 passed.
- `npx vitest run`: 19 archivos, 103/103 passed (incluye `adwCmiPerspectivas.test.jsx` con `TarjetaKpi`, `CmiDetalleKpi`, `DesglosePerspectiva` y guardia 0 hex sueltos).
- `npm run build` (Vite): built in 4.85s, 0 errores.

Servicios reconstruidos + estado de docker compose ps:
- Reconstruidos `api` y `web` (`docker compose up -d --build api web`); 9/9 servicios `Up`, `giragroup_db` y `giragroup_catalog_db` `(healthy)`, `gateway_health=200`, `api_health=200`, `web_root=200`.

Cambios de esquema o API:
- `027_adw_l6_cmi_config.sql` (solo tmpfs): `CREATE OR REPLACE VIEW bi.vw_cmi_valores` (CTE `backlog` por gestión del dato) y `CREATE OR REPLACE VIEW bi.vw_cmi_gestiones` (`HAVING count(*) >= 10 AND count(*) FILTER (WHERE umbral_verde IS NOT NULL) >= 5`).
- `GET /api/v1/cmi/scorecard` y `GET /api/v1/cmi/kpis/{codigo}/historial`: agregan campo opcional `n_respuestas` para `KPI-19` y `KPI-20`.

Cifras nuevas (cifra | valor | archivo en docs/mediciones/):
- Serie predictiva (`N` por fuente) | DW=43, API=33, Ejecutado=41/40 | `docs/mediciones/adw_l9_auditoria_n_predictiva.csv`
- KPI-18 por gestión del dato (tmpfs `fu_l6_pg_tmpfs`) | 2022=4, 2023=18, 2024=26, 2025=818, 2026=769 | `docs/mediciones/adw_l6_cmi_config_antes_despues.csv`
- `KPI-20 n_respuestas` (DW viva) | 2024=1.091, 2025=14.342, 2026=6.715 | Verificado en `/api/v1/cmi/kpis/KPI-20/historial`

Impacto en el documento (sección o tabla): sin cambios aún en `docs/fuente_verdad_tesis.md` (se recongela en `ADW-L9`).
Riesgos abiertos:
- 5 contenedores tmpfs previos siguen en Docker (`fu_l6_pg_tmpfs`, `fu_l5_pg_tmpfs`, `adw_pg_tmpfs`, `beto_pg_tmpfs`, `beto_pg_f3w`).
- `027` aún no está en `giragroup_db` viva ni en `migraciones.py` (espera `FU-L9`/`ADW-L9`).

Pendiente para el chat 4 / `dev-alta`:
- Verificación visual de `ADW-M2` en `http://localhost/`.
- Respuesta de Lean a DA5, KPI-01 (A7) y `52ecec0`, seguida de `FU-L9`/`ADW-L9` (`dev-alta`) + `ADW-B5`.
