# Ronda 7 — grupos no aprobables, stock histórico, cronometraje (cifras de ejecuciones reales)

## Tabla única de cifras
| Cifra | Antes (ronda 6) | Después | Evidencia |
|---|---|---|---|
| Casos / grupos HITL del ciclo completo | 252 / 38 | 188 / 37 | grupos_hitl_final_*.json, cronometraje_aprobaciones.json |
| Grupos aprobables en bloque | 36 de 38 (94,7 %; 2 caso por caso = 47 casos) | 37 de 37 (100 %) | idem |
| Tiempo de máquina del ciclo completo | 59,1 s ± 0,7 (3 corridas) | 65,8 s (una corrida en modo cronometraje; la corrida previa de esta ronda, antes de la última corrección de la tarea 1, dio 63,3 s) | cronometraje_ciclo.json |
| Aprobaciones, máquina | ~1 s por ciclo | 1,55 s en total (37 acciones) | cronometraje_aprobaciones.json, cronometraje_servidor.jsonl |
| Tiempo humano (SIMULADO) | — | 296 s: 37 grupos × (6 s de lectura + 2 s de acción) | cronometraje_aprobaciones.json |
| Total ciclo + revisión (máquina real + humano simulado) | — | ≈ 6,1 min (65,8 + 296 s), dentro de 15 min | idem |
| Staging pendiente del DW real | 23.121 | 1.044 | stock_reglas_nuevas_dw_real.json |
| — CI_NOMBRE_DISCORDANTE | 20.707 | 756 | idem |
| — BAJA_CONFIANZA_IA | 1.844 | 288 | idem |
| — HOMONIMIA | 570 | 0 | idem |
| Hechos académicos en revisión (DW real) | 3.678 | 559 | idem |
| Hechos financieros en revisión | 16 | 3 | idem |
| Remanente de la bandeja en grupos | — | 1.606 casos en 786 grupos (725 grupos de CI con nombre realmente distinto, 56 de líneas de planificación, 5 de hechos) | remanente_stock_grupos.json |
| pytest | 451 passed | 452 passed, 0 failed, 11 skipped, 7 xfailed | pytest_por_suite_y_cobertura.json |
| Cobertura global | 60,0 % | 59,7 % (7.907 de 13.243 líneas) | idem |

## 1. Grupos no aprobables
a) **Hecho ARCA sin nota: se carga con nota NULL y su estado de origen** cuando el estado es válido (`sin_nota_por_acta`); solo va a revisión si falta la fecha o el estado/combinación no es válido. Decisión según el KPI académico (`kpi_service`): el promedio usa `AVG(nota_final)`, que ignora los NULL; la tasa de aprobación divide por todos los hechos, y con 22.618 hechos y 21.800 con nota da 82,46 % frente a 85,55 % si solo se contaran los calificados (aprobación ≥ 70). Se prefirió conservar el estado (Deserción, Reprobado, Aprobado sin notas de módulo) que descartar el hecho; la diferencia de 3,1 puntos en la tasa queda sin tocar porque cambiar el denominador es un cambio de definición del KPI, que no estaba pedido.
b) **Estado fuera de catálogo / combinación no admitida: acción de grupo "mapear a estado canónico"** (`POST /dataops/review-tray/approve-group` con `accion = MAPEAR_ESTADO`): una combinación (p. ej. Aprobado, Tutoria, Titulado: 18 casos del ciclo, 498 en el stock) se agrega a `cat_combinacion_estado`; un estado desconocido se reescribe a `canonico` o se agrega a `cat_estado_*`; luego se invalida la caché del catálogo y se aprueba el grupo. Una cuarta acción, `CORREGIR_FECHA` (mes y gestión para todo el grupo), cubre los hechos a los que solo les falta la fecha (1 hecho de cobranza en el ciclo).
Los grupos del ciclo: 37 de 37 resolubles en bloque. Ojo: la tasa de 100 % incluye aprobar en bloque los grupos de líneas de planificación y de la hoja Gestiones (`BAJA_CONFIANZA_IA`, la mayoría de los 37); su "aprobación" es una decisión sobre filas sin hecho aplicable, no una carga.

## 2. Stock histórico (respaldo previo: base `giragroup_db_respaldo_r7` y volcado 26,7 MB fuera del repo)
Reglas aplicadas a 23.121 casos de staging y 3.694 hechos en revisión del DW real (`scripts/stock_reglas_nuevas.py`, 37,6 s): CI_NOMBRE_VARIANTE 19.953 (incluye CI con marcador 'Estudiante CI …' en cualquiera de los dos lados; se renombran los marcadores de dim_estudiante), HOMONIMIA → no es persona 570, líneas sin hecho posible o encabezados genéricos 1.400, líneas que las reglas resuelven y se cargan 156 (+143 hechos académicos, +2 estudiantes), 3.208 hechos académicos y 13 financieros liberados (estudiante, módulo, fecha, estado y combinación válidos). Se quedan: 498 hechos por combinación de estado, 61 por falta de estudiante/módulo/fecha. El mismo script sobre un clon dio cifras idénticas (`stock_reglas_nuevas_clon.json`). Cambios de contenido del DW real: los anteriores; resoluciones marcadas `RESUELTO_VARIANTE`, `DESCARTADO_REGLA`, `RESUELTO_REGLAS` en `stg_entidad_no_resuelta` y registros agregados en `log_inconsistencias`.
Los 756 CI_NOMBRE_DISCORDANTE que quedan son conflictos de nombre reales (CI exacta con un nombre distinto y sin marcador); 725 CI distintas, no se pueden aprobar en bloque con sentido.

## 3. Modo cronometraje (`scripts/cronometraje_ciclo.sh`)
Restaura un clon de `giragroup_db`, ejecuta el ciclo completo, filtra la bandeja a los documentos del ciclo (`GET /dataops/review-tray/grupos?doc_desde=`), simula al usuario (`scripts/simular_revision.py`) e imprime el tiempo de máquina y el número de grupos. Con `CRONOMETRAJE_LOG=<archivo>` el servidor escribe una línea JSON con inicio y fin de cada `approve-group` y de cada resolución individual (middleware), así que una revisión hecha desde la UI queda registrada igual. El tiempo humano de este informe es simulado (reloj virtual, sin esperar): 6 s de lectura y 2 s de acción por grupo, 20 s por caso manual (no hubo). Es un supuesto, no una medición de una persona.

## 4. Suites por carpeta (`pytest_por_suite_y_cobertura.json`, código final)
| Suite | Pruebas | Pasadas | Omitidas | xfail | Fallidas |
|---|---|---|---|---|---|
| sprint1 | 16 | 16 | 0 | 0 | 0 |
| sprint2 | 32 | 32 | 0 | 0 | 0 |
| sprint3 | 120 | 120 | 0 | 0 | 0 |
| sprint4 | 23 | 23 | 0 | 0 | 0 |
| loops | 9 | 9 | 0 | 0 | 0 |
| readiness | 39 | 21 | 11 | 7 | 0 |
| transversales | 231 | 231 | 0 | 0 | 0 |
Cobertura de líneas (archivos clave): dw_loader 44,1 %; pipeline (router) 35,7 %; bandeja_grupos 20,8 %; revision_hechos 88,1 %; confianza_service 56,3 %; indice_confianza 32,9 %; extraccion_por_encabezado 81,2 %; person_resolver 92,8 %; fk_resolver 87,6 %; dataops 42,6 %; kpi_service 67,6 %. Las dos de más riesgo sin cubrir son `bandeja_grupos` y `dw_loader`.

## Límites
- La revisión humana es simulada; la cifra de ≈ 6,1 min usa los tiempos supuestos de arriba.
- El tiempo de máquina de esta corrida (65,8 s) es una corrida; las 3 corridas de la ronda 6 dieron 59,1 s ± 0,7 con el código anterior.
- Los casos HITL del ciclo (188) no incluyen el remanente del stock (1.606).
- `nivel_confianza_ia` sigue nulo en las líneas resueltas por reglas sin índice en caché.
