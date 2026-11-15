# Cierre de Fase F1 — Consolidación e Integración BETO (Cierre parcial por decisiones pendientes)

**Fecha:** 2026-11-14  
**Rama:** `beto-integracion` (base F0: `2aa5398d917ef503a26bb300cf514ed2ffd1db62`)  
**Estado:** Parcial — completadas todas las tareas independientes de las decisiones pendientes de Lean (`F1-P`, `A-9`, `A-7`, `F0-R0`, `A-8a`, `A-8b`, `A-8c`, `pytest`, reconstrucción de `api` y desmonte de `tmpfs`). Quedan bloqueadas por decisión explícita de Lean: **D1/A-5**, **D2/A-9**, **D3**, **F0-R3/R4** y **F1-V**.

---

## 1. Resumen de entregables completados

### F1-P — Preflight, `tmpfs` e invariancia del snapshot
- `scripts/aislada_tmpfs.sh`: parametrizado con `TMPFS_PORT="${TMPFS_PORT:-55432}"` (en esta sesión se usó `55632` por rango excluido de Hyper-V en Windows).
- Lote F0 verificado antes de operar: `sha256: aafde8adc246af13c4eeb9ffbf766eda4348cfb6e855860d0bf00bcd24cbdb60` (`20` archivos, `valido: true`).
- `docs/mediciones/f1_preflight.json`: `snapshot_igual_copia: true`.
- `docs/mediciones/f1_snapshot_despues.json` vs `docs/mediciones/f1_snapshot_antes.json`: **0 diferencias en las 59 relaciones**.

### A-9 — Inventario físico de esquemas
- `docs/mediciones/f1_inventario_objetos.csv`:
  - `giragroup_db`: `48` `public.BASE TABLE` + `2` `bi.BASE TABLE` = `50` tablas físicas + `9` `bi.VIEW`.
  - `dw_vacio` (con migración `015`): `49` `public.BASE TABLE` + `2` `bi.BASE TABLE` = `51` tablas físicas + `9` `bi.VIEW` (tabla adicional: `public.cache_beto_entidades`).
  - `catalogo_copia`: `20` `public.BASE TABLE`.

### A-7 — Purga explícita de `cache_beto_entidades`
- Implementado [purgar_cache_beto.py](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/scripts/purgar_cache_beto.py) y [test_purga_cache.py](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/tests/f1/test_purga_cache.py) (`2 passed in 5.88s`).
- Evidencia en `docs/mediciones/f1_purga_cache.json` sobre base aislada `f1_a7_evidencia`: `2` filas purgadas -> `0` filas, segunda ejecución idempotente, tablas ajenas intactas.

### F0-R0 — Comparación de referencia `73ec78f` vs `a0` (flags `False`)
- Ejecutadas `f1_base` (`/tmp/f0_ref_73ec78f`: `794.23 s`, `12.992` líneas) y `f1_off` (`/tmp/medida`: `948.05 s`, `12.992` líneas) contra el lote congelado de F0.
- Resultado en [f1_comparacion_base.txt](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/mediciones/f1_comparacion_base.txt):
  `IDÉNTICAS: 14 tablas, bandeja 182 casos / 12 grupos, KPI {'KPI-10': None, 'KPI-11': None, 'KPI-18': 59.0}`.

### A-8a — Integración de `beto-entrenamiento@9888539`
- Integrados `17` archivos no conflictivos desde `9888539` (sin sobrescribir `pipeline/semantic/beto_local` ni `data/*.jsonl`, y conservando `$(TEST_DATABASE_URL)` de B-10 en [Makefile](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/Makefile)).
- `scripts/evaluar_beto_checkpoint.py`: corregida la serialización JSON de escalares NumPy (`int64`) en `metricas.json`.
- Verificación: `tests/sprint3/test_beto_entrenamiento_endurecimiento.py` (`15 passed in 48.90s`). Detalle en [f1_a8_integracion.md](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/mediciones/f1_a8_integracion.md).

### A-8b y A-8c — Auditoría de corpus, entrenamiento reproducible y comparación de checkpoints
- [f1_corpus_auditoria.json](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/mediciones/f1_corpus_auditoria.json):
  - `determinismo_sha256_identico: true` en dos corridas independientes (`train_robusto.jsonl`: `d02ae16807831aab92b4d7cef34962c0d2a42f5221c646162e46efd5f155c5b7`, `dev_robusto.jsonl`: `9f3e7371ae654404591d6892c8d4d01b806f37f5344640d8ea8c52a774c7de9e`, `test_gold_real.jsonl`: `ebbbe6f262a28ac9a17dd9abbb195fd8a7db1f8429720d6f791d8adad3dd8f60`).
  - `personas_solapadas`: `0` en `train_dev`, `train_test` y `dev_test` (`personas_unicas`: `1967 / 485 / 83`).
- Entrenamiento reproducible ejecutado en `output/f1/reproduccion_1` (`4537.6 s`, mejor época `2` con Dev F1 `99.79%`); corpus verificado idéntico al auditado. Metadatos y manifiesto en [f1_training_info.json](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/mediciones/f1_training_info.json) y [f1_modelo_manifest.json](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/mediciones/f1_modelo_manifest.json) (sin pesos en Git).
- Comparación [f1_modelo_comparacion.json](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/mediciones/f1_modelo_comparacion.json) (`pipeline/semantic/beto_local` vigente vs `output/f1/reproduccion_1/modelo` candidato, sin promover el candidato):
  - `gold_510`: estricto micro F1 `0.977561` -> `0.980507` (`+0.002946`), relajado F1 `0.989289` -> `0.993184` (`+0.003895`, TP `508` -> `510/510`).
  - `layouts_5`: estricto micro F1 `0.246154` -> `0.279412` (`+0.033258`), relajado F1 `0.766234` -> `0.840764` (`+0.074531`, TP `59` -> `66/72`).
  - `test.conll`: estricto micro F1 `0.714715` -> `0.766816` (`+0.052101`), relajado F1 `0.880052` -> `0.914323` (`+0.034271`, TP `675` -> `699/750`).

---

## 2. Verificación de pruebas y servicios

- **Suite completa (`pytest`):** [f1_pruebas.txt](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/mediciones/f1_pruebas.txt) -> `801 passed, 11 skipped, 7 xfailed` en `365.90 s`, cobertura total `70%` sobre `beto_pg_tmpfs` (`127.0.0.1:55632/giragroup_db` y `catalogo_copia`).
- **Servicios Docker:** Reconstruido `api` tras el cambio en `backend/routers/dataops/maestros.py`. En [f1_servicios.txt](file:///c:/Users/DAZA/Documents/Universidad/Proyecto%20de%20Grado%207MO%20semestre/giragroup_bi_system/docs/mediciones/f1_servicios.txt): los `9` servicios activos en `docker compose ps` y `GET /health` -> `{"status":"healthy","service":"giragroup-bi-api","database":"connected"}`.
- **Limpieza:** `beto_pg_tmpfs` desmontado (`scripts/aislada_tmpfs.sh down`), flags `BETO_*` intactos en `False`, `pipeline/semantic/beto_local` sin sobrescribir.

---

## 3. Decisiones pendientes para completar F1 / F1-V (bloqueadas por Lean)

1. **D1 / A-5 (Flags BETO):** Confirmar qué combinación de los 4 flags (`BETO_ACTIVO`, `BETO_UMBRALES_CALIBRADOS`, `BETO_CACHE_ENTIDADES`, `BETO_INT8`) se adopta según la matriz F0 (`a0`..`a6`).
2. **D2 / A-9 (Alcance 50 tablas / métricas):** Definir si se alinea `50` vs `51` tablas (por `public.cache_beto_entidades` de la migración `015`) y el tratamiento de `KPI-10`/`KPI-11`/`KPI-18`.
3. **D3 (Adopción de checkpoint):** Autorizar explícitamente la promoción de `output/f1/reproduccion_1/modelo` sobre `pipeline/semantic/beto_local` (los artefactos locales permanecen en `output/f1/reproduccion_1/`).
4. **F0-R3 / F0-R4:** Completar las revisiones humanas ciegas (`A-3` sobre 90 contextos y `A-4` sobre los 7 casos faltantes) y **B-10** (rotación de credenciales / reescritura de historial Git si aplica).
5. **F1-V:** Ejecutar las 6 corridas finales de validación una vez resueltas D1, D2 y D3.
