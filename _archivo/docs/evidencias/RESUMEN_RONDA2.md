# Ronda 2 — rama `ablacion-beto-personas` (cifras de ejecuciones reales; un commit por tarea)

| # | Tarea | Estado | Resultado |
|---|-------|--------|-----------|
| 1 | Personas nuevas en estado C | Hecho | lote 1.387: directo 42,32 % -> **83,06 %**, HITL 57,68 % -> **16,94 %**, staging 0 % -> 0 % |
| 2 | Filtro de correos | Hecho | 139 entidades (139 registros) ya no pasan por la resolución de personas; ningún registro cambia de banda |
| 3 | Idempotencia | Hecho | TBL_INSCRITOS dos veces: 8.946 filas / 15.196 inscritos / 15.196 claves, idénticas |
| 4 | 141 inscritos perdidos | Hecho (causa distinta a la supuesta) | ahora 15.196 de 15.196; 43/43 meses iguales a `inscritos.csv` |
| 5 | deuda_total negativa | Hecho: es dato real | 629 filas con sobrepago en la fuente; no es defecto de signo |
| 6 | Carga masiva | Parcial | los inserts no eran el cuello de botella; se corrigió el real. Ciclo 554,4 s -> **230,2 s** |
| 7 | Holt-Winters desde el DW | Hecho | MAPE hold-out 10,27 % con DW y con CSV (idénticos) |
| 8 | BETO, una cifra | Hecho | directo A 1.380 (99,50 %), B 1.382 (99,64 %), diferencia +2 |
| 9 | ANTIGUO RESPUESTAS | Hecho | no se cuelga: es volumen (≈19.100 filas × BETO) |
| 10 | pytest | Hecho | **441 passed, 0 failed, 11 skipped, 7 xfailed** (sin DATABASE_URL ni PYTHONIOENCODING) |

## 1. Estado C (`dim_estudiante.fk_estado`, `dim_docente.fk_estado`; schema.sql, modelos y ALTER de arranque)
Personas del lote tras el filtro de correos: 3.587 = 2.378 CI exacta (A) + 127 fuzzy (B) + 717 nuevas (C: 63 estudiantes, 654 docentes) + 365 HITL.
HITL de personas: 240 docentes y 122 estudiantes con un solo token ("CACERES", "CUELLAR": no identifican a nadie, no se crea miembro) + 3 empates entre estudiantes. Es una desviación explícita de la regla "sin candidatos => crear": los nombres de un solo token no se crean.
En el loader (`dw_loader.py`): estudiante nuevo sin CI se crea con `id_temporal` (clave sustituta) y `fk_estado='C'`; docente nuevo con `fk_estado='C'`. El hecho carga directo si la confianza ≥ 0,85 (el loader ya devolvía "B" para ese caso). El lote es una simulación de solo lectura: no crea esos miembros.
Antes/después: previa 0,85 con contexto duro 41,38 % directo; ronda 1 (escalonada) 42,32 %; ronda 2 83,06 %.

## 2. Correos
`person_resolver.es_correo` (regex) devuelve motivo `correo` antes de CI/fuzzy; `resolver_o_crear_estudiante` descarta un correo como nombre. Test nuevo. Lote: 139 entidades; personas 3.726 -> 3.587; bandas sin cambio (1.152 / 235 / 0).

## 3. Idempotencia
Tabla `carga_fila_origen(clave PK = sha256(hash del archivo | hoja | fila | contenido), id_documento, tabla)`; el alta es `INSERT … ON CONFLICT DO NOTHING` en la misma transacción. Se aplica a las cargas acumulativas (fact_marketing); el resto de hechos ya eran upserts por clave natural (rendimiento, financiero, rentabilidad, evaluación con `clave_respuesta`). Evidencia: `idempotencia_tbl_inscritos.txt`.

## 4. Inscritos perdidos (`inscritos_perdidos_causa.txt`)
No era "POS fuera de dim_modulo": en la fila serializada se pierde la etiqueta de "NOMBRE DEL PROGRAMA" cuando el valor trae ':' y el módulo no se creaba sin nombre. Códigos POS (inscritos): POS-4527: 52, POS-4772: 41, POS-4907: 26, POS-4629: 16, POS-4921: 3, POS-4153: 1, POS-6254: 1, POS-5361: 1 (esta última por MARCA TEMPORAL con milisegundos). Fix: el código POS basta; lo que aún no se pueda cargar va a `stg_entidad_no_resuelta` con `POS_NO_EN_DIM_MODULO` o `FECHA_INSCRIPCION_INVALIDA` (hoy 0 filas).

## 5. deuda_total (`deuda_total_negativa_causa.txt`, `deuda_total_negativa_filas.csv`)
BD Cobranzas.xlsx, hoja COBRANZAS 2024 2025, columna DEUDA TOTAL: 629 filas < 0 (mínimo -2.900; suma -38.276,07); en las 629 `TOTAL PAGADO > MONTO A COBRAR` y `DEUDA TOTAL = COBRAR - PAGADO`. Saldo a favor real. DW: 627 filas. `risk_service` expresa `deuda_total` como `max(0, suma)`.

## 6. Tiempos (clon del DW, CPU, contenedor sin GPU; `tiempos_ciclo_mensual.json`)
| | Ronda 1 | Ronda 2 |
|---|---|---|
| Total | 554,4 s | **230,2 s** |
| lectura/ingesta | 2,4 s | 3,7 s |
| reglas y resto | 30,1 s | 39,4 s |
| BETO | 7,6 s | 92,2 s |
| carga DW | 514,1 s | 94,7 s |

La ronda 2 incluye dos archivos que la 1 no medía (Evaluación Docente y Unifranz, y ANTIGUO RESPUESTAS; hojas sin fecha: primeras 300 filas), por eso BETO sube. Por archivo (s): Cobranzas 43,2; Egresos 5,0; Techos 3,6; ARCA 7,1; Ejecutado vs Meta 4,1; Evaluación Docente y Unifranz 58,5 (BETO 26,5; carga 27,2); Experiencia Docente 10,6; PLANIFICACION 477 -> 25,6; TBL_INSCRITOS 5,1; ANTIGUO 67,4 (BETO 58,0).
Causa real del cuello: `resolver_o_crear_estudiante` cargaba toda `dim_estudiante` por ORM y llamaba a RapidFuzz una vez por estudiante en cada fila (29,6 de 35,7 s en 150 cargas). Ahora lista en caché y búsqueda vectorizada: 150 cargas 35,7 s -> 6,7 s. No se implementó `executemany/COPY`: el insert no era el costo. Pendiente: Cobranzas sigue en 38,3 s de carga para 746 filas (51 ms/fila), sin perfilar.

## 7. Holt-Winters (`holtwinters_dw_vs_csv.json`)
Misma ventana (N=33, 2023-09 a 2026-05, hold-out 6, mismos parámetros que `scripts/hw.py`): RMSE 53,38; MAPE 10,27 %; AIC 308,37 con la serie de `fact_marketing` y con `inscritos.csv`; las series coinciden mes a mes. El 10,3 % reportado se reproduce.

## 8. BETO (lote 1.387, arquitectura final; `beto_cifra_unica.json`)
Directo con A: 1.380 (99,50 %). Con B: 1.382 (99,64 %). Diferencia: +2. Rescatados por BETO (A no resuelve): 7. Registros directos con entidades BETO: 1.239 (3.248 entidades); de ellos 247 tienen alguna entidad BETO cuyo valor coincide con una celda de dim_estudiante/dim_docente/dim_modulo. Nota: la corrida previa de `ablacion_beto.json` daba A 1.382 / B 1.385; esta ejecución da 1.380 / 1.382.

## 9. ANTIGUO RESPUESTAS (`antiguo_respuestas_columnas.txt`)
No es un cuelgue: hojas de 16.454 + 2.538 + 130 filas ≈ 19.100 líneas. Medido sobre 883 líneas: BETO 58,0 s (66 ms/línea) y 3.705 hechos (4,2 por línea); extrapolado a las 19.100 líneas: ≈ 1.250 s solo de BETO y ≈ 80 mil hechos, o sea más que el timeout de 900 s del cliente (la extrapolación es cuenta, no medición).
Texto libre (filas no vacías): TBL EVALUACION DOCENTE — "8. ¿Qué aspectos del estilo de enseñanza…" 16.195; "4. ¿Qué otro contenido… le gustaría explorar" 13.957; columna sin nombre (Unnamed: 19) 131. TBL EXPERIENCIA UNIFRANZ — "5. ¿Qué sugerencias… experiencia del curso" 2.525; "4. ¿Qué sugerencia… personal administrativo" 2.443. Hoja Análisis de Evaluación — Unnamed: 7 con 129.

## Qué capturar para la tesis
`lote_1387_uploads_data_arquitectura_b.json` (`personas`, `personas_por_fk_estado`, `correos_filtrados_como_no_nombre`, bandas), `tiempos_ciclo_mensual.json`, `holtwinters_dw_vs_csv.json`, `beto_cifra_unica.json`, `idempotencia_tbl_inscritos.txt`, `inscritos_perdidos_causa.txt`, `deuda_total_negativa_*`, `antiguo_respuestas_columnas.txt`, `pytest_completo_sin_env.txt`. Comparativos: `lote_1387_..._ronda1_escalonada.json`, `..._ronda2_estado_C_sin_filtro_correos.json`.
