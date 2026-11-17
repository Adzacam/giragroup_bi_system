# CIERRE F3T — 2026-11-16
Rama: `beto-integracion` · Commit código T-1: `124c3f7` (`fix(f3t): D-T1 convenios resueltos por regla no van a revisión`).

**No se anuncia «F3 congelado»: eso lo hace el chat 1 tras revisar este cierre y decidir T-5.**

## 1. Resumen de tareas T-1..T-5
| Tarea | Estado | Resultado y evidencia |
|---|---|---|
| **T-1 (`D-T1`)** | **Completada** | `fila_resuelta_por_regla` (`backend/services/extraccion_por_encabezado.py:767-780`) exime del índice de persona a toda fila convertida en hecho por regla estructural (`rentabilidad`, `marketing`, `admision`). Prueba nueva: `tests/f3t/test_d_t1_convenios_en_marketing.py` (3 filas reales 11, 13 y 14 del documento 20). En tmpfs con `uploads/data/BD Techos.xlsx` completo: **`207`** filas, **`207`** `inserted_dw`, **`206`** `fact_techo_convenio` (1 par consolidado por `ON CONFLICT`), **`0`** staging `ESTUDIANTE`, **`0`** sin explicar (`docs/mediciones/f3t_d_t1.json`). |
| **T-2 (Clasificación `BD Techos.xlsx`)** | **Completada (solo diagnóstico)** | `detectar_tipo_fuente_por_cabeceras` (`ingestion_service.py:367-382`) asigna **`MARKETING` (`14`)** por `"asesor comercial"` frente a **`TECHOS` (`12`)** por `"techo"` / `"techos"`, tanto en el libro completo como en el recorte. Si `TECHOS` superara 14, cambiarían también `BD Egresos.xlsx` y `EJECUTADO VS META.xlsx` (`docs/mediciones/f3t_clasificacion_techos.json`). |
| **T-3 (Huella post D-T1)** | **Completada** | Corrida de `f3t_base` sobre los recortes (`docs/mediciones/f3t_base.json`, `docs/mediciones/f3t_huella_post_d_t1.json`): **48/48 tablas DW, hechos, dimensiones, staging, logs, bandeja (`676` casos / `17` grupos) y KPIs (`KPI-18 = 32`) son 100 % idénticos** a `f3s_base.json.huella.json` ($\Delta=0$). Única diferencia esperada: `cache_indice_beto` pasa de `11.139` a `11.138` filas (la fila de `BD Techos` ya no va a BETO) y `applied_at` de `schema_migrations`. No hace falta remedir `S-7`/`S-8`. |
| **T-4 (`KPI-15`)** | **Completada** | `bi.vw_cmi_valores` (`006_capa_semantica_cmi.sql:73,268-269`) define `KPI-15` como `100,0 * SUM(monto_deuda)` en `Mora`/`En Mora`/`Previsionable` sobre `SUM(monto_deuda)` por gestión (**`73,44 %`** en 2025 sobre `f3_base`). El **`69,93 %`** (`(500+7)/725`) es conteo de filas acumuladas del cuadre (`docs/mediciones/f3t_kpi15_formula.json`). Aclarado en `docs/fuente_verdad_tesis.md` (`Tabla F.2`). |
| **T-5 (DW viva, lote #3 doc 20)** | **Pendiente de confirmación (DECISIÓN 1)** | No se tocó la DW viva ni se ejecutó `pg_dump` sin el sí explícito de Lean. |

## 2. Rebuild, Gateway y Pruebas
- **Rebuild y Gateway:** `docker compose build api pipeline && docker compose up -d api pipeline && docker restart giragroup_gateway` ejecutado tras el commit `124c3f7`; `GET http://localhost/health` = `200` (`{"status":"healthy","service":"giragroup-bi-api","database":"connected"}`).
- **`pytest` en worktree limpio (`124c3f7`) contra `beto_pg_tmpfs` + `uploads/data/`:** **`829 passed, 0 failed, 11 skipped, 7 xfailed`** en `230,02 s` (`docs/mediciones/f3t_pruebas.txt`). Las pruebas de `D-A8a`, `D-T1` y orden de cascada pasaron en verde.
- **SFV (`verificar_sfv.py`):** **`168` entradas, `0` discrepancias, `0` cifras sin fuente, `0` menciones `v1`/`v2` (`0 / 0 / 0`)** (`docs/mediciones/f3t_sfv_verificacion.txt`).
- **Contenedor tmpfs:** `beto_pg_tmpfs` detenido limpiamente (`aislada_tmpfs.sh down`).

## 3. Decisiones pendientes para Lean
1. **T-5 (DW viva):** ¿se vuelve a procesar el documento 20 (`BD Techos.xlsx`) para convertir los 30 casos en convenios (recomendado, con `pg_dump` previo a `output/f3t/`), o se borra el lote #3 y se recarga completo?
2. **Clasificación de `BD Techos.xlsx` (T-2):** se recomienda mantener `MARKETING` con `D-T1` (cambiar el clasificador obligaría a remedir y afectaría a `BD Egresos.xlsx` y `EJECUTADO VS META.xlsx`).
3. **Pendientes heredados de `CIERRE_F3S.md`:** versionado o marcado de pruebas dependientes de `uploads/data`, `n=1` vs `3` en B-7, decisión 3 de F2R sobre `KPI-15`, y migración 016 en la DW viva / B-10 / merge a `main`.
