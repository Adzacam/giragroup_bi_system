# Ronda 4 — rama `main` (cifras de ejecuciones reales)

| # | Tarea | Estado | Resultado |
|---|-------|--------|-----------|
| 1 | Idempotencia del staging | Hecho | cola 111.850 -> 23.121 pendientes; 2.ª pasada del ciclo agrega 0 |
| 2 | HITL real por ciclo | Hecho | n = 1.165 casos nuevos en la bandeja por ciclo mensual |
| 3 | Descartes PER_SIN_FORMA_NOMBRE | Hecho | 494 en `log_inconsistencias`; 122 hechos sin persona van a HITL; lote: 90,77 % directo / 9,23 % HITL / 0 % staging |
| 4 | Tablas | Hecho | 55 -> 48 (se eliminan 7) |
| 5 | OLS y Holt-Winters desde el DW | Hecho | ver abajo; Tabla 3.24 no se pudo contrastar |
| 6 | pytest, tag, merge, push | ver final de este archivo | |

## 1. Idempotencia del staging (`migracion_staging_idempotente.json`, `ciclo_idempotencia_hitl.json`)
Clave `clave_origen` = md5(hash SHA-256 del archivo | tipo | motivo | valor normalizado) con índice único `uq_stg_entidad_clave_origen`. Un listener `before_flush` (`backend/models/staging_entidad.py`) descarta lo ya encolado. Cada subida crea un `dim_origen_documental` nuevo, por eso la clave usa el hash del archivo y no `id_documento`; sin fila de origen en los puntos de inserción, el mismo valor repetido en un archivo queda como una sola entidad.
Migración (`scripts/migrar_staging_idempotente.py`, sobre el DW real): 111.854 filas -> 23.125; pendientes 111.850 -> 23.121 (CI_NOMBRE_DISCORDANTE 104.266 -> 20.707; BAJA_CONFIANZA_IA 6.758 -> 1.844; HOMONIMIA 826 -> 570).
Ciclo mensual (2026-03, mismos archivos, clon del DW): pasada 1 = +1.165 en staging (159,0 s); pasada 2 = +0 en staging, hechos, evaluación docente y estudiantes (97,6 s).

## 2. HITL real por ciclo (n)
Casos que muestra la bandeja (`GET /dataops/review-tray`, `total_items`) antes y después de la pasada 1: 26.815 -> 27.980 = **+1.165**.
- Personas con empate (HOMONIMIA): 597
- Hechos en revisión (académicos + financieros): 0 (stock previo 3.678 + 16, sin cambio)
- Staging nuevo único: 568 (BAJA_CONFIANZA_IA 300 + CI_NOMBRE_DISCORDANTE 268)
- Evaluación docente: la tabla no tiene marca de revisión, no aparece en la bandeja; la pasada 1 agregó 9.208 filas, todas con `id_docente` NULL. En el DW real, 14.234 de 14.234 filas de `fact_evaluacion_docente` tienen `id_docente` NULL y 1.970 `id_tiempo` NULL.
Antes de la deduplicación el mismo ciclo agregaba 1.403 entidades.
T = 2,61 min + 1.165 × (tiempo humano por caso).

## 3. Descartes (`corrida_final_1.json` = `corrida_final_2.json`)
494 entidades PER sin CI ni coincidencia y sin forma de nombre propio, en 261 registros, quedan en `log_inconsistencias` (tipo_regla PER_SIN_FORMA_NOMBRE, estado DESCARTADO, con id_documento y fila de origen; 494 filas tras cada una de las dos corridas). 122 registros quedaron sin ninguna persona: pasan a HITL (antes se cargaban directo). Los 20 ejemplos de cada lista están en el JSON.
Lote 1.387, dos corridas idénticas: directo 1.259 (90,77 %), HITL 128 (9,23 %), staging 0. De los 128 HITL, 125 eran directos y se movieron por persona sin resolver (122 por quedar sin persona + 3 por empate); los otros 3 ya estaban en la banda de revisión por su índice.
Aviso: la mayoría de las 494 son nombres de pila o apellidos sueltos en MAYÚSCULAS de actas ARCA (p. ej. CACERES, VARGAS, CARLOS) o etiquetas de respuesta ('5/Totalmente de acuerdo'): la regla de forma descarta también personas reales partidas en columnas. El 99,57 % de la ronda 3 no incluía esta regla de "única persona".

## 4. Tablas (`inventario_tablas.json`, `inventario_tablas_antes_011.json`)
Bloque idempotente de arranque en `backend/main.py` (`DROP TABLE IF EXISTS`; no es un archivo de migración numerado porque `tests/test_migraciones_arranque.py` fija la lista exacta 003-010): se eliminan 7 tablas con 0 filas y sin consulta en el código: cat_alias, cat_alias_docente, cat_alias_financiero, cat_alias_modulo, cat_alias_programa, cat_docente, cat_tipo_cartera; también `dim_docente.id_cat_docente`. Se quitaron sus clases ORM (el `create_all` las recrearía).
Quedan 17 tablas con 0 filas que se conservan por tener consultas en el código (cat_* leídas de `giragroup_catalog_db`, dim_meta en kpi_service, ref_metas_gestion) o prueba que las fija (fact_cobranzas_proyectadas en `TABLAS_TRUNCAR`).
`db/schema.sql` no se modificó: `tests/test_esquema_alineado_ddl.py` exige `cat_docente` y `id_cat_docente` en el DDL; en una instalación nueva el arranque las elimina.
Conteo final 48: hechos 9, dimensiones 8, catálogos 18, staging 3, auditoría 4, seguridad 2, control 4.
- Hechos: fact_cobranzas_proyectadas, fact_costo_programa, fact_evaluacion_docente, fact_forecast, fact_marketing, fact_rendimiento_academico, fact_rentabilidad, fact_situacion_financiera, fact_techo_convenio
- Dimensiones: bridge_modulo_docente, dim_categoria_financiera, dim_docente, dim_estudiante, dim_meta, dim_modulo, dim_origen_documental, dim_tiempo
- Catálogos: cat_categoria_financiera, cat_combinacion_estado, cat_concepto_financiero, cat_escuela, cat_estado_academico, cat_estado_arca, cat_estado_reprobado, cat_etiqueta_clasificacion, cat_guia_texto_plano, cat_historico_equivalencia, cat_institucion, cat_institucion_convenio, cat_mapeo_columna, cat_modalidad, cat_modulo, cat_programa, cat_tipo_programa, ref_metas_gestion

## 5. OLS y Holt-Winters (`ols_hw_proyecciones.json`)
(a) Recaudación anual PROGRAMAS (suma de `monto_ejecutado`): 2023 8.035.694,25; 2024 9.989.730,09; 2025 12.570.961,91 Bs. Tesis 8,03 / 9,98 / 12,90 M. 2023 y 2024 coinciden con `recaudacion.csv` (la tesis trunca a dos decimales en millones). 2025: el DW está 337.015,70 Bs por debajo del csv (12.907.977,61) por marzo de 2025: `EJECUTADO VS META.xlsx` trae 997.224,70 y `BD Egresos.xlsx` (doc 8) lo reemplazó por 660.209,00; queda registrado como CONFLICTO_FUENTES pendiente en `log_inconsistencias`. 12.570.961,91 + 337.015,70 = 12.907.977,61.
(b) OLS mensual N=36 (2023-01..2025-12) con la serie del DW: pendiente 13.911,94 Bs/mes, R² 0,5861, RMSE de ajuste 121.438,48. Proyección con IC 95 % de predicción (t, 34 gl): 2026-01 1.107.270 [839.013; 1.375.528]; 02 1.121.182 [851.752; 1.390.613]; 03 1.135.094 [864.435; 1.405.754]; 04 1.149.006 [877.062; 1.420.951]; 05 1.162.918 [889.634; 1.436.202]; 06 1.176.830 [902.152; 1.451.508].
Con marzo de 2025 = 997.224,70 (sensibilidad): pendiente 14.649,29, R² 0,6589, 2026-01 1.130.273 y 2026-06 1.203.520.
Corrección a la ronda 3: el DW tiene `monto_ejecutado` real para 2026-01..2026-05 (1.307.697,23; 984.911,79; 1.353.826,01; 1.410.779,33; 252.233,32 parcial), no todo metas. Contra enero–abril de 2026 el OLS tiene MAPE 16,0 % (15,33; 13,84; 16,16; 18,56 %); el hold-out de la ronda 3 (11,51 %) no incluía 2026.
(c) Holt-Winters aditivo desde `fact_marketing` (N=33, 2023-09..2026-05): alfa 0,6358, beta 0,0, gamma 0,1918; RMSE de ajuste 65,85; AIC 308,37; hold-out 6: RMSE 53,38, MAPE 10,27 %. Proyección h=6 (IC ±1,96·RMSE): 2026-06 448,0; 07 468,4; 08 602,2; 09 561,9; 10 534,5; 11 514,3. La Tabla 3.24 no está en forma de texto en el .docx (no aparece "3.24" en el XML), no pude contrastarla; el AIC y MAPE coinciden con la ronda 2 (308,37 y 10,27 %).

## 6. pytest (`pytest_completo_sin_env.txt`)
Sin `DATABASE_URL` ni `PYTHONIOENCODING`: 444 passed, 0 failed, 11 skipped, 7 xfailed (462 pruebas; +2 de `tests/test_staging_idempotente.py`). Dos defectos propios hallados por la suite y corregidos: el listener usaba `ANY(...)` de PostgreSQL (fallaba en SQLite) y la migración numerada 011 rompía la lista exacta de `test_migraciones_arranque` (sin tocar la aserción, el DROP pasó al bloque idempotente de arranque).

## 7. Tabla única de cifras
| Cifra | Valor | Evidencia |
|---|---|---|
| Staging pendiente antes -> después de deduplicar | 111.850 -> 23.121 | migracion_staging_idempotente.json |
| Entidades nuevas en staging, pasada 1 / pasada 2 | +1.165 / +0 | ciclo_idempotencia_hitl.json |
| n (casos nuevos en bandeja por ciclo) | 1.165 = 597 empate + 568 staging + 0 hechos | ciclo_idempotencia_hitl.json |
| Duración del ciclo mensual (pasada 1 / 2) | 159,0 s / 97,6 s | ciclo_idempotencia_hitl.json |
| PER_SIN_FORMA_NOMBRE en log_inconsistencias | 494 (261 registros; 122 sin persona -> HITL) | corrida_final_1/2.json |
| Lote 1.387 directo / HITL / staging | 90,77 % / 9,23 % / 0 % (x2 idéntico) | corrida_final_1/2.json |
| Extracción A / B | 99,50 % / 99,64 % | corrida_final_1.json |
| Tablas | 55 -> 48 (hechos 9, dim 8, cat 18, stg 3, aud 4, seg 2, ctl 4) | inventario_tablas.json |
| Recaudación DW 2023/2024/2025 | 8.035.694,25 / 9.989.730,09 / 12.570.961,91 | ols_hw_proyecciones.json |
| OLS mensual N=36 | pend. 13.911,94 Bs/mes, R² 0,5861; 2026-06 = 1.176.830 [902.152; 1.451.508] | ols_hw_proyecciones.json |
| OLS vs ejecutado 2026 ene-abr | MAPE 16,0 % | ols_hw_proyecciones.json |
| Holt-Winters (DW) | α 0,6358, β 0, γ 0,1918, RMSE 65,85, AIC 308,37, MAPE hold-out 10,27 % | ols_hw_proyecciones.json |
| pytest | 444 passed, 0 failed, 11 skipped, 7 xfailed | pytest_completo_sin_env.txt |
