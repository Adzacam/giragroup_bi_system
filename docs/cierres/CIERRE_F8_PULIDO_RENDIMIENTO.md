# CIERRE F8_PULIDO_RENDIMIENTO — 2026-11-24

- **Plan ejecutado:** `docs/cierres/PLAN_F8_PULIDO_RENDIMIENTO.md`
- **Rama / Commit:** `main` (`4312bb3`)
- **Snapshot protegido:** `snapshot_dw_20261110_1201` intacto (todas las mediciones se ejecutaron en clones aislados sobre `beto_pg_tmpfs`).

## Resumen por tarea

| ID | Estado | Evidencia en `docs/mediciones/` | Resultado medido |
|---|---|---|---|
| F8-0 | Completado | `f8_perfil_sql.json` | Perfilado `cProfile` (1500 filas c/u en `f8_prof`): `TBL_INSCRITOS` (`consolidacion_s=59.41 s`, de los cuales `47.87 s` fueron `confianza_service.indices_cascada` / `POST /indice` en caché fría y `3.65 s` `cursor.execute` en 6.349 llamadas) y `BD Cobranzas` (`consolidacion_s=55.32 s`, `47.50 s` `indices_cascada` y `1.29 s` `cursor.execute` en 1.960 llamadas). |
| F8-1a | Completado | `f8_sql_opt_diff.json` | Índice en memoria de `dim_estudiante` (`_est_meta`, `_est_por_ci`, `_est_por_ci_num`, `_est_por_codigo`) activo en consolidación por lotes Postgres (`diferir_eval=True`), evitando `SELECT` y `flush()` por fila cuando no hay cambios, y acumulación diferida de `fact_marketing` (`_mkt_pendientes` + `execute_values` en `finalizar_cargas()`). `0` diferencias en todas las tablas de hechos, dimensiones y `stg_entidad_no_resuelta`. |
| F8-1b | Completado (con brecha RNF-03 documentada) | `f8_completo.json`, `f8_aporte_10archivos.json`, `f8_invariantes.json`, `f8_auditoria_dw.json` | Carga histórica completa (10 libros, caché fría): `1459.49 s` (`24,32 min`) vs `1617.7 s` (`26,96 min`) en F7 (`-158.21 s`); `ARCA` bajó de `317.15 s` a `189.83 s` (`-127.32 s`). Invariantes intactos: `51` tablas DW (`49` `public` + `2` `bi`), `10` vistas `bi`, `23` KPIs en `bi.ref_kpi`; `1901` casos en bandeja (`0` diferencias). |
| F8-2 | Completado | `f8_front_layout_check.md` | Corregidos en `UserProfileDropdown.jsx` (`flexShrink: 0` en avatar `42×42`), `GestionUsuarios.jsx` (celda `Acciones` compacta sin salto de línea) y `v2-layout.css` (`@media (min-width: 769px) { .v2-mobile-bottom-wrap { display: none !important; } }`). Verificados visualmente en `http://localhost:5173` a `1280×800` en claro y oscuro (`0` errores JS; `0px` de desborde en `/v2/admin/usuarios`; V1 `/admin/usuarios` conserva `21px` de scroll interno en la tarjeta de tabla por el sidebar de `276px`). |
| F8-3 | Completado | `f8_pruebas.txt`, `f8_pruebas_front.txt` | Frontend: `25/25` archivos de prueba Vitest aprobados y `vite build` exitoso (`3.92 s` local / `6.58 s` en imagen `web`); `api` y `web` reconstruidos y en ejecución (`docker compose ps`). Backend: `115 passed, 1 skipped` (`test_l7_pipeline.py` requiere `ADW_DB_URL`), `2 failed` preexistentes en `tests/sprint5/test_beto_sugerencia_hitl.py` (`test_candidatos_por_similitud_enmascara_la_cedula`, `test_la_api_agrega_el_campo_solo_cuando_hay_sugerencias_y_no_cambia_el_resto`). |

## Brecha abierta para RNF-03 (`< 15 min` / aceptable `< 20 min`)
- En carga histórica fría (`cache_indice_beto` vacía), el perfilado `cProfile` (`f8_perfil_sql.json`) y las trazas de `giragroup_pipeline` confirman que `TBL_INSCRITOS` (`541.51 s`) y `BD Cobranzas` (`353.70 s`) invierten ~85 % de su tiempo en inferencia CPU del modelo BETO (`POST /indice`), no en consultas SQL.
- Para bajar la carga histórica completa fría por debajo de `15–20 min` sin alterar los umbrales invariantes se requiere decisión de arquitectura en Chat 1 (`gira-planificar`) sobre aceleración de `/indice` (GPU o recorte de envíos redundantes a `/indice` en fuentes estructuradas).
