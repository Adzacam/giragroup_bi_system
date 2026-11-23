# CIERRE BETO_ACTIVO — 2026-11-23
Rama / commit: beto-integracion ab74c1d
Hecho (máx. 10 líneas):
- BA-L0 y BA-L1b: línea base en `giragroup_db` (78.027 filas, 268.091 entidades, 1.220 casos) y precisión REGEX 100 % sobre muestra de 100 (`ba_l0_linea_base.csv`, `ba_l1b_regex.csv`).
- BA-L1 y BA-L2: medición A/B `a0` vs `a3` en `beto_pg_tmpfs` (99,62 % acuerdo QC, 0 sobrescrituras A/B, 0 perfiles creados por BETO, F1=1,0) y registro de decisión DB1+DB2 (`ba_l1_ab.csv`, `ba_l1_ab.json`, `ba_l2_decision_flags.json`).
- BA-L3: activada combinación `a3` (`BETO_CASCADA_FINAL`, `BETO_ACUERDO_QC`, `BETO_SUGERENCIA_HITL` = True; `BETO_VENTANA` = False) en `pipeline/config.py` y `docker-compose.yml`; nuevo ruteo en `consolidacion.py` (< 0,85, `DESACUERDO_REGLA_BETO` y `RELACION_INCOHERENTE` van a bandeja sin insertar; banda 0,60 define prioridad `MEDIA` vs `ALTA`); 0 filas < 0,85 insertadas en `ba_s10_l3` (`ba_l3_aplicado.csv`).
- BA-L6: tabla `cat_regla_relacion` en `giragroup_catalog_db` (`catalog_001_reglas_relacion.sql`), motor `validacion_relaciones.py` con 6 reglas configurables (a)–(f), acciones en `revision_acciones_descriptor.py`, pruebas unitarias (`test_validacion_relaciones.py`) y conteo en `ba_l6_relaciones.csv`.
- BA-L4 y BA-L5: `_calcular_resumen_cascada` (`lectura.py`) y `BetoCascadaResumen.jsx` con 3 cifras honestas y aviso cuando un flag está apagado; pruebas Vitest (`betoCascadaResumen.test.jsx`) y coherencia con lote 1.387 en `ba_l5_coherencia.json`.
No hecho y por qué:
- Medición completa de `a3` en los 78.027 registros con caché de entidades vacía y 3 repeticiones: en el slice estratificado del 10 % (8.143 líneas) `a3` tardó 366,64 s (extrapolado ~56,5 min > 20 min RNF-03) porque `BETO_ACUERDO_QC` usa `CacheMemoria()` vacía por corrida sobre ~59.650+ filas; se reporta a Lean.
Invariantes cambiados: no (cascada `CI_EXACTA -> ENCABEZADO -> FUZZY -> REGEX -> BETO`, umbrales 0,85/0,60, 128 tokens, 0 sobrescrituras A/B y 0 perfiles BETO intactos). Cambio de semántica de la banda 0,60–0,85 declarado (pasa a prioridad `MEDIA` en bandeja sin inserción directa).
Pruebas:
- Backend (`pytest` selectivo `test_ba_l3_ruteo.py`, `test_beto_integracion_flujo.py`, `test_validacion_relaciones.py`): 16 passed / 0 failed.
- Backend (`test_dataops_revision.py`): 17 passed / 3 failed (fallos preexistentes por `page_size` DF-L8: 14 != 5, 200 != 422).
- Frontend (`vitest run`): 24 archivos / 121 passed / 0 failed; `vite build`: OK (2,71 s).
Servicios reconstruidos + estado de docker compose ps: `api`, `pipeline` y `web` reconstruidos con `--no-deps` y en ejecución (`Up`); 9/9 servicios activos.
Cambios de esquema o API: tabla `cat_regla_relacion` en `giragroup_catalog_db` (`catalog_001_reglas_relacion.sql`, sin cambios en `giragroup_db`); `resumen_cascada` en `/api/v1/dataops/lote/{id}/resumen` añade `lineas_confianza_beto`, `acuerdo_qc_pct` y `flags`.
Cifras nuevas (cifra | valor | archivo en docs/mediciones/):
- Línea base lote 1 (flags off) | 78.027 filas · 268.091 entidades · 1.220 casos · 1.515,85 s | `ba_l0_linea_base.csv`
- Precisión REGEX (muestra 100) | 100,0 % | `ba_l1b_regex.csv`
- Acuerdo QC (a3, slice 10 %) | 99,62 % (5.965 acuerdos / 4 desacuerdos) | `ba_l1_ab.csv`, `ba_l3_aplicado.csv`
- Tiempo a0 full lote / a3 slice 10 % | 1.050,39 s (17,51 min) / 366,64 s (extrapolado 56,5 min) | `ba_l1_ab.csv`, `ba_l1_ab.json`
- Filas < 0,85 insertadas con ruteo nuevo | 0 | `ba_l3_aplicado.csv`
Impacto en el documento (sección o tabla):
- Chat 3: Cap. III Sec. 3.4 (banda 0,60–0,85 pasa a prioridad en bandeja sin inserción directa) y actualización de SFV línea 10 / A-15 con `ba_l5_coherencia.json`.
- Chat 4: regenerar Gráfico 4.2 con conteos bajo configuración `a3`.
Riesgos abiertos:
- **RNF-03 (> 20 min)**: con `BETO_ACUERDO_QC=True` y `CacheMemoria()` vacía por corrida, la consolidación completa de 78.027 filas extrapola a ~56,5 min; activar `CacheEntidades` persistente o limitar QC a muestreo requiere decisión de Lean.
- 3 tests de paginación en `tests/sprint5/test_dataops_revision.py` desalineados con `page_size` DF-L8.
Pendiente para el chat 4: regenerar Gráfico 4.2 a partir de `docs/mediciones/ba_l3_aplicado.csv` y `docs/mediciones/ba_l5_coherencia.json`.
