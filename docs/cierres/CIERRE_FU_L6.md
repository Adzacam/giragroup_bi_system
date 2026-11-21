# CIERRE FU-L6 (Borrador) — 2026-11-21
Rama / commit: beto-integracion (en curso · FU-B1)

Hecho (máx. 10 líneas):
- `pytest tests/fu_l6 -v`: **45 passed** de 45 (granularidad anual/mensual, prioridad RENTABILIDAD > EGRESOS, orden inverso, migración 026 en PostgreSQL tmpfs).
- Ejecución de `fu_l6_comparar_fuente_vs_dw.py` contra `fu_l6_pg_tmpfs` (`127.0.0.1:55441`, `giragroup_db` y `dw_l6_inverso`) y lectura READ ONLY de la DW viva (`127.0.0.1:5434`):
  - `fact_rentabilidad`: **129/129** filas comparadas `IGUAL` (diferencia = 0,00; 31 con fuentes en conflicto explicadas por prioridad).
  - `CONFLICTO_FUENTES`: **10** conflictos esperados, **10** `RESUELTO_REGLA` en la DW, **0** pendientes, **7** múltiplos de 100.000 señalados para aviso financiero; `orden_inverso` idéntico (`distintos: 0`, `fact_rentabilidad_identica: true`).
- Generados los 3 CSV y resumen en `docs/mediciones/` sin PII: `fu_l6_metas_fuente_vs_dw.csv`, `fu_l6_conflictos_metas.csv`, `fu_l6_kpi_antes_despues.csv`, `fu_l6_resumen.json`.

No hecho y por qué:
- Recarga completa de `BD Egresos.xlsx` + `PLANIFICACION` en `fu_l6_pg_tmpfs` quedó en ejecución en background (`task-112`) por tiempo de lectura BETO en CPU; por ello `dim_meta` en `fu_l6_pg_tmpfs` reportó 58 filas pendientes (`diferentes: 58`).
- Migración 026 NO aplicada en la DW viva (espera `FU-L9`).

Invariantes cambiados: no

Pruebas: `tests/fu_l6`: 45 passed / 0 failed.

Servicios reconstruidos + estado de docker compose ps: `fu_l6_pg_tmpfs` arriba en `127.0.0.1:55441`.

Cambios de esquema o API: ninguno nuevo en `FU-B1`.

Cifras nuevas (cifra | valor | archivo en docs/mediciones/):
- `fact_rentabilidad` iguales fuente vs tmpfs | 129 / 129 | `fu_l6_resumen.json`, `fu_l6_metas_fuente_vs_dw.csv`
- `CONFLICTO_FUENTES` resueltos / pendientes | 10 / 0 (7 múltiplos de 100.000) | `fu_l6_conflictos_metas.csv`
- `KPI-02` 2024 (viva → tmpfs) | 6,25 % → sin dato ("La fuente solo trae meta anual") | `fu_l6_kpi_antes_despues.csv`
- `KPI-02` 2026 (viva → tmpfs) | 15,28 % → 100,99 % | `fu_l6_kpi_antes_despues.csv`
- `KPI-03` 2026 (viva → tmpfs) | 85,76 % → 109,07 % | `fu_l6_kpi_antes_despues.csv`
- `KPI-12` 2026 (viva → tmpfs) | -1,21 % → 20,61 % | `fu_l6_kpi_antes_despues.csv`

Impacto en el documento (sección o tabla): KPI-02, 03, 12, 13 y 14 por gestión (recongelado en `FU-L9`).

Riesgos abiertos:
- Completar la recarga de `PLANIFICACION` en `fu_l6_pg_tmpfs` para cerrar las 58 filas de `dim_meta` a diferencia 0.

Pendiente para el chat 4: ninguno hasta `FU-L9`.
