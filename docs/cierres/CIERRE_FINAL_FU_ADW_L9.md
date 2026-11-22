# CIERRE FINAL CONSOLIDADO — FU-L9 + ADW-L9 + ADW-B5 (2026-11-21)

**Rama:** `beto-integracion` · **Estado:** **CONGELADO** (`ADW + FU congelado`)

---

## 1. Ordenamiento Git y Respaldo Preventivo
- **Commit `FU-L6` (`c724ef0`):** commit acotado de los 31 archivos de `FU-L6` (`026_fu_l6_metas_granularidad.sql`, `metas_canonica.py`, `metas_cobertura.py`, `fact_rentabilidad.py`, `kpi_service.py`, `forecast_service.py`, `tests/fu_l6/`, `scripts/auditoria_fuentes/fu_l6_*`, etc.), dejando intactos los archivos ajenos de figuras `F5C`/`.claude/*`.
- **Respaldo preventivo:** `backups/giragroup_db_pre_fu_adw_l9_20261121.dump` (230.554.142 bytes) generado con `pg_dump -Fc` antes de modificar `giragroup_db`. `snapshot_dw_20261110_1201` intacto (solo lectura).

## 2. Deuda del Principio Rector (`M5`)
- Migradas las listas fijas de cabeceras y roles hacia `config/mapeo_fuentes.yaml` (sección `extraccion`) + espejo `pipeline/mapeo_fuentes.json`:
  - `backend/services/extraccion_por_encabezado.py`
  - `backend/routers/pipeline.py`
  - `backend/routers/dataops/extraccion.py`

## 3. Decisiones Escritas de Lean + Migración Final (`028_fu_l9_decisiones_lean.sql`)
1. **KPI-01 (A7):** `bi.vw_cmi_valores` usa `pagantes` como denominador único para todos los años (2023–2026).
2. **Riesgo estudiantil (`52ecec0`):** `bi.vw_riesgo_estudiante` = unión académico + financiero por `(gestion, id_estudiante)` (`docs/propuestas/adw_riesgo_base_union.sql`), guarda `NULL` en `riesgo_g` de `bi.vw_cmi_valores` cuando no hay registros académicos (2026 → `SIN_DATO`), y nuevo endpoint `GET /api/v1/riesgos/resumen-vista` en `backend/routers/riesgos.py` leyendo la vista.
3. **Encuestas (`FU-L5`):** En `backend/services/dw_loader.py`, las respuestas sin fecha quedan con `id_tiempo = NULL` (fuera de gestión, sin asignar al último período del programa: `12.937` filas con `id_tiempo IS NULL`, `0` con `TIEMPO_IMPUTADO`); NPS queda solo informativo (mantiene el invariante de 23 KPI en `bi.ref_kpi`).
4. **DA5:** Los 9 KPI sin umbral se mantienen en `NULL` y `KPI-13` sin cambios hasta que Lean defina metas en UI.
5. **Registro en `backend/core/migraciones.py`:** registradas `022..028` en `MIGRACIONES_EN_ARRANQUE`.
6. **Invariantes DW verificados tras `022..028`:** **51 tablas** (49 `public` + 2 `bi`) + **10 vistas `bi`** + **23 KPI en `bi.ref_kpi`**.

## 4. Recarga Controlada `FU-L9` (10 libros de `uploads/data/`)
Ejecutada en `giragroup_db` mediante `scripts/auditoria_fuentes/fu_l9_recarga_completa.py` (lotes `37..46`, documentos `45..54`, todos HTTP 200):
- `fact_rendimiento_academico`: **25.208** filas
- `fact_situacion_financiera`: **27.217** filas (pagos por año: `8.071.737,03 Bs` / `12.422.501,39 Bs` / `4.841.944,46 Bs` en 2024/2025/2026 — coincidencia exacta con fuente; mora DA3: `362` / `808` / `641` estudiantes)
- `fact_evaluacion_docente`: **409.859** filas (`12.937` con `id_tiempo IS NULL`, `0` con `TIEMPO_IMPUTADO`)
- `fact_marketing`: **9.223** filas (sin duplicación ×2)
- `fact_rentabilidad`: **95** filas (DA4 y prioridad `RENTABILIDAD > EGRESOS`)
- `fact_techo_convenio`: **206** filas
- `fact_planificacion_programa`: **2.411** filas (incluye IBP 2026)

## 5. Infraestructura, Pruebas y Recongelado
- **Contenedores:** eliminados los 5 contenedores `tmpfs` huérfanos (`fu_l6_pg_tmpfs`, `fu_l5_pg_tmpfs`, `adw_pg_tmpfs`, `beto_pg_tmpfs`, `beto_pg_f3w`); reconstruidos `api`, `pipeline` y `web`; `9/9` servicios `Up`; `/health` = `200 {"status":"healthy","service":"giragroup-bi-api","database":"connected"}`.
- **Pruebas:**
  - `pytest` completo (host): `1279 passed, 41 skipped, 7 xfailed, 7 failed` (1 fallo de `test_migraciones_arranque.py` corregido para `022..028` → `12/12 passed` en `tests/sprint1/test_migraciones_arranque.py tests/fu_l9/`; los otros 6 fallos son de entorno en el host Windows sin `statsmodels`/`torch`/`seqeval`: `test_f2_b8_intervalos.py`, `test_production_readiness.py::TestHoltWinters::test_parametros_suavizado_estimados` y 4 de `tests/sprint3/test_beto_entrenamiento_endurecimiento.py`).
  - `vitest`: **19 archivos / 103 passed (103)** (`0` fallos).
  - `npm run build`: **2.060 módulos compilados en 3,50 s** (`0` errores).
- **Remedición y recongelado:** `docs/mediciones/adw_l9_remedicion_final.csv` (23 KPI × 4 gestiones), `docs/fuente_verdad_tesis.md` marcado **CONGELADO** (21-nov-2026) y `docs/cierres/AVISO_CHAT3_ADW.md` actualizado a **ADW + FU CONGELADO**.
