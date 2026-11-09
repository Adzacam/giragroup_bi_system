# Ronda 8 — catálogo, fk_estado, pruebas de la bandeja, medición final (cifras de ejecuciones reales)

## Tabla única de cifras
| Cifra | Antes (ronda 7) | Después | Evidencia |
|---|---|---|---|
| Tablas de giragroup_catalog_db | 21 (con cat_docente: 735 filas) | 20 (sin cat_docente) | catalogo_tablas_filas.txt |
| Cobertura de bandeja_grupos | 20,8 % | 95,3 % (11 pruebas nuevas) | pytest_por_suite_y_cobertura.json |
| Tiempo total del ciclo (10 archivos, sin recorte) | 65,8 s (1 corrida) | 60,0 s ± 0,8 (3 corridas: 60,84 / 59,24 / 59,92) | ciclo_r8_{1,2,3}.json, ciclo_r8_resumen.json |
| Por etapa (media ± DE, s) | — | lectura 5,17 ± 0,06; reglas 5,43 ± 0,06; BETO 5,40 ± 0,20; carga DW 43,97 ± 0,87 | ciclo_r8_resumen.json (por archivo también) |
| Casos / grupos HITL del ciclo | 188 / 37 | 188 / 37 en las 3 corridas, mismos grupos; 37 aprobables en bloque | revision_r8_*.json, tiempo_klm.json |
| Aprobaciones, máquina | 1,55 s | 2,25 / 1,42 / 1,45 s | revision_r8_*.json |
| Tiempo humano (SIMULADO) | 296 s | 296 s (37 × 8 s); no medido con una persona | idem |
| Tasa de aprobación, todos los hechos (22.618) | 82,46 % | 82,46 % (18.650 aprobados) | tasa_aprobacion_dw_real.txt |
| Tasa de aprobación, solo hechos con nota (21.800) | 85,55 % | 85,55 % | idem |
| pytest | 452 passed | 463 passed, 0 failed, 11 skipped, 7 xfailed | pytest_junit.xml |
| Cobertura global | 59,7 % | 60,7 % (8.040 de 13.243 líneas) | cobertura.json |

## 1. cat_docente en giragroup_catalog_db
Existía (735 filas; no hay tabla de alias de docente). Ningún código la leía: las personas se resuelven contra dim_docente. Eliminada con `db/migrations_catalogo/001_eliminar_cat_docente.sql` (respaldo previo con pg_dump fuera del repo). Se quitaron su DDL (`schema_catalogos.sql`), sus 735 INSERT del seed y del generador, los modelos de audit/notifications y las aserciones de volumen de docentes (cambio de requisito). Tablas finales y filas: `catalogo_tablas_filas.txt` (20 tablas; cat_modulo 1.747, cat_programa 1.229, cat_convenio_programa 195, cat_mapeo_columna 159, ref_metas_gestion 59 …). Nota: `backend/tests_root/sprint3/test_catalogos_db.py::test_categorias_financieras_sembradas` falla igual antes del cambio (ruta de semilla distinta); esa carpeta no es la suite oficial.

## 2. fk_estado
En el código, `resolver_o_crear_estudiante` devuelve C solo con id None (derivado a staging). Ningún hecho persistido tenía C (DW real: hechos A/B únicamente) y la condición `requiere_revision or fk_estado == "C"` era inalcanzable. Mientras tanto dim_* creaba "miembro nuevo" con C y el hecho recibía B. Unificado: **A** = CI exacta; **B** = vinculado sin CI exacta (fuzzy o miembro nuevo TEMP); **C** = sin vincular, solo en `stg_entidad_no_resuelta`. Cambios: dim_estudiante/dim_docente crean miembros nuevos como B, condición muerta retirada, comentarios de modelos y DDL. Contenido del DW real: 411 `dim_estudiante` TEMP-hash pasaron de A a B (`scripts/reparar_fk_estado_temp.sql`, respaldo previo de la tabla). `dim_docente` (638, todos A) no se tocó: no se puede distinguir cuáles se crearon sin candidato.

## 3. Pruebas de bandeja_grupos
`tests/test_bandeja_grupos.py`: agrupación (casos, grupos, alcance por documentos), motivo de estado, ids del grupo, approve-group con APROBAR, rechazo de grupos con campos faltantes, CORREGIR_FECHA (académico y financiero), MAPEAR_ESTADO (combinación, reescritura a canónico, alta en catálogo, grupo OK) y delegación de staging. 11 pruebas; cobertura 95,3 %.

## 4. Medición final
3 corridas, clon restaurado cada vez, código final. `tiempo_klm.json` lleva el detalle de los 37 grupos (n_casos, acción); los tiempos humanos para el KLM no se miden aquí.

## 5. Tasa de aprobación
La definición del KPI (aprobados ≥ 70 / todos los hechos) da 82,46 %; sobre los hechos con nota, 85,55 %. La diferencia corresponde a los 818 hechos sin nota (actas sin notas con estado de origen). El KPI no se modificó.

## Límites
- Tiempo humano simulado. Suites: sprint1 16, sprint2 32, sprint3 120, sprint4 23, loops 9, readiness 39 (21 pasadas, 11 omitidas, 7 xfail), transversales 242; 0 fallidas.
- Quedan sin commit `scripts/diccionario_datos_csv.py`, `docs/evidencias/diccionario_datos.csv` y `diccionario_datos.csv` (raíz): cambios de una ronda anterior, no revisados en esta.
