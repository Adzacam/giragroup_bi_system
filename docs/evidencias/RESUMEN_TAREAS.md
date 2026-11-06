# Resumen de tareas (ejecución real)

| # | Tarea | Estado |
|---|-------|--------|
| 1 | Personas sin cat_docente (`pipeline/normalization/person_resolver.py`) | Hecho. `cat_docente` queda en el DDL (FK de dim_docente). Test gira41 original falla con `AttributeError` (método `enlazar_docente` eliminado); no se modificó |
| 2 | DW poblado + 5 tests forecast sin skip | **Falló (5/5)**. DW: fact_rentabilidad=108 (META_MENSUAL_PROGRAMAS 48 meses, META_ANUAL 3 años), fact_marketing=0 (ALUMNOS_GLOBAL 0 meses). `test_extractor_series_reales` llama `extraer_serie_temporal` sin engine => serie vacía siempre. Los otros 4 devuelven método None / "sin_datos" |
| 3 | Skips SMTP | Hecho: sin skip, mock de smtplib; pasan |
| 4 | 50 entidades BETO (semilla 42) | Hecho: `muestra_50_entidades_beto_semilla42.json`; 1 de 50 persistida en DW |
| 5 | Criterio de muestreo | Hecho: no hay criterio documentado (ver JSON del lote) |
| 6 | Reejecución del lote (DW poblado: dim_estudiante=13486) | Hecho. Sin regla personas: 99,78 % directo / 0,22 % HITL / 0 % staging. Con regla: 573 (41,31 %) directo, 814 (58,69 %) HITL, 0 staging. Personas 3726: 2375 CI_EXACTA, 1 FUZZY, 1350 HITL. Fuentes: CI_EXACTA 1850, ENCABEZADO 3079, FUZZY 146, REGEX 3103, BETO 3248. KPI-10a=0,9618 (n=11426); KPI-10b (solo BETO)=0,9209 (n=3248) |
| 7 | TESTING en producción | Hecho: no definido en docker-compose ni .env |
| 8 | pytest completo (con DATABASE_URL) | 8 failed / 429 passed / 11 skipped / 7 xfailed |

## Carga del DW (13 archivos)
Vía `/api/v1/pipeline/process`. 5 archivos (BD Cobranzas, Experiencia Docente 2.0, TBL_INSCRITOS, Evaluación Docente y Unifranz, Base centralizada ARCA) superaron el timeout de 900 s del cliente pero el servidor los terminó (30–38 min cada uno). dim_docente=631, bridge_modulo_docente=0, fact_marketing=0, fact_rendimiento_academico=0.

## Los 8 fallos del pytest final
- gira41 (AttributeError, tarea 1) y los 5 de forecast/loop4 (tarea 2): causas arriba.
- `test_servicio_caido_no_inventa_indices` y `test_app_env_test_en_produccion_no_arranca`: fallan solo por el entorno de la corrida (DATABASE_URL definido / PYTHONIOENCODING=utf-8). Sin esas variables: 33 passed en ambos módulos.

## Skips (11)
READINESS_TOKEN no definido (2), READINESS_TOKEN+TOKEN_2 (1), READINESS_BETO_URL (3), READINESS_DB_URL (5).
## Xfails (7)
HW-IC, HW-GAP, OLS-CAGR, FK-CI-EXT, FK-HASH, FK-BANDA ×2 (hallazgos documentados en el reason de cada test).

## Qué capturar para la tesis
- `lote_1387_uploads_data_arquitectura_b.json`: `personas`, `distribucion_bandas_*`, `kpis`, `conteos_fuente_resolucion`, `muestreo_por_archivo`.
- `lote_1387_uploads_data_arquitectura_b_dw_casi_vacio.json` / `_previo_tarea1.json`: corridas anteriores, para comparar.
- `muestra_50_entidades_beto_semilla42.json`: lista completa.
- `pytest_completo_final.txt`: "short test summary info".
