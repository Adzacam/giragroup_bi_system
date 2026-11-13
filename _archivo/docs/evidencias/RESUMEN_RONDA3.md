# Ronda 3 — rama `ablacion-beto-personas` (cifras de ejecuciones reales)

| # | Tarea | Estado | Resultado |
|---|-------|--------|-----------|
| 1 | Listado HITL | Hecho | 110,5 s -> 0,02–0,91 s por página (1,84 s la primera, en frío) |
| 2 | Texto libre fuera de personas | Hecho | lote: 99,57 % directo / 0,43 % HITL (6) / 0 % staging; dos corridas idénticas |
| 3 | Ciclo completo sin límite | Hecho (medido) | Evaluación Docente 194,6 s; ANTIGUO RESPUESTAS 958,1 s |
| 4 | OLS mensual vs anual | Hecho | mensual N=36: MAPE hold-out 11,51 %, R² 0,495 |
| 5 | cat_docente y tablas | Hecho | queda en el DDL sin uso; 55 tablas |
| 6 | pytest por suite y cobertura | Hecho | 442 passed, 11 skipped, 7 xfailed; cobertura global 60,6 % |
| 7 | 3 corridas del ciclo | Hecho | 156,7 s ± 0,8 (DE) |
| 8 | RoBERTa-BNE | No realizado | opcional; ver abajo |
| 9 | Pytest, tag, merge | Hecho | ver abajo |

## 1. Listado HITL (`bandeja_listado_tiempos.txt`)
Causa: `get_review_tray` armaba los casos de toda la cola (115.544 pendientes) y recortaba la página al final. Ahora: COUNT + OFFSET/LIMIT en SQL (staging y hechos en revisión), historial limitado a 200, dimensiones en memoria 60 s. 6 páginas sin filtro: 1,84 / 0,91 / 0,85 / 0,18 / 0,10 / 0,02 s; con `doc_id`: 0,2–0,4 s. No se guardaron entidades en la ingesta: el reconocimiento se hace solo para los 20 casos de la página. Cambio de contrato: `un_clic_total` cuenta solo la página.

## 2. Texto libre (`corrida_final_1.json` = `corrida_final_2.json`)
Encabezados comentario/sugerencia/observación/opinión (y mejorar/aspectos/explorar/libre) quedan fuera de la resolución de personas (87 entidades, 87 registros con comentario); una entidad PER sin forma de nombre y sin CI/fuzzy se descarta (494), no va a HITL; correos 139. El texto de comentarios en el DW lo guarda `registros_evaluacion` -> `fact_evaluacion_docente.comentario` (hoy 337 filas con comentario de 14.234); no hubo cambio ahí.
Lote 1.387: directo 1.381 (99,57 %), HITL 6 (0,43 %), staging 0. Personas 3.006 = 2.378 CI exacta (A) + 127 fuzzy (B) + 498 nuevas (C, docentes) + 3 HITL. HITL por motivo: empate 3 personas (estudiantes). KPI-10 0,9618 / 0,9209; KPI-11 99,57 %. Extracción A 99,50 % vs B 99,64 %.
Advertencia: el salto de 80,82 % a 99,57 % viene de descartar 494 entidades por forma (nombres en minúscula o de una palabra incluidos), no de resolverlas. La cifra depende de esa regla; cuenta de entidades descartadas en `texto_libre`.

## 3. Ciclo completo (`ciclo_completo_evaluacion_docente.json`, `ciclo_completo_antiguo_respuestas.json`)
| Archivo | Filas | Hechos | Total | lectura | BETO | carga | reglas |
|---|---|---|---|---|---|---|---|
| Evaluación Docente y Unifranz | 27.189 | 53.432 | 194,6 s | 9,0 s | 0,5 s | 169,1 s | 15,9 s |
| ANTIGUO RESPUESTAS | 19.119 | 206.729 | 958,1 s | 9,0 s | 137,7 s | 802,9 s | 8,3 s |
La estimación anterior de ≈1.250 s de BETO para ANTIGUO era errónea: se midieron 137,7 s. La carga es el costo dominante.

## 4. OLS (`ols_mensual_vs_anual.json`)
Serie `META_MENSUAL_PROGRAMAS` ejecutada, 2023-01 a 2025-12 (N=36). Los 12 meses de 2026 que devuelve el extractor son metas (suma 15.960.170,68), no recaudación; se excluyeron.
Mensual (train 30, hold-out 6): pendiente 13.580,51 Bs/mes, R² 0,4949, RMSE 134.809,62, MAPE 11,51 %. Serie completa: pendiente 13.911,94 Bs/mes (≈ +2.003.318,72 Bs/año en el total), R² 0,5861, RMSE de ajuste 121.438,48.
Anual (N=3): pendiente 2.267.633,83 Bs/año, R² 0,9937, RMSE de ajuste 147.831,51. Con N=3 el R² alto no valida el modelo.

## 5. cat_docente y tablas (`cat_docente_estado.txt`, `tablas_por_capa.json`)
`cat_docente` sigue en `db/schema.sql`, modelos y migraciones; 0 filas, `dim_docente.id_cat_docente` sin valores, ningún resolver la consulta. `giragroup_db` (public) tiene 55 tablas: hechos 9, dimensiones 8, catálogos 25, staging 3, auditoría 4, seguridad 2, control 4 (clasificación por nombre, mía).

## 6. Pytest y cobertura (`pytest_por_suite_y_cobertura.json`, `pytest_completo_sin_env.txt`)
Sin `DATABASE_URL` ni `PYTHONIOENCODING`: 442 passed, 0 failed, 11 skipped, 7 xfailed (460 pruebas).
| Suite | Pruebas | Pasadas | Omitidas | xfail | Fallidas |
|---|---|---|---|---|---|
| sprint1 | 16 | 16 | 0 | 0 | 0 |
| sprint2 | 32 | 32 | 0 | 0 | 0 |
| sprint3 | 120 | 120 | 0 | 0 | 0 |
| sprint4 | 23 | 23 | 0 | 0 | 0 |
| loops | 9 | 9 | 0 | 0 | 0 |
| readiness | 39 | 21 | 11 | 7 | 0 |
| transversales | 221 | 221 | 0 | 0 | 0 |
Cobertura de líneas (alcance `--cov=backend --cov=pipeline`): security 87,4 %; ingestion_service 61,3 %; fk_resolver 88,3 %; fuzzy_normalizer 83,1 %; person_resolver 92,9 %; alert_engine 91,5 %; financial_rules_engine 97,6 %; risk_service 94,4 %; forecasting_holtwinters 52,1 %; forecasting_ols 100 %; forecast_service 44,7 %; kpi_service 67,6 %; reportes 84,7 %; dataops 42,7 %. Global: 7.699 de 12.709 líneas = 60,6 %.
Skips: READINESS_TOKEN (2), READINESS_TOKEN+TOKEN_2 (1), READINESS_BETO_URL (3), READINESS_DB_URL (5).

## 7. Tiempo del ciclo mensual, 3 corridas (`tiempos_ciclo_mensual_corrida{1,2,3}.json`)
Total 155,9 / 157,4 / 156,9 s: media 156,7 s, DE 0,8 s. Por etapa (media ± DE): lectura 3,1 ± 0,1 s; reglas 30,6 ± 0,1 s; BETO 64,0 ± 0,4 s; carga 58,9 ± 1,1 s. 6.931 filas procesadas y 26.256 hechos en las tres corridas (10 archivos, con ANTIGUO y Evaluación Docente recortados a 300 filas en hojas sin fecha).
Resultado HITL del ciclo: +1.403 entidades en `stg_entidad_no_resuelta` por ciclo (113.253 vs 111.850), igual en las tres; hechos de rendimiento/financieros con revisión: +0. Los hechos en revisión de evaluación docente no se contaron en esta medición.
La corrida anterior del mismo ciclo dio 230,2 s; no investigué la diferencia (mismas máquinas y archivos; otro estado del clon y del equipo).

## 8. RoBERTa-BNE
No realizado (opcional): requiere descargar el modelo y ajustar en CPU con el corpus de BETO; no lo intenté, por tiempo, y no hay cifra.
