# CIERRE ADW-L9 (COMPLETO) — 2026-11-21

**Rama:** `beto-integracion` · **Estado:** **ADW + FU CONGELADO**

## Qué se completó respecto al cierre parcial previo
- Integrada la migración final `028_fu_l9_decisiones_lean.sql` y registrada `022..028` en `backend/core/migraciones.py`:
  - `KPI-01` (A7): denominador único `pagantes` (2023–2026).
  - `bi.vw_riesgo_estudiante` (`52ecec0`): unión académico + financiero por gestión, con guarda `NULL` en `bi.vw_cmi_valores` (`riesgo_g`) cuando no hay registros académicos en la gestión (`2026` → `SIN_DATO`).
  - `backend/routers/riesgos.py`: endpoint `GET /api/v1/riesgos/resumen-vista` leyendo `bi.vw_riesgo_estudiante`.
  - `DA5`: los 9 KPI sin umbral se mantienen en `NULL` y `KPI-13` sin cambios.
- Remedición completa de los 23 KPI × 4 gestiones tras la recarga `FU-L9` en `docs/mediciones/adw_l9_remedicion_final.csv`.
- `docs/fuente_verdad_tesis.md` recongelado (`CONGELADO — 21 de noviembre de 2026`) y `docs/cierres/AVISO_CHAT3_ADW.md` actualizado a **ADW + FU CONGELADO**.
- Rebuild de `api`, `pipeline` y `web` (`9/9` servicios `Up`, `/health` `200`), `vitest` (`103/103 passed`), `npm run build` (`2.060` módulos, `0` errores) y `pytest` (`12/12` en `test_migraciones_arranque.py` + `tests/fu_l9/`; en suite completa `1279 passed`, `41 skipped`, `7 xfailed`, `6` de entorno host sin `torch`/`seqeval`/`statsmodels`).

Ver detalle consolidado en `docs/cierres/CIERRE_FINAL_FU_ADW_L9.md`.
