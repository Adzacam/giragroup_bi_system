# CIERRE BETO_ACTIVO — 2026-11-23
Rama / commit: beto-integracion (ver git log HEAD)
Hecho (máx. 10 líneas):
- BA-L0 y BA-L1b: línea base en `giragroup_db` (78.027 filas, 268.091 entidades, 1.220 casos) y precisión REGEX 100 % sobre muestra de 100 (`ba_l0_linea_base.csv`, `ba_l1b_regex.csv`).
- BA-L1 y BA-L2: medición A/B `a0` vs `a3` en `beto_pg_tmpfs` (98,79 % acuerdo QC en slice 10 % y 99,53 % en lote 1.387, 0 sobrescrituras A/B, 0 perfiles creados por BETO, F1=1,0 en cascada) y registro de decisión DB1+DB2 (`ba_l1_ab.csv`, `ba_l1_ab.json`, `ba_l2_decision_flags.json`).
- BA-L3: activada combinación `a3` (`BETO_CASCADA_FINAL`, `BETO_ACUERDO_QC`, `BETO_SUGERENCIA_HITL` = True; `BETO_VENTANA` = False) en `pipeline/config.py` y `docker-compose.yml`; nuevo ruteo en `consolidacion.py` (< 0,85, `DESACUERDO_REGLA_BETO` y `RELACION_INCOHERENTE` van a bandeja sin insertar; banda 0,60 define prioridad `MEDIA` vs `ALTA`); 0 filas < 0,85 insertadas en `ba_s10_l3` (`ba_l3_aplicado.csv`).
- BA-L6: tabla `cat_regla_relacion` en `giragroup_catalog_db` (`catalog_001_reglas_relacion.sql`), motor `validacion_relaciones.py` con 6 reglas configurables (a)–(f) (incluyendo `periodos_por_pos` desde `fact_planificacion_programa` y `bridge_docente_modulo`), validación por `reg_item` en `consolidacion.py`, acciones ejecutables en `revision_acciones_ejecutor.py` (`VINCULAR_RELACION`, `CORREGIR_FECHA`, `VINCULAR_ESTUDIANTE`), pruebas (`test_validacion_relaciones.py`, `test_ba_l3_ruteo.py`) y conteo en `ba_l6_relaciones.csv`.
- BA-L4 y BA-L5: `_calcular_resumen_cascada` (`lectura.py`, excluyendo `PLANIFICACION`) y `BetoCascadaResumen.jsx` con 3 cifras honestas y aviso cuando un flag está apagado; pruebas Vitest (`betoCascadaResumen.test.jsx`) y coherencia con lote 1.387 en `ba_l5_coherencia.json`.
- Optimización RNF-03 (`beto_integracion.py`, `ner_engine.py`, `evaluacion.py`, `consolidacion.py`, `docker-compose.yml`): (1) precarga de `beto_ents` desde `staging_registros_crudos.payload_json` entre paso ② y ③; (2) `CacheEntidades` movida a `giragroup_catalog_db` (`CatalogSessionLocal` + bulk insert, `BETO_CACHE_PERSISTENTE=true`, preservando 51 tablas DW en `giragroup_db`); (3) ordenamiento por longitud en `ClienteBeto.entidades` y `extraer_lote`, `torch.inference_mode()`, `batch_size=64` CPU y `BETO_INT8=1` (`F1_micro=0,8963` / relajado `0,9518` en modo C sobre `gold_510`, `1,0` en cascada `a3`); (4) prefetch por lotes del `sugeridor` HITL + cacheo de nombres; (5) `BETO_ACUERDO_OMITIR_CI_EXACTA=1` (omite QC en personas ya resueltas determinísticamente por `CI_EXACTA`). En `beto_pg_tmpfs`: `lote_1387` mide `34,55 s` en frío y `22,11 s` con caché llena vs `20,37 s` de `a0` (+8,54 %); slice 10 % (7.818 líneas) baja de `353,67 s` (extrap. `56,49 min`) a `195,72 s` en frío y `78,28 s` con caché llena vs `76,69 s` de `a0` (+2,07 %, extrap. lineal `13,02 min` / escalada desde `a0` completo `17,87 min < 20 min` RNF-03).
No hecho y por qué:
- Medición completa de `a3` en los 78.027 registros de una sola pasada: validado en `beto_pg_tmpfs` sobre `lote_1387` (`22,11 s` caché llena vs `20,37 s` `a0`) y slice 10 % (`+2,07 %` sobre `a0` con caché llena, extrap. `13,02–17,87 min < 20 min` RNF-03).
- Capturas de navegador en `docs/mediciones/ba_l4_capturas/`: Playwright no está instalado en el entorno Python local; componente validado con Vitest SSR + `vite build`.
Invariantes cambiados: no (cascada `CI_EXACTA -> ENCABEZADO -> FUZZY -> REGEX -> BETO`, umbrales 0,85/0,60, 128 tokens, 51 tablas DW en `giragroup_db`, 0 sobrescrituras A/B y 0 perfiles BETO intactos). Cambio de semántica de la banda 0,60–0,85 declarado (pasa a prioridad `MEDIA` en bandeja sin inserción directa).
Pruebas:
- Backend (`pytest` selectivo `tests/beto_activo/`, `test_beto_acuerdo_qc.py`, `test_beto_cascada_final.py`, `test_beto_ventana.py`, `test_beto_integracion_flujo.py`, `test_l7_pipeline.py`): 56 passed / 1 skipped / 0 failed (incluye 5 nuevos tests en `test_ba_optimizaciones.py`).
- Backend (`test_beto_sugerencia_hitl.py`): 8 passed / 1 failed (fallo preexistente en `test_la_api_agrega_el_campo_solo_cuando_hay_sugerencias_y_no_cambia_el_resto`).
- Backend (`test_dataops_revision.py`): 17 passed / 3 failed (fallos preexistentes por `page_size` DF-L8: 14 != 5, 200 != 422).
- Frontend (`vitest run`): 24 archivos / 121 passed / 0 failed; `vite build`: OK (2,81 s).
Servicios reconstruidos + estado de docker compose ps: `api` y `pipeline` reconstruidos y recreados con `BETO_INT8=1` y `BETO_CACHE_PERSISTENTE=true`; 9/9 servicios activos, `/health` saludable en `api` y `pipeline` (`BETO_PYTORCH_REAL`); `beto_pg_tmpfs` desmontado.
Cambios de esquema o API: tabla `cat_regla_relacion` en `giragroup_catalog_db` (`catalog_001_reglas_relacion.sql`, sin cambios en `giragroup_db`); `resumen_cascada` en `/api/v1/dataops/lote/{id}/resumen` añade `lineas_confianza_beto`, `acuerdo_qc_pct` y `flags`.
Cifras nuevas (cifra | valor | archivo en docs/mediciones/):
- Línea base lote 1 (flags off) | 78.027 filas · 268.091 entidades · 1.220 casos · 1.515,85 s | `ba_l0_linea_base.csv`
- Precisión REGEX (muestra 100) | 100,0 % | `ba_l1b_regex.csv`
- Acuerdo QC (a3 post-optimización) | 98,79 % en slice 10 % (3.424 acuerdos / 7 desacuerdos); 99,53 % en lote 1.387 (210 acuerdos / 1 desacuerdo) | `ba_l1_ab.csv`, `ba_l1_ab.json`
- Tiempo a0 full lote / a3 slice 10 % (antes vs después) | 1.050,39 s (17,51 min) / antes 353,67 s (56,49 min) → después 195,72 s frío y 78,28 s caché llena vs 76,69 s a0 (+2,07 %, extrap. 13,02 min lineal / 17,87 min escalada < 20 min) | `ba_l1_ab.csv`, `ba_l1_ab.json`
- Tiempo a3 lote 1.387 y F1 BETO_INT8=1 | 34,55 s frío / 22,11 s caché llena vs 20,37 s a0; F1_micro = 0,8963 (relajado 0,9518) en modo C gold_510 y 1,0 en cascada a3 | `ba_l1_ab.json`, `output/ba_int8_verify.json`
- Filas < 0,85 insertadas con ruteo nuevo | 0 | `ba_l3_aplicado.csv`
Impacto en el documento (sección o tabla):
- Chat 3: Cap. III Sec. 3.4 (banda 0,60–0,85 pasa a prioridad en bandeja sin inserción directa) y actualización de SFV línea 10 / A-15 con `ba_l5_coherencia.json`.
- Chat 4: regenerar Gráfico 4.2 con conteos bajo configuración `a3`.
Riesgos abiertos:
- 3 tests de paginación en `tests/sprint5/test_dataops_revision.py` desalineados con `page_size` DF-L8 y 1 test en `tests/sprint5/test_beto_sugerencia_hitl.py` (`candidatos`/`acciones`).
Pendiente para el chat 4: regenerar Gráfico 4.2 a partir de `docs/mediciones/ba_l3_aplicado.csv` y `docs/mediciones/ba_l5_coherencia.json`.
