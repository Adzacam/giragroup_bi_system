# CIERRE FU-L9 (COMPLETO) — 2026-11-21

**Rama:** `beto-integracion` · **Estado:** **ADW + FU CONGELADO**

## Qué se ejecutó
- Commit acotado previo de `FU-L6` (`c724ef0`).
- Respaldo preventivo de `giragroup_db` en `backups/giragroup_db_pre_fu_adw_l9_20261121.dump` (`snapshot_dw_20261110_1201` intacto).
- Deuda `M5`: listas fijas de cabeceras y roles migradas a `config/mapeo_fuentes.yaml` + `pipeline/mapeo_fuentes.json` en `extraccion_por_encabezado.py`, `routers/pipeline.py` y `routers/dataops/extraccion.py`.
- Encuestas (`FU-L5`): respuestas sin fecha quedan con `id_tiempo = NULL` (`12.937` filas fuera de gestión, `0` con `TIEMPO_IMPUTADO`); NPS queda solo informativo (`23` KPI en `bi.ref_kpi`).
- Aplicadas migraciones `022..028` en `giragroup_db` (verificado `51` tablas + `10` vistas `bi` + `23` KPI) y ejecutada la recarga controlada completa de los 10 libros de `uploads/data/` (`scripts/auditoria_fuentes/fu_l9_recarga_completa.py`).
- Remedición y recongelado en `docs/mediciones/adw_l9_remedicion_final.csv` y `docs/fuente_verdad_tesis.md`.

Ver detalle consolidado en `docs/cierres/CIERRE_FINAL_FU_ADW_L9.md`.
