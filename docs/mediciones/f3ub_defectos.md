# F3U-B — defectos y observaciones de cobertura

## Resultado del cuadre

Evidencia: [f3ub_cobertura_por_hoja.json](f3ub_cobertura_por_hoja.json), [CSV por archivo y hoja](f3ub_cobertura_por_hoja.csv), [totales](f3ub_reproducibilidad.json), [rangos por hecho](f3ub_fechas_por_hecho.json).

Se analizaron los 10 documentos con `scripts/f3s_cobertura_por_archivo.py`; dos corridas idénticas dieron MD5 `07ef88fb2452794d2534889c1aea07d2`. Las filas leídas se clasificaron todas: 90.508 con registros, 4.638 en bandeja, 21.411 con motivo de ruido y 0 `sin_explicar`. Esto satisface la clasificación de las líneas leídas; **no** demuestra que el total de filas de origen cuadre en cada archivo.

El campo `balance_ok` del script verifica `leidas = con_registros + bandeja + ruido + sin_explicar`. No verifica el balance de origen que el plan solicita. La salida del script tampoco desglosa hechos, staging, logs ni fechas por hoja; hechos y log están agregados por documento, y los rangos de fechas aquí se consultaron por tabla completa. Esas limitaciones quedan abiertas y no se presentan como criterio satisfecho.

## Diferencias origen vs. lectura

`origen_slice` aplica el inventario de celdas con dos datos, menos cabecera; `leidas` cuenta líneas del staging. Los siguientes deltas no tienen una explicación demostrada por el script y quedan como `requiere_revision`, sin crear IDs D-U duplicados:

| Archivo | Origen | Leídas | SUBTOTAL | Delta origen - leídas - subtotal | Estado |
|---|---:|---:|---:|---:|---|
| TBL_INSCRITOS.xlsx | 15.196 | 15.196 | 2 | -2 | requiere_revision |
| BD Cobranzas.xlsx | 15.964 | 16.034 | 0 | -70 | requiere_revision |
| PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx | 6.768 | 8.216 | 0 | -1.448 | requiere_revision |
| [BBDD] ANTIGUO RESPUESTAS EVALUACIÓN DOCENTE - EXP. UNIFRANZ POSTGRADO.xlsx | 19.062 | 19.119 | 266 | -323 | requiere_revision |
| Evaluación Docente y Unifranz.xlsx | 3.813 | 27.189 | 356 | -23.732 | requiere_revision |
| Experiencia Docente 2.0.xlsx | 16.629 | 17.695 | 409 | -1.475 | requiere_revision |
| Base centralizada Académica ARCA (1).xlsx | 11.454 | 11.456 | 0 | -2 | requiere_revision |

BD Techos, EJECUTADO VS META y BD Egresos tienen delta cero. La diferencia entre filas Excel y líneas exportadas puede deberse a la expansión a texto del extractor o al criterio de origen; no se atribuye a una causa sin evidencia.

## Reglas esperadas frente a hechos persistidos

El script calcula registros esperados por documento y los compara con tablas que puede atribuir por `id_documento`. Diferencias sin causa comprobada quedan `requiere_revision`; `fact_marketing` no tiene `id_documento` y el script sustituye el conteo por `carga_fila_origen`, cuyo resultado no es comparable directamente con el esperado. El `SELECT` de `carga_fila_origen` agrupado por documento/tabla mostró 30.366 filas todas bajo `id_documento=1` y `tabla=fact_marketing`; se registra como `requiere_revision`, sin atribuirlas a un libro sin trazabilidad fiable. No interpretar esta tabla como cuadre por hoja.

| Documento | Esperado por regla | Persistido atribuible | Estado |
|---|---|---|---|
| TBL_INSCRITOS.xlsx | fact_marketing 15.191 | El script reporta 30.366 en `carga_fila_origen`, no filas de `fact_marketing` atribuibles | requiere_revision |
| BD Cobranzas.xlsx | fact_situacion_financiera 15.472 | 10.719 | requiere_revision |
| BD Techos.xlsx | fact_techo_convenio 207 | 206 | D-T1, duplicado consolidado según evidencia previa |
| EJECUTADO VS META.xlsx | fact_rentabilidad 95 | 95 | coincide |
| BD Egresos.xlsx | fact_costo_programa 1.373; fact_rentabilidad 72 | fact_costo_programa 1.371; no se atribuyen hechos rentabilidad | requiere_revision |
| PLANIFICACION Y EJECUCION ACADÉMICA (INICIOS Y OKR`S).xlsx | 0; todas las filas clasificadas como ruido | 0 | coincide con regla de descarte observada; razón agregada, sin dato fuente útil |
| [BBDD] ANTIGUO RESPUESTAS EVALUACIÓN DOCENTE - EXP. UNIFRANZ POSTGRADO.xlsx | fact_evaluacion_docente 206.729 | 197.876 | requiere_revision |
| Evaluación Docente y Unifranz.xlsx | fact_evaluacion_docente 46.792 | 14.173 | requiere_revision |
| Experiencia Docente 2.0.xlsx | fact_evaluacion_docente 503.168 | 503.168 | coincide; D-A4 no se reproduce como pérdida en esta corrida |
| Base centralizada Académica ARCA (1).xlsx | académico 30.226 | rendimiento 25.108 + bridge docente 1.690 = 26.798 | requiere_revision |

Las cifras esperadas son la evaluación de reglas línea a línea del script existente, no un contrato contable; antes de asignar causa se necesita confirmar el grano y la aplicabilidad por documento/hoja.
## Defectos conocidos: vínculo y estado observado

- **D-A2 — `fact_cobranzas_proyectadas`**: la tabla sigue en 0 filas. No se duplica como D-U. Véase [CIERRE_F3R_A.md](../cierres/CIERRE_F3R_A.md) y conteo final en [f3ub_completo.json](f3ub_completo.json).
- **D-A4 — enrutamiento de Experiencia Docente 2.0**: no se reproduce como pérdida en esta corrida: `fact_evaluacion_docente` tiene 503.168 filas atribuibles al documento y el cálculo de reglas también espera 503.168. Se conserva el enlace histórico a [CIERRE_F3R_A.md](../cierres/CIERRE_F3R_A.md); revisar la diferencia de conteo origen/lectura de arriba.
- **D-A4b — cabecera de baja confianza**: conservar el hallazgo previo de 18 filas de `TBL EXPERIENCIA UNIFRANZ`; esta corrida no vuelve a probar ese criterio de cabecera. Referencia: [CIERRE_F3R_A.md](../cierres/CIERRE_F3R_A.md).
- **D-A5 — rango de `dim_tiempo`**: persiste; la dimensión va de 2005-02-05 a 2034-01-12, con 39 fechas fuera de 2022–2027. El rango de hechos aparece en [f3ub_fechas_por_hecho.json](f3ub_fechas_por_hecho.json). Referencia: [CIERRE_F3R_A.md](../cierres/CIERRE_F3R_A.md).
- **D-A8a — filas agregadas de EJECUTADO VS META**: en esta corrida se esperan y hay 95 `fact_rentabilidad`; no se reproduce la pérdida observada anteriormente. Referencias: [cobertura](f3ub_cobertura_por_hoja.json), [CIERRE_F3R_A.md](../cierres/CIERRE_F3R_A.md).
- **D-A9 — truncado de `carga_fila_origen`**: no se cambia el script de limpieza. En esta preparación se verificó `dw_vacio` vacío, incluso `carga_fila_origen=0`; el hallazgo histórico no bloqueó el clon nuevo. Referencias: [f3ub_preparacion.json](f3ub_preparacion.json), [CIERRE_F3R_A.md](../cierres/CIERRE_F3R_A.md).
- **D-T1 — Techos**: la entrada produjo 207 líneas y 206 hechos `fact_techo_convenio`, igual al comportamiento ya documentado de deduplicación. No se crea un defecto nuevo. Véase [CIERRE_F3T.md](../cierres/CIERRE_F3T.md).

## Decisión operativa

Hay 0 filas `sin_explicar`; no se requieren ejemplos de 10 filas. Los siete deltas origen/lectura quedan `requiere_revision` hasta cotejar el parser con las hojas del Excel. No se crea ningún D-U# duplicado. El script no fue modificado.


