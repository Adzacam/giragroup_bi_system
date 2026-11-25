# CIERRE F9_RNF03_INDICE — 2026-11-25

- **Plan ejecutado:** `docs/cierres/PLAN_F9_RNF03_INDICE.md`
- **Rama base:** `main` (`281feb7`)
- **Snapshot protegido:** `snapshot_dw_20261110_1201` intacto (todas las mediciones se ejecutaron en clones aislados sobre `beto_pg_tmpfs`).

## Resumen por tarea

| ID | Estado | Evidencia en `docs/mediciones/` | Resultado medido |
|---|---|---|---|
| F9-0 | Completado | `f9_linea_base.json` | Rama `main` (`281feb7`), `beto_pg_tmpfs` operativo; línea base F8: `1459.49 s`, `1901` casos en bandeja (`TBL_INSCRITOS`: `541.51 s`, `BD Cobranzas`: `353.70 s`). |
| F9-1a | Completado | `f9_indice_recorte_diff.json`, `f9_fila_regla_test.txt` | Regla estricta en `fila_resuelta_por_regla` (`backend/services/extraccion_por_encabezado.py`) validando `_tiene_identidad_ci_valida(campos)` (`PATRON_CI_BOLIVIA`, sin `?` ni `TEMP-`, con nombre real) + programa/POS en `marketing`/`admision` o `registros_cobranza`/campo financiero numérico en `financiero`. Test `tests/sprint5/test_f9_fila_resuelta_regla.py`: **4 passed** (`0 failed`). `TBL_INSCRITOS` bajó de `541.51 s` a **`50.92 s`** (`fact_marketing = 9208`, `0` pérdida) y `BD Cobranzas` de `353.70 s` a **`30.82 s`** (`fact_situacion_financiera = 27190`, `0` pérdida). |
| F9-1b | Completado | `f9_sugerencia_test.txt` | Alineados los 2 asserts preexistentes de F6-3b en `tests/sprint5/test_beto_sugerencia_hitl.py` al corte `80.0` y al contrato aditivo que expone `candidatos` junto a `sugerencias_beto`: **9 passed** (`0 failed`). |
| F9-2 | Completado | `f9_completo.json`, `f9_aporte_10archivos.json`, `f9_pruebas.txt`, `f9_invariantes.json`, `f9_kpi10_check.json`, `f9_auditoria_dw.json` | Suite `pytest`: **121 passed, 1 skipped, 0 failed** (`test_l7_pipeline.py` omitido por requerir `ADW_DB_URL` en puerto `55433`). Carga histórica completa en caché fría (10 libros): **`655.91 s`** (`10,93 min`, **`-803.58 s`** vs F8; `rnf03_cumplido_15m: true`, **`0` diferencias** en los 16 conteos de tablas y `1901` casos en bandeja). Lote de 10 archivos Modo B: **`119.82 s`** (`< 2 min`) con `141` casos en bandeja. `KPI-10` en scorecard (gestión 2025): **`99.99`** (`VERDE`, `puntaje: 100.0`); `fact_situacion_financiera.nivel_confianza_ia`: `27190/27190` poblados (`0` `NULL`, promedio `0.9836`). Invariantes intactos: `51` tablas DW (`49` `public` + `2` `bi`), `10` vistas `bi`, `23` KPIs en `bi.ref_kpi`. |
| F9-3 | Completado | `CIERRE_F9_RNF03_INDICE.md` | `giragroup_api` reconstruido, `9/9` servicios Up/healthy (`docker compose ps`), `GET http://localhost:8000/health` → `200` (`{"status":"healthy","service":"giragroup-bi-api","database":"connected"}`). |

## Conclusión de fase
- **RNF-03 cumplido en carga histórica fría (`655.91 s` = `10,93 min` < `15 min` = `900 s`)** sin modificar umbrales (`0,92 / 90 % / 85 % / 80 % / 0,85 / 0,60`), cascada (`CI_EXACTA → ENCABEZADO → FUZZY → REGEX → BETO`), ventana (`128` tokens) ni esquema (`51 / 10 / 23`).
